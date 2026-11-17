"""Guarda de segredos do pre-commit: caminho proibido ou conteudo com forma de credencial."""
import re
import subprocess
import sys

CAMINHOS = re.compile(r"(^|/)(\.env|.*\.db|.*\.pem|id_rsa|\.credentials\.json)$")
PADROES = {
    "token Meta": re.compile(r"EAA[A-Za-z0-9]{40,}"),
    "token bot Telegram": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "senha de app Apple": re.compile(r"\b[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}\b"),
    "chave Anthropic/OpenAI": re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),
    "token GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
}


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout or ""


achados = []
for arq in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines():
    if CAMINHOS.search(arq):
        achados.append(f"{arq}: arquivo proibido")
        continue
    conteudo = git("show", f":{arq}")
    for nome, rx in PADROES.items():
        if rx.search(conteudo):
            achados.append(f"{arq}: parece {nome}")
if achados:
    print("[guarda] commit bloqueado:\n  " + "\n  ".join(achados), file=sys.stderr)
    sys.exit(1)
