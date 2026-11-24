"""Leitura de preço e dados do produto na API do Mercado Livre."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.mercadolibre.com"
UA = "promo-bot/1.0"


class ErroML(Exception):
    pass


def _req(url, token=None, data=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode(errors="replace")[:300]
        raise ErroML(f"HTTP {e.code} em {url}: {detalhe}") from e


def renovar_token(client_id, client_secret, refresh_token):
    """Troca o refresh token por um access token novo.

    O Mercado Livre devolve um refresh token NOVO a cada renovação (o antigo
    deixa de valer). Ele é gravado em .ml_refresh_token_novo para o workflow
    atualizar o secret do GitHub.
    """
    r = _req(f"{API}/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    })
    novo = r.get("refresh_token")
    if novo and novo != refresh_token:
        with open(".ml_refresh_token_novo", "w") as f:
            f.write(novo)
    return r["access_token"]


def token_do_ambiente():
    cid, sec, ref = (os.environ.get(k) for k in ("ML_CLIENT_ID", "ML_CLIENT_SECRET", "ML_REFRESH_TOKEN"))
    if cid and sec and ref:
        return renovar_token(cid, sec, ref)
    return None


def identificar(link):
    """Devolve ('item', 'MLB123') ou ('produto', 'MLB123') a partir do link do anúncio."""
    link = urllib.parse.unquote(link)
    m = re.search(r"(?:item_id[:=]|wid=)\s*(MLB-?\d+)", link, re.I)
    if m:
        return "item", m.group(1).replace("-", "").upper()
    m = re.search(r"/p/(MLB\d+)", link, re.I)
    if m:
        return "produto", m.group(1).upper()
    m = re.search(r"(MLB)-?(\d{6,})", link, re.I)
    if m:
        return "item", f"MLB{m.group(2)}"
    raise ErroML(f"Não achei o código MLB no link: {link}")


NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def _reais(texto):
    """'Antes: 399 reais com 90 centavos' -> 399.9"""
    m = re.search(r"([\d.]+)\s*reais(?:\s*com\s*(\d+)\s*centavos)?", texto)
    if not m:
        return None
    return float(m.group(1).replace(".", "")) + (int(m.group(2)) / 100 if m.group(2) else 0)


def consultar_pagina(link):
    """Plano B sem app do Mercado Livre: lê preço, título e foto da página do anúncio."""
    _tipo, cod = identificar(link)
    req = urllib.request.Request(link, headers={
        "User-Agent": NAVEGADOR, "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise ErroML(f"HTTP {e.code} ao abrir a página {link}") from e

    produto = None
    for bloco in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            dado = json.loads(bloco)
        except ValueError:
            continue
        for d in (dado if isinstance(dado, list) else [dado]):
            if isinstance(d, dict) and d.get("@type") == "Product" and d.get("offers"):
                produto = d
                break
        if produto:
            break
    if not produto:
        raise ErroML(f"Página sem dados de preço (pode ter caído em verificação/captcha): {link}")

    ofertas = produto["offers"]
    oferta = ofertas[0] if isinstance(ofertas, list) else ofertas
    if "InStock" not in str(oferta.get("availability", "InStock")):
        return None
    preco = float(oferta["price"])
    imagem = produto.get("image")
    if isinstance(imagem, list):
        imagem = imagem[0] if imagem else None

    # Preço riscado do anúncio principal (o primeiro "Antes:" da página).
    orig = None
    m = re.search(r'aria-label="Antes:\s*([^"]+)"', html)
    if m:
        v = _reais(m.group(1))
        if v and preco < v < preco * 3:
            orig = v

    return {"id": cod, "titulo": produto.get("name", ""), "preco": preco,
            "preco_original": orig, "foto": imagem, "full": False, "frete_gratis": False}


def consultar(link, token=None):
    """Tenta a API; se ela recusar (sem app/token), lê a página do anúncio."""
    try:
        return consultar_api(link, token)
    except ErroML as e:
        if token:
            print(f"! API recusou, usando a página: {e}")
        return consultar_pagina(link)


def consultar_api(link, token=None):
    """Consulta o anúncio e devolve um dicionário padronizado (ou None se indisponível)."""
    tipo, cod = identificar(link)
    if tipo == "produto":
        p = _req(f"{API}/products/{cod}", token)
        bb = p.get("buy_box_winner")
        if not bb or not bb.get("price"):
            return None
        fotos = p.get("pictures") or []
        return {
            "id": cod,
            "titulo": p.get("name", ""),
            "preco": float(bb["price"]),
            "preco_original": float(bb["original_price"]) if bb.get("original_price") else None,
            "foto": fotos[0].get("url") if fotos else None,
            "full": (bb.get("shipping") or {}).get("logistic_type") == "fulfillment",
            "frete_gratis": bool((bb.get("shipping") or {}).get("free_shipping")),
        }

    it = _req(f"{API}/items/{cod}", token)
    if it.get("status") != "active":
        return None
    fotos = it.get("pictures") or []
    envio = it.get("shipping") or {}
    return {
        "id": cod,
        "titulo": it.get("title", ""),
        "preco": float(it["price"]),
        "preco_original": float(it["original_price"]) if it.get("original_price") else None,
        "foto": (fotos[0].get("secure_url") or fotos[0].get("url")) if fotos else None,
        "full": envio.get("logistic_type") == "fulfillment",
        "frete_gratis": bool(envio.get("free_shipping")),
    }
