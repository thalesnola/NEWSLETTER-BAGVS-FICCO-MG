import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import coleta  # noqa: E402
import dedup  # noqa: E402
import ia  # noqa: E402
import painel  # noqa: E402
from boletim import selecionar  # noqa: E402


def item(titulo, url, fonte="A", peso=1, trecho="", veiculo=""):
    return {"fonte": fonte, "veiculo": veiculo, "peso": peso, "titulo": titulo, "url": url,
            "trecho": trecho, "publicado": "2026-11-14T12:00:00+00:00"}


def test_url_norm_tira_rastreio_e_www():
    a = dedup.url_norm("http://www.site.com/x/?utm_source=tg&id=3#topo")
    assert a == dedup.url_norm("https://site.com/x?id=3")


def test_dedup_por_titulo_mantem_maior_peso_e_registra_veiculo():
    its = [item("PF deflagra operação contra facção em Valadares", "https://a.com/1", "A", 1, veiculo="Jornal A"),
           item("PF deflagra operação contra facção em Valadares - atualizado", "https://b.com/2", "B", 3)]
    unicos, rem = dedup.deduplicar(its)
    assert rem == 1 and unicos[0]["fonte"] == "B" and unicos[0]["tambem_em"] == ["Jornal A"]


def test_dedup_nao_junta_noticias_diferentes():
    its = [item("STJ julga prova digital", "https://a.com/1"), item("Lei nova sobre armas é sancionada", "https://a.com/2")]
    assert dedup.deduplicar(its)[1] == 0


def test_historico_bloqueia_dia_anterior_mas_nao_o_mesmo_dia(tmp_path):
    h = dedup.Historico(tmp_path / "h.db")
    u, _ = dedup.deduplicar([item("Notícia velha de ontem", "https://a.com/1")])
    h.registrar("ed", "2026-11-14", u)
    assert h.filtrar_novos("ed", u, 21, "2026-11-15")[1] == 1
    assert h.filtrar_novos("ed", u, 21, "2026-11-14")[1] == 0


def test_data_pt_do_stj():
    d = coleta._data_pt("Sex, nov 13 2026 19:15:00")
    assert d.astimezone(timezone.utc) == datetime(2026, 11, 13, 22, 15, tzinfo=timezone.utc)
    assert coleta._data_pt("sem data") is None


def test_palavras_sigla_casa_caixa_exata():
    assert coleta._casa_palavras(["AI"], "New AI model")
    assert not coleta._casa_palavras(["AI"], "ai que dor")
    assert coleta._casa_palavras(["tráfico"], "Operação contra TRÁFICO")


def test_conferir_descarta_id_invalido_tema_estranho_e_marca_numero_inventado():
    lote, _ = dedup.deduplicar([item("Empresa lança modelo", "https://a.com/1", trecho="custa 20 dólares"),
                                item("Outra coisa", "https://a.com/2")])
    resp = {"visao_geral": "ok", "destaques": [0, 9],
            "itens": [{"id": 0, "titulo": "T", "resumo": "Custa 20 e tem 4096 tokens", "tema": "X", "relevancia": 9},
                      {"id": 9, "titulo": "fantasma"}, {"id": "abc"}]}
    finais, dest, visao, avisos = ia.conferir(resp, lote, ["Modelos"])
    assert [f["id"] for f in finais] == [0] and dest == [0] and len(avisos) == 2
    f = finais[0]
    assert f["tema"] == "Outros" and f["relevancia"] == 5 and f["conferir"] == ["4096"]
    assert f["url"] == "https://a.com/1"          # link vem da coleta, nunca da IA


def test_selecionar_rodizio_por_peso():
    its = [item(f"a{i}", f"https://a/{i}", "A", 1) for i in range(5)] + [item(f"b{i}", f"https://b/{i}", "B", 3) for i in range(5)]
    sel = selecionar(its, 4)
    assert [x["fonte"] for x in sel] == ["B", "A", "B", "A"]


def test_painel_escapa_html_e_funciona_sem_itens():
    ed = {"nome": "t", "titulo": "Teste", "temas": ["Um"], "destaques": 3}
    agora = datetime(2026, 11, 15, 6, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    vazio = painel.gerar(ed, "2026-11-15", agora, [], [], "", [], {"coletados": 0, "repetidas": 0}, [])
    assert "Nada novo" in vazio
    assert 'src="http' not in vazio and "@import" not in vazio and "url(" not in vazio   # 100% offline
    lote, _ = dedup.deduplicar([item("<script>x</script>", "https://a.com/1")])
    finais, dest, _ = ia.sem_ia(lote)
    pg = painel.gerar(ed, "2026-11-15", agora, finais, dest, "", [{"fonte": "A", "itens": 1, "erro": None}],
                      {"coletados": 1, "repetidas": 0}, [])
    assert "<script>x</script>" not in pg and "&lt;script&gt;" in pg


def test_dedup_guarda_os_links_repetidos_como_membros_do_evento():
    its = [item("PF prende chefe de facção em Governador Valadares", "https://a.com/1", "A", 3),
           item("PF prende chefe de facção em Governador Valadares hoje", "https://b.com/2", "B", 1, veiculo="Jornal B")]
    ev, n = dedup.deduplicar(its)
    assert n == 1 and [m["url"] for m in ev[0]["membros"]] == ["https://b.com/2"]
    assert ev[0]["membros"][0]["veiculo"] == "Jornal B"


def test_conferir_junta_links_das_duplicatas_apontadas_pela_ia():
    lote, _ = dedup.deduplicar([item("Operação Alfa prende 10", "https://a.com/1"),
                                item("Dez presos em ação policial no Vale", "https://b.com/2", "B")])
    resp = {"itens": [{"id": 0, "titulo": "T", "resumo": "R", "tema": "X", "relevancia": 3, "duplicatas": [1]}]}
    finais, *_ = ia.conferir(resp, lote, ["X"])
    assert len(finais) == 1 and [m["url"] for m in finais[0]["membros"]] == ["https://b.com/2"]


def test_panorama_conta_por_publicacao_e_instituicao_por_perfil():
    import analise
    pubs = [{"titulo": "Polícia Civil prende suspeito", "trecho": "tráfico tráfico tráfico"},
            {"titulo": "Operação contra o tráfico", "trecho": "PF cumpre mandados"},
            {"titulo": "Novo comandante", "trecho": "", "perfil": "pmmg.oficial"},
            {"titulo": "Placa PFX123 apreendida", "trecho": "pc gamer"}]
    top = dict(analise.palavras_top(pubs, 5))
    assert top["tráfico"] == 2                          # uma vez por publicacao
    inst = dict(analise.instituicoes(pubs))
    assert inst == {"Polícia Civil": 1, "Polícia Federal": 1, "Polícia Militar": 1}   # sigla nao casa dentro de palavra


def test_painel_embute_audio_e_escapa_roteiro():
    agora = datetime(2026, 11, 15, 5, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
    ed = {"nome": "x", "titulo": "T", "temas": []}
    faixa = {"mp3": b"ID3fake", "segundos": 125, "roteiro": "Primeiro <b>evento</b>.\nSegundo."}
    html = painel.gerar(ed, "2026-11-15", agora, [], [], "", [], {"coletados": 0, "repetidas": 0}, [], faixa=faixa)
    assert 'src="data:audio/mpeg;base64,SUQzZmFrZQ=="' in html and "2:05" in html
    assert "&lt;b&gt;evento" in html and "<p>Segundo.</p>" in html


def test_audio_sem_kokoro_devolve_none(tmp_path):
    import audio
    assert audio.gerar_mp3("texto", {"python": str(tmp_path / "nao-existe.exe")}) is None
    assert audio.gerar_mp3("", {}) is None
