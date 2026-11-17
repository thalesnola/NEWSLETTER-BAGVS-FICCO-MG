"""Deduplicacao em camadas, sem rede e sem modelo:

1. URL normalizada (sem utm_*, fbclid, fragmento, www, barra final).
2. Titulo parecido (Jaccard de palavras >= limiar) - pega a mesma noticia em fontes diferentes.
3. Historico (SQLite): o que ja saiu em edicoes anteriores nao volta.

A camada semantica (mesmo fato com titulos diferentes) fica com a IA, que recebe o lote inteiro
de uma vez e agrupa duplicatas; os ids que ela devolve sao conferidos em boletim.py.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_RASTREIO = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|ref_src$|igshid$|si$)")
_VAZIAS = set("a o e de da do das dos em no na nos nas um uma para por com que se ao à "
              "the a an of to in on for and is with by from at as".split())


def url_norm(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.").removeprefix("m.")
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _RASTREIO.match(k.lower())])
    caminho = p.path.rstrip("/") or "/"
    return urlunsplit(("https", host, caminho, q, ""))


def palavras(titulo: str) -> frozenset[str]:
    t = unicodedata.normalize("NFKD", titulo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return frozenset(w for w in re.findall(r"[a-z0-9]+", t) if w not in _VAZIAS and len(w) > 1)


def parecido(a: frozenset, b: frozenset, limiar: float = 0.6) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= limiar


def deduplicar(itens: list[dict], limiar: float = 0.6) -> tuple[list[dict], int]:
    """Agrupa a mesma noticia: o de maior peso (empate: o mais recente) vira o principal do evento e os
    outros entram em 'membros' (fonte, titulo, link, trecho) - nada se perde, so deixa de repetir.
    Devolve (eventos, quantos_itens_viraram_membro)."""
    ordem = sorted(itens, key=lambda x: (-x["peso"], -(_ts(x))))
    unicos: list[dict] = []
    vistos_url: dict[str, dict] = {}
    for it in ordem:
        u = url_norm(it["url"])
        w = palavras(it["titulo"])
        dono = vistos_url.get(u) or next((x for x in unicos if parecido(w, x["_w"], limiar)), None)
        if dono:
            nome = it.get("veiculo") or it["fonte"]
            if nome != (dono.get("veiculo") or dono["fonte"]) and nome not in dono["tambem_em"]:
                dono["tambem_em"].append(nome)
            if u != dono["_u"] and all(u != m["_u"] for m in dono["membros"]):
                dono["membros"].append(membro(it, u))
            vistos_url.setdefault(u, dono)
            continue
        it = dict(it, _u=u, _w=w, tambem_em=[], membros=[])
        unicos.append(it)
        vistos_url[u] = it
    return unicos, len(itens) - len(unicos)


def membro(it: dict, u: str | None = None) -> dict:
    return {"veiculo": it.get("veiculo") or it["fonte"], "titulo": it["titulo"], "url": it["url"],
            "_u": u or it.get("_u") or url_norm(it["url"]), "trecho": it.get("trecho", ""),
            "publicado": it.get("publicado")}


def _ts(x: dict) -> float:
    try:
        return datetime.fromisoformat(x["publicado"]).timestamp()
    except Exception:
        return 0.0


class Historico:
    def __init__(self, arq: Path):
        arq.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(arq)
        self.con.execute("""CREATE TABLE IF NOT EXISTS publicados(
            edicao TEXT, dia TEXT, url TEXT, titulo TEXT, PRIMARY KEY(edicao, url))""")

    def filtrar_novos(self, edicao: str, itens: list[dict], dias: int, hoje: str,
                      limiar: float = 0.6) -> tuple[list[dict], int]:
        """Tira o que ja saiu em dias ANTERIORES (rodar de novo no mesmo dia regenera igual)."""
        corte = (datetime.now(timezone.utc) - timedelta(days=dias)).date().isoformat()
        linhas = self.con.execute(
            "SELECT url, titulo FROM publicados WHERE edicao=? AND dia>=? AND dia<?",
            (edicao, corte, hoje)).fetchall()
        urls = {u for u, _ in linhas}
        titulos = [palavras(t) for _, t in linhas]
        novos = [it for it in itens
                 if it["_u"] not in urls and not any(parecido(it["_w"], t, limiar) for t in titulos)]
        return novos, len(itens) - len(novos)

    def registrar(self, edicao: str, dia: str, itens: list[dict]) -> None:
        with self.con:
            self.con.executemany(
                "INSERT OR REPLACE INTO publicados VALUES(?,?,?,?)",
                [(edicao, dia, x["_u"], x["titulo"]) for it in itens for x in [it, *it.get("membros", [])]])
