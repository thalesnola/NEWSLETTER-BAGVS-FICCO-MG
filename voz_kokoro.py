"""Sintese local (Kokoro, pt-BR) chamada por audio.py. Roda no venv do Kokoro, nao no do boletim.

Uso: <python do kokoro> voz_kokoro.py <saida.wav> <voz> <velocidade>   (texto pela entrada padrao)
Imprime a duracao em segundos. Nada sai da maquina: modelo do cache local (HF_HUB_OFFLINE).
"""
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
import warnings  # noqa: E402

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from kokoro import KPipeline  # noqa: E402

TAXA = 24000


def main() -> None:
    saida, voz, vel = sys.argv[1], sys.argv[2], float(sys.argv[3])
    texto = sys.stdin.buffer.read().decode("utf-8").strip()
    pipe = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
    pausa = np.zeros(int(TAXA * 0.45), dtype=np.float32)
    partes = []
    for paragrafo in [p.strip() for p in texto.split("\n") if p.strip()]:
        for r in pipe(paragrafo, voice=voz, speed=vel):
            if r.audio is not None:
                partes.append(r.audio.numpy())
        partes.append(pausa)
    audio = np.concatenate(partes) if partes else pausa
    sf.write(saida, audio, TAXA)
    print(round(len(audio) / TAXA, 1))


if __name__ == "__main__":
    main()
