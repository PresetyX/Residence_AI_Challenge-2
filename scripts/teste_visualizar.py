"""Teste manual do AgenteVisualizar com a agenda real (Passo 1).

Consulta um dia inteiro do Google Agenda e imprime, em sequência:
    1. Os horários ocupados (eventos e dias inteiros).
    2. Os horários livres, com a duração de cada um.
    3. Os conflitos entre eventos (ou "Nenhum").
    4. Os totais de minutos livres e ocupados.
    5. A resposta escrita pelo Gemma para "Como está minha agenda nesse dia?".

Diferença em relação ao cli.py: aqui o período é definido pelo próprio
script (o dia escolhido, de 00:00 a 00:00 do dia seguinte), sem pedir ao
LLM que interprete a pergunta. Assim dá para conferir o cálculo e a
resposta separadamente da etapa de interpretação.

Uso (na raiz do projeto, com -m para o Python encontrar o pacote destrava):
    python -m scripts.teste_visualizar              -> testa o dia de amanhã
    python -m scripts.teste_visualizar 2026-10-29   -> testa um dia específico

Requisitos:
    - credentials.json na raiz do projeto (na primeira vez, o navegador abre
      para autorizar a leitura da agenda).
    - Ollama rodando com o modelo definido em config.MODELO (só para a
      etapa 5; as etapas 1 a 4 funcionam sem o LLM).
"""

import sys
from datetime import date, datetime, timedelta

from destrava.agents.visualizar import AgenteVisualizar
from destrava.core import config
from destrava.agents.visualizar import responder

def formatar(texto_iso: str) -> str:
    """Converte uma data e hora em ISO 8601 para o formato curto dia/mês hora.

    Exemplo: '2026-10-29T09:00:00-03:00' vira '29/10 09:00'.

    Args:
        texto_iso: data e hora em texto no formato ISO 8601, como as que o
            AgenteVisualizar devolve.

    Returns:
        Texto no formato "DD/MM HH:MM".

    Raises:
        ValueError: se o texto não estiver em formato ISO 8601 válido.
    """
    return datetime.fromisoformat(texto_iso).strftime("%d/%m %H:%M")


if len(sys.argv) > 1:
    dia = date.fromisoformat(sys.argv[1])
else:
    dia = datetime.now(config.FUSO).date() + timedelta(days=1)

inicio = datetime.combine(dia, datetime.min.time(), tzinfo=config.FUSO)
fim = inicio + timedelta(days=1)

print(f"Período: {formatar(inicio.isoformat())} até {formatar(fim.isoformat())}\n")

resultado = AgenteVisualizar().executar(inicio, fim)

print("=== OCUPADOS ===")
for bloco in resultado["ocupados"]:
    print(f"- {formatar(bloco['inicio'])} a {formatar(bloco['fim'])}  "
          f"{bloco['titulo']} ({bloco['tipo']})")

print("\n=== LIVRES ===")
for livre in resultado["livres"]:
    print(f"- {formatar(livre['inicio'])} a {formatar(livre['fim'])}  "
          f"({livre['duracao_minutos']:.0f} min)")

print("\n=== CONFLITOS ===")
titulos = {bloco["id"]: bloco["titulo"] for bloco in resultado["ocupados"]}
if not resultado["conflitos"]:
    print("- Nenhum")
for conflito in resultado["conflitos"]:
    nomes = " x ".join(titulos.get(i, i) for i in conflito["ids_eventos"])
    print(f"- {nomes}: {formatar(conflito['inicio_sobreposicao'])} a "
          f"{formatar(conflito['fim_sobreposicao'])}")

print(f"\nTotal livre: {resultado['total_minutos_livres']:.0f} min | "
      f"Total ocupado: {resultado['total_minutos_ocupados']:.0f} min")

print("\n=== RESPOSTA DO GEMMA ===")
print(responder("Como está minha agenda nesse dia?", resultado))