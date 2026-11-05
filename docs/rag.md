# RAG

> Documentação técnica do **estado atual** do RAG. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Dar a cada agente (Supervisor, Planejador) o contexto certo para cada pedido: o RAG busca numa base de conhecimento e devolve só os trechos relevantes, para o prompt ficar curto (o modelo é pequeno, `gemma2:2b`).

O RAG é **a máquina**: chunking, embeddings, banco vetorial, busca, construção do prompt e geração. Ele **não tem conteúdo**: o que vai dentro de cada base é responsabilidade de quem cuida dela (ver "Como preencher uma base"). Base vazia é válida: a busca não devolve nada e nada quebra.

## Fluxo

```
INDEXAÇÃO (uma vez, ao criar o Rag; refeita sozinha se a base mudar)
  base de conhecimento → chunking → embedding dos chunks → armazenamento (banco vetorial)

INFERÊNCIA (a cada pergunta)
  pergunta → embedding da pergunta → busca por similaridade → recuperação de contexto
           → construção do prompt → geração da resposta
```

| # | Passo | Onde |
|---|---|---|
| 1 | Lê os `.md`/`.txt` da base (arquivos ou pastas, com subpastas) | `indice.ler_fontes` |
| 2 | **Chunking**: divide por seção; seções grandes por parágrafo; blocos ainda maiores por linha/frase, com sobreposição | `chunker.dividir_texto` |
| 3 | **Embedding dos chunks**: um vetor por trecho (Ollama), em lotes | `indice.construir_indice`, `llm_client.gerar_embeddings` |
| 4 | **Armazenamento**: trechos + vetores no banco vetorial; cópia em `.rag_indices/<base>.json` | `banco_vetorial.BancoVetorialLocal`, `indice` |
| 5 | **Embedding da pergunta**, com o mesmo modelo da indexação | `recuperador.Recuperador` |
| 6 | **Busca por similaridade** (cosseno) + palavras-chave (BM25), combinadas por RRF | `recuperador.Recuperador.buscar` |
| 7 | **Recuperação de contexto**: os `N` trechos mais próximos, numerados e com a fonte | `Rag.contexto` |
| 8 | **Construção do prompt**: o contexto injetado no prompt do agente | `Rag.montar_prompt`, `prompts/rag.py` |
| 9 | **Geração da resposta** pelo LLM (só se achou contexto) | `Rag.responder` |

### Chunking

1. **Por seção**: cada título Markdown (`#` a `######`) abre uma seção, e o caminho de títulos (`Agente Criar > Fluxo`) acompanha o trecho. Texto sem títulos (`.txt`) vira uma seção só, com o nome do arquivo.
2. **Por parágrafo**: seção maior que `RAG_TAMANHO_MAX_TRECHO` (1200 caracteres) é dividida em blocos separados por linha em branco; blocos vizinhos pequenos são juntados até o limite. Bloco de código (```) e tabela não são cortados no meio.
3. **Por linha, frase e palavra**: um bloco que sozinho passa do limite é cortado nessas fronteiras, e cada parte repete o fim da anterior (`RAG_SOBREPOSICAO`, 150 caracteres), para uma ideia na divisa não se perder.

Nenhum trecho passa de `RAG_TAMANHO_MAX_TRECHO`. `RAG_SOBREPOSICAO` precisa ser menor que ele (senão o chunker levanta `ValueError`).

### Busca

- **Embeddings** (significado): "marcar dentista" acha "criar evento" sem palavras em comum.
- **BM25** (palavras-chave): acha o que o significado deixa passar (nomes, siglas, números). Sempre disponível, não precisa do Ollama.
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
| `usa_embeddings`, `total_trechos`, `vazia` | estado do índice |

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

Cuidados com o template (`str.format`):

- Chaves literais (um JSON de exemplo no prompt) devem ser escritas `{{` e `}}`.
- Chaves **dentro do contexto** não causam problema: só o template é interpretado.
- O contexto é dado de consulta, não instrução: o prompt deve dizer isso (o `PROMPT_RAG` já diz).

Os agentes **ainda não chamam o RAG**: o Supervisor não existe e o `PROMPT_PLANEJADOR` (em outra branch) ainda não tem a lacuna `{contexto}`. Quem integrar cada um acrescenta a lacuna e chama `montar_prompt`.

## Como preencher uma base

Cada agente tem a sua pasta, hoje vazia (só um `.gitkeep`):

| Base | Pasta |
|---|---|
| `supervisor` | `destrava/rag/conhecimento/supervisor/` |
| `planejador` | `destrava/rag/conhecimento/planejador/` |

Basta colocar arquivos `.md` ou `.txt` na pasta (subpastas valem). **Não é preciso mexer em código**: o índice é refeito sozinho na próxima execução. Para outra pasta ou outro arquivo, edite `RAG_BASES` em `destrava/core/config.py`.

Regras do formato:

- **UTF-8** (o BOM do Bloco de Notas é aceito). Outro encoding dá erro dizendo qual arquivo.
- **Títulos importam**: cada seção vira um trecho, e o caminho de títulos entra na busca. Prefira seções curtas e focadas, com título que diga do que tratam (`## Criar evento`, não `## Detalhes`).
- Uma seção de até ~1200 caracteres vira **um** trecho inteiro. Acima disso é dividida automaticamente, mas o ideal é uma ideia por seção.
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
| Ollama fora do ar ou sem o modelo ao montar o índice | índice só com palavras-chave; na próxima criação do `Rag` ele tenta gerar os embeddings de novo |
| Ollama cai depois do índice pronto | aquela busca usa só palavras-chave (`metodo = "lexico"`) |
| `Rag(nome, usar_embeddings=False)` | nunca chama o Ollama |
| `Rag(nome, usar_embeddings=True)` | exige embeddings: levanta `ErroLLM` se não houver |
| Modelo de embeddings trocado (outra dimensão de vetor) | a busca cai para palavras-chave até o índice ser refeito |

Para ter a busca completa: `ollama pull nomic-embed-text` (modelo em `config.MODELO_EMBEDDING`).

## Banco vetorial

`BancoVetorialLocal` (`banco_vetorial.py`) guarda os trechos e os vetores em memória e compara a pergunta com todos por cosseno, em Python puro. Para uma base de centenas de trechos é instantâneo e não exige dependência nova. A cópia em disco (`.rag_indices/<base>.json`, no `.gitignore`) só é reaproveitada se os arquivos, o tamanho dos trechos, a sobreposição e o modelo de embeddings forem os mesmos.

Para trocar por Chroma, FAISS ou pgvector, escreva uma classe com os membros de `BancoVetorial` (o `Protocol` no mesmo arquivo) e passe-a ao `Recuperador(indice, banco=...)`.

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
| `RAG_LOTE_EMBEDDING` | 32 | trechos por chamada ao gerar embeddings |
| `RAG_TOP_K` | 4 | trechos devolvidos por busca |
| `RAG_SIMILARIDADE_MINIMA` | 0,30 | cosseno mínimo na busca por embeddings |
| `PASTA_INDICES_RAG` | `.rag_indices/` | cópia local dos índices |

Mexer em tamanho, sobreposição, modelo ou prefixo refaz o índice sozinho.

## Dependências do core

- `llm_client`: `gerar_embeddings(textos)` (endpoint `/api/embed` do Ollama), `perguntar(prompt)` e `ErroLLM`.
- `config`: as constantes acima, mais `RAIZ_PROJETO`, `OLLAMA_URL` e `TIMEOUT_LLM`.
- `prompts/rag.py`: `PROMPT_RAG` e `RESPOSTA_SEM_CONTEXTO`.
- Sem dependências novas no `requirements.txt` (BM25 e cosseno são feitos em Python puro; `pydantic` já é usado no projeto).

## Como testar

Testes automáticos (sem Ollama e sem internet; o Ollama é simulado, e a base usada é fictícia, criada numa pasta temporária):

```
python -m pytest tests/test_rag.py
```

Manual, vendo trechos, prompt e resposta (a busca completa precisa do Ollama com `nomic-embed-text`; `--responder` precisa também do `config.MODELO`):

```
python -m scripts.teste_rag supervisor "marca dentista amanhã às 15h" --prompt
python -m scripts.teste_rag planejador "api de cadastro de alunos" --sem-embeddings
```

## Limitações

- **Sem conteúdo**: com as bases vazias, `buscar` devolve `[]` e `responder` devolve o texto fixo. A qualidade real da busca só pode ser avaliada depois que as bases forem preenchidas.
- **Nenhum agente chama o RAG ainda** (ver "Usar o contexto no prompt de um agente").
- **A busca completa (com embeddings) não foi medida com uma base real**; os testes automáticos simulam o Ollama.
- **Banco vetorial local, em Python puro**: bom para centenas de trechos; para muito mais, troque por um banco vetorial de verdade.
- **Radical de 6 letras** (palavras-chave): aproximação, não é um stemmer completo; palavras diferentes com o mesmo começo podem se confundir.
- **Chunking por seção**: um arquivo sem títulos e sem parágrafos vira trechos por frase, com menos contexto. Títulos bons ajudam muito.
- **Não guarda memória** entre perguntas: cada busca é independente.
