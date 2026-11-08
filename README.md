# Destrava (Residence_AI_Challenge-2)

Agentes que trabalham com o Google Agenda. Hoje existem **dois agentes prontos, o de visualização e o de criação**. Eles serão chamados pelo **Supervisor**: cada um recebe um JSON e devolve um JSON, sem usar LLM.

| Agente | Situação |
|---|---|
| Visualização | Pronto: recebe um período em JSON e devolve os horários livres (somente leitura) |
| Criar | Pronto: recebe título, início e fim em JSON e cria o evento |
| Editar, excluir | Em desenvolvimento |
| RAG (Supervisor e Planejador) | Máquina pronta, com LangChain (chunking, embeddings, banco vetorial Chroma, busca, prompt e geração). A base do Planejador tem conteúdo; a do Supervisor aguarda (ver [`docs/rag.md`](docs/rag.md)) |

O formato de entrada e de saída de cada agente está em [`docs/contrato.md`](docs/contrato.md).

## Pré-requisitos

- Python 3.10 ou superior
- Conta Google (para o Google Agenda)

## Instalação

1. Crie e ative um ambiente virtual na raiz do projeto:

   ```
   python -m venv .venv
   ```

   - Linux / macOS: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`

2. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

## Credenciais do Google

1. No [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e ative a **Google Calendar API**.
2. Configure a tela de consentimento OAuth e adicione o seu e-mail como usuário de teste.
3. Crie uma credencial **OAuth Client ID** do tipo **Desktop app** e baixe o arquivo JSON.
4. Salve o arquivo como `credentials.json` na **raiz do projeto** (ao lado deste README).

> `credentials.json` e `token*.json` estão no `.gitignore`. **Nunca** faça commit deles.

## Como rodar

Todos os comandos são executados **na raiz do projeto**, com o ambiente virtual ativo.

**Na primeira execução com o Google**, o navegador abre para você autorizar o acesso à agenda (leitura para o visualizar, escrita para o criar). Se aparecer o aviso "app não verificado", clique em **Avançado** e continue (o app está em modo de teste). Depois disso, os arquivos `token_readonly.json` e `token_calendar.json` são criados e o login não é pedido de novo.

### 1. CLI: os dois agentes (Google real)

```
python cli.py
```

Escolha o agente (`1` = visualizar, `2` = criar), cole um JSON e veja o JSON de resposta. Para encerrar, digite `sair`.

Visualizar (devolve os horários livres; se `fim` for igual a `inicio`, o período vira o dia inteiro):

```
{"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}
```

Criar (**cria o evento de verdade** na agenda; datas sem fuso valem no horário de `config.FUSO`):

```
{"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}
```

Os dois agentes devolvem o mesmo formato (`status`, `acao`, `periodo`, `dados`, `fluxo`, `erro`). Pedido inválido ou falha no Google não levanta exceção: volta como `"status": "erro"` e não altera a agenda.

### 2. Scripts de teste manual

Use `python -m` (e não `python scripts/arquivo.py`), senão aparece `ModuleNotFoundError: destrava`.

| Comando | O que faz | Google |
|---|---|---|
| `python -m scripts.teste_visualizar` | Mostra os ocupados, livres e conflitos de amanhã e o JSON do contrato | Real (leitura) |
| `python -m scripts.teste_visualizar 2026-11-04` | O mesmo, para um dia específico (AAAA-MM-DD) | Real (leitura) |
| `python -m scripts.teste_criar` | Cria um evento com um serviço simulado e mostra o que seria enviado à API | Simulado |
| `python -m scripts.teste_criar_real` | Pede um JSON, mostra o evento e só cria na agenda real se você digitar `CRIAR` | Real (escrita) |
| `python -m scripts.teste_rag supervisor "sua pergunta"` | Mostra os trechos (e, com `--prompt` ou `--responder`, o prompt e a resposta) que o RAG devolve para a pergunta | Não usa |
| `python -m scripts.avaliar_rag planejador` | Avalia a qualidade do RAG com o ragas (notas de 0 a 1, com o LLM como juiz). Precisa do Ollama; leva alguns minutos | Não usa |

### 3. Testes automáticos

```
python -m pytest tests/
```

Os testes simulam o Google e o Ollama, então não precisam de `credentials.json` nem do Ollama. A única exceção à internet: na primeira execução, o RAG baixa os dados do NLTK (stopwords e stemmer em português). Para baixar antes: `python -m nltk.downloader stopwords rslp`.

## Ollama (opcional, para o RAG)

O RAG funciona sem o Ollama, só com busca por palavras-chave. Para a busca completa (palavras-chave + significado), com o Ollama instalado e rodando:

```
ollama pull nomic-embed-text
```

O nome do modelo de embeddings fica em `destrava/core/config.py` (`MODELO_EMBEDDING`). Os agentes de visualizar e criar não usam o Ollama.

## Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| `ModuleNotFoundError: destrava` | Rode a partir da raiz do projeto e use `python -m scripts.teste_visualizar` (com `-m`). |
| `credentials.json` não encontrado | Siga a seção "Credenciais do Google" e salve o arquivo na raiz do projeto. |
| `SSL: CERTIFICATE_VERIFY_FAILED` ao falar com o Google | A rede pode estar interceptando a conexão (ex.: Wi-Fi com login). Tente outra rede. Não desative a verificação de certificado. |
| Erro de fuso horário no Windows (`ZoneInfo`) | Instale o pacote de fusos: `pip install tzdata` (já está no `requirements.txt`). |
| Autorização do Google travada ou com conta errada | Apague o arquivo `token_readonly.json` (visualizar) ou `token_calendar.json` (criar) e rode de novo para autorizar novamente. |

## Estrutura

```
destrava/
├── core/      configurações e conexões compartilhadas (config, google_client, agenda_engine, models)
├── agents/    um arquivo por agente (visualizar, criar, editar, excluir)
├── rag/       RAG (LangChain): chunker, banco vetorial, índice, recuperador; as bases de conhecimento ficam em rag/conhecimento/
└── prompts/   prompts dos agentes ainda em desenvolvimento (editar, excluir)
docs/          documentação técnica de cada agente e contrato JSON
scripts/       scripts de teste manual
tests/         testes automáticos (Google simulado)
cli.py         linha de comando: cole um JSON e veja o JSON do agente
```

## Configuração

Fuso horário, horários de acordar e dormir, duração mínima de um horário livre e demais valores ficam em `destrava/core/config.py`.

Para conferir se a configuração carrega, na raiz do projeto:

```
python -c "from destrava.core import config; print(config.FUSO)"
```

## Documentação

A documentação técnica de cada agente fica na pasta `docs/`. O contrato JSON dos agentes está em `docs/contrato.md` e o RAG em `docs/rag.md`.
