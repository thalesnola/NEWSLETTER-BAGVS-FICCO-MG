"""Resumo em audio: roteiro escrito pela IA -> voz local (Kokoro) -> MP3 mono.

Tudo local: o texto nao vai a servico de voz na nuvem. Falha nunca derruba o boletim: devolve None e o
painel sai sem o bloco de audio.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

log = logging.getLogger("boletim.audio")
AQUI = Path(__file__).resolve().parent


def gerar_mp3(roteiro: str, cfg: dict) -> tuple[bytes, float] | None:
    """Devolve (mp3, segundos) ou None. cfg = [audio] do config.toml."""
    roteiro = (roteiro or "").strip()
    py = Path(cfg.get("python", "C:/Boletim/voz/kokoro/.venv/Scripts/python.exe"))
    ffmpeg = cfg.get("ffmpeg") or shutil.which("ffmpeg")
    if not roteiro:
        return None
    if not py.is_file() or not ffmpeg:
        log.warning("audio: Kokoro (%s) ou ffmpeg ausente; painel sai sem audio", py)
        return None
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="boletim-audio-") as tmp:
        wav, mp3 = Path(tmp) / "fala.wav", Path(tmp) / "fala.mp3"
        try:
            r = subprocess.run([str(py), str(AQUI / "voz_kokoro.py"), str(wav), cfg.get("voz", "pf_dora"),
                                str(cfg.get("velocidade", 1.05))],
                               input=roteiro.encode("utf-8"), capture_output=True,
                               timeout=int(cfg.get("timeout_s", 600)))
            if r.returncode != 0 or not wav.exists():
                log.warning("audio: Kokoro saiu com %s: %s", r.returncode, r.stderr.decode("utf-8", "ignore")[-400:])
                return None
            segundos = float(r.stdout.decode().strip().splitlines()[-1])
            r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "24000",
                                "-c:a", "libmp3lame", "-b:a", f"{int(cfg.get('kbps', 48))}k", str(mp3)],
                               capture_output=True, timeout=300)
            if r.returncode != 0:
                log.warning("audio: ffmpeg falhou: %s", r.stderr.decode("utf-8", "ignore")[-300:])
                return None
            dados = mp3.read_bytes()
        except Exception as ex:
            log.warning("audio: falhou (%s: %s)", type(ex).__name__, ex)
            return None
    log.info("audio: %.0f s de fala, %d KB, gerado em %.0f s", segundos, len(dados) // 1024, time.time() - t0)
    return dados, segundos
