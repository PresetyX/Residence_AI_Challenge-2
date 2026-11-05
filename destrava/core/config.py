# Configurações globais do projeto.
#
# O que este arquivo guarda (somente valores, sem lógica):
#   - Fuso horário (ex.: America/Sao_Paulo)
#   - Horário de acordar e de dormir (período em que se procura horário livre)
#   - Nome do modelo usado no Ollama (ex.: gemma2:2b para desenvolver, gemma2:9b para o final)
#
# Decisões do grupo:
#   - Trocar de modelo é mudar apenas o nome aqui; llm_client.py lê este valor.
#   - Toda a configuração fica neste arquivo (o projeto não usa .env).
#   - O escopo do OAuth NÃO fica aqui: cada agente informa o escopo de que precisa
#     ao chamar get_service() (ver google_client.py).
#   - Regras de negócio de cada agente ficam no próprio agente, não aqui.
#     Exceção: core/agenda_engine.py (cálculo de livres, ocupados e conflitos) fica
#     no core porque pode ser reaproveitado por mais de um agente.


from datetime import time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# MODELO (usado pelo llm_client.py, via Ollama)
MODELO = "gemma2:2b"            # depois: "gemma2:9b"
OLLAMA_URL = "http://localhost:11434"
TIMEOUT_LLM = 120

# RAG (usado por destrava/rag/)
# Modelo de embeddings do Ollama (instale com: ollama pull nomic-embed-text).
# Se não estiver disponível, o RAG busca só por palavras-chave (BM25).
MODELO_EMBEDDING = "nomic-embed-text"
# O nomic-embed-text rende mais quando o texto indexado e a pergunta recebem
# estes prefixos. Para um modelo de embeddings sem prefixo, deixe os dois "".
RAG_PREFIXO_DOCUMENTO = "search_document: "
RAG_PREFIXO_CONSULTA = "search_query: "
# Uma base de conhecimento por agente. Cada valor é uma lista de arquivos ou
# pastas (relativos à raiz do projeto); de pasta entram todos os .md e .txt,
# inclusive das subpastas. O conteúdo é mantido por quem cuida da base: o RAG
# só indexa e busca (ver docs/rag.md). Base vazia é válida: a busca devolve nada.
RAG_BASES = {
    "supervisor": ("destrava/rag/conhecimento/supervisor",),
    "planejador": ("destrava/rag/conhecimento/planejador",),
}
RAG_EXTENSOES = (".md", ".txt")
RAG_TAMANHO_MAX_TRECHO = 1200   # caracteres por trecho (seções maiores são divididas)
RAG_SOBREPOSICAO = 150          # caracteres repetidos entre trechos de uma seção dividida
RAG_LOTE_EMBEDDING = 32         # trechos enviados ao Ollama por chamada ao gerar embeddings
RAG_TOP_K = 4                   # quantos trechos devolver por busca
RAG_SIMILARIDADE_MINIMA = 0.30  # cosseno mínimo para um trecho entrar pela busca por embeddings

# ROTINA
FUSO = ZoneInfo("America/Sao_Paulo")
HORARIO_ACORDAR = time(6, 0)
HORARIO_DORMIR = time(22, 0)
DURACAO_MINIMA_LIVRE = timedelta(minutes=30)
# Eventos de dia inteiro (feriado, aniversário, viagem) sempre aparecem na lista.
# False: não ocupam horário (não tiram horários livres nem geram conflitos).
#        É o padrão do Google, que marca esses eventos como "disponível".
# True:  ocupam o dia todo, como um evento normal.
DIA_INTEIRO_BLOQUEIA = False

# GOOGLE
# pega seu diretório, config.py deve estar em destrava/core (parents[2] sai dois níveis)
ESCOPO_SOMENTE_LEITURA = "https://www.googleapis.com/auth/calendar.readonly"
ESCOPO_CALENDARIO = "https://www.googleapis.com/auth/calendar"
NOME_ARQUIVO_CREDENCIAIS = "credentials.json"
ARQUIVO_TOKEN_SOMENTE_LEITURA = "token_readonly.json"
ARQUIVO_TOKEN_CALENDARIO = "token_calendar.json"
RAIZ_PROJETO = Path(__file__).resolve().parents[2]
ARQUIVO_CREDENCIAIS = RAIZ_PROJETO / NOME_ARQUIVO_CREDENCIAIS

# RAG: pasta com a cópia local do índice de cada base (um arquivo por agente),
# reconstruída sozinha quando as fontes ou os parâmetros mudam. Está no .gitignore.
PASTA_INDICES_RAG = RAIZ_PROJETO / ".rag_indices"




