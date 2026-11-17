"""Liga a edicao de seguranca publica a um CANAL privado do Telegram (o bot ja configurado e o bot do painel).

Antes: no canal, adicionar o bot do painel como ADMINISTRADOR com "Publicar mensagens" e postar
qualquer mensagem no canal. Depois:

    configurar_canal.cmd          (acha o canal pelas atualizacoes do bot, confirma, testa e grava)
    configurar_canal.cmd teste    (so manda um teste ao canal ja gravado)

Grava SO TELEGRAM_CANAL_ID no .env (as demais linhas ficam byte a byte iguais; copia .bak antes),
e so depois que a mensagem de teste chegou ao canal. O id do canal nao e segredo, mas fica fora do repo.
"""
from __future__ import annotations

import sys
import time

import configurar_telegram as ct

CHAVE = "TELEGRAM_CANAL_ID"


def achar_canais(tok: str, segundos: int = 180) -> dict[str, str]:
    """Canais em que o bot apareceu: post no canal (channel_post) ou mudanca de cargo (my_chat_member)."""
    achados, fim, offset = {}, time.time() + segundos, 0
    print(f"Aguardando ate {segundos} s por uma mensagem no canal (poste qualquer coisa la agora)...")
    while time.time() < fim and not achados:
        _, r = ct.api(tok, "getUpdates", timeout=20, offset=offset,
                      allowed_updates='["channel_post","my_chat_member","message"]')
        if not r.get("ok"):
            sys.exit(f"getUpdates recusado: {r.get('description', '')[:160]}")
        for up in r.get("result", []):
            offset = up["update_id"] + 1
            for campo in ("channel_post", "my_chat_member"):
                c = (up.get(campo) or {}).get("chat", {})
                if c.get("type") == "channel":
                    achados[str(c["id"])] = c.get("title", "")
    if offset:
        ct.api(tok, "getUpdates", offset=offset, timeout=0)   # confirma a leitura
    return achados


def testar(tok: str, canal: str) -> bool:
    st, r = ct.api(tok, "sendMessage", chat_id=canal,
                   text="✅ Canal ligado ao Boletim Segurança Pública. O painel diário passa a chegar aqui às 05:30.")
    if not r.get("ok"):
        print(f"Falhou ({st}): {r.get('description', '')[:200]}")
        if st in (400, 403):
            print("Confira se o bot do painel e ADMINISTRADOR do canal com 'Publicar mensagens'.")
        return False
    return True


def main() -> None:
    arq = ct.caminho_env()
    env = ct.ler_env(arq)
    tok = env.get(ct.CHAVE_TOKEN)
    if not tok:
        sys.exit(f"{ct.CHAVE_TOKEN} ausente em {arq}: rode configurar.cmd primeiro.")
    if sys.argv[1:] == ["teste"]:
        canal = env.get(CHAVE)
        sys.exit(0 if canal and testar(tok, canal) else f"{CHAVE} ausente ou teste falhou.")

    _, r = ct.api(tok, "getWebhookInfo")
    if (r.get("result") or {}).get("url"):
        sys.exit("O bot tem webhook ativo; getUpdates nao funciona. Remova o webhook antes.")
    canais = achar_canais(tok)
    if not canais:
        sys.exit("Nenhum canal apareceu. O bot ja e admin do canal? Postou algo depois de adiciona-lo?")
    lista = list(canais.items())
    for n, (cid, titulo) in enumerate(lista, 1):
        print(f"  {n}. {titulo}  ({cid})")
    escolha = input("Numero do canal do boletim [1]: ").strip() or "1"
    cid, titulo = lista[int(escolha) - 1]
    if not testar(tok, cid):
        sys.exit("Nada gravado.")
    copia = ct.gravar_env(arq, {CHAVE: cid})
    print(f"Gravado {CHAVE} para '{titulo}' em {arq}" + (f" (copia: {copia.name})" if copia else ""))


if __name__ == "__main__":
    main()
