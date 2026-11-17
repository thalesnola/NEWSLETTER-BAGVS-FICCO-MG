"""Painel HTML offline, um arquivo so, pensado para o celular.

Tudo vem renderizado no servidor (abre ate no visualizador do app Arquivos/Telegram, que nao roda
JavaScript). O filtro por tema funciona so com CSS (radio + :checked). Busca e "lido" sao
melhorias em JS que somem sem prejuizo quando o visualizador nao executa script.
Nenhum recurso externo: sem CDN, sem fonte web, sem imagem remota.
"""
from __future__ import annotations

import html
import re
from datetime import datetime

CSS = """
:root{--bg:#f6f6f4;--card:#fff;--tx:#1b1b1f;--sub:#62626b;--linha:#e4e4e0;--acc:%(cor)s;--aviso:#a15c00;--aviso-bg:#fff4e0}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--card:#1c1c20;--tx:#ececef;--sub:#a0a0aa;--linha:#2c2c32;--aviso:#ffb454;--aviso-bg:#2e2412}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%%}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0)}
main{max-width:720px;margin:0 auto;padding:16px 16px 48px}
header{padding:8px 0 4px}
.marca{font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--acc)}
h1{font-size:26px;line-height:1.2;margin:4px 0 2px}
.sub{color:var(--sub);font-size:14px}
.nums{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:12px 0 4px}
.num{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:8px 10px;font-size:12px;line-height:1.25;color:var(--sub)}
.num b{display:block;font-size:20px;color:var(--tx);font-variant-numeric:tabular-nums}
.audio{background:var(--card);border-radius:12px;padding:12px 16px;margin:16px 0}
.audio-t{font-weight:700;margin-bottom:8px}.audio audio{width:100%%}
.audio details{margin-top:8px}.audio summary{cursor:pointer;color:var(--acc)}.audio p{margin:8px 0}
.visao{background:var(--card);border-left:4px solid var(--acc);border-radius:12px;padding:14px 16px;margin:16px 0}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:var(--sub);margin:28px 0 10px}
.card{background:var(--card);border:1px solid var(--linha);border-radius:14px;padding:14px 16px;margin:0 0 10px}
.card.dest{border-color:var(--acc);border-width:1.5px}
.meta{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;font-size:12.5px;color:var(--sub);margin-bottom:6px}
.tema{color:var(--acc);font-weight:600}
.rel{letter-spacing:1px;color:var(--acc)}
.card h3{font-size:17px;line-height:1.35;margin:0 0 6px}
.card h3 a{color:inherit;text-decoration:none}
.card p{margin:0 0 8px}
.orig{font-size:13px;color:var(--sub);font-style:italic;margin-bottom:6px}
.rodape{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;font-size:13px}
.rodape a{color:var(--acc);font-weight:600;text-decoration:none;padding:6px 0}
.tambem{color:var(--sub)}
.conferir{display:inline-block;background:var(--aviso-bg);color:var(--aviso);border-radius:8px;padding:2px 8px;font-size:12px;margin-bottom:6px}
.filtros{position:sticky;top:env(safe-area-inset-top,0);z-index:2;background:var(--bg);padding:8px 0;margin:0 -16px;padding-inline:16px;
 display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;border-bottom:1px solid var(--linha)}
.filtros::-webkit-scrollbar{display:none}
.filtros input{position:absolute;opacity:0;pointer-events:none}
.filtros label{flex:none;border:1px solid var(--linha);background:var(--card);border-radius:999px;padding:6px 12px;font-size:14px;white-space:nowrap;cursor:pointer}
.filtros label small{color:var(--sub);margin-left:4px}
.busca{display:none;width:100%%;margin:12px 0 4px;padding:10px 12px;font-size:16px;border:1px solid var(--linha);border-radius:10px;background:var(--card);color:var(--tx)}
.js .busca{display:block}
.lido-bt{display:none;border:0;background:none;color:var(--sub);font-size:13px;padding:6px 0;cursor:pointer}
.js .lido-bt{display:inline}
.card.lido{opacity:.5}
.card.lido .lido-bt::before{content:"✓ "}
details{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:10px 14px;margin:10px 0;font-size:14px}
summary{cursor:pointer;font-weight:600}
table{width:100%%;border-collapse:collapse;margin-top:8px}td{padding:4px 0;border-top:1px solid var(--linha);vertical-align:top}
td.n{text-align:right;font-variant-numeric:tabular-nums;width:3em}.erro{color:var(--aviso)}
footer{color:var(--sub);font-size:12.5px;margin-top:24px}
.topo{display:flex;align-items:center;gap:14px}
.emblemas{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:4px 8px 12px;
 border-bottom:1px solid var(--linha);margin-bottom:12px}
.emblemas img{width:104px;height:104px;object-fit:contain}
.emblemas img:only-child{margin:0 auto}
.links{margin:8px 0 2px;padding:8px 12px;font-size:14px}
.links ol{margin:6px 0 0;padding-left:20px}.links li{margin:4px 0}
.links a{color:var(--acc);text-decoration:none}.links small{color:var(--sub)}
.graf{background:var(--card);border:1px solid var(--linha);border-radius:14px;padding:14px 16px;margin:0 0 10px}
.graf h3{font-size:16px;margin:0 0 2px}.graf .sub{font-size:12.5px;margin-bottom:10px}
.bar{display:grid;grid-template-columns:minmax(0,9.5em) 1fr 2.6em;align-items:center;gap:8px;font-size:13.5px;min-height:22px}
.bar .r{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar .t{height:12px}.bar .f{height:12px;background:var(--acc);border-radius:0 4px 4px 0;min-width:2px}
.bar .v{text-align:right;font-variant-numeric:tabular-nums;color:var(--tx)}
.assin{margin-top:10px;font-weight:600;color:var(--tx)}
"""

JS = r"""
document.documentElement.classList.add('js');
(function(){
  var chave='boletim:'+document.body.dataset.edicao+':lidos', lidos={};
  try{lidos=JSON.parse(localStorage.getItem(chave)||'{}')}catch(e){}
  function salvar(){try{localStorage.setItem(chave,JSON.stringify(lidos))}catch(e){}}
  document.querySelectorAll('.card[data-k]').forEach(function(c){
    if(lidos[c.dataset.k])c.classList.add('lido');
    var b=c.querySelector('.lido-bt'); if(!b)return;
    b.addEventListener('click',function(){var k=c.dataset.k;
      if(lidos[k]){delete lidos[k]}else{lidos[k]=Date.now()}
      document.querySelectorAll('.card[data-k="'+k+'"]').forEach(function(x){x.classList.toggle('lido',!!lidos[k])});salvar();});
    c.querySelectorAll('a.ext').forEach(function(a){a.addEventListener('click',function(){
      lidos[c.dataset.k]=Date.now();c.classList.add('lido');salvar();})});
  });
  var q=document.getElementById('q'); if(!q)return;
  function norm(s){return s.toLowerCase().normalize('NFD').split('').filter(function(c){
    var k=c.charCodeAt(0);return k<768||k>879}).join('')}
  q.addEventListener('input',function(){var t=norm(q.value.trim());
    document.querySelectorAll('#lista .card').forEach(function(c){
      c.style.display=(!t||norm(c.textContent).indexOf(t)>=0)?'':'none'})});
})();
"""


def bloco_audio(faixa: dict) -> str:
    """MP3 embutido (data URI): toca offline, sem script; o roteiro fica abaixo para quem prefere ler."""
    import base64
    s = int(faixa.get("segundos") or 0)
    uri = "data:audio/mpeg;base64," + base64.b64encode(faixa["mp3"]).decode()
    paragrafos = "".join(f"<p>{_e(p)}</p>" for p in str(faixa.get("roteiro") or "").splitlines() if p.strip())
    return (f'<section class="audio"><div class="audio-t">🎧 Resumo em áudio · {s // 60}:{s % 60:02d}</div>'
            f'<audio controls preload="metadata" src="{uri}"></audio>'
            + (f'<details><summary>Ler o roteiro</summary>{paragrafos}</details>' if paragrafos else "")
            + "</section>")


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


_PT = set("de da do das dos em no na que para com por uma um os as ao à é não mais sobre".split())
_EN = set("the of and to for with in on is are from how why what new your this that".split())


def _estrangeiro(titulo: str) -> bool:
    """Titulo original so aparece quando parece ingles (traducao): leitor confere o termo exato."""
    w = re.findall(r"[a-zà-ú]+", titulo.lower())
    return sum(x in _EN for x in w) > sum(x in _PT for x in w)


def _classe(tema: str) -> str:
    return "t-" + re.sub(r"[^a-z0-9]+", "-", tema.lower()).strip("-")


def _hora(iso: str | None, fuso) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).astimezone(fuso).strftime("%d/%m %H:%M")
    except Exception:
        return ""


def _card(it: dict, fuso, destaque: bool = False) -> str:
    fonte = it.get("veiculo") or it["fonte"]
    tambem = (f'<span class="tambem">também em {_e(", ".join(it["tambem_em"][:4]))}</span>'
              if it.get("tambem_em") and not it.get("membros") else "<span></span>")
    orig = f'<div class="orig">{_e(it["titulo"])}</div>' if _estrangeiro(it["titulo"]) else ""
    conferir = (f'<div class="conferir">⚠ conferir na fonte: {_e(", ".join(it["conferir"][:4]))}</div>'
                if it.get("conferir") else "")
    rel = "●" * it["relevancia"] + "○" * (5 - it["relevancia"])
    todos = [{"veiculo": fonte, "titulo": it["titulo"], "url": it["url"]}] + list(it.get("membros") or [])
    links = ""
    if len(todos) > 1:
        links = (f'<details class="links" open><summary>{len(todos)} links sobre este evento</summary><ol>' + "".join(
            f'<li><a class="ext" href="{_e(m["url"])}" target="_blank" rel="noopener noreferrer">{_e(m["titulo"][:140])}</a>'
            f' <small>· {_e(m["veiculo"])}</small></li>' for m in todos) + "</ol></details>")
    return (
        f'<article class="card{" dest" if destaque else ""} {_classe(it["tema"])}" data-k="{_e(it["_u"])}">'
        f'<div class="meta"><span class="tema">{_e(it["tema"])}</span><span>{_e(fonte)}</span>'
        f'<span>{_hora(it.get("publicado"), fuso)}</span><span class="rel" title="relevância {it["relevancia"]}/5">{rel}</span></div>'
        f'<h3><a class="ext" href="{_e(it["url"])}" target="_blank" rel="noopener noreferrer">{_e(it["titulo_pt"])}</a></h3>'
        f'{orig}{conferir}<p>{_e(it["resumo"])}</p>{links}'
        f'<div class="rodape">{tambem}<span><button class="lido-bt" type="button">lido</button> · '
        f'<a class="ext" href="{_e(it["url"])}" target="_blank" rel="noopener noreferrer">abrir fonte ↗</a></span></div>'
        f'</article>')


def grafico_barras(titulo: str, sub: str, dados: list[tuple[str, int]], unidade: str) -> str:
    """Barras horizontais em HTML/CSS puro (renderiza sem JS), uma cor, ordenadas, valor na ponta."""
    if not dados:
        return ""
    topo = max(v for _, v in dados) or 1
    linhas = "".join(
        f'<div class="bar" title="{_e(r)}: {v} {unidade}"><span class="r">{_e(r)}</span>'
        f'<span class="t"><span class="f" style="display:block;width:{100 * v / topo:.1f}%"></span></span>'
        f'<span class="v">{v}</span></div>' for r, v in dados)
    return f'<section class="graf"><h3>{_e(titulo)}</h3><div class="sub">{_e(sub)}</div>{linhas}</section>'


def gerar(edicao: dict, dia: str, agora: datetime, itens: list[dict], destaques: list[int],
          visao: str, status: list[dict], stats: dict, avisos: list[str],
          panorama: dict | None = None, identidade: dict | None = None, faixa: dict | None = None) -> str:
    fuso = agora.tzinfo
    ordem = sorted(itens, key=lambda x: x.get("publicado") or "", reverse=True)
    ordem = sorted(ordem, key=lambda x: -x["relevancia"])   # estavel: relevancia, depois mais recente
    por_id = {it["id"]: it for it in itens}
    dest = [por_id[d] for d in destaques if d in por_id][: int(edicao.get("destaques", 5))]
    temas = [t for t in list(edicao.get("temas") or []) + ["Outros"] if any(i["tema"] == t for i in itens)]
    temas += sorted({i["tema"] for i in itens} - set(temas))

    # filtro por tema so com CSS: cada radio esconde os cards de outros temas
    css_filtro = "".join(
        f'#f{n}:checked~#lista .card:not(.{_classe(t)}){{display:none}}'
        f'#f{n}:checked~.filtros label[for=f{n}]{{background:var(--acc);color:#fff;border-color:var(--acc)}}'
        for n, t in enumerate(temas, 1))
    css_filtro += "#f0:checked~.filtros label[for=f0]{background:var(--acc);color:#fff;border-color:var(--acc)}"
    radios = '<input type="radio" name="f" id="f0" checked hidden>' + "".join(
        f'<input type="radio" name="f" id="f{n}" hidden>' for n in range(1, len(temas) + 1))
    chips = (f'<label for="f0">Tudo<small>{len(itens)}</small></label>' + "".join(
        f'<label for="f{n}">{_e(t)}<small>{sum(1 for i in itens if i["tema"] == t)}</small></label>'
        for n, t in enumerate(temas, 1)))

    falhas = [s for s in status if s["erro"]]
    linhas_fontes = "".join(
        f'<tr><td>{_e(s["fonte"])}{"<br><span class=erro>" + _e(s["erro"]) + "</span>" if s["erro"] else ""}</td>'
        f'<td class="n">{s["itens"]}</td></tr>' for s in status)

    h = [
        f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<meta name="color-scheme" content="light dark">'
        f'<title>{_e(edicao["titulo"])} · {agora:%d/%m/%Y}</title>'
        f'<style>{CSS % {"cor": edicao.get("cor", "#5b5bd6")}}{css_filtro}</style></head>'
        f'<body data-edicao="{_e(edicao["nome"])}"><main>',
        (f'<div class="emblemas">' + "".join(f'<img src="{u}" alt="{_e(a)}">' for u, a in identidade["logos"])
         + '</div>' if identidade and identidade.get("logos") else "")
        + f'<header class="topo">'

        + f'<div><div class="marca">{_e(edicao["titulo"])}</div>'
        f'<h1>{agora:%d/%m/%Y}</h1><div class="sub">{_e(edicao.get("descricao", ""))}</div></div></header>',
        f'<div class="nums"><div class="num"><b>{len(itens)}</b>eventos</div>'
        f'<div class="num"><b>{stats["coletados"]}</b>publicações</div>'
        f'<div class="num"><b>{stats["repetidas"]}</b>agrupadas</div>'
        f'<div class="num"><b>{len(status) - len(falhas)}/{len(status)}</b>fontes ok</div></div>',
    ]
    if visao:
        h.append(f'<div class="visao">{_e(visao)}</div>')
    if faixa:
        h.append(bloco_audio(faixa))
    if not itens:
        h.append('<div class="card">Nada novo dentro do foco desta edição hoje.</div>')
    if panorama and (panorama.get("palavras") or panorama.get("instituicoes")):
        h.append("<h2>Panorama das publicações</h2>"
                 + grafico_barras("Instituições mais presentes",
                                  f"Em quantas das {stats['coletados']} publicações cada instituição aparece "
                                  "(citada no texto ou autora do post)", panorama.get("instituicoes") or [], "publicações")
                 + grafico_barras(f"{len(panorama.get('palavras') or [])} palavras mais frequentes",
                                  f"Em quantas publicações cada palavra aparece (títulos, trechos e legendas)",
                                  panorama.get("palavras") or [], "publicações"))
    if dest:
        h.append("<h2>Destaques</h2>" + "".join(_card(it, fuso, True) for it in dest))
    if itens:
        h.append(f'<h2>Todas as notícias</h2>{radios}<div class="filtros">{chips}</div>'
                 f'<input id="q" class="busca" type="search" placeholder="Buscar nesta edição" autocomplete="off">'
                 f'<div id="lista">' + "".join(_card(it, fuso) for it in ordem) + "</div>")
    h.append(f'<details{" open" if falhas else ""}><summary>Fontes ({len(status) - len(falhas)} ok'
             f'{", " + str(len(falhas)) + " com falha" if falhas else ""})</summary><table>{linhas_fontes}</table></details>')
    if avisos:
        h.append("<details><summary>Avisos da conferência</summary><ul>" +
                 "".join(f"<li>{_e(a)}</li>" for a in avisos) + "</ul></details>")
    h.append(f'<footer>Gerado em {agora:%d/%m/%Y %H:%M} · {stats.get("modo", "")} · '
             f'Resumos feitos por IA a partir do título e do trecho de cada fonte; confira o original antes de citar.'
             f' Arquivo offline: os links levam à fonte e precisam de rede.'
             + (f'<div class="assin">{_e(identidade["assinatura"])} · {agora:%d/%m/%Y}</div>'
                if identidade and identidade.get("assinatura") else "") + '</footer>')
    h.append(f"</main><script>{JS}</script></body></html>")
    return "".join(h)


# ---------------------------------------------------------------- e-mail e Telegram

def _te(x) -> str:
    return html.escape(str(x or ""), quote=False)


def texto_email(edicao: dict, agora: datetime, itens: list[dict], destaques: list[int], visao: str) -> tuple[str, str]:
    """Corpo do e-mail (clientes de e-mail cortam CSS/JS: HTML simples, painel vai anexo)."""
    por_id = {it["id"]: it for it in itens}
    top = [por_id[d] for d in destaques if d in por_id] or sorted(itens, key=lambda x: -x["relevancia"])[:5]
    cor = edicao.get("cor", "#5b5bd6")
    blocos = "".join(
        f'<p style="margin:0 0 14px"><a href="{_e(it["url"])}" style="color:{cor};font-weight:600;text-decoration:none">'
        f'{_te(it["titulo_pt"])}</a><br><span style="color:#666;font-size:13px">{_te(it["tema"])} · '
        f'{_te(it.get("veiculo") or it["fonte"])}</span><br>{_te(it["resumo"])}</p>' for it in top)
    html_ = (f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;font-size:15px;line-height:1.5">'
             f'<div style="color:{cor};font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.06em">{_te(edicao["titulo"])}</div>'
             f'<h2 style="margin:4px 0 12px">{agora:%d/%m/%Y} · {len(itens)} notícias</h2>'
             + (f'<p style="border-left:3px solid {cor};padding-left:10px">{_te(visao)}</p>' if visao else "")
             + f'<h3>Destaques</h3>{blocos}<p style="color:#666;font-size:13px">O painel completo, com filtro por tema e busca, '
             f'está anexo: abra o arquivo .html no celular, funciona offline.</p></div>')
    texto = f"{edicao['titulo']} · {agora:%d/%m/%Y}\n\n" + (visao + "\n\n" if visao else "") + "\n\n".join(
        f"• {it['titulo_pt']}\n  {it['resumo']}\n  {it['url']}" for it in top)
    return texto, html_


def texto_telegram(edicao: dict, agora: datetime, itens: list[dict], destaques: list[int], visao: str) -> str:
    por_id = {it["id"]: it for it in itens}
    top = [por_id[d] for d in destaques if d in por_id] or sorted(itens, key=lambda x: -x["relevancia"])[:5]
    partes = [f"<b>{_te(edicao['titulo'])}</b> · {agora:%d/%m/%Y} · {len(itens)} notícias"]
    if visao:
        partes.append(_te(visao))
    for n, it in enumerate(top, 1):
        partes.append(f'{n}. <a href="{_e(it["url"])}">{_te(it["titulo_pt"])}</a>\n<i>{_te(it["tema"])}</i> · {_te(it["resumo"])}')
    partes.append("📎 Painel completo no arquivo abaixo (abre offline).")
    return "\n\n".join(partes)
