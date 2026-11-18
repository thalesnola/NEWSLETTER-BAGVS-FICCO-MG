"""Gera docs/arquitetura-motion.svg (animado) e, com --png, docs/arquitetura-motion.png (Chrome/Edge headless).

Padrao visual Motion: largura 1000, fundo em gradiente lilas -> branco -> azul-claro, brilhos ambientes,
cartoes arredondados, tipografia Segoe UI Variable Display e faixa final escura. Sem <filter>: o GitHub
remove filtros de SVG exibido por <img>; brilho e sombra sao feitos com gradiente e retangulo deslocado.
A animacao e CSS dentro do SVG (fluxo nos conectores, entrada dos cartoes) e respeita prefers-reduced-motion.
"""
from __future__ import annotations

import base64
import io
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
VERSAO = (RAIZ / "VERSION").read_text(encoding="utf-8").strip()

W, H = 1000, 1170
NAVY, VIOLETA, AZUL, VERDE, TINTA, SUB = "#1B1F3B", "#6D4AFF", "#1E88E5", "#0F766E", "#1B1F3B", "#5A5F7A"
FONTE = "'Segoe UI Variable Display','Segoe UI',system-ui,-apple-system,Roboto,sans-serif"


def emblema_uri(px: int = 220) -> str:
    im = Image.open(AQUI / "emblema-bagvs-ficco-mg.png").convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def t(x, y, txt, size=15, peso=400, cor=TINTA, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{anchor}" {extra}>{escape(txt)}</text>')


def linhas(x, y, textos, size=14, cor=SUB, passo=19, peso=400):
    return "".join(t(x, y + i * passo, s, size, peso, cor) for i, s in enumerate(textos))


def cartao(x, y, w, h, rx=24, cor="#FFFFFF", borda="#E3DEF7", atraso=0.0, classe="entra"):
    return (f'<g class="{classe}" style="animation-delay:{atraso:.2f}s">'
            f'<rect x="{x + 3}" y="{y + 6}" width="{w}" height="{h}" rx="{rx}" fill="#1B1F3B" opacity=".06"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{cor}" stroke="{borda}" stroke-width="1.5"/>')


def no(n, x, y, titulo, desc, cor, atraso):
    w, h = 280, 150
    return (cartao(x, y, w, h, atraso=atraso)
            + f'<rect x="{x}" y="{y}" width="8" height="{h}" rx="4" fill="{cor}"/>'
            + f'<circle cx="{x + 40}" cy="{y + 38}" r="18" fill="{cor}"/>'
            + t(x + 40, y + 44, str(n), 17, 800, "#FFFFFF", "middle")
            + t(x + 68, y + 44, titulo, 18, 800, TINTA)
            + linhas(x + 24, y + 78, desc, 13.5)
            + "</g>")


def svg() -> str:
    em = emblema_uri()
    p = []
    p.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONTE}"
 role="img" aria-labelledby="titulo desc">
<title id="titulo">NEWSLETTER BAGVS/FICCO/MG v{VERSAO}: o que é, mapa de funcionamento e para que serve</title>
<desc id="desc">Fontes públicas e perfis oficiais do Instagram são coletados todo dia, agrupados por evento, resumidos por IA,
conferidos e entregues como painel HTML offline no canal privado do Telegram e por e-mail.</desc>
<defs>
 <linearGradient id="fundo" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#F3EEFF"/><stop offset=".5" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E9F7FF"/></linearGradient>
 <radialGradient id="brilhoV"><stop offset="0" stop-color="{VIOLETA}" stop-opacity=".22"/><stop offset="1" stop-color="{VIOLETA}" stop-opacity="0"/></radialGradient>
 <radialGradient id="brilhoA"><stop offset="0" stop-color="{AZUL}" stop-opacity=".20"/><stop offset="1" stop-color="{AZUL}" stop-opacity="0"/></radialGradient>
 <linearGradient id="faixa" x1="0" x2="1"><stop offset="0" stop-color="{NAVY}"/><stop offset="1" stop-color="#2A2F5A"/></linearGradient>
 <marker id="seta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0 0L10 5L0 10z" fill="{VIOLETA}"/></marker>
</defs>
<style>
 .entra{{opacity:0;animation:entra .7s ease-out forwards}}
 @keyframes entra{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
 .fluxo{{stroke-dasharray:7 9;animation:fluxo 1.1s linear infinite}}
 @keyframes fluxo{{to{{stroke-dashoffset:-32}}}}
 .pulso{{transform-box:fill-box;transform-origin:center;animation:pulso 2.4s ease-in-out infinite}}
 @keyframes pulso{{0%,100%{{transform:scale(1);opacity:.9}}50%{{transform:scale(1.18);opacity:.35}}}}
 .rastro{{animation:rastro 9s ease-in-out infinite alternate}}
 @keyframes rastro{{from{{transform:translateX(-30px) rotate(-12deg)}}to{{transform:translateX(30px) rotate(-12deg)}}}}
 @media (prefers-reduced-motion:reduce){{.entra,.fluxo,.pulso,.rastro{{animation:none;opacity:1}}}}
</style>
<rect width="{W}" height="{H}" fill="url(#fundo)"/>
<circle cx="120" cy="120" r="260" fill="url(#brilhoV)"/>
<circle cx="900" cy="560" r="300" fill="url(#brilhoA)"/>
<circle cx="180" cy="980" r="240" fill="url(#brilhoA)"/>
<g class="rastro" opacity=".5">
 <rect x="760" y="150" width="200" height="10" rx="5" fill="{VIOLETA}" opacity=".18"/>
 <rect x="790" y="172" width="160" height="8" rx="4" fill="{AZUL}" opacity=".16"/>
 <rect x="820" y="190" width="120" height="6" rx="3" fill="{VIOLETA}" opacity=".12"/>
</g>''')

    # ---- cabecalho
    p.append(f'<g class="entra"><image href="{em}" x="40" y="34" width="132" height="132"/>'
             + t(196, 78, "NEWSLETTER BAGVS/FICCO/MG", 34, 800)
             + t(196, 110, "Boletim diário de segurança pública que chega pronto no celular e abre sem internet", 16.5, 500, SUB)
             + f'<rect x="196" y="128" width="96" height="30" rx="15" fill="{VIOLETA}"/>'
             + t(244, 148, f"v{VERSAO}", 14, 800, "#FFFFFF", "middle")
             + f'<rect x="302" y="128" width="236" height="30" rx="15" fill="#FFFFFF" stroke="#E3DEF7"/>'
             + t(420, 148, "BAGVS/FICCO/MG · Minas Gerais", 13.5, 700, NAVY, "middle")
             + "</g>")

    # ---- 1. o que e
    y = 196
    p.append(t(40, y, "O QUE É", 13, 800, VIOLETA, extra='letter-spacing="2"'))
    p.append(cartao(40, y + 14, 920, 112, atraso=.15)
             + f'<rect x="40" y="{y + 14}" width="8" height="112" rx="4" fill="{VIOLETA}"/>'
             + linhas(70, y + 50, [
                 "Uma ferramenta que, todo dia, lê notícias públicas e posts de perfis oficiais (PF, PRF, PCMG, PMMG, MPMG, STF, STJ…),",
                 "junta tudo o que fala do mesmo fato num único evento, resume com IA, confere o resumo contra a fonte e entrega",
                 "um painel HTML de arquivo único: abre offline no celular, com destaques, temas, gráficos e todos os links."],
                 15, TINTA, 25)
             + "</g>")

    # ---- 2. mapa (serpentina 3 + 3)
    y = 356
    p.append(t(40, y, "MAPA DE FUNCIONAMENTO", 13, 800, VIOLETA, extra='letter-spacing="2"'))
    col = [40, 360, 680]
    l1, l2 = y + 26, y + 236
    nos = [
        (1, col[0], l1, "Fontes", ["RSS e buscas do Google News", "24 perfis oficiais no Instagram", "(API oficial da Meta)"], VIOLETA),
        (2, col[1], l1, "Coleta", ["Janela das últimas 30 h", "Palavras-chave por fonte", "Falha de uma fonte não para as outras"], VIOLETA),
        (3, col[2], l1, "Eventos", ["Mesmo link ou título parecido = 1 evento", "Histórico: o que já saiu não volta", "A IA junta o mesmo fato com outro título"], AZUL),
        (4, col[2], l2, "Resumo + conferência", ["IA resume o evento com todas as versões", "Link sempre vem da fonte, nunca da IA", "Número sem fonte ganha alerta"], AZUL),
        (5, col[1], l2, "Painel offline", ["Destaques, filtro por tema e busca", "20 palavras e instituições mais citadas", "Emblemas, assinatura e podcast do dia"], VERDE),
        (6, col[0], l2, "Entrega", ["Telegram: painel HTML + podcast", "E-mail com o painel anexo", "Cópia na pasta sincronizada do celular"], VERDE),
    ]
    # conectores (atras dos cartoes)
    con = [
        f"M{col[0] + 280} {l1 + 75} H{col[1] - 8}",
        f"M{col[1] + 280} {l1 + 75} H{col[2] - 8}",
        f"M{col[2] + 140} {l1 + 150} V{l2 - 8}",
        f"M{col[2]} {l2 + 75} H{col[1] + 280 + 8}",
        f"M{col[1]} {l2 + 75} H{col[0] + 280 + 8}",
    ]
    for d in con:
        p.append(f'<path d="{d}" stroke="{VIOLETA}" stroke-opacity=".25" stroke-width="6" fill="none" stroke-linecap="round"/>'
                 f'<path class="fluxo" d="{d}" stroke="{VIOLETA}" stroke-width="2.5" fill="none" marker-end="url(#seta)"/>')
    for i, (n, x, yy, tit, desc, cor) in enumerate(nos):
        p.append(no(n, x, yy, tit, desc, cor, .25 + i * .12))
    # agendador
    ya = l2 + 172
    p.append(cartao(40, ya, 920, 58, rx=29, cor=NAVY, borda=NAVY, atraso=1.0)
             + f'<circle class="pulso" cx="76" cy="{ya + 29}" r="11" fill="#7CF2C8"/>'
             + f'<circle cx="76" cy="{ya + 29}" r="6" fill="#7CF2C8"/>'
             + t(100, ya + 35, "Agendador do Windows: roda sozinho às 05:30 · vigia às 07:30 avisa se o boletim não saiu", 15.5, 600, "#FFFFFF")
             + "</g>")

    # ---- 3. para que serve
    y = ya + 100
    p.append(t(40, y, "PARA QUE SERVE", 13, 800, VIOLETA, extra='letter-spacing="2"'))
    usos = [
        ("Começar o dia informado", ["Operações, prisões, decisões do", "STF/STJ e normas novas, de MG", "e do país, num só lugar."], VIOLETA),
        ("Menos ruído, mais fonte", ["O mesmo fato aparece uma vez,", "com todos os links que o citam e", "quem mais apareceu no dia."], AZUL),
        ("Leitura em campo", ["Arquivo único no celular, sem", "login e sem internet para abrir.", "Só os links pedem rede."], VERDE),
    ]
    for i, (tit, desc, cor) in enumerate(usos):
        x = 40 + i * 316
        p.append(cartao(x, y + 14, 288, 138, atraso=1.15 + i * .12)
                 + f'<rect x="{x + 24}" y="{y + 36}" width="40" height="6" rx="3" fill="{cor}"/>'
                 + t(x + 24, y + 68, tit, 17.5, 800)
                 + linhas(x + 24, y + 94, desc, 14, SUB, 20)
                 + "</g>")

    # ---- faixa final
    yf = H - 92
    p.append(f'<rect x="0" y="{yf}" width="{W}" height="92" fill="url(#faixa)"/>'
             + t(40, yf + 40, "Coleta pública → evento único → resumo conferido → painel offline no canal da equipe", 18, 800, "#FFFFFF")
             + t(40, yf + 68, f"BAGVS/FICCO/MG · v{VERSAO} · apfnola, 24099 - thales.tnb", 14, 600, "#C9C6F5"))
    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    destino = AQUI / "arquitetura-motion.svg"
    destino.write_text(svg(), encoding="utf-8")
    print("SVG:", destino, f"{destino.stat().st_size // 1024} KB")
    if "--png" in sys.argv:
        nav = next((c for c in (shutil.which("chrome"), shutil.which("msedge"),
                                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") if c and Path(c).exists()), None)
        if not nav:
            sys.exit("Chrome/Edge nao encontrado para o PNG")
        png = AQUI / "arquitetura-motion.png"
        html = AQUI / "_render.html"
        # congela a animacao no estado final para a imagem estatica
        html.write_text("<style>html,body{margin:0}*{animation-duration:0s!important;animation-delay:0s!important}</style>"
                        + destino.read_text(encoding="utf-8").replace('class="entra"', 'class=""'), encoding="utf-8")
        subprocess.run([nav, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1.6",
                        f"--window-size={W},{H}", f"--screenshot={png}", html.as_uri()], check=True,
                       capture_output=True, timeout=120)
        html.unlink()
        print("PNG:", png, f"{png.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
