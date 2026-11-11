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
#     Exceção: o que muda de máquina para máquina (endereço do servidor de IA,
#     modelo, tempos limite, chave de API) pode vir de variáveis de ambiente do
#     sistema, com o mesmo nome da constante. Sem a variável, vale o padrão
#     daqui. Assim nenhum IP nem chave fica no código (ver README, "Servidor de IA").
#   - O escopo do OAuth NÃO fica aqui: cada agente informa o escopo de que precisa
#     ao chamar get_service() (ver google_client.py).
#   - Regras de negócio de cada agente ficam no próprio agente, não aqui.
#     Exceção: core/agenda_engine.py (cálculo de livres, ocupados e conflitos) fica
#     no core porque pode ser reaproveitado por mais de um agente.


import os
from datetime import time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path


def _texto_do_ambiente(nome: str, padrao: str) -> str:
    """Valor da variável de ambiente `nome`, ou `padrao` se ausente ou vazia."""
    valor = os.environ.get(nome, "").strip()
    return valor or padrao


def _numero_do_ambiente(nome: str, padrao: float) -> float:
    """Número positivo da variável de ambiente `nome`, ou `padrao` se ausente.

    Raises:
        ValueError: Se a variável existir mas não for um número positivo. Falhar
            na importação é melhor que descobrir o erro no meio de uma chamada.
    """
    bruto = os.environ.get(nome, "").strip()
    if not bruto:
        return padrao
    try:
        valor = float(bruto)
    except ValueError:
        raise ValueError(f"A variável de ambiente {nome} deve ser um número (recebido: {bruto!r}).") from None
    if valor <= 0:
        raise ValueError(f"A variável de ambiente {nome} deve ser maior que zero (recebido: {bruto!r}).")
    return valor


# MODELO (usado pelo llm_client.py, via Ollama)
# Em desenvolvimento, o Ollama roda na própria máquina. Com o servidor de IA
# compartilhado, cada pessoa aponta OLLAMA_URL para o PC com a GPU (pela
# Tailscale) e não baixa modelo nenhum. Ex.: MODELO=gemma4:12b-it-q4_K_M.
MODELO = _texto_do_ambiente("MODELO", "gemma2:2b")
OLLAMA_URL = _texto_do_ambiente("OLLAMA_URL", "http://localhost:11434")
# Segundos para a resposta do modelo chegar. Com várias pessoas na mesma GPU,
# os pedidos entram em fila no Ollama; o padrão folgado evita estourar o tempo
# enquanto se espera a vez. Aumente com TIMEOUT_LLM=600, por exemplo.
TIMEOUT_LLM = _numero_do_ambiente("TIMEOUT_LLM", 300)
# Tamanho da janela de contexto (tokens) pedida ao Ollama. O padrão do Ollama
# (~4096) pode cortar o prompt do Planejador (regras + trechos do RAG).
NUM_CTX = int(_numero_do_ambiente("NUM_CTX", 8192))

# SERVIDOR DE IA (opcional)
# Endereço do serviço de story points (BGE-M3 + rede neural) no PC com a GPU,
# ex.: http://<ip-tailscale>:8001. Vazio: o backend carrega o modelo localmente
# (precisa de torch e sentence-transformers; ver requirements-ia.txt).
STORY_POINTS_URL = _texto_do_ambiente("STORY_POINTS_URL", "")
TIMEOUT_STORY_POINTS = _numero_do_ambiente("TIMEOUT_STORY_POINTS", 120)
# Chave compartilhada do servidor de IA. Se definida no servidor, o serviço de
# story points exige o cabeçalho X-API-Key; se definida no notebook, o backend
# envia esse cabeçalho (e também um Authorization: Bearer ao Ollama, útil se o
# Ollama estiver atrás de um proxy que confere a chave). Vazio: desligado.
CHAVE_API_IA = _texto_do_ambiente("CHAVE_API_IA", "")

# RAG (usado por destrava/rag/)
# Modelo de embeddings do Ollama (instale com: ollama pull nomic-embed-text).
# Se não estiver disponível, o RAG busca só por palavras-chave (BM25).
MODELO_EMBEDDING = _texto_do_ambiente("MODELO_EMBEDDING", "nomic-embed-text")
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

# RAG: pasta do banco vetorial (Chroma) e dos registros da Indexing API de cada
# base (uma subpasta por agente). Atualizada sozinha quando as fontes ou os
# parâmetros mudam; pode ser apagada para recomeçar do zero. Está no .gitignore.
PASTA_INDICES_RAG = RAIZ_PROJETO / ".rag_indices"




