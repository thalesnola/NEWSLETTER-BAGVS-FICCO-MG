<p align="center">
  <img src="docs/emblema-bagvs-ficco-mg.png" width="148" alt="Emblema FICCO BAGVS/MG">
</p>

<h1 align="center">NEWSLETTER BAGVS/FICCO/MG</h1>

<p align="center">
  Boletim diário de segurança pública que chega pronto no celular e abre sem internet.<br>
  <b>Versão 1.0.0</b> · BAGVS/FICCO/MG · Minas Gerais
</p>

<p align="center">
  <img src="docs/arquitetura-motion.svg" alt="O que é, mapa de funcionamento e para que serve a NEWSLETTER BAGVS/FICCO/MG" width="100%">
</p>

<p align="center"><sub>Diagrama animado (<a href="docs/arquitetura-motion.svg">SVG</a>) · versão estática em alta resolução (<a href="docs/arquitetura-motion.png">PNG</a>)</sub></p>

## O que é

Uma ferramenta que, todo dia, lê **fontes públicas** (RSS de portais e tribunais, buscas do Google News) e **posts de
perfis oficiais no Instagram** (polícias, Ministério Público, tribunais, secretarias), junta tudo o que fala do
**mesmo fato num único evento**, resume com IA, **confere o resumo contra a fonte** e entrega um **painel HTML de arquivo
único** que abre offline no celular.

O painel traz destaques do dia, filtro por tema, busca, a lista de **todos os links** de cada evento, gráficos das
**20 palavras mais frequentes** e das **instituições mais presentes**, e pode trazer um resumo em áudio gerado localmente.
A entrega é feita num **canal privado do Telegram** da equipe e por **e-mail**.

## Como funciona

| Etapa | O que faz |
|---|---|
| 1. Fontes | Cada boletim é um arquivo em `edicoes/*.toml`: fontes RSS/Atom, buscas do Google News e perfis do Instagram (API oficial da Meta, Business Discovery), com peso e palavras-chave por fonte |
| 2. Coleta | Janela das últimas 30 h; cada fonte falha sozinha e aparece no painel como falha, sem derrubar as outras |
| 3. Eventos | Mesmo link (sem parâmetros de rastreio) ou título parecido viram um evento só, com os outros links guardados; o histórico (SQLite, 21 dias) impede que o que já saiu volte |
| 4. Resumo + conferência | Uma chamada de IA por edição, com o lote inteiro: descarta o que está fora do foco, junta o mesmo fato com títulos diferentes e resume cada evento com todas as versões. O link sempre vem da coleta, nunca do texto da IA; número do resumo que não está na fonte ganha alerta "conferir na fonte" |
| 5. Painel offline | HTML único, sem CDN nem fonte web. Filtro por tema funciona só com CSS (abre até no visualizador do app Arquivos e do Telegram no iPhone, que não executam JavaScript) |
| 6. Entrega | Canal privado do Telegram (bot próprio, administrador do canal), e-mail com o painel anexo e cópia numa pasta sincronizada com o celular |

O Agendador do Windows roda tudo às 05:30; às 07:30, uma vigia avisa se o painel do dia não saiu.

## Uso

Requisitos: Windows, [uv](https://docs.astral.sh/uv/), Python 3.12, [Claude Code](https://claude.com/claude-code) logado
(o resumo usa `claude -p` em modo headless).

```bash
uv sync
uv run boletim.py --sem-ia --sem-envio --saida C:/temp/teste      # teste rápido, sem IA e sem enviar
uv run boletim.py --edicao seguranca-publica --sem-envio          # gera o painel do dia
uv run boletim.py                                                 # todas as edições, com envio
uv run --group dev python -m pytest -q tests                      # testes
uv run python docs/gerar_diagrama.py --png                        # refaz o diagrama
```

Configuração, tudo **fora do repositório**:

- `.env` na pasta de dados (`config.toml` → `env`): `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_PARA`, `TELEGRAM_TOKEN_PAINEL`,
  `TELEGRAM_CHAT_ID`, `TELEGRAM_CANAL_ID`, `IG_USER_ID`, `IG_TOKEN`. Tokens são gravados pelos configuradores
  (`configurar.cmd`, `configurar_canal.cmd`), que leem a chave sem eco e só gravam depois que uma mensagem de teste chega.
- `identidade.toml` (modelo em `identidade.exemplo.toml`): emblemas do topo (esquerda e direita) e assinatura do rodapé.
- `agendar.ps1` registra as tarefas diárias no Agendador.

## Cuidados

- **Só fonte pública.** A busca do Google News e a consulta ao Instagram enviam o termo e o @ pesquisados a terceiros:
  nunca usar nome de investigado, número de procedimento ou operação em curso como termo de busca.
- **Perfil do Instagram precisa ser comercial ou de criador** para a API ler. Conferir o @ na API antes de incluir:
  há perfis parecidos que não são da instituição.
- O resumo é feito por IA a partir do título e do trecho de cada fonte: **confira o original antes de citar**.
- O painel é clipping de fonte aberta: não substitui consulta a sistemas oficiais.

## Créditos

**BAGVS/FICCO/MG**, Força Integrada de Combate ao Crime Organizado, Governador Valadares, Minas Gerais.

Versão **1.0.0** · desenvolvimento: **apfnola, 24099 - thales.tnb**

Inspirado na ideia de curadoria automática de notícias por IA (ex.: `rafarcm/projeto_radar_ia`), reescrito sem LangChain,
sem embeddings e sem PDF, com foco em leitura offline no celular.
