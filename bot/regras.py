"""Histórico de preços e a decisão de 'isso é promoção de verdade?'."""
import json
import os
from datetime import datetime, timedelta
from statistics import median

ARQ_HIST = "data/historico.json"
ARQ_POST = "data/postados.json"


def carregar(caminho):
    if os.path.exists(caminho):
        with open(caminho) as f:
            return json.load(f)
    return {}


def salvar(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)


def registrar_preco(hist, pid, preco, agora, dias_guardar=60):
    """Guarda no máximo um preço por dia (o menor visto no dia)."""
    dia = agora.date().isoformat()
    serie = hist.setdefault(pid, {})
    serie[dia] = min(preco, serie.get(dia, preco))
    limite = (agora.date() - timedelta(days=dias_guardar)).isoformat()
    for d in [d for d in serie if d < limite]:
        del serie[d]


def avaliar(prod, hist_prod, cfg, agora, preco_alvo=None):
    """Decide se o preço atual merece post.

    Devolve None (não posta) ou um dict com o motivo e o preço de referência
    usado no texto. Só usa "De R$ X" quando o próprio anúncio informa o preço
    original, para não inventar desconto.
    """
    preco = prod["preco"]
    hoje = agora.date().isoformat()
    corte = (agora.date() - timedelta(days=cfg["janela_dias"])).isoformat()
    anteriores = [p for d, p in hist_prod.items() if corte <= d < hoje]

    # 1) Desconto informado pelo próprio anúncio
    orig = prod.get("preco_original")
    if orig and orig > preco:
        off = round((1 - preco / orig) * 100)
        # Se já temos histórico, o preço também precisa estar abaixo do normal,
        # pra evitar o "aumenta e dá desconto".
        if off >= cfg["desconto_minimo"] and (len(anteriores) < 3 or preco < median(anteriores)):
            return {"motivo": "desconto", "de": orig, "off": off}

    # 2) Queda real em relação ao histórico
    if len(anteriores) >= cfg["dias_minimos_historico"]:
        mediana = median(anteriores)
        queda = round((1 - preco / mediana) * 100)
        if queda >= cfg["queda_minima"]:
            return {"motivo": "queda", "de": None, "off": queda, "mediana": mediana}
        if preco < min(anteriores) and queda >= cfg["queda_minima"] / 2:
            return {"motivo": "minimo", "de": None, "off": queda}

    # 3) Preço-alvo definido por você na planilha
    if preco_alvo and preco <= preco_alvo:
        return {"motivo": "alvo", "de": orig if orig and orig > preco else None,
                "off": round((1 - preco / orig) * 100) if orig and orig > preco else None}
    return None


def pode_repostar(postados, pid, preco, cfg, agora):
    ult = postados.get(pid)
    if not ult:
        return True
    quando = datetime.fromisoformat(ult["quando"])
    if agora - quando >= timedelta(days=cfg["intervalo_repost_dias"]):
        return True
    # Dentro do intervalo, só reposta se caiu bem mais.
    return preco <= ult["preco"] * (1 - cfg["queda_para_repostar"] / 100)


def proximo_horario(postados, cfg, agora):
    """Escolhe o horário do próximo post respeitando intervalo, janela e limite diário.

    Devolve None se o limite do dia já foi atingido ou se não cabe mais hoje.
    """
    hoje = agora.date().isoformat()
    agendados_hoje = [datetime.fromisoformat(v["agendado"]) for v in postados.values()
                      if v.get("agendado", "").startswith(hoje)]
    if len(agendados_hoje) >= cfg["max_posts_dia"]:
        return None
    inicio = agora.replace(hour=cfg["hora_inicio"], minute=0, second=0, microsecond=0)
    fim = agora.replace(hour=cfg["hora_fim"], minute=0, second=0, microsecond=0)
    t = max(agora + timedelta(minutes=5), inicio)
    if agendados_hoje:
        t = max(t, max(agendados_hoje) + timedelta(minutes=cfg["intervalo_minutos"]))
    return t if t <= fim else None
