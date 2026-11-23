"""Gera o primeiro refresh token do Mercado Livre (rodar uma vez, no seu computador).

    python autorizar_ml.py

Pede o Client ID, o Client Secret e a Redirect URI do app que você criou em
developers.mercadolivre.com.br, abre o link de autorização e troca o código
pelo refresh token. Guarde o resultado no secret ML_REFRESH_TOKEN do GitHub.
"""
import getpass
import json
import urllib.parse
import urllib.request

cid = input("Client ID: ").strip()
sec = getpass.getpass("Client Secret (não aparece ao digitar): ").strip()
redir = input("Redirect URI (igual à cadastrada no app): ").strip()

url = "https://auth.mercadolivre.com.br/authorization?" + urllib.parse.urlencode(
    {"response_type": "code", "client_id": cid, "redirect_uri": redir})
print("\n1) Abra este link logado na sua conta do Mercado Livre e autorize:\n\n" + url)
print("\n2) Você vai cair na Redirect URI com ?code=TG-... na barra de endereço.")
code = input("Cole aqui o code (começa com TG-): ").strip()

body = urllib.parse.urlencode({"grant_type": "authorization_code", "client_id": cid,
                               "client_secret": sec, "code": code, "redirect_uri": redir}).encode()
req = urllib.request.Request("https://api.mercadolibre.com/oauth/token", data=body,
                             headers={"Content-Type": "application/x-www-form-urlencoded",
                                      "Accept": "application/json"})
with urllib.request.urlopen(req) as r:
    tok = json.loads(r.read())
print("\nPronto. Cadastre no GitHub o secret ML_REFRESH_TOKEN com este valor:\n")
print(tok["refresh_token"])
