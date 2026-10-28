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

# MODELO
# Qual cliente de LLM usar: "ollama" (oficial, llm_client.py) ou
# "transformers" (alternativo, llm.py). Os agentes não mudam: sempre usam
# perguntar() do llm_client.py, que repassa para o cliente escolhido aqui.
CLIENTE_LLM = "ollama"
MODELO = "gemma2:2b"            # depois: "gemma2:9b"
OLLAMA_URL = "http://localhost:11434"
TIMEOUT_LLM = 120

# MODELO ALTERNATIVO (core/llm.py, via transformers, para quem não pode usar o Ollama)
MODELO_TRANSFORMERS = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_TOKENS_TRANSFORMERS = 350
TEMPERATURA_TRANSFORMERS = 0.3

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




