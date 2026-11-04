# Destrava (Residence_AI_Challenge-2)

Agentes que trabalham com o Google Agenda, usando o modelo Gemma 2 rodando localmente com o Ollama.

| Agente | Situação |
|---|---|
| Visualização | Pronto: recebe um período em JSON e devolve os horários livres (somente leitura) |
| Criar | Pronto: recebe título, início e fim em JSON e cria o evento |
| Editar, excluir | Em desenvolvimento |

## Pré-requisitos

- Python 3.10 ou superior
- [Ollama](https://ollama.com/download) instalado (só é usado nos caminhos em texto; os caminhos em JSON não usam LLM)
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

3. Baixe o modelo no Ollama (o nome do modelo usado está em `destrava/core/config.py`):

   ```
   ollama pull gemma2:2b
   ```

## Credenciais do Google

1. No [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e ative a **Google Calendar API**.
2. Configure a tela de consentimento OAuth e adicione o seu e-mail como usuário de teste.
3. Crie uma credencial **OAuth Client ID** do tipo **Desktop app** e baixe o arquivo JSON.
4. Salve o arquivo como `credentials.json` na **raiz do projeto** (ao lado deste README).

> `credentials.json` e `token*.json` estão no `.gitignore`. **Nunca** faça commit deles.

## Como rodar os agentes

Todos os comandos são executados **na raiz do projeto**, com o ambiente virtual ativo.

Os agentes **recebem JSON e devolvem JSON, sem usar LLM**. O formato está em [`docs/contrato.md`](docs/contrato.md).

### 1. Inicie o CLI

```
python cli.py
```

Escolha o agente (`1` = visualizar, `2` = criar) e cole um JSON. Para encerrar, digite `sair`.

**Na primeira execução**, o navegador abre para você autorizar o acesso ao Google Agenda (leitura para o visualizar, escrita para o criar). Se aparecer o aviso "app não verificado", clique em **Avançado** e continue (o app está em modo de teste). Depois disso, os arquivos `token_readonly.json` e `token_calendar.json` são criados e o login não é pedido de novo.

### 2. Exemplos de JSON

Visualizar (devolve os horários livres; se `fim` for igual a `inicio`, o período vira o dia inteiro):

```
{"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}
```

Criar (devolve o evento criado; datas sem fuso valem no horário de `config.FUSO`):

```
{"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}
```

Pedido inválido (título vazio, início depois do fim, evento no passado...) devolve `{"erro": "Pedido inválido", "detalhes": [...]}` e não altera a agenda.

## Teste rápido sem o CLI

Mostra, para um dia, os horários ocupados, livres e conflitos calculados:

```
python -m scripts.teste_visualizar              # dia de amanhã
python -m scripts.teste_visualizar 2026-10-29   # um dia específico (AAAA-MM-DD)
```

Use `python -m` (e não `python scripts/teste_visualizar.py`), senão aparece `ModuleNotFoundError: destrava`.

## Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| Erro de conexão com o modelo, ou demora muito | Confira se o Ollama está rodando (`ollama list`) e se o modelo foi baixado (`ollama pull gemma2:2b`). |
| `ModuleNotFoundError: destrava` | Rode a partir da raiz do projeto e use `python -m scripts.teste_visualizar`. |
| `credentials.json` não encontrado | Siga a seção "Credenciais do Google" e salve o arquivo na raiz do projeto. |
| `SSL: CERTIFICATE_VERIFY_FAILED` ao falar com o Google | A rede pode estar interceptando a conexão (ex.: Wi-Fi com login). Tente outra rede. Não desative a verificação de certificado. |
| Erro de fuso horário no Windows (`ZoneInfo`) | Instale o pacote de fusos: `pip install tzdata` (já está no `requirements.txt`). |
| Resposta com período errado | O modelo pequeno pode errar. Reformule com datas mais claras (ex.: "amanhã", "esta semana"). |
| Autorização do Google travada ou com conta errada | Apague o arquivo `token_readonly.json` e rode de novo para autorizar novamente. |

## Estrutura

```
destrava/
├── core/      configurações e conexões compartilhadas (config, google_client, llm_client, agenda_engine, models)
├── agents/    um arquivo por agente (visualizar, criar, editar, excluir)
└── prompts/   prompts de cada agente
docs/          documentação técnica de cada agente
scripts/       scripts de teste manual
cli.py         linha de comando: cole um JSON e veja o JSON do agente
```

## Configuração

Fuso horário, horários de acordar e dormir, duração mínima de um horário livre, modelo e demais valores ficam em `destrava/core/config.py`.

Para conferir se a configuração carrega, na raiz do projeto:

```
python -c "from destrava.core import config; print(config.MODELO, config.FUSO)"
```

## Testes

```
python -m pytest tests/
```

Os testes simulam o Google e bloqueiam o LLM nos caminhos em JSON, então não precisam de `credentials.json` nem do Ollama.

## Documentação

A documentação técnica de cada agente fica na pasta `docs/`. O contrato JSON dos agentes está em `docs/contrato.md`.
