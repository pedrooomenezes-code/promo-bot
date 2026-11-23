"""Roda uma rodada do bot: consulta preços, decide e agenda os posts.

Uso:  python -m bot            (usa o modo definido em config.json)
      python -m bot --teste    (só mostra o que faria, não agenda nada)
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import ml, regras, textos

TZ = ZoneInfo("America/Sao_Paulo")


def ler_produtos(caminho="produtos.csv"):
    with open(caminho, newline="", encoding="utf-8") as f:
        linhas = [l for l in f if l.strip() and not l.lstrip().startswith("#")]
    for row in csv.DictReader(linhas):
        if (row.get("ativo") or "sim").strip().lower() in ("nao", "não", "n", "0"):
            continue
        if not row.get("link_produto") or not row.get("link_afiliado"):
            continue
        alvo = (row.get("preco_alvo") or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
        row["preco_alvo"] = float(alvo) if alvo else None
        yield row


def main():
    teste = "--teste" in sys.argv
    with open("config.json") as f:
        cfg = json.load(f)
    modo = "teste" if teste else cfg["modo"]  # teste | rascunho | agendar
    agora = datetime.now(TZ)

    hist = regras.carregar(regras.ARQ_HIST)
    postados = regras.carregar(regras.ARQ_POST)
    token = ml.token_do_ambiente()
    integracao = os.environ.get("POSTIZ_X_ID")
    if modo != "teste" and not integracao:
        sys.exit("Falta POSTIZ_X_ID (id do X no Postiz). Rode com --teste ou configure o secret.")

    ultimo_modelo = None
    agendou = 0
    for row in ler_produtos():
        try:
            prod = ml.consultar(row["link_produto"], token)
        except ml.ErroML as e:
            print(f"! {e}")
            continue
        if not prod:
            print(f"- indisponível: {row['link_produto']}")
            continue

        decisao = regras.avaliar(prod, hist.get(prod["id"], {}), cfg, agora, row["preco_alvo"])
        regras.registrar_preco(hist, prod["id"], prod["preco"], agora)
        rotulo = f"{textos.encurtar(prod['titulo'], 50)} R$ {textos.brl(prod['preco'])}"
        if not decisao:
            print(f"· sem promoção: {rotulo}")
            continue
        if not regras.pode_repostar(postados, prod["id"], prod["preco"], cfg, agora):
            print(f"· já postado recentemente: {rotulo}")
            continue
        quando = regras.proximo_horario(postados, cfg, agora)
        if not quando:
            print(f"· limite/janela do dia atingido, fica pra próxima: {rotulo}")
            continue

        texto, ultimo_modelo = textos.montar(prod, decisao, row["link_afiliado"].strip(),
                                             row.get("categoria", ""), ultimo_modelo)
        print(f"\n✔ {decisao['motivo'].upper()} às {quando:%H:%M} ({textos.tamanho_x(texto)}/280)\n{texto}\n")

        if modo != "teste":
            from . import postiz
            foto = None
            try:
                foto = postiz.subir_foto(prod["foto"])
            except Exception as e:  # post sem foto é melhor que post nenhum
                print(f"! foto não enviada: {e}")
            postiz.agendar(texto, quando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           integracao, foto, rascunho=(modo == "rascunho"))
        postados[prod["id"]] = {"quando": agora.isoformat(), "agendado": quando.isoformat(),
                                "preco": prod["preco"], "titulo": prod["titulo"]}
        agendou += 1
        time.sleep(1)

    if modo != "teste":
        regras.salvar(regras.ARQ_HIST, hist)
        regras.salvar(regras.ARQ_POST, postados)
    print(f"\nFim. {agendou} post(s) {'simulados' if modo == 'teste' else modo}.")


if __name__ == "__main__":
    main()
