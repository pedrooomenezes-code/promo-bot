"""Agendamento no X através do Postiz (CLI oficial `postiz`, instalado via npm)."""
import json
import os
import subprocess
import tempfile
import urllib.request

from .ml import UA


def _cli(*args):
    r = subprocess.run(["postiz", *args], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"postiz {' '.join(args[:1])} falhou: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def _json(saida):
    # O CLI às vezes imprime uma linha de cabeçalho antes do JSON.
    i = min([p for p in (saida.find("{"), saida.find("[")) if p >= 0], default=-1)
    return json.loads(saida[i:]) if i >= 0 else {}


def subir_foto(url_foto):
    if not url_foto:
        return None
    sufixo = ".webp" if url_foto.lower().endswith(".webp") else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as f:
        req = urllib.request.Request(url_foto, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            f.write(r.read())
        caminho = f.name
    try:
        return _json(_cli("upload", caminho)).get("path")
    finally:
        os.unlink(caminho)


def agendar(texto, quando_utc, integracao_id, foto=None, rascunho=True):
    args = ["posts:create", "-c", texto, "-s", quando_utc, "-i", integracao_id,
            "--settings", json.dumps({"who_can_reply_post": "everyone"})]
    if foto:
        args += ["-m", foto]
    if rascunho:
        args += ["-t", "draft"]
    return _json(_cli(*args))
