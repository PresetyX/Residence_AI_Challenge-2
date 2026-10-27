# Residence_AI_Challenge-2

No momento, agentes que fazem o CRUD do Google Agenda (visualizar, criar, editar e excluir), usando o modelo Gemma 2 rodando localmente com o Ollama.

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

Na primeira execução, o navegador abre para você autorizar o acesso e um arquivo `token*.json` é gerado.

> `credentials.json` e `token*.json` estão no `.gitignore`. **Nunca** faça commit deles.

## Estrutura

```
destrava/
├── core/      configurações e conexões compartilhadas (config, google_client, llm_client)
├── agents/    um arquivo por agente (visualizar, criar, editar, excluir)
└── prompts/   prompts de cada agente
docs/          documentação técnica de cada agente
```

## Configuração

Fuso horário, horários de acordar e dormir, duração mínima de um horário livre, modelo e demais valores ficam em `destrava/core/config.py`.

Para conferir se a configuração carrega, na raiz do projeto:

```
python -c "from destrava.core import config; print(config.MODELO, config.FUSO)"
```

## Documentação

A documentação técnica de cada agente fica na pasta `docs/`.
