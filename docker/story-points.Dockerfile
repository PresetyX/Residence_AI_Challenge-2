# Serviço de story points do servidor de IA (BGE-M3 + modelos/rede_neural.pt) na GPU.
#
# Não use este arquivo direto: ele é construído pelo docker-compose.servidor-ia.yml
# (ver README, "Servidor de IA com Docker"). O contexto é a raiz do projeto, e o
# .dockerignore libera só os arquivos copiados abaixo: nada de credentials.json,
# token_*.json, .venv ou frontend entra na imagem.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# torch com CUDA 12.8 (a RTX 50xx precisa do 12.8 ou mais novo). Fica numa camada
# própria: é a parte mais pesada e quase nunca muda.
RUN pip install torch --index-url https://download.pytorch.org/whl/cu128

# Só o que o serviço importa (mesmas faixas de requirements.txt e requirements-ia.txt).
RUN pip install \
    "fastapi>=0.115,<1.0" \
    "uvicorn[standard]>=0.34,<1.0" \
    "httpx>=0.27,<1.0" \
    "pydantic==2.14.3" \
    "sentence-transformers>=3.0,<6.0" \
    tzdata

COPY destrava/__init__.py destrava/__init__.py
COPY destrava/core/__init__.py destrava/core/config.py destrava/core/
COPY backend/__init__.py backend/story_points.py backend/servidor_story_points.py backend/
COPY modelos/rede_neural.pt modelos/rede_neural.pt

EXPOSE 8001

# start-period longo: na primeira subida o BGE-M3 (~2,3 GB) é baixado para o volume.
HEALTHCHECK --interval=15s --timeout=5s --start-period=600s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/saude', timeout=4)"

CMD ["uvicorn", "backend.servidor_story_points:app", "--host", "0.0.0.0", "--port", "8001"]
