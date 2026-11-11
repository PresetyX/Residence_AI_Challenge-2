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

   Isso basta para quem usa o [servidor de IA compartilhado](#servidor-de-ia-compartilhado): nada de torch nem de modelos baixados.
   Para rodar a IA na própria máquina (Ollama local e story points sem `STORY_POINTS_URL`), instale também as dependências pesadas:

   ```
   pip install -r requirements.txt -r requirements-ia.txt
   ```

## Credenciais do Google

1. No [Google Cloud Console](https://console.cloud.google.com/), crie um projeto e ative a **Google Calendar API**.
2. Configure a tela de consentimento OAuth e adicione o seu e-mail como usuário de teste.
3. Crie uma credencial **OAuth Client ID** do tipo **Desktop app** e baixe o arquivo JSON.
4. Salve o arquivo como `credentials.json` na **raiz do projeto** (ao lado deste README).

> `credentials.json` e `token*.json` estão no `.gitignore`. **Nunca** faça commit deles.

## Como rodar

Todos os comandos são executados **na raiz do projeto**, com o ambiente virtual ativo.

### API FastAPI

Para iniciar o backend com a rota de template:

```
uvicorn backend.main:app
```

A rota `GET /` responde com `{}`. O CORS libera o frontend em
`http://localhost:3000` e `http://localhost:3210` (variável `CORS_ORIGINS`).
Erros do planejador voltam como `422` (entrada inválida), `502` (resposta da IA
fora do contrato) ou `503` (Ollama indisponível), com a mensagem em `detail`.

### Frontend

A interface web (Next.js) fica em [`frontend/`](frontend/README.md):

```
cd frontend
npm install
npm run dev
```

O chat chama `POST /projetos` quando o usuário descreve um projeto com prazo.

Para criar um projeto, envie o texto e o prazo para `POST /projetos`:

```
curl -X POST http://127.0.0.1:8000/projetos `
  -H "Content-Type: application/json" `
  -d '{"texto":"Criar uma API de cadastro de alunos.","prazo":"2026-12-01"}'
```

O backend valida os campos, executa o agente planejador com o prazo informado,
imprime um resumo no terminal e retorna o prazo e as tarefas em JSON.

Depois do Planejador, os textos de cada tarefa passam pelo embedding
multilíngue BGE-M3 e pelo modelo PyTorch treinado. O valor original de
`story_points` é descartado e substituído pela previsão da rede neural.
Com `STORY_POINTS_URL` definido, essa etapa roda no servidor de IA (ver
[Servidor de IA compartilhado](#servidor-de-ia-compartilhado)); se ele estiver
fora do ar, `POST /projetos` responde `503` com o motivo em `detail`.
Coloque o artefato exportado pelo notebook em `modelos/rede_neural.pt`. Ele
deve conter o `state_dict` da MLP, a PCA e o `StandardScaler` usados no treino.

Para treinar esse modelo com um CSV contendo `title`, `description` e
`storypoint`:

```
python -m scripts.treinar_story_points joined_dataset.csv
```

O notebook segue o mesmo fluxo: limpa o texto, gera embeddings BGE-M3, ajusta
a PCA e o `StandardScaler` somente no conjunto de treino, treina uma MLP e
exporta tudo em `modelos/rede_neural.pt`.

**Na primeira execução com o Google**, o navegador abre para você autorizar o acesso à agenda (leitura para o visualizar, escrita para o criar). Se aparecer o aviso "app não verificado", clique em **Avançado** e continue (o app está em modo de teste). Depois disso, os arquivos `token_readonly.json` e `token_calendar.json` são criados e o login não é pedido de novo.

### 1. CLI: os dois agentes (Google real)

```
python cli.py
```

Escolha o agente (`1` = visualizar, `2` = criar, `3` = planejador). Nos agentes `1` e `2`, cole um JSON e veja o JSON de resposta. No `3`, digite a descrição do projeto em texto livre e o prazo (`AAAA-MM-DD`; Enter usa daqui a 14 dias) e veja o plano de tarefas em JSON: ele usa o RAG e o modelo, então precisa do Ollama ligado (ver a seção Ollama) e pode demorar. Para encerrar, digite `sair`.

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

Os testes simulam o Google e o Ollama, então não precisam de `credentials.json` nem do Ollama. Os do servidor de IA (`tests/test_servidor_ia.py`) simulam a rede e o modelo de story points, cobrindo o modo remoto e o local sem baixar o BGE-M3. A única exceção à internet: na primeira execução, o RAG baixa os dados do NLTK (stopwords e stemmer em português). Para baixar antes: `python -m nltk.downloader stopwords rslp`.

## Ollama (opcional, para o RAG)

O RAG funciona sem o Ollama, só com busca por palavras-chave. Para a busca completa (palavras-chave + significado), com o Ollama instalado e rodando:

```
ollama pull nomic-embed-text
```

O nome do modelo de embeddings fica em `destrava/core/config.py` (`MODELO_EMBEDDING`). Os agentes de visualizar e criar não usam o Ollama.

Quem usa o servidor de IA compartilhado não instala o Ollama: basta apontar `OLLAMA_URL` para ele (seção abaixo).

## Servidor de IA compartilhado

Toda a inferência pode rodar num único PC com GPU, que o time acessa pela rede (Tailscale) como se fosse uma LLM na nuvem. Os notebooks não baixam modelo nenhum nem instalam torch.

| Onde | O que roda |
|---|---|
| **Servidor de IA** (PC com GPU) | Ollama (`gemma4:12b-it-q4_K_M` para o chat, `nomic-embed-text` para os embeddings do RAG) e o serviço de story points (BGE-M3 + `modelos/rede_neural.pt`) |
| **Notebook de cada pessoa** | Frontend, backend FastAPI, RAG (Chroma + BM25, em CPU) e agentes do Google Agenda, com o `credentials.json` e os `token_*.json` da própria conta |

O backend continua local porque o Google Agenda usa o OAuth de cada um: só as chamadas de IA vão para o servidor.

### Variáveis de ambiente

Todas são opcionais. Sem elas, vale o padrão do `destrava/core/config.py` (tudo local). Os endereços **não** vão para o código nem para o repositório: cada pessoa define as variáveis na própria máquina.

| Variável | Padrão | Para que serve |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Endereço do Ollama (no time: `http://<ip-tailscale-do-servidor>:11434`) |
| `MODELO` | `gemma2:2b` | Modelo de chat do Ollama (no servidor: `gemma4:12b-it-q4_K_M`) |
| `MODELO_EMBEDDING` | `nomic-embed-text` | Modelo de embeddings do RAG |
| `STORY_POINTS_URL` | vazio (modo local) | Endereço do serviço de story points (`http://<ip-tailscale-do-servidor>:8001`) |
| `TIMEOUT_LLM` | `300` | Segundos de espera pela resposta do modelo. Com várias pessoas na mesma GPU os pedidos fazem fila: aumente se aparecer erro de tempo esgotado |
| `TIMEOUT_STORY_POINTS` | `120` | Segundos de espera pelo serviço de story points |
| `NUM_CTX` | `8192` | Janela de contexto pedida ao Ollama. O padrão do Ollama (~4096) pode cortar o prompt do Planejador. Use o mesmo valor em todo o time: um valor diferente faz o Ollama recarregar o modelo |
| `CHAVE_API_IA` | vazio (desligada) | Chave compartilhada. No servidor, o serviço de story points passa a exigir o cabeçalho `X-API-Key`; no notebook, o backend envia esse cabeçalho |

### 1. Preparar o servidor de IA com Docker (recomendado)

Tudo o que o servidor roda (Ollama + serviço de story points, os dois na GPU) fica num Docker Compose: liga quando o time precisa e desliga para liberar a GPU. Não precisa instalar Ollama, Python nem torch no PC.

Requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/) com o backend WSL 2 e o driver da NVIDIA atualizado. Para conferir se o Docker enxerga a GPU:

```
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

Na raiz do projeto:

```
docker compose -f docker-compose.servidor-ia.yml up -d --build
```

Isso sobe três serviços:

| Serviço | O que faz |
|---|---|
| `ollama` | Ollama na porta `11434`, com `OLLAMA_NUM_PARALLEL=2`, `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=30m` e contexto de 8192 tokens |
| `baixar-modelos` | Baixa `gemma4:12b-it-q4_K_M` e `nomic-embed-text` para o volume, se ainda não estiverem lá, e termina |
| `story-points` | Serviço de story points na porta `8001` (BGE-M3 + `modelos/rede_neural.pt`). Na primeira vez, baixa o BGE-M3 (cerca de 2,3 GB) |

A primeira subida demora (build da imagem com torch + cerca de 10 GB de modelos). Das próximas vezes, os modelos já estão nos volumes `destrava-ia_ollama-modelos` e `destrava-ia_hf-cache`, e a subida leva segundos.

| Para | Comando |
|---|---|
| Ligar | `docker compose -f docker-compose.servidor-ia.yml up -d` |
| Ver se está pronto | `docker compose -f docker-compose.servidor-ia.yml ps` (o `story-points` deve ficar `healthy`) |
| Acompanhar os logs | `docker compose -f docker-compose.servidor-ia.yml logs -f ollama story-points` |
| Desligar (libera a GPU) | `docker compose -f docker-compose.servidor-ia.yml down` |
| Atualizar depois de mudar o código | `docker compose -f docker-compose.servidor-ia.yml up -d --build` |

Opções, definidas no terminal antes do `up` (nada fica salvo no repositório):

```
$env:CHAVE_API_IA = "<chave>"       # o serviço de story points passa a exigir X-API-Key
$env:MODELO = "gemma4:12b-it-q4_K_M" # outro modelo de chat para baixar e servir
$env:IP_PUBLICACAO = "<ip-tailscale>" # abre as portas só na interface da Tailscale (recomendado)
$env:OLLAMA_NUM_PARALLEL = "1"        # menos pedidos ao mesmo tempo, menos memória de GPU
```

Medido numa RTX 5070 Ti (16 GB), com `OLLAMA_NUM_PARALLEL=2`: o plano completo (Gemma 4 + RAG + story points) leva cerca de 25 s com os modelos já carregados, e a GPU chega a cerca de 14 GB. Não aumente o paralelismo com 16 GB. O primeiro pedido depois de ligar demora mais (cerca de 2 min), porque carrega os modelos na GPU.

> Se o Ollama instalado no Windows também estiver aberto, ele continua respondendo em `localhost:11434` neste PC (o do Docker atende pelo IP da rede). Para testar o do Docker no próprio PC, use o IP da Tailscale ou feche o Ollama do Windows pelo ícone da bandeja (Quit).

Depois, faça o passo 4 da seção seguinte (Tailscale + regra de firewall), que vale igual para o Docker.

### 1b. Preparar o servidor de IA sem Docker (PC com a GPU)

1. **Ollama.** Instale o [Ollama](https://ollama.com/download) e baixe os modelos:

   ```
   ollama pull gemma4:12b-it-q4_K_M
   ollama pull nomic-embed-text
   ```

   O `gemma4:12b-it-q4_K_M` é o Gemma 4 12B em 4 bits (cerca de 7,4 GB; a tag `gemma4:12b` aponta para o mesmo arquivo).

2. **Configurar o Ollama para atender a rede.** No PowerShell (vale para o seu usuário; feche o Ollama pelo ícone da bandeja e abra de novo depois):

   ```
   setx OLLAMA_HOST 0.0.0.0:11434
   setx OLLAMA_NUM_PARALLEL 2
   setx OLLAMA_MAX_LOADED_MODELS 2
   setx OLLAMA_KEEP_ALIVE 30m
   ```

   - `OLLAMA_HOST=0.0.0.0:11434`: aceita conexões de outros PCs (o padrão só aceita a própria máquina). Quem limita o acesso é o firewall do passo 4.
   - `OLLAMA_NUM_PARALLEL=2`: atende duas pessoas ao mesmo tempo; os demais pedidos esperam na fila. Cada pedido simultâneo reserva memória de contexto (`NUM_CTX`) na GPU: com 16 GB, 2 já usa cerca de 14 GB junto com o BGE-M3; não passe disso.
   - `OLLAMA_MAX_LOADED_MODELS=2`: mantém o modelo de chat e o de embeddings carregados juntos, sem trocar um pelo outro a cada pedido.
   - `OLLAMA_KEEP_ALIVE=30m`: o modelo fica na GPU por 30 minutos depois do último uso, sem o atraso de recarregar a cada pedido (`-1` mantém para sempre).

3. **Serviço de story points.** Na raiz do projeto, num ambiente virtual próprio. O torch com suporte a CUDA vem do índice do PyTorch (a RTX 50xx precisa do CUDA 12.8 ou mais novo):

   ```
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   pip install -r requirements.txt -r requirements-ia.txt
   python -c "import torch; print(torch.cuda.is_available())"
   uvicorn backend.servidor_story_points:app --host 0.0.0.0 --port 8001
   ```

   O último comando deixa o serviço rodando. Ele carrega o BGE-M3 e a rede neural **uma vez**, ao iniciar (na primeira vez o BGE-M3 é baixado, cerca de 2,3 GB), e atende:

   - `GET /saude`: `{"status": "ok", "dispositivo": "cuda:0"}`. Se aparecer `cpu`, o torch instalado não tem CUDA.
   - `POST /story-points` com `{"tarefas": [{"titulo", "objetivo", "entregaveis", "demonstracao"}, ...]}`: devolve `{"story_points": [...]}`, na mesma ordem.

   Para exigir a chave (opcional), defina-a antes de iniciar: `$env:CHAVE_API_IA = "<uma-chave-longa-e-aleatória>"`. Gere uma com `python -c "import secrets; print(secrets.token_urlsafe(32))"` e passe ao time por um canal privado, nunca pelo repositório.

4. **Rede: Tailscale + firewall.** O Ollama e o serviço de story points **não têm login**. Eles só podem ficar acessíveis pela Tailscale:

   - Instale a [Tailscale](https://tailscale.com/download) no servidor e em cada notebook, todos na mesma rede (tailnet). Convide o time ou compartilhe o dispositivo do servidor pelo painel da Tailscale.
   - Veja o IP do servidor na tailnet com `tailscale ip -4` (algo como `100.x.y.z`) ou use o nome do MagicDNS.
   - Libere as duas portas **só para a faixa da Tailscale**. No PowerShell como administrador:

     ```
     New-NetFirewallRule -DisplayName "Destrava IA (Tailscale)" -Direction Inbound -Protocol TCP -LocalPort 11434,8001 -RemoteAddress 100.64.0.0/10,fd7a:115c:a1e0::/48 -Action Allow
     ```

   - **Não** faça port forward no roteador e não exponha as portas na internet.
   - Para restringir ainda mais, use as ACLs da Tailscale e libere as portas `11434` e `8001` só para os membros do time.

   Sobre a `CHAVE_API_IA`: ela protege o serviço de story points. O Ollama não confere chave nenhuma. O backend também envia `Authorization: Bearer <chave>` ao Ollama, mas isso só tem efeito se você colocar um proxy na frente dele (Caddy, nginx) que exija o cabeçalho. Sem proxy, quem protege o Ollama é a Tailscale com o firewall.

### 2. Configurar o notebook do time

1. Instale só as dependências leves: `pip install -r requirements.txt` (sem `requirements-ia.txt`).
2. Instale e conecte a Tailscale na mesma tailnet do servidor e teste o acesso:

   ```
   curl http://<ip-tailscale-do-servidor>:11434/api/tags
   curl http://<ip-tailscale-do-servidor>:8001/saude
   ```

3. Defina as variáveis de ambiente. Para a sessão atual do PowerShell:

   ```
   $env:OLLAMA_URL = "http://<ip-tailscale-do-servidor>:11434"
   $env:STORY_POINTS_URL = "http://<ip-tailscale-do-servidor>:8001"
   $env:MODELO = "gemma4:12b-it-q4_K_M"
   $env:CHAVE_API_IA = "<a-chave-que-o-servidor-usa>"   # só se o servidor usar chave
   ```

   Para deixar fixo no Windows, use `setx NOME valor` e abra um terminal novo. No Linux/macOS, use `export NOME=valor` (ou coloque no `~/.bashrc`).

4. Rode o backend e o frontend normalmente (seções "API FastAPI" e "Frontend"). Ao iniciar, o backend mostra `Story points: modo remoto (http://...:8001)`. O Google Agenda continua usando o `credentials.json` e os `token_*.json` da sua conta, na sua máquina.

O índice do RAG (Chroma) é gerado na primeira execução com os embeddings do servidor e fica em `.rag_indices/` no notebook. Ele só é refeito quando a base de conhecimento ou o modelo de embeddings mudam.

## Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| `ModuleNotFoundError: destrava` | Rode a partir da raiz do projeto e use `python -m scripts.teste_visualizar` (com `-m`). |
| `credentials.json` não encontrado | Siga a seção "Credenciais do Google" e salve o arquivo na raiz do projeto. |
| `SSL: CERTIFICATE_VERIFY_FAILED` ao falar com o Google | A rede pode estar interceptando a conexão (ex.: Wi-Fi com login). Tente outra rede. Não desative a verificação de certificado. |
| Erro de fuso horário no Windows (`ZoneInfo`) | Instale o pacote de fusos: `pip install tzdata` (já está no `requirements.txt`). |
| Autorização do Google travada ou com conta errada | Apague o arquivo `token_readonly.json` (visualizar) ou `token_calendar.json` (criar) e rode de novo para autorizar novamente. |
| "Não foi possível conectar ao Ollama em http://100..." | Confira se a Tailscale está conectada nos dois PCs, se o Ollama do servidor foi reiniciado com `OLLAMA_HOST=0.0.0.0:11434` e se a regra de firewall existe. |
| "O Ollama excedeu o tempo limite" com o servidor compartilhado | A GPU está atendendo outras pessoas e o pedido ficou na fila. Aumente `TIMEOUT_LLM` (ex.: `600`) ou, no servidor, `OLLAMA_NUM_PARALLEL`. |
| `503` "serviço de story points" no `POST /projetos` | O serviço da porta `8001` não está rodando no servidor, ou a Tailscale caiu. Teste com `curl http://<ip>:8001/saude`. |
| "recusou a chave de API" | `CHAVE_API_IA` do notebook é diferente da do servidor. |
| Ollama retorna HTTP 404 | O modelo de `MODELO` não foi baixado **no servidor** (`ollama pull ...` lá, não no notebook). |

## Estrutura

```
backend/
├── main.py                    API FastAPI (POST /projetos)
├── story_points.py            estimativa de story points: local (torch) ou cliente HTTP do servidor de IA
└── servidor_story_points.py   serviço de story points do servidor de IA (POST /story-points)
docker/                        Dockerfile do serviço de story points
docker-compose.servidor-ia.yml servidor de IA com Docker (Ollama + story points na GPU)
frontend/      interface web Next.js (landing, chat, agenda)
destrava/
├── core/      configurações e conexões compartilhadas (config, google_client, agenda_engine, models)
├── agents/    um arquivo por agente (visualizar, criar, editar, excluir)
├── rag/       RAG (LangChain): chunker, banco vetorial, índice, recuperador; as bases de conhecimento ficam em rag/conhecimento/
└── prompts/   prompts dos agentes ainda em desenvolvimento (editar, excluir)
docs/          documentação técnica de cada agente e contrato JSON
scripts/       scripts de teste manual
tests/         testes automáticos (Google simulado)
cli.py         linha de comando: cole um JSON (visualizar, criar) ou descreva um projeto (planejador)
```

## Configuração

Fuso horário, horários de acordar e dormir, duração mínima de um horário livre e demais valores ficam em `destrava/core/config.py`. O que muda de máquina para máquina (endereço do servidor de IA, modelo, tempos limite e chave) também pode vir de variáveis de ambiente; ver [Servidor de IA compartilhado](#servidor-de-ia-compartilhado).

Para conferir se a configuração carrega, na raiz do projeto:

```
python -c "from destrava.core import config; print(config.FUSO)"
```

## Documentação

A documentação técnica de cada agente fica na pasta `docs/`. O contrato JSON dos agentes está em `docs/contrato.md` e o RAG em `docs/rag.md`.
