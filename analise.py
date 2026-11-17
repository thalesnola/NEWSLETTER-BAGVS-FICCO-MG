"""Panorama das publicacoes do dia (sem IA, deterministico): palavras mais frequentes e instituicoes citadas.

Conta sobre TODAS as publicacoes coletadas na janela (inclusive as que viraram membro de um evento),
porque a pergunta e "do que se falou", e repeticao e justamente o sinal.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Palavras vazias do portugues + ruido tipico de legenda de rede social e de manchete.
_VAZIAS = set("""
a à ao aos as às até após com como contra da das de depois desde do dos e é ela elas ele eles em entre era essa
esse esta está estão este eu foi foram há isso isto já la lá lhe mais mas me mesmo muito na nas não nem no nos
nós o os ou para pela pelas pelo pelos por qual quando que quem se sem ser seu seus sua suas são também te tem
têm ter um uma umas uns você vai vão sobre onde cada todo toda todos todas outro outra outros outras ainda
bem pode podem deve devem sendo segundo segunda terça quarta quinta sexta sábado domingo ontem hoje amanhã
dia dias ano anos mês meses hora horas semana vez vezes nesta neste nessa nesse desta deste dessa desse
aqui ali assim então porque pois enquanto durante através cerca mil milhão milhões r$ via
the of and to in for on with
siga confira saiba veja link bio clique acesse instagram foto fotos vídeo vídeos post perfil oficial
leia mais notícia notícias g1 uol cnn redação após diz afirma informou
""".split())


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def palavras_top(publicacoes: list[dict], n: int = 20, extras: list[str] | None = None) -> list[tuple[str, int]]:
    """Conta em quantas publicacoes cada palavra aparece (uma vez por publicacao, para um post
    que repete a palavra 10 vezes nao dominar). Mostra a grafia mais comum, com acento."""
    vazias = {_sem_acento(w) for w in _VAZIAS | {x.lower() for x in (extras or [])}}
    docs, grafias = Counter(), {}
    for p in publicacoes:
        texto = re.sub(r"https?://\S+|@\w[\w.]*", " ", f"{p.get('titulo', '')} {p.get('trecho', '')}")
        vistas = set()
        for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", texto):
            chave = _sem_acento(w.lower())
            if chave in vazias:
                continue
            grafias.setdefault(chave, Counter())[w.lower()] += 1
            vistas.add(chave)
        docs.update(vistas)
    return [(grafias[k].most_common(1)[0][0], c) for k, c in docs.most_common(n)]


# Instituicao -> padroes no texto. Sigla em maiusculas casa caixa exata; o resto ignora caixa e acento.
INSTITUICOES = {
    "Polícia Federal": ["Polícia Federal", "PF"],
    "PRF": ["PRF", "PRF"],
    "Polícia Civil": ["Polícia Civil", "PCMG", "PC"],
    "Polícia Militar": ["Polícia Militar", "PMMG", "PM"],
    "Polícia Penal": ["Polícia Penal", "Depen", "Senappen", "policial penal", "policiais penais"],
    "Ministério Público": ["Ministério Público", "MPMG", "MPF", "Gaeco", "promotoria", "promotor", "procurador"],
    "Judiciário": ["STF", "STJ", "TJMG", "Supremo", "Tribunal de Justiça", "Superior Tribunal"],
    "Sejusp / MJSP": ["Sejusp", "Ministério da Justiça", "MJSP", "Força Nacional"],
    "Receita Federal": ["Receita Federal"],
    "Guarda Municipal": ["Guarda Municipal", "Guarda Civil"],
    "ABIN": ["ABIN", "Agência Brasileira de Inteligência"],
    "Corpo de Bombeiros": ["Corpo de Bombeiros", "bombeiros"],
}
# Post de perfil oficial conta para a propria instituicao mesmo sem cita-la na legenda.
PERFIS = {
    "policiafederal": "Polícia Federal", "prf": "PRF", "prf_mg": "PRF",
    "pcmg.oficial": "Polícia Civil", "pmmg.oficial": "Polícia Militar", "depenmg": "Polícia Penal",
    "senappen": "Polícia Penal", "policiapenalfederal": "Polícia Penal", "mpmg.oficial": "Ministério Público",
    "mpfederal": "Ministério Público", "cnmpoficial": "Ministério Público", "stjnoticias": "Judiciário",
    "supremotribunalfederal": "Judiciário", "tjmgoficial": "Judiciário",
    "cnj_oficial": "Judiciário", "seguranca.minas": "Sejusp / MJSP", "mjspgov": "Sejusp / MJSP",
    "abin_oficial": "ABIN",
}


def _padrao(termos: list[str]) -> list[re.Pattern]:
    out = []
    for t in termos:
        if t.isupper() and len(t) <= 6:
            out.append(re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])"))
        else:
            out.append(re.compile(r"(?<!\w)" + re.escape(_sem_acento(t.lower())) + r"(?!\w)"))
    return out


_COMPILADO = {k: _padrao(v) for k, v in INSTITUICOES.items()}


def instituicoes(publicacoes: list[dict]) -> list[tuple[str, int]]:
    """Em quantas publicacoes cada instituicao aparece (citada no texto ou autora do post)."""
    cont = Counter()
    for p in publicacoes:
        bruto = f"{p.get('titulo', '')} {p.get('trecho', '')}"
        baixo = _sem_acento(bruto.lower())
        achou = {PERFIS[p["perfil"]]} if p.get("perfil") in PERFIS else set()
        for nome, pads in _COMPILADO.items():
            if any(rx.search(bruto if rx.pattern.startswith("(?<![") else baixo) for rx in pads):
                achou.add(nome)
        cont.update(achou)
    return cont.most_common()
