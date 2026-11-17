"""Liga o painel ao bot exclusivo bot do painel, sem o token passar pelo chat nem pela tela.

Uso:  configurar.cmd            (pede o token, confere, envia teste e grava)
      configurar.cmd teste      (so envia um teste com o que ja esta no .env)

O .env (config.toml -> [geral] env) pode ser dividido com outros bots. Por isso:
- grava SO TELEGRAM_TOKEN_PAINEL (e TELEGRAM_CHAT_ID_PAINEL, se o chat deste bot for outro);
  TELEGRAM_TOKEN, TELEGRAM_TOKEN_RELATORIO, TELEGRAM_TOKEN_PUBLICAR e o resto ficam intactos, linha a linha;
- recusa o token de outro bot ja gravado no .env;
- so grava depois que a mensagem de teste chegou, e guarda copia do .env antes (.env.bak-AAAAMMDD-HHMMSS).
"""
from __future__ import annotations

import getpass
import json
import os
import re
import shutil
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import entrega  # noqa: E402

BOT_ESPERADO = os.environ.get("BOT_ESPERADO", "").lstrip("@").lower()  # opcional: @ do bot do painel
CHAVE_TOKEN = "TELEGRAM_TOKEN_PAINEL"
CHAVE_CHAT = "TELEGRAM_CHAT_ID_PAINEL"
OUTROS_TOKENS = ("TELEGRAM_TOKEN", "TELEGRAM_TOKEN_RELATORIO", "TELEGRAM_TOKEN_PUBLICAR")
FORMATO_TOKEN = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


def caminho_env() -> Path:
    cfg = tomllib.loads((AQUI / "config.toml").read_text(encoding="utf-8"))
    return Path(cfg["geral"].get("env") or Path(cfg["geral"]["dados"]) / ".env")


def ler_env(arq: Path) -> dict:
    d = {}
    if arq.exists():
        for ln in arq.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip().strip('"')
    return d


def gravar_env(arq: Path, novos: dict) -> Path | None:
    """Troca so as chaves de `novos`, no lugar; as demais linhas saem byte a byte iguais.

    Chave nova vai para o fim. Copia de seguranca antes; troca atomica (temp + replace).
    Devolve o caminho da copia (None se o .env nao existia).
    """
    bruto = arq.read_bytes() if arq.exists() else b""
    texto = bruto.decode("utf-8")
    nl = "\r\n" if "\r\n" in texto else "\n"
    linhas = texto.splitlines(keepends=True)
    pendentes = dict(novos)
    for i, ln in enumerate(linhas):
        k = ln.split("=", 1)[0].strip() if "=" in ln and not ln.lstrip().startswith("#") else None
        if k in pendentes:
            fim = ln[len(ln.rstrip("\r\n")):] or nl
            linhas[i] = f"{k}={pendentes.pop(k)}{fim}"
    if linhas and not linhas[-1].endswith(("\n", "\r")):
        linhas[-1] += nl
    linhas += [f"{k}={v}{nl}" for k, v in pendentes.items()]
    copia = None
    if arq.exists():
        copia = arq.with_name(f"{arq.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(arq, copia)
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_bytes("".join(linhas).encode("utf-8"))
    os.replace(tmp, arq)
    return copia


def api(tok: str, metodo: str, **campos) -> tuple[int, dict]:
    """(status HTTP, resposta). Nunca mostra a URL, que contem o token."""
    dados = urllib.parse.urlencode(campos).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{metodo}", data=dados)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as ex:
        try:
            return ex.code, json.loads(ex.read().decode("utf-8", "ignore"))
        except ValueError:
            return ex.code, {}


def esperar_start(tok: str, segundos: int = 120) -> tuple[str, str] | None:
    """Le o chat privado por getUpdates (pode: o bot do painel nao tem outro leitor)."""
    fim, offset = time.time() + segundos, 0
    while time.time() < fim:
        _, r = api(tok, "getUpdates", timeout=20, offset=offset)
        for up in r.get("result", []):
            offset = up["update_id"] + 1
            c = (up.get("message") or {}).get("chat", {})
            if c.get("type") == "private":
                api(tok, "getUpdates", offset=offset, timeout=0)  # confirma a leitura
                return str(c["id"]), c.get("first_name", "")
    return None


def configurar() -> None:
    arq = caminho_env()
    atual = ler_env(arq)
    print(f".env: {arq}")
    print(f"Bot: @{BOT_ESPERADO}. Copie o token no @BotFather (/mybots > o bot > API Token).")
    if atual.get(CHAVE_TOKEN):
        if input(f"Já existe {CHAVE_TOKEN}. Substituir? [s/N] ").strip().lower() != "s":
            sys.exit("Nada mudou.")
    tok = getpass.getpass("Token do bot (não aparece na tela) e Enter: ").strip()
    if not FORMATO_TOKEN.match(tok):
        sys.exit("Isso não tem cara de token do @BotFather (números:letras). Nada mudou.")
    for k in OUTROS_TOKENS:
        if atual.get(k) == tok:
            sys.exit(f"Esse token é o de {k} (outro bot). O painel precisa do token do "
                     f"@{BOT_ESPERADO}. Nada mudou.")

    st, eu = api(tok, "getMe")
    if st != 200 or not eu.get("ok"):
        sys.exit(f"getMe recusou ({st}): token errado ou revogado. Nada mudou.")
    nome = eu["result"].get("username", "")
    print(f"ok: getMe respondeu @{nome}")
    if BOT_ESPERADO and nome.lower() != BOT_ESPERADO and input(
            f"Esperava @{BOT_ESPERADO}. Usar @{nome} mesmo assim? [s/N] ").strip().lower() != "s":
        sys.exit("Nada mudou.")

    chat = atual.get(CHAVE_CHAT) or atual.get("TELEGRAM_CHAT_ID")
    quem = ""
    texto = "✅ Painel diário BAGVS/FICCO-MG ligado neste bot. O boletim chega aqui."
    st, r = api(tok, "sendMessage", chat_id=chat, text=texto) if chat else (0, {})
    if st != 200:
        if st:
            print(f"O envio para o chat já configurado deu {st} ({r.get('description', '')}).")
        print(f"Abra @{nome} no Telegram e mande /start ... (esperando até 2 min)")
        achado = esperar_start(tok)
        if not achado:
            sys.exit("Não recebi o /start. Rode de novo. Nada mudou.")
        chat, quem = achado
        st, r = api(tok, "sendMessage", chat_id=chat, text=texto)
        if st != 200:
            sys.exit(f"Envio de teste falhou ({st}): {r.get('description', '')}. Nada mudou.")
    print(f"ok: mensagem de teste enviada{' a ' + quem if quem else ''}")

    novos = {CHAVE_TOKEN: tok}
    if chat != atual.get("TELEGRAM_CHAT_ID"):
        novos[CHAVE_CHAT] = chat
    copia = gravar_env(arq, novos)
    print(f"ok: gravado {', '.join(novos)} (demais chaves intactas)")
    if copia:
        print(f"cópia anterior: {copia}")


def teste() -> None:
    os.environ.update(ler_env(caminho_env()))
    if not os.environ.get(CHAVE_TOKEN):
        print(f"aviso: {CHAVE_TOKEN} ausente; o envio usaria o fallback TELEGRAM_TOKEN (outro bot)")
    entrega.telegram_texto("🧪 <b>Painel BAGVS/FICCO-MG</b>: teste de entrega")
    print("ok: teste enviado")


if __name__ == "__main__":
    teste() if sys.argv[1:2] == ["teste"] else configurar()
