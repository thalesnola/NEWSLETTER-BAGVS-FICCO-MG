"""Entrega do boletim: e-mail (SMTP, iCloud por padrao) e Telegram (bot proprio).

Segredos no .env da pasta de dados (nunca no repositorio):
    SMTP_USUARIO=voce@icloud.com      # login SMTP (no iCloud: o endereco completo)
    SMTP_SENHA=<senha-de-app>          # senha de app (appleid.apple.com), NAO a senha da conta
    EMAIL_PARA=voce@icloud.com        # destinatarios separados por virgula
    TELEGRAM_TOKEN_PAINEL=123456:ABC... # bot exclusivo bot do painel (configurar_telegram.py)
    TELEGRAM_CHAT_ID=123456789          # chat privado (o mesmo id em todos os bots)
    TELEGRAM_CHAT_ID_PAINEL=...         # opcional: so se o chat deste bot for outro

TELEGRAM_TOKEN (bot geral) fica so como fallback enquanto o bot proprio nao estiver configurado.

Cada canal falha sozinho: erro de envio vira aviso no log e nunca derruba o boletim.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
import uuid
from email.message import EmailMessage

log = logging.getLogger("boletim.entrega")


# ---------------------------------------------------------------- e-mail

def email_configurado() -> bool:
    return all(os.environ.get(k) for k in ("SMTP_USUARIO", "SMTP_SENHA", "EMAIL_PARA"))


def enviar_email(cfg: dict, assunto: str, texto: str, html: str,
                 anexo_nome: str | None = None, anexo_html: str | None = None) -> None:
    usuario = os.environ["SMTP_USUARIO"]
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = os.environ.get("EMAIL_DE") or usuario
    msg["To"] = cfg.get("email_para") or os.environ["EMAIL_PARA"]
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    if anexo_html:
        msg.add_attachment(anexo_html.encode("utf-8"), maintype="text", subtype="html",
                           filename=anexo_nome or "relatorio.html")
    host = cfg.get("smtp_host", "smtp.mail.me.com")
    porta = int(cfg.get("smtp_porta", 587))
    with smtplib.SMTP(host, porta, timeout=60) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(usuario, os.environ["SMTP_SENHA"])
        s.send_message(msg)


# ---------------------------------------------------------------- Telegram

LIMITE_TG = 4096


CHAT_EDICAO: str | None = None   # boletim.py troca por edicao (telegram_chat)


def token() -> str:
    """Bot exclusivo do painel; o token geral so como fallback."""
    return os.environ.get("TELEGRAM_TOKEN_PAINEL") or os.environ.get("TELEGRAM_TOKEN") or ""


def chat_id() -> str:
    return CHAT_EDICAO or os.environ.get("TELEGRAM_CHAT_ID_PAINEL") or os.environ["TELEGRAM_CHAT_ID"]


def telegram_configurado() -> bool:
    return bool(token() and (os.environ.get("TELEGRAM_CHAT_ID_PAINEL") or os.environ.get("TELEGRAM_CHAT_ID")))


def _tg(metodo: str, dados: bytes, tipo: str, tok: str | None = None) -> dict:
    url = f"https://api.telegram.org/bot{tok or token()}/{metodo}"
    req = urllib.request.Request(url, data=dados, headers={"Content-Type": tipo})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as ex:
        # a URL contem o token: nunca repassar str(ex) nem a URL para o log
        corpo = ex.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"Telegram {metodo} {ex.code}: {corpo}") from None


def telegram_texto(texto: str, html: bool = True) -> None:
    for parte in _fatiar(texto, LIMITE_TG):
        campos = {"chat_id": chat_id(), "text": parte,
                  "disable_web_page_preview": "true"}
        if html:
            campos["parse_mode"] = "HTML"
        _tg("sendMessage", urllib.parse.urlencode(campos).encode(), "application/x-www-form-urlencoded")


def telegram_arquivo(nome: str, conteudo: bytes, legenda: str = "") -> None:
    _tg_multipart("sendDocument", "document", nome, "text/html", conteudo, {"caption": legenda[:1024]})


def _tg_multipart(metodo: str, campo: str, nome: str, tipo: str, conteudo: bytes, extra: dict) -> dict:
    limite = "----boletim" + uuid.uuid4().hex
    partes = []
    for k, v in {"chat_id": chat_id(), **extra}.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{campo}"; filename="{nome}"\r\n'
                  f"Content-Type: {tipo}\r\n\r\n".encode() + conteudo + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return _tg(metodo, b"".join(partes), f"multipart/form-data; boundary={limite}")


def _fatiar(texto: str, n: int) -> list[str]:
    if len(texto) <= n:
        return [texto]
    out, atual = [], ""
    for bloco in texto.split("\n\n"):
        if len(atual) + len(bloco) + 2 > n and atual:
            out.append(atual)
            atual = ""
        atual = (atual + "\n\n" + bloco) if atual else bloco[:n]
    if atual:
        out.append(atual)
    return out


# ---------------------------------------------------------------- orquestracao

def telegram_audio(nome: str, mp3: bytes, titulo: str, segundos: int) -> None:
    _tg_multipart("sendAudio", "audio", nome, "audio/mpeg", mp3,
                  {"title": titulo[:64], "performer": "Resumo em áudio", "duration": segundos})


def entregar(cfg: dict, dia: str, assunto: str, texto: str, html_email: str, msg_telegram: str,
             nome_anexo: str, html_completo: str, audio: tuple | None = None) -> dict:
    """Envia por todos os canais ativos. Devolve {canal: 'ok' | 'erro: ...' | 'nao configurado'}."""
    res = {}
    if cfg.get("email", True):
        if email_configurado():
            try:
                enviar_email(cfg, assunto, texto, html_email, nome_anexo, html_completo)
                res["email"] = "ok"
            except Exception as ex:
                res["email"] = f"erro: {type(ex).__name__}: {str(ex)[:200]}"
        else:
            res["email"] = "nao configurado"
    if cfg.get("telegram", True):
        if telegram_configurado():
            try:
                telegram_texto(msg_telegram)
                telegram_arquivo(nome_anexo, html_completo.encode("utf-8"), "Painel completo · abre offline")
                if audio:
                    try:
                        telegram_audio(*audio)
                    except Exception as ex:   # audio e extra: nao rebaixa a entrega do painel
                        log.warning("telegram audio falhou: %s", ex)
                res["telegram"] = "ok"
            except Exception as ex:
                res["telegram"] = f"erro: {type(ex).__name__}: {str(ex)[:200]}"
        else:
            res["telegram"] = "nao configurado"
    for canal, r in res.items():
        (log.info if r == "ok" else log.warning)("entrega %s: %s", canal, r)
    return res


def alertar(texto: str, cfg: dict | None = None) -> bool:
    """Aviso curto de falha. Tenta Telegram; se nao der, e-mail. Nunca levanta excecao."""
    cfg = cfg or {}
    if telegram_configurado():
        try:
            telegram_texto("⚠️ " + texto, html=False)
            return True
        except Exception as ex:
            log.warning("alerta telegram falhou: %s", ex)
    if email_configurado():
        try:
            enviar_email(cfg, "⚠️ Boletim diário: falha", texto, f"<pre>{_esc(texto)}</pre>")
            return True
        except Exception as ex:
            log.warning("alerta e-mail falhou: %s", ex)
    return False


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
