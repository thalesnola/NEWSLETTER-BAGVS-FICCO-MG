"""Coleta de fontes RSS/Atom (inclui releases do GitHub e buscas do Google News).

Cada fonte falha sozinha: o erro vai para a lista de falhas e aparece no painel.
"""
from __future__ import annotations

import calendar
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser

log = logging.getLogger("boletim.coleta")

AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) boletim-diario/0.1"
_TAG = re.compile(r"<[^>]+>")
_ESPACO = re.compile(r"\s+")


def texto_limpo(s: str | None, limite: int = 600) -> str:
    s = html.unescape(_TAG.sub(" ", s or ""))
    s = _ESPACO.sub(" ", s).strip()
    return s[:limite]


_MESES = {m: i for i, m in enumerate("jan fev mar abr mai jun jul ago set out nov dez".split(), 1)}
_DATA_PT = re.compile(r"(?:(\d{1,2})\s+)?([a-zç]{3})[a-z]*\.?\s+(\d{1,2})?\s*,?\s*(\d{4})\s+(\d{1,2}):(\d{2})", re.I)


def _data_pt(s: str) -> datetime | None:
    """'Sex, nov 13 2026 19:15:00' (STJ) ou '13 nov 2026 19:15'. Hora de Brasilia (UTC-3)."""
    m = _DATA_PT.search(s or "")
    if not m or m.group(2).lower()[:3] not in _MESES:
        return None
    dia = int(m.group(1) or m.group(3) or 0)
    if not dia:
        return None
    try:
        return datetime(int(m.group(4)), _MESES[m.group(2).lower()[:3]], dia, int(m.group(5)), int(m.group(6)),
                        tzinfo=timezone(timedelta(hours=-3)))
    except ValueError:
        return None


def _quando(e) -> datetime | None:
    for campo in ("published_parsed", "updated_parsed"):
        t = e.get(campo)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    for campo in ("published", "updated"):
        d = _data_pt(e.get(campo))
        if d:
            return d
    return None


def _casa_palavras(palavras: list[str], texto: str) -> bool:
    """Palavra toda em MAIUSCULAS (sigla) casa com caixa exata; o resto ignora caixa."""
    for p in palavras:
        flags = 0 if (p.isupper() and len(p) <= 5) else re.I
        if re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", texto, flags):
            return True
    return False


def coletar_fonte(fonte: dict, desde: datetime, timeout: int = 30) -> list[dict]:
    import socket
    socket.setdefaulttimeout(timeout)
    d = feedparser.parse(fonte["url"], agent=AGENTE)
    status = getattr(d, "status", 200)
    if status >= 400:
        raise RuntimeError(f"HTTP {status}")
    if d.bozo and not d.entries:
        raise RuntimeError(f"feed ilegivel: {type(d.bozo_exception).__name__}")
    itens = []
    for e in d.entries:
        quando = _quando(e)
        if quando and quando < desde:
            continue
        titulo = texto_limpo(e.get("title"), 300)
        link = e.get("link") or ""
        if not titulo or not link:
            continue
        corpo = e.get("summary") or ""
        if e.get("content"):
            corpo = e["content"][0].get("value") or corpo
        trecho = texto_limpo(corpo)
        veiculo = (e.get("source") or {}).get("title") or ""
        if veiculo and titulo.endswith(" - " + veiculo):   # Google News: "Titulo - Veiculo"
            titulo = titulo[: -len(veiculo) - 3].strip()
        if "news.google.com" in fonte["url"]:
            trecho = ""                                     # o resumo do GN repete o titulo
        if fonte.get("palavras") and not _casa_palavras(fonte["palavras"], f"{titulo} {trecho}"):
            continue
        itens.append({
            "fonte": fonte["nome"], "veiculo": veiculo, "peso": int(fonte.get("peso", 1)),
            "titulo": titulo, "url": link, "trecho": trecho,
            "publicado": quando.isoformat() if quando else None,
        })
    return itens


# ---------------------------------------------------------------- Instagram (Graph API oficial)

IG_API = "https://graph.facebook.com/v23.0"


def coletar_instagram(fonte: dict, desde: datetime, timeout: int = 30) -> list[dict]:
    """Ultimos posts de um perfil comercial/criador via Business Discovery (token do .env: IG_USER_ID, IG_TOKEN).
    So a legenda entra: texto dentro da arte nao vem pela API."""
    import json
    import os
    import urllib.error
    import urllib.parse
    import urllib.request
    uid, tok = os.environ.get("IG_USER_ID"), os.environ.get("IG_TOKEN")
    if not (uid and tok):
        raise RuntimeError("IG_USER_ID/IG_TOKEN ausentes no .env")
    conta = fonte["conta"]
    campos = (f"business_discovery.username({conta}){{name,media.limit({int(fonte.get('limite', 12))})"
              "{caption,permalink,timestamp,media_type,like_count,comments_count}}")
    url = f"{IG_API}/{uid}?" + urllib.parse.urlencode({"fields": campos, "access_token": tok})
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            bd = json.load(r)["business_discovery"]
    except urllib.error.HTTPError as ex:   # a URL tem o token: nunca repassar str(ex)
        erro = json.loads(ex.read().decode("utf-8", "ignore") or "{}").get("error", {})
        raise RuntimeError(f"Graph API {ex.code}: {erro.get('error_user_title') or erro.get('message', '')[:120]}") from None
    nome = bd.get("name") or conta
    itens = []
    for m in (bd.get("media") or {}).get("data", []):
        try:
            quando = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
        except Exception:
            quando = None
        if quando and quando < desde:
            continue
        legenda = texto_limpo(m.get("caption"), 900)
        if not legenda or not m.get("permalink"):
            continue
        if fonte.get("palavras") and not _casa_palavras(fonte["palavras"], legenda):
            continue
        primeira = re.split(r"(?<=[.!?])\s|\n", (m.get("caption") or "").strip(), maxsplit=1)[0]
        titulo = texto_limpo(primeira, 160) or legenda[:160]
        itens.append({
            "fonte": fonte["nome"], "veiculo": f"@{conta}", "perfil": conta, "peso": int(fonte.get("peso", 1)),
            "titulo": titulo, "url": m["permalink"], "trecho": legenda,
            "publicado": quando.isoformat() if quando else None, "rede": "instagram",
            "engajamento": (m.get("like_count") or 0) + (m.get("comments_count") or 0),
        })
    return itens


def expandir(fontes: list[dict]) -> list[dict]:
    """Fonte do tipo instagram com `contas = [...]` vira uma fonte por perfil (status e falha por perfil)."""
    out = []
    for f in fontes:
        if not f.get("ativo", True):
            continue
        if f.get("tipo") == "instagram":
            out += [dict(f, conta=c.lstrip("@"), nome=f"@{c.lstrip('@')}") for c in f.get("contas", [])]
        else:
            out.append(f)
    return out


def coletar(fontes: list[dict], janela_horas: int) -> tuple[list[dict], list[dict]]:
    """Devolve (itens, status_por_fonte)."""
    desde = datetime.now(timezone.utc) - timedelta(hours=janela_horas)
    ativas = expandir(fontes)

    def _uma(f):
        try:
            its = coletar_instagram(f, desde) if f.get("tipo") == "instagram" else coletar_fonte(f, desde)
            return f, its, None
        except Exception as ex:
            return f, [], f"{type(ex).__name__}: {str(ex)[:160]}"

    itens, status = [], []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f, its, erro in ex.map(_uma, ativas):
            itens += its
            status.append({"fonte": f["nome"], "itens": len(its), "erro": erro})
            (log.warning if erro else log.info)("fonte %s: %s", f["nome"], erro or f"{len(its)} itens")
    return itens, status
