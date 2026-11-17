"""Resumo editorial pelo Claude Code headless (assinatura logada, sem chave de API).

A IA so ve ids, titulos e trechos; links, fontes e datas voltam do dado coletado, nunca do texto
gerado. Tudo o que ela devolve e conferido em `conferir()`.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("boletim.ia")
_NUM = re.compile(r"\d[\d.,]*\d|\d")
AUDIO_FOCO = ("eventos críticos de política criminal, justiça criminal (decisões do STF/STJ, leis penais), "
              "operações policiais e segurança pública")


def _extrair_json(txt: str) -> dict:
    txt = txt.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", txt, re.S)
    if m:
        txt = m.group(1)
    ini, fim = txt.find("{"), txt.rfind("}")
    return json.loads(txt[ini:fim + 1])


def rodar(sistema_txt: str, entrada: str, modelo: str, timeout_s: int, cwd: Path) -> dict:
    claude = shutil.which("claude") or str(Path.home() / ".local/bin/claude.exe")
    cmd = [claude, "-p", "--model", modelo, "--tools", "",
           "--setting-sources", "project,local",      # sem hooks/plugins do usuario
           "--no-session-persistence", "--system-prompt", sistema_txt, "--output-format", "text"]
    ultimo = None
    for tentativa in (1, 2):
        r = subprocess.run(cmd, input=entrada, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout_s, cwd=cwd)
        if r.returncode != 0:
            ultimo = f"claude saiu com {r.returncode}: {(r.stderr or r.stdout)[:400]}"
            log.warning(ultimo)
            continue
        try:
            return _extrair_json(r.stdout)
        except Exception as ex:
            ultimo = f"JSON invalido ({ex}); inicio: {r.stdout[:300]}"
            log.warning("tentativa %d: %s", tentativa, ultimo)
            (cwd / "logs").mkdir(exist_ok=True)
            (cwd / "logs" / "ia_ultima_saida.txt").write_text(r.stdout, encoding="utf-8")
    raise RuntimeError(ultimo or "falha desconhecida")


def resumir(edicao: dict, itens: list[dict], modelo: str, timeout_s: int, cwd: Path) -> dict:
    sistema = (Path(__file__).parent / "prompts" / "resumo.md").read_text(encoding="utf-8")
    pacote = {
        "edicao": {k: edicao.get(k) for k in ("titulo", "descricao", "foco", "temas")},
        "dia": edicao.get("_dia_extenso"),
        "itens": [{"id": i, "fonte": it.get("veiculo") or it["fonte"], "titulo": it["titulo"],
                   "trecho": it["trecho"][:450],
                   "outras_versoes": [{"fonte": m["veiculo"], "titulo": m["titulo"], "trecho": m["trecho"][:220]}
                                      for m in it.get("membros", [])[:6]]}
                  for i, it in enumerate(itens)],
    }
    if edicao.get("audio"):
        pacote["edicao"]["audio"] = {"foco": edicao.get("audio_foco") or AUDIO_FOCO,
                                     "palavras": int(150 * float(edicao.get("audio_minutos", 3)))}
    entrada = "Edição de hoje (JSON):\n\n" + json.dumps(pacote, ensure_ascii=False) + "\n\nResponda só com o JSON."
    return rodar(sistema, entrada, modelo, timeout_s, cwd)


def conferir(resp: dict, itens: list[dict], temas: list[str]) -> tuple[list[dict], list[int], str, list[str]]:
    """Valida a resposta da IA contra o coletado. Devolve (itens_finais, destaques, visao, avisos)."""
    avisos = []
    finais, usados = [], set()
    for r in resp.get("itens") or []:
        try:
            i = int(r["id"])
        except Exception:
            avisos.append(f"item sem id valido descartado: {str(r)[:80]}")
            continue
        if not 0 <= i < len(itens) or i in usados:
            avisos.append(f"id {i} inexistente ou repetido descartado")
            continue
        usados.add(i)
        base = itens[i]
        dups = [int(d) for d in (r.get("duplicatas") or []) if str(d).isdigit() and int(d) < len(itens)
                and int(d) != i and int(d) not in usados]
        tema = r.get("tema") if r.get("tema") in temas else "Outros"
        resumo = str(r.get("resumo") or "").strip() or base["trecho"][:300]
        grupo = [base] + [itens[d] for d in dups]
        fonte_txt = " ".join(f"{x['titulo']} {x['trecho']} " + " ".join(f"{m['titulo']} {m['trecho']}" for m in x.get("membros", []))
                             for x in grupo)
        # numero no resumo que nao esta na fonte = possivel invencao: marca para conferir
        inventados = [n for n in _NUM.findall(resumo) if len(n) >= 2 and n not in fonte_txt]
        # todos os links do evento: os que o dedup juntou + os que a IA reconheceu como o mesmo fato
        from dedup import membro
        membros = list(base.get("membros", []))
        for d in dups:
            membros += [membro(itens[d])] + itens[d].get("membros", [])
        vistos, unicos = {base["_u"]}, []
        for m in membros:
            if m["_u"] not in vistos:
                vistos.add(m["_u"])
                unicos.append(m)
        tambem = list(dict.fromkeys([m["veiculo"] for m in unicos if m["veiculo"] != (base.get("veiculo") or base["fonte"])]))
        finais.append(dict(base, id=i, titulo_pt=str(r.get("titulo") or base["titulo"])[:160],
                           resumo=resumo, tema=tema, relevancia=max(1, min(5, int(r.get("relevancia") or 3))),
                           tambem_em=tambem, membros=unicos, conferir=inventados))
        usados.update(dups)
    validos = {f["id"] for f in finais}
    destaques = [int(d) for d in (resp.get("destaques") or []) if str(d).isdigit() and int(d) in validos]
    return finais, destaques, str(resp.get("visao_geral") or "").strip(), avisos


def sem_ia(itens: list[dict]) -> tuple[list[dict], list[int], str]:
    """Modo degradado: sem resumo, tema = fonte, ordem por peso e data."""
    finais = [dict(it, id=i, titulo_pt=it["titulo"], resumo=it["trecho"][:300], tema=it["fonte"],
                   relevancia=min(5, it["peso"] + 1), conferir=[]) for i, it in enumerate(itens)]
    return finais, [], ""
