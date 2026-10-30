# Destrava (Residence_AI_Challenge-2)

Agentes que trabalham com o Google Agenda, usando o modelo Gemma 2 rodando localmente com o Ollama.

| Agente | Situação |
|---|---|
| Visualização | Pronto: mostra compromissos, horários livres e conflitos (somente leitura) |
| Criar, editar, excluir | Em desenvolvimento |

## Pré-requisitos

- Python 3.10 ou superior
- [Ollama](https://ollama.com/download) instalado
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

## Como rodar o agente de visualização

Todos os comandos são executados **na raiz do projeto**, com o ambiente virtual ativo.

### 1. Confirme que o Ollama está rodando

```
ollama list
```

O modelo `gemma2:2b` deve aparecer na lista. Se o comando falhar, inicie o servidor com `ollama serve` (em outro terminal) e tente de novo.

### 2. Inicie o chat

```
python cli.py
```

Digite uma pergunta sobre a agenda e pressione Enter. Para encerrar, digite `sair`.

**Na primeira execução**, o navegador abre para você autorizar o acesso de **leitura** ao Google Agenda. Se aparecer o aviso "app não verificado", clique em **Avançado** e continue (o app está em modo de teste). Depois disso, o arquivo `token_readonly.json` é criado e o login não é pedido de novo.

### 3. Exemplos de perguntas

```
Quais são meus horários livres hoje?
Quais são meus compromissos amanhã?
Tenho conflito de horário esta semana?
Como está minha agenda na sexta?
```

O agente interpreta o período, busca os eventos, calcula e responde só com o que foi pedido. Pedidos de ação (criar, editar, excluir) são recusados, porque o agente é somente de leitura.

## Teste rápido sem o chat

Mostra, para um dia, os horários ocupados, livres e conflitos calculados, e depois a resposta do Gemma:

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
├── core/      configurações e conexões compartilhadas (config, google_client, llm_client, agenda_engine)
├── agents/    um arquivo por agente (visualizar, criar, editar, excluir)
└── prompts/   prompts de cada agente
docs/          documentação técnica de cada agente
scripts/       scripts de teste manual
cli.py         chat de linha de comando
```

## Configuração

Fuso horário, horários de acordar e dormir, duração mínima de um horário livre, modelo e demais valores ficam em `destrava/core/config.py`.

Para conferir se a configuração carrega, na raiz do projeto:

```
python -c "from destrava.core import config; print(config.MODELO, config.FUSO)"
```

## Documentação

A documentação técnica de cada agente fica na pasta `docs/`.
