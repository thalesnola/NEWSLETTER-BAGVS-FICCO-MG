import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configurar_telegram as ct  # noqa: E402
import entrega  # noqa: E402


def test_token_proprio_vence_e_o_do_radar_fica_de_fallback(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN_PAINEL", raising=False)
    monkeypatch.setenv("TELEGRAM_TOKEN", "radar")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    assert entrega.token() == "radar" and entrega.telegram_configurado()
    monkeypatch.setenv("TELEGRAM_TOKEN_PAINEL", "painel")
    assert entrega.token() == "painel"


def test_chat_proprio_e_da_edicao_vencem(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.delenv("TELEGRAM_CHAT_ID_PAINEL", raising=False)
    monkeypatch.setattr(entrega, "CHAT_EDICAO", None)
    assert entrega.chat_id() == "1"
    monkeypatch.setenv("TELEGRAM_CHAT_ID_PAINEL", "2")
    assert entrega.chat_id() == "2"
    monkeypatch.setattr(entrega, "CHAT_EDICAO", "-100")
    assert entrega.chat_id() == "-100"


def test_gravar_env_troca_so_a_chave_nova_e_preserva_o_resto(tmp_path):
    arq = tmp_path / ".env"
    original = b"# radar\r\nTELEGRAM_TOKEN=velho\r\nTELEGRAM_TOKEN_RELATORIO=r\r\nTELEGRAM_CHAT_ID=1"
    arq.write_bytes(original)
    copia = ct.gravar_env(arq, {"TELEGRAM_TOKEN_PAINEL": "novo"})
    assert copia.read_bytes() == original
    assert arq.read_bytes() == original + b"\r\nTELEGRAM_TOKEN_PAINEL=novo\r\n"
    ct.gravar_env(arq, {"TELEGRAM_TOKEN_PAINEL": "outro"})
    linhas = arq.read_text(encoding="utf-8").splitlines()
    assert linhas == ["# radar", "TELEGRAM_TOKEN=velho", "TELEGRAM_TOKEN_RELATORIO=r",
                      "TELEGRAM_CHAT_ID=1", "TELEGRAM_TOKEN_PAINEL=outro"]
