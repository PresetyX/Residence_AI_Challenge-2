# RAG do Supervisor

> Documentação técnica do **estado atual** do RAG. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Dar ao Supervisor o contexto certo para cada pedido do usuário: qual agente chamar, que JSON montar e como interpretar a resposta. O RAG busca na documentação dos agentes e em um guia de roteamento e devolve só os trechos relevantes, para o prompt do Supervisor ficar curto (o modelo é pequeno, `gemma2:2b`).

O RAG **só recupera trechos**. Ele não escolhe o agente, não chama o Google e não gera a resposta: isso é do Supervisor.

## Contrato

Classe `RagSupervisor` em `destrava/rag/recuperador.py` (importável de `destrava.rag`).

| Método | Entrada | Saída |
|---|---|---|
| `buscar(pergunta, k=None)` | pedido em texto livre; `k` = quantos trechos (padrão `config.RAG_TOP_K`) | lista de `TrechoEncontrado`, do mais ao menos relevante (pode ser vazia) |
| `contexto(pergunta, k=None)` | o mesmo | texto pronto para o prompt (`""` se nada for relevante) |

`TrechoEncontrado`: `fonte` (arquivo), `secao` (caminho de títulos), `texto`, `score` e `metodo` (`lexico` ou `hibrido`). A nota só serve para ordenar resultados do mesmo método.

Formato do `contexto`:

```
[1] Fonte: destrava/rag/conhecimento/roteamento.md | Roteamento do Supervisor > Quando chamar o agente criar
<texto do trecho>

[2] Fonte: docs/criar.md | Agente Criar > Regras
<texto do trecho>
```

Uso:

```python
from destrava.rag import RagSupervisor

rag = RagSupervisor()   # monta (ou carrega do disco) o índice
contexto = rag.contexto("marca dentista amanhã às 15h")
prompt = f"...{contexto}..."
```

Crie o `RagSupervisor` **uma vez** (na inicialização do Supervisor) e reaproveite: montar o índice pode chamar o Ollama.

Erros: `buscar` levanta `TypeError` (pergunta que não é texto) e `ValueError` (pergunta vazia ou `k` inválido). Falha do Ollama **não** é erro (ver "Sem o Ollama"), exceto com `usar_embeddings=True`.

## Fluxo

| # | Passo | Onde |
|---|---|---|
| 1 | Lê as fontes de `config.RAG_FONTES` | `indice.ler_fontes` |
| 2 | Divide cada `.md` em trechos, um por seção (seções grandes são divididas por parágrafo, sem cortar bloco de código) | `chunker.dividir_markdown` |
| 3 | Gera um embedding por trecho (Ollama) e salva o índice em `.rag_indice.json` | `indice.construir_indice` |
| 4 | Na busca: nota BM25 de cada trecho para o pedido | `recuperador._BM25` |
| 5 | Na busca: similaridade por embeddings, se disponível | `recuperador._ordem_por_significado` |
| 6 | Combina as duas listas por RRF e devolve os `k` melhores | `RagSupervisor.buscar` |

```
pedido → [BM25] ───────────┐
                           ├→ [RRF] → k trechos → contexto do prompt
pedido → [embedding] ──────┘
```

## Regras

- **Fontes** (`config.RAG_FONTES`): `docs/contrato.md`, `docs/visualizar.md`, `docs/criar.md` e `destrava/rag/conhecimento/roteamento.md`. Os docs de editar e excluir ainda são modelos em branco e ficam de fora; quando esses agentes ficarem prontos, inclua os `.md` em `RAG_FONTES` e atualize o guia de roteamento.
- **Guia de roteamento** (`destrava/rag/conhecimento/roteamento.md`): escrito para o RAG. Diz quando chamar cada agente, com frases de exemplo, o JSON de entrada, como converter datas e como ler a resposta. É a fonte que mais pesa na decisão do Supervisor; edite com cuidado. Parte dele são **orientações de comportamento** (perguntar quando falta o horário de término, checar a agenda antes de criar, avisar que editar/excluir não estão prontos): revise com o grupo.
- **BM25**: palavras sem acento nem maiúscula, sem stopwords, reduzidas a um radical de 6 letras (`agendar`, `agenda` e `agendamento` se encontram). Não é um stemmer completo.
- **RRF**: soma `1 / (60 + posição)` de cada lista. Evita comparar notas BM25 com cosseno, que têm escalas diferentes.
- **Similaridade mínima**: pela busca por embeddings só entram trechos com cosseno ≥ `RAG_SIMILARIDADE_MINIMA` (0,30).
- **Cópia em disco**: `.rag_indice.json` (no `.gitignore`) só é reaproveitada se as fontes, o tamanho dos trechos e o modelo de embeddings forem os mesmos. Editar um `.md` refaz o índice sozinho.

## Sem o Ollama

O RAG funciona sem o Ollama, só com palavras-chave:

| Situação | O que acontece |
|---|---|
| Ollama fora do ar ou sem o modelo ao montar o índice | índice só com palavras-chave; na próxima criação do `RagSupervisor` ele tenta gerar os embeddings de novo |
| Ollama cai depois do índice pronto | aquela busca usa só palavras-chave (`metodo = "lexico"`) |
| `RagSupervisor(usar_embeddings=False)` | nunca chama o Ollama |
| `RagSupervisor(usar_embeddings=True)` | exige embeddings: levanta `ErroLLM` se não houver |

Para ter a busca completa: `ollama pull nomic-embed-text` (modelo em `config.MODELO_EMBEDDING`).

## Dependências do core

- `llm_client`: `gerar_embeddings(textos)` (endpoint `/api/embed` do Ollama) e `ErroLLM`.
- `config`: `MODELO_EMBEDDING`, `RAG_PREFIXO_DOCUMENTO`, `RAG_PREFIXO_CONSULTA`, `RAG_FONTES`, `RAG_TAMANHO_MAX_TRECHO`, `RAG_TOP_K`, `RAG_SIMILARIDADE_MINIMA`, `ARQUIVO_INDICE_RAG`, `RAIZ_PROJETO`, `OLLAMA_URL`, `TIMEOUT_LLM`.
- Sem dependências novas no `requirements.txt` (BM25 e cosseno são feitos em Python puro; `pydantic` já é usado no projeto).

## Como testar

Testes automáticos (sem Ollama e sem internet; o Ollama é simulado):

```
python -m pytest tests/test_rag.py
```

Manual, vendo os trechos que o Supervisor receberia:

```
python -m scripts.teste_rag "marca dentista amanhã às 15h"
python -m scripts.teste_rag --sem-embeddings --contexto "cancela a reunião de sexta"
```

| Pedido | Seção esperada entre as primeiras |
|---|---|
| `Tenho horário livre amanhã?` | Quando chamar o agente visualizar |
| `Marca um dentista dia 15 às 15h` | Quando chamar o agente criar |
| `Cancela a reunião de sexta` | Quando chamar editar ou excluir |
| `O que significa erro na etapa meio do fluxo?` | Contrato JSON dos agentes > Erros |
| `Qual a capital da França?` | Fora do escopo |

## Limitações

- **Não decide nada**: devolve trechos; escolher o agente e montar o JSON é do Supervisor.
- **Corpus pequeno** (cerca de 40 trechos): a busca é feita em Python puro, sem banco vetorial. Se as fontes crescerem muito (centenas de arquivos), vale trocar por um banco vetorial.
- **Radical de 6 letras** é uma aproximação: palavras diferentes com o mesmo começo podem se confundir.
- **A busca só por palavras-chave** não acha sinônimos que não estejam no texto (por isso o guia de roteamento lista vários jeitos de pedir a mesma coisa).
- **Não guarda memória** entre pedidos: cada busca é independente.
- **A qualidade da busca completa (com embeddings) não foi medida com o Ollama real** nos testes automáticos, que o simulam. Confira com `scripts/teste_rag.py` na máquina que tem o `nomic-embed-text`.
