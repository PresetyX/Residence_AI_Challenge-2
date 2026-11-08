# RAG

> Documentação técnica do **estado atual** do RAG. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Dar a cada agente (Supervisor, Planejador) o contexto certo para cada pedido: o RAG busca numa base de conhecimento e devolve só os trechos relevantes, para o prompt ficar curto (o modelo é pequeno, `gemma2:2b`).

O RAG é **a máquina**: chunking, embeddings, banco vetorial, busca, construção do prompt e geração. Ele **não tem conteúdo**: o que vai dentro de cada base é responsabilidade de quem cuida dela (ver "Como preencher uma base"). Base vazia é válida: a busca não devolve nada e nada quebra.

## Frameworks

O RAG é montado com o **LangChain** e bibliotecas do ecossistema:

| Parte | Biblioteca | Onde |
|---|---|---|
| Chat e embeddings do Ollama | `langchain-ollama` (`ChatOllama`, `OllamaEmbeddings`) | `core/llm_client.py` |
| Chunking | `langchain-text-splitters` (`ExperimentalMarkdownSyntaxTextSplitter` + `RecursiveCharacterTextSplitter`) | `rag/chunker.py` |
| Banco vetorial | `chromadb` + `langchain-chroma` | `rag/banco_vetorial.py` |
| Indexação incremental | Indexing API do LangChain (`index()` + `SQLRecordManager`) | `rag/indice.py` |
| Normalização para palavras-chave | `nltk` (stopwords e stemmer RSLP) | `rag/texto.py` |
| Busca por palavras-chave | `rank-bm25` (`BM25Plus`) | `rag/recuperador.py` |
| Prompt e geração | `ChatPromptTemplate` + LCEL (`prompt \| chat \| StrOutputParser`) | `rag/rag.py` |
| Avaliação | `ragas` | `scripts/avaliar_rag.py` (fora do RAG em uso) |

## Fluxo

```
INDEXAÇÃO (ao criar o Rag; só os trechos novos ou alterados geram embeddings)
  base de conhecimento → chunking → embedding dos chunks → armazenamento (Chroma)

INFERÊNCIA (a cada pergunta)
  pergunta → embedding da pergunta → busca por similaridade → recuperação de contexto
           → construção do prompt → geração da resposta
```

| # | Passo | Onde |
|---|---|---|
| 1 | Lê os `.md`/`.txt` da base (arquivos ou pastas, com subpastas) | `indice.ler_fontes` |
| 2 | **Chunking**: divide por seção (títulos Markdown); seções grandes por parágrafo, linha, frase e palavra, com sobreposição | `chunker.dividir_texto` |
| 3 | **Embedding dos chunks**: um vetor por trecho novo ou alterado, em lotes | `indice.construir_indice` (Indexing API), `llm_client.EmbeddingsOllama` |
| 4 | **Armazenamento**: trechos + vetores no Chroma, em `.rag_indices/<base>/` | `banco_vetorial.BancoVetorial` |
| 5 | **Embedding da pergunta**, com o mesmo modelo da indexação | `EmbeddingsOllama.embed_query` (chamado pelo Chroma) |
| 6 | **Busca por similaridade** (cosseno, no Chroma) + palavras-chave (BM25), combinadas por RRF | `recuperador.Recuperador.buscar` |
| 7 | **Recuperação de contexto**: os `N` trechos mais próximos, numerados e com a fonte | `Rag.contexto` |
| 8 | **Construção do prompt**: o contexto injetado no prompt (`ChatPromptTemplate`) | `Rag.montar_prompt`, `prompts/rag.py` |
| 9 | **Geração da resposta** pela cadeia LCEL (só se achou contexto) | `Rag.responder`, `Rag.cadeia_de_resposta` |

### Chunking

1. **Por seção** (`ExperimentalMarkdownSyntaxTextSplitter`): cada título Markdown (`#` a `######`) abre uma seção, e o caminho de títulos (`Agente Criar > Fluxo`) acompanha o trecho. Texto sem títulos (`.txt`) vira uma seção só, com o nome do arquivo. `#` dentro de bloco de código não é título, e a indentação é preservada.
2. **Por tamanho** (`RecursiveCharacterTextSplitter`): seção maior que `RAG_TAMANHO_MAX_TRECHO` (1200 caracteres) é cortada nas fronteiras mais naturais, em ordem: parágrafo, linha, frase, palavra e caractere. Partes vizinhas de uma mesma seção repetem até `RAG_SOBREPOSICAO` (150) caracteres, para uma ideia na divisa não se perder.

Nenhum trecho passa de `RAG_TAMANHO_MAX_TRECHO`. `RAG_SOBREPOSICAO` precisa ser menor que ele (senão o chunker levanta `ValueError`).

Por que não o `MarkdownHeaderTextSplitter` (o mais conhecido): ele apaga a indentação e troca as linhas em branco por `"  \n"`, e sem linhas em branco o passo 2 não consegue cortar por parágrafo.

### Indexação incremental (Indexing API)

Cada trecho vira um `Document` do LangChain. A função `index()` calcula um hash de cada um (conteúdo + metadados) e consulta o `SQLRecordManager` (um SQLite) para saber o que já está no Chroma:

- trecho já indexado: **pulado** (nenhum embedding novo);
- trecho novo ou alterado: **adicionado** (só ele vai ao Ollama);
- trecho que não existe mais (arquivo editado ou apagado): **apagado** do Chroma (`cleanup="full"`).

Na prática: a primeira execução gera todos os embeddings; nas seguintes, só os do arquivo que mudou. Se o Ollama cair no meio, os lotes já gravados ficam registrados, e a próxima execução continua de onde parou.

O chunking roda sempre (é rápido); o que a Indexing API poupa são os embeddings.

### Busca

- **Embeddings** (significado): "marcar dentista" acha "criar evento" sem palavras em comum.
- **BM25** (palavras-chave, `BM25Plus`): acha o que o significado deixa passar (nomes, siglas, números). Sempre disponível, não precisa do Ollama. Só entram trechos com pelo menos uma palavra (radical) em comum com a pergunta. Usa o `BM25Plus`, e não o `BM25Okapi`, porque o Okapi dá idf negativo ou zero em bases pequenas.
- **Palavras-chave em português**: stopwords do NLTK + verbos de pedido ("quero", "preciso"); radicais pelo stemmer RSLP ("agendar", "agenda" e "agendamento" → `agend`). Cada palavra gera o radical da forma com acento e da forma sem acento, para "reuniao" achar "reunião".
- **RRF**: soma `1 / (60 + posição)` de cada lista, sem comparar escalas diferentes. Por isso o `score` é pequeno (no máximo ≈ 0,033): só compare scores de uma mesma busca.
- **Similaridade mínima**: pela busca por embeddings só entram trechos com cosseno ≥ `RAG_SIMILARIDADE_MINIMA` (0,30).

## Contrato

```python
from destrava.rag import obter_rag

rag = obter_rag("supervisor")   # ou "planejador"; criado uma vez e reaproveitado
```

Crie o `Rag` **uma vez** (na inicialização do agente): montar o índice pode chamar o Ollama. `obter_rag(nome)` já faz esse reaproveitamento. `Rag(nome, usar_embeddings=None, indice=None)` cria um novo, direto.

| Método | O que faz |
|---|---|
| `buscar(pergunta, k=None)` | lista de `TrechoEncontrado` (`fonte`, `secao`, `texto`, `score`, `metodo`), do mais ao menos relevante; `[]` se nada for relevante ou a base for vazia |
| `contexto(pergunta, k=None)` | texto numerado, com a fonte de cada trecho; `""` se nada for relevante |
| `montar_prompt(pergunta, template=PROMPT_RAG, k=None, **campos)` | o `template` com `{contexto}` e `{pergunta_do_usuario}` preenchidos |
| `responder(pergunta, k=None)` | `RespostaRag(resposta, trechos, usou_llm)`: busca, monta o prompt e chama o LLM |
| `cadeia_de_resposta()` | a cadeia LCEL de geração (entrada: `{"contexto", "pergunta_do_usuario"}`; saída: texto) |
| `usa_embeddings`, `total_trechos`, `vazia`, `indice` | estado do índice (`indice.estatisticas`: adicionados, pulados, apagados) |

Formato do `contexto`:

```
[1] Fonte: destrava/rag/conhecimento/supervisor/agenda.md | Agenda > Criar evento
<texto do trecho>

[2] Fonte: ...
```

Erros: `buscar` levanta `TypeError` (pergunta que não é texto) e `ValueError` (pergunta vazia ou `k` inválido). `responder` levanta `ErroLLM` se o Ollama falhar ao gerar. `Rag("inexistente")` levanta `ValueError` listando as bases. Falha do Ollama na **busca** não é erro (ver "Sem o Ollama").

Se a busca não achar nada, `responder` devolve o texto fixo `RESPOSTA_SEM_CONTEXTO` **sem chamar o LLM** (`usou_llm = False`): perguntar ao modelo sem contexto o deixaria inventar.

### Usar o contexto no prompt de um agente

Ponha `{contexto}` no prompt do agente e monte com `montar_prompt`. A pergunta passada é a que se busca na base.

```python
# Supervisor: o contexto entra no prompt que decide o agente
rag = obter_rag("supervisor")
prompt = rag.montar_prompt(pedido_do_usuario, template=PROMPT_SUPERVISOR)

# Planejador: busca pela descrição do projeto; {entrada} é o campo que o prompt já tem
rag = obter_rag("planejador")
prompt = rag.montar_prompt(projeto, template=PROMPT_PLANEJADOR, entrada=entrada_json)
```

O template vira um `ChatPromptTemplate` (uma mensagem "human"; o Gemma 2 não tem papel "system"). Cuidados (formato `str.format`):

- Chaves literais (um JSON de exemplo no prompt) devem ser escritas `{{` e `}}`.
- Chaves **dentro do contexto** não causam problema: só o template é interpretado.
- O contexto é dado de consulta, não instrução: o prompt deve dizer isso (o `PROMPT_RAG` já diz).

Os agentes **ainda não chamam o RAG**: o Supervisor não existe e o `PROMPT_PLANEJADOR` (em outra branch) ainda não tem a lacuna `{contexto}`. Quem integrar cada um acrescenta a lacuna e chama `montar_prompt`.

## Como preencher uma base

Cada agente tem a sua pasta:

| Base | Pasta |
|---|---|
| `supervisor` | `destrava/rag/conhecimento/supervisor/` |
| `planejador` | `destrava/rag/conhecimento/planejador/` |

Basta colocar arquivos `.md` ou `.txt` na pasta (subpastas valem). **Não é preciso mexer em código**: na próxima execução, a Indexing API indexa só o que mudou. Para outra pasta ou outro arquivo, edite `RAG_BASES` em `destrava/core/config.py`.

Regras do formato:

- **UTF-8** (o BOM do Bloco de Notas é aceito). Outro encoding dá erro dizendo qual arquivo.
- **Títulos importam**: cada seção vira um trecho, e o caminho de títulos entra na busca. Prefira seções curtas e focadas, com título que diga do que tratam (`## Criar evento`, não `## Detalhes`).
- Uma seção de até ~1200 caracteres vira **um** trecho inteiro. Acima disso é dividida automaticamente, mas o ideal é uma ideia por seção.
- Feche todo bloco de código (```` ``` ````): um bloco aberto e nunca fechado é descartado pelo splitter, junto com o resto do arquivo.
- Arquivos e pastas começando com `.` são ignorados.
- Escreva do jeito que o usuário **pede**, não só do jeito que o sistema **faz**: a busca funciona melhor quando o texto traz as palavras da pergunta (e sinônimos).
- O que é **regra fixa e sempre necessária** ao agente (formato de saída, restrições) é melhor no prompt do agente; o RAG serve para o conteúdo que muda, cresce ou só é preciso em alguns pedidos.

Para conferir o que o RAG acha na sua base:

```
python -m scripts.teste_rag supervisor "sua pergunta" --prompt
```

## Sem o Ollama

O RAG funciona sem o Ollama, só com palavras-chave:

| Situação | O que acontece |
|---|---|
| Ollama fora do ar ou sem o modelo ao montar o índice | índice só com palavras-chave; na próxima criação do `Rag` ele sincroniza o Chroma de novo |
| Ollama cai no meio da indexação | os lotes já gravados ficam; a próxima execução continua de onde parou |
| Ollama cai depois do índice pronto | aquela busca usa só palavras-chave (`metodo = "lexico"`) |
| `Rag(nome, usar_embeddings=False)` | nunca chama o Ollama nem abre o Chroma |
| `Rag(nome, usar_embeddings=True)` | exige embeddings: levanta `ErroLLM` se não houver |

Para ter a busca completa: `ollama pull nomic-embed-text` (modelo em `config.MODELO_EMBEDDING`).

Todas as falhas do Ollama (servidor fora, modelo não instalado, tempo esgotado) chegam como `ErroLLM`: `llm_client.traduzir_erros` converte as exceções do `httpx` e do cliente do Ollama.

## Banco vetorial

`BancoVetorial` (`banco_vetorial.py`) abre um Chroma persistente (`chromadb.PersistentClient`) pelo adaptador `langchain_chroma.Chroma`, com métrica de cosseno e telemetria desligada. A busca devolve a similaridade de cosseno (1 − distância), na escala de `RAG_SIMILARIDADE_MINIMA`.

O que fica em disco (`.rag_indices/`, no `.gitignore`):

```
.rag_indices/<base>/<assinatura do modelo>/chroma/          banco vetorial
.rag_indices/<base>/<assinatura do modelo>/registro.sqlite  registros da Indexing API
```

A assinatura é um hash do modelo de embeddings e do prefixo de documento. Trocar um deles cria uma pasta nova (todos os vetores são refeitos) e apaga a antiga. Para recomeçar do zero, basta apagar `.rag_indices/`.

Para trocar por FAISS, Qdrant ou pgvector, use outro `VectorStore` do LangChain que aceite apagar por ID; a Indexing API e o recuperador continuam iguais.

## Configuração

Tudo em `destrava/core/config.py`:

| Constante | Padrão | O que é |
|---|---|---|
| `MODELO_EMBEDDING` | `nomic-embed-text` | modelo de embeddings do Ollama |
| `RAG_PREFIXO_DOCUMENTO` / `RAG_PREFIXO_CONSULTA` | `search_document: ` / `search_query: ` | prefixos do nomic-embed-text (deixe `""` em modelo sem prefixo) |
| `RAG_BASES` | supervisor, planejador | pasta(s) de cada base |
| `RAG_EXTENSOES` | `.md`, `.txt` | arquivos lidos das pastas |
| `RAG_TAMANHO_MAX_TRECHO` | 1200 | caracteres por trecho |
| `RAG_SOBREPOSICAO` | 150 | caracteres repetidos entre partes de uma seção dividida |
| `RAG_LOTE_EMBEDDING` | 32 | trechos por chamada ao gerar embeddings (`batch_size` da Indexing API) |
| `RAG_TOP_K` | 4 | trechos devolvidos por busca |
| `RAG_SIMILARIDADE_MINIMA` | 0,30 | cosseno mínimo na busca por embeddings |
| `PASTA_INDICES_RAG` | `.rag_indices/` | Chroma e registros da Indexing API |

Mexer em tamanho ou sobreposição muda os trechos, e a Indexing API reindexa os que mudaram. Mexer no modelo ou no prefixo de documento refaz todos os vetores.

## Dependências

- `llm_client`: `criar_chat()`, `criar_embeddings()`, `perguntar(prompt)`, `traduzir_erros` e `ErroLLM`.
- `config`: as constantes acima, mais `RAIZ_PROJETO`, `MODELO`, `OLLAMA_URL` e `TIMEOUT_LLM`.
- `prompts/rag.py`: `PROMPT_RAG` e `RESPOSTA_SEM_CONTEXTO`.
- Bibliotecas: ver a seção "Frameworks" e o `requirements.txt`.
- **Dados do NLTK**: as stopwords e as regras do RSLP são baixadas na primeira execução (para `~/nltk_data`). Sem internet, baixe antes: `python -m nltk.downloader stopwords rslp`.

## Como testar

Testes automáticos (sem Ollama e sem internet: as requisições HTTP são bloqueadas e um modelo de embeddings falso gera os vetores; o Chroma e o SQLite são reais, numa pasta temporária):

```
python -m pytest tests/test_rag.py
```

Manual, vendo trechos, prompt e resposta (a busca completa precisa do Ollama com `nomic-embed-text`; `--responder` precisa também do `config.MODELO`):

```
python -m scripts.teste_rag supervisor "marca dentista amanhã às 15h" --prompt
python -m scripts.teste_rag planejador "api de cadastro de alunos" --sem-embeddings
```

### Avaliação com o ragas

`scripts/avaliar_rag.py` roda o RAG em perguntas de um JSON e usa um LLM juiz para dar notas de 0 a 1: fidelidade (a resposta inventou?), relevância da resposta, precisão do contexto (a busca trouxe trechos úteis?) e, com respostas de referência, cobertura do contexto.

```
python -m scripts.avaliar_rag planejador                        # usa scripts/avaliacao/planejador.json
python -m scripts.avaliar_rag planejador --juiz gemma2:9b -k 3
```

Use para comparar configurações (mude um parâmetro, rode de novo, sempre com o mesmo juiz). Com o `gemma2:2b` como juiz, uma pergunta leva cerca de 2 minutos, e notas `nan` (juiz fora do formato) são comuns.

## Limitações

- **Base do supervisor vazia**: `buscar` devolve `[]` e `responder` devolve o texto fixo.
- **Nenhum agente chama o RAG ainda** (ver "Usar o contexto no prompt de um agente").
- **Juiz fraco na avaliação**: com o `gemma2:2b`, as notas do ragas são ruidosas; compare tendências, não valores absolutos.
- **Radical depende de acento**: o RSLP trata "reunião" e "reuniao" de forma diferente. Gerar os dois radicais resolve a maioria dos casos, mas não todos (ex.: "reunioes" sem acento).
- **Splitter "experimental"**: o `ExperimentalMarkdownSyntaxTextSplitter` pode mudar entre versões do `langchain-text-splitters` (a versão está fixada no `requirements.txt`).
- **Início mais lento**: importar LangChain e Chroma leva alguns segundos na criação do `Rag` (por isso `obter_rag` reaproveita o objeto).
- **Não guarda memória** entre perguntas: cada busca é independente.
