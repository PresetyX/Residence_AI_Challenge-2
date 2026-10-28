"""Teste manual do AgenteVisualizar com a agenda real (Passo 1).

Uso:
    python teste_visualizar.py              -> testa o dia de amanhã
    python teste_visualizar.py 2026-10-29   -> testa um dia específico
"""

import sys
from datetime import date, datetime, timedelta

from destrava.agents.visualizar import AgenteVisualizar
from destrava.core import config
from destrava.agents.visualizar import responder

def formatar(texto_iso: str) -> str:
    """Converte '2026-10-29T09:00:00-03:00' em '29/10 09:00'."""
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