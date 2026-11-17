"""Boletim diario: fontes -> dedup -> resumo por IA -> painel HTML offline -> e-mail + Telegram.

Uso:
    uv run boletim.py                         # todas as edicoes de edicoes/*.toml (o que o agendador roda)
    uv run boletim.py --edicao ia-opensource  # so uma
    uv run boletim.py --sem-envio             # gera o painel, nao envia
    uv run boletim.py --sem-ia                # so coleta e dedup (teste rapido, sem gastar assinatura)
    uv run boletim.py --saida C:/tmp/teste    # grava em outra pasta e nao mexe no historico
    uv run boletim.py --vigiar                # so confere se o painel de hoje saiu; se nao, avisa
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import tomllib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import analise  # noqa: E402
import audio  # noqa: E402
import coleta  # noqa: E402
import dedup  # noqa: E402
import entrega  # noqa: E402
import ia  # noqa: E402
import painel  # noqa: E402

log = logging.getLogger("boletim")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


def carregar_env(arq: Path) -> None:
    if arq.exists():
        for ln in arq.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def manter_acordado(ligar: bool = True) -> None:
    """Windows: o WakeToRun so acorda o PC; isto impede que ele volte a dormir no meio."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if ligar else 0))


def resolver(valor: str | None) -> str | None:
    """'env:NOME' le do ambiente (.env); qualquer outro valor vale como esta."""
    if valor and str(valor).startswith("env:"):
        return os.environ.get(valor[4:]) or None
    return valor or None


def logo_uri(caminho: str | None) -> str | None:
    """Imagem -> data URI WebP de ate 288 px com alfa (aceita PNG/JPG/WebP de qualquer tamanho)."""
    import base64
    import io
    if not caminho or not Path(caminho).is_file():
        return None
    from PIL import Image
    im = Image.open(caminho).convert("RGBA")
    im.thumbnail((288, 288), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=86, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def carregar_identidade(cfg: dict) -> dict | None:
    """Emblemas e assinatura vivem fora do repo (identidade.toml na pasta de dados)."""
    arq = Path(cfg["geral"].get("identidade", Path(cfg["geral"]["dados"]) / "identidade.toml"))
    if not arq.exists():
        log.warning("identidade pedida mas %s nao existe", arq)
        return None
    ident = tomllib.loads(arq.read_text(encoding="utf-8"))
    for k in ("logo", "logo_direita"):
        if ident.get(k) and not Path(ident[k]).is_file():
            log.warning("emblema %s nao encontrado: %s", k, ident[k])
    # esquerda e direita, nessa ordem; o que faltar simplesmente nao aparece
    ident["logos"] = [(u, alt) for u, alt in ((logo_uri(ident.get("logo")), ident.get("logo_alt", "")),
                                              (logo_uri(ident.get("logo_direita")), ident.get("logo_direita_alt", "")))
                      if u]
    return ident


def selecionar(itens: list[dict], maximo: int) -> list[dict]:
    """Rodizio entre fontes, das de maior peso para as de menor, mais recentes primeiro."""
    if len(itens) <= maximo:
        return itens
    por_fonte = defaultdict(list)
    for it in sorted(itens, key=lambda x: x.get("publicado") or "", reverse=True):
        por_fonte[it["fonte"]].append(it)
    filas = sorted(por_fonte.values(), key=lambda f: -f[0]["peso"])
    out = []
    while len(out) < maximo and any(filas):
        for f in filas:
            if f and len(out) < maximo:
                out.append(f.pop(0))
    return out


def rodar_edicao(ed: dict, cfg: dict, args, agora: datetime, hist: dedup.Historico | None) -> dict:
    dia = agora.date().isoformat()
    t0 = time.time()
    brutos, status = coleta.coletar(ed["fontes"], int(ed.get("janela_horas", 30)))
    unicos, rep_lote = dedup.deduplicar(brutos)
    rep_hist = 0
    if hist:
        unicos, rep_hist = hist.filtrar_novos(ed["nome"], unicos, int(cfg["geral"].get("memoria_dias", 21)), dia)
    lote = selecionar(unicos, int(ed.get("max_itens", 80)))
    log.info("[%s] coletados %d, repetidos no lote %d, ja publicados %d, para a IA %d",
             ed["nome"], len(brutos), rep_lote, rep_hist, len(lote))

    avisos, modo, roteiro = [], "sem IA", ""
    ed["_dia_extenso"] = f"{agora.day} de {MESES[agora.month - 1]} de {agora.year}"
    if lote and cfg["ia"].get("ativo", True) and not args.sem_ia:
        try:
            resp = ia.resumir(ed, lote, cfg["ia"].get("modelo", "sonnet"), int(cfg["ia"].get("timeout_s", 900)),
                              Path(cfg["geral"]["dados"]))
            itens, destaques, visao, avisos = ia.conferir(resp, lote, list(ed.get("temas") or []))
            roteiro = str(resp.get("roteiro_audio") or "").strip() if ed.get("audio") else ""
            modo = f"IA ({cfg['ia'].get('modelo', 'sonnet')})"
        except Exception as ex:
            log.exception("[%s] IA falhou, painel sem resumo", ed["nome"])
            entrega.alertar(f"Boletim {ed['titulo']}: IA falhou ({type(ex).__name__}); painel saiu sem resumo.", cfg["entrega"])
            itens, destaques, visao = ia.sem_ia(lote)
            avisos.append(f"IA indisponível: {type(ex).__name__}")
    else:
        itens, destaques, visao = ia.sem_ia(lote)

    stats = {"coletados": len(brutos), "repetidas": sum(len(i.get("membros") or []) for i in itens),
             "modo": modo, "segundos": round(time.time() - t0)}
    panorama = None
    if ed.get("panorama"):
        panorama = {"palavras": analise.palavras_top(brutos, int(ed.get("panorama_palavras", 20)), ed.get("stopwords")),
                    "instituicoes": analise.instituicoes(brutos)}
    identidade = carregar_identidade(cfg) if ed.get("identidade") else None
    som = audio.gerar_mp3(roteiro, cfg.get("audio", {})) if roteiro else None
    if ed.get("audio") and itens and not som:
        avisos.append("Resumo em áudio indisponível hoje" + ("" if roteiro else " (sem roteiro da IA)"))
    faixa = {"mp3": som[0], "segundos": som[1], "roteiro": roteiro} if som else None
    pagina = painel.gerar(ed, dia, agora, itens, destaques, visao, status, stats, avisos, panorama, identidade, faixa)

    pasta = Path(args.saida or cfg["geral"]["saida"]) / ed["nome"]
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{ed['nome']}-{dia}.html"
    if faixa:
        (pasta / f"{ed['nome']}-{dia}.mp3").write_bytes(faixa["mp3"])
    (pasta / nome).write_text(pagina, encoding="utf-8")
    (pasta / "hoje.html").write_text(pagina, encoding="utf-8")
    if hist:
        hist.registrar(ed["nome"], dia, itens)
    log.info("[%s] painel %s (%d itens, %s, %ds)", ed["nome"], pasta / nome, len(itens), modo, stats["segundos"])

    res = {"painel": str(pasta / nome), "itens": len(itens)}
    if not args.sem_envio and itens:
        ce = dict(cfg["entrega"], email_para=ed.get("email_para"))
        entrega.CHAT_EDICAO = resolver(ed.get("telegram_chat"))
        if ed.get("telegram_chat") and not entrega.CHAT_EDICAO:
            log.warning("[%s] canal do Telegram nao configurado (%s); envio vai para o chat pessoal",
                        ed["nome"], ed["telegram_chat"])
        texto, html_email = painel.texto_email(ed, agora, itens, destaques, visao)
        res.update(entrega.entregar(
            ce, dia, f"{ed['titulo']} · {agora:%d/%m} · {len(itens)} notícias", texto, html_email,
            painel.texto_telegram(ed, agora, itens, destaques, visao), nome, pagina,
            (f"{ed['nome']}-{dia}.mp3", faixa["mp3"], f"{ed['titulo']} · {agora:%d/%m}", int(faixa["segundos"]))
            if faixa else None))
        entrega.CHAT_EDICAO = None
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(AQUI / "config.toml"))
    ap.add_argument("--edicao", action="append", help="nome da edicao (repetivel); padrao: todas")
    ap.add_argument("--sem-envio", action="store_true")
    ap.add_argument("--sem-ia", action="store_true")
    ap.add_argument("--saida", help="pasta alternativa (teste): nao grava historico")
    ap.add_argument("--vigiar", action="store_true", help="avisa se o painel de hoje nao existe")
    args = ap.parse_args()

    cfg = tomllib.loads(Path(args.config).read_text(encoding="utf-8"))
    dados = Path(cfg["geral"]["dados"])
    (dados / "logs").mkdir(parents=True, exist_ok=True)
    agora = datetime.now(ZoneInfo(cfg["geral"].get("fuso", "America/Sao_Paulo")))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(dados / "logs" / f"{agora:%Y-%m-%d}.log", encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])
    carregar_env(Path(cfg["geral"].get("env", dados / ".env")))

    edicoes = []
    for arq in sorted((AQUI / "edicoes").glob("*.toml")):
        ed = tomllib.loads(arq.read_text(encoding="utf-8"))
        ed.setdefault("nome", arq.stem)
        if ed.get("ativo", True) and (not args.edicao or ed["nome"] in args.edicao):
            edicoes.append(ed)
    if not edicoes:
        log.error("nenhuma edicao encontrada/ativa")
        return 1

    if args.vigiar:
        faltam = [ed["titulo"] for ed in edicoes
                  if not (Path(cfg["geral"]["saida"]) / ed["nome"] / f"{ed['nome']}-{agora.date().isoformat()}.html").exists()]
        if faltam:
            log.warning("vigia: sem painel hoje: %s", faltam)
            entrega.alertar("Boletim não saiu hoje: " + ", ".join(faltam) + ". Ver logs em " + str(dados / "logs"), cfg["entrega"])
        return 1 if faltam else 0

    hist = None if args.saida else dedup.Historico(dados / "boletim.db")
    manter_acordado(True)
    falhas = 0
    try:
        for ed in edicoes:
            try:
                log.info("[%s] resultado: %s", ed["nome"], rodar_edicao(ed, cfg, args, agora, hist))
            except Exception as ex:
                falhas += 1
                log.exception("[%s] falhou", ed["nome"])
                if not args.sem_envio:
                    entrega.alertar(f"Boletim {ed.get('titulo', ed['nome'])} falhou: {type(ex).__name__}: {str(ex)[:200]}",
                                    cfg["entrega"])
    finally:
        manter_acordado(False)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
