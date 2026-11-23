"""Textos dos posts. Vários modelos para não repetir a mesma frase."""
import random
import re


def brl(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s[:-3] if s.endswith(",00") else s


def encurtar(titulo, n=70):
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo if len(titulo) <= n else titulo[: n - 1].rsplit(" ", 1)[0] + "…"


# Cada modelo recebe: p (produto), por, de, off, extra, link, motivo
COM_DE = [
    "🔥 {p}\n\nDe R$ {de} por R$ {por} ({off}% OFF){extra}\n\n🔗 {link}",
    "CORRE que baixou ⚡\n\n{p} por R$ {por}\n(era R$ {de}){extra}\n\n{link}",
    "Pra quem tava esperando baixar: baixou.\n\n{p}\nR$ {por} ({off}% OFF){extra}\n\n{link}",
    "Achadinho {cat}\n\n{p}\nDe R$ {de} por R$ {por}{extra}\n\n{link}",
    "Relâmpago ⏱️ pode acabar a qualquer momento\n\n{p}\nR$ {por} ({off}% OFF){extra}\n\n{link}",
]
# Sem preço original no anúncio: fala do histórico, sem inventar "De R$".
SEM_DE = [
    "Menor preço que eu vi nesse aqui 👀\n\n{p}\n💸 R$ {por}{extra}\n\n{link}",
    "Baixou {off}% em relação ao preço normal dos últimos dias 📉\n\n{p}\nR$ {por}{extra}\n\n{link}",
    "Tava de olho nesse? Caiu.\n\n{p}\nAgora R$ {por}{extra}\n\n{link}",
    "Bom preço detectado 🔌\n\n{p}\nR$ {por}{extra}\n\n{link}",
]
SO_PRECO = [
    "Chegou no preço 🎯\n\n{p}\nR$ {por}{extra}\n\n{link}",
    "Bom preço detectado 🔌\n\n{p}\nR$ {por}{extra}\n\n{link}",
]


def montar(prod, decisao, link, categoria="", ultimo_modelo=None):
    if decisao.get("de"):
        modelos = COM_DE
    elif decisao.get("off"):
        # "Menor preço que eu vi" só quando é de fato o menor do histórico.
        modelos = SEM_DE if decisao.get("motivo") == "minimo" else SEM_DE[1:]
    else:
        modelos = SO_PRECO
    opcoes = [m for m in modelos if m != ultimo_modelo] or modelos
    modelo = random.choice(opcoes)

    extras = []
    if prod.get("full"):
        extras.append("⚡ Full, chega rapidinho")
    elif prod.get("frete_gratis"):
        extras.append("🚚 Frete grátis")
    extra = ("\n" + "\n".join(extras)) if extras else ""
    cat = {"casa": "pra casa 🏠", "tech": "tech 💻"}.get(categoria.strip().lower(), "do dia 🔎")

    texto = modelo.format(
        p=encurtar(prod["titulo"]), por=brl(prod["preco"]),
        de=brl(decisao["de"]) if decisao.get("de") else "",
        off=decisao.get("off") or "", extra=extra, link=link, cat=cat,
    )
    return texto, modelo


def tamanho_x(texto):
    """Contagem aproximada do X: link = 23, emoji = 2."""
    n = 0
    sem_links = re.sub(r"https?://\S+", lambda m: "", texto)
    n += 23 * len(re.findall(r"https?://\S+", texto))
    for ch in sem_links:
        c = ord(ch)
        if c in (0xFE0F, 0x200D):
            continue
        n += 2 if (c >= 0x1F000 or 0x2600 <= c <= 0x27BF or 0x2300 <= c <= 0x23FF) else 1
    return n
