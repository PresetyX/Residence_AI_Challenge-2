"""Compara o Planejador SEM o RAG e COM o RAG, nos mesmos projetos.

Sem RAG, o prompt é montado com o contexto "(nenhum trecho relevante
encontrado)", exatamente como acontece quando a busca não acha nada.

Uso (na raiz do projeto, com o Ollama ligado):
    python -m scripts.teste_planejador_sem_rag             -> só sem RAG, projetos prontos
    python -m scripts.teste_planejador_sem_rag -p "API de cadastro de alunos"
    python -m scripts.teste_planejador_sem_rag -i          -> pede os projetos, um por vez
    python -m scripts.teste_planejador_sem_rag -p "..." --prazo 2026-12-31
    python -m scripts.teste_planejador_sem_rag --com-rag   -> sem e com RAG
    python -m scripts.teste_planejador_sem_rag --prompt    -> mostra o prompt enviado
"""

import argparse
import json
from datetime import date, timedelta

from destrava.agents.planejador import PROMPT_PLANEJADOR, AgentePlanejador, ErroPlanejador
from destrava.core.llm_client import ErroLLM
from destrava.rag.rag import criar_template
from scripts.teste_planejador import PROJETOS


class RagVazio:
    """RAG de mentira: nunca acha trecho nenhum."""

    def montar_prompt(self, pergunta, template, **campos):
        return criar_template(template).format_messages(
            contexto="(nenhum trecho relevante encontrado)",
            pergunta_do_usuario=pergunta,
            **campos,
        )[0].content


def rodar(agente: AgentePlanejador, rotulo: str, prazo: str, projetos: list[str]) -> int:
    print(f"\n{'=' * 20} {rotulo} {'=' * 20}")
    validos = 0
    for numero, projeto in enumerate(projetos, start=1):
        print(f"\nCASO {numero}: {projeto}")
        try:
            resultado = agente.executar(projeto, prazo)
        except ErroPlanejador as erro:
            print(f"FALHA DE FORMATO OU CONTRATO: {erro}")
        except ErroLLM as erro:
            print(f"FALHA NA CHAMADA AO MODELO: {erro}")
        else:
            validos += 1
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(f"\n[{rotulo}] aprovadas: {validos}/{len(projetos)}")
    return validos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--com-rag", action="store_true", help="roda também com o RAG")
    parser.add_argument("--prompt", action="store_true", help="mostra o prompt sem RAG")
    parser.add_argument("-p", "--projeto", action="append",
                        help="descrição do projeto (pode repetir a opção)")
    parser.add_argument("-i", "--interativo", action="store_true",
                        help="pede os projetos digitados, um por vez")
    parser.add_argument("--prazo", help="AAAA-MM-DD (padrão: daqui a 14 dias)")
    args = parser.parse_args()

    prazo = args.prazo or (date.today() + timedelta(days=14)).isoformat()

    if args.interativo:
        agente = AgentePlanejador(rag=RagVazio())
        agente_rag = AgentePlanejador() if args.com_rag else None
        while True:
            texto = input("\nProjeto (ou 'sair'): ").strip()
            if texto.lower() in ("", "sair", "exit", "quit"):
                return
            rodar(agente, "SEM RAG", prazo, [texto])
            if agente_rag:
                rodar(agente_rag, "COM RAG", prazo, [texto])

    projetos = args.projeto or PROJETOS

    if args.prompt:
        entrada = json.dumps({"projeto": projetos[0], "prazo": prazo}, ensure_ascii=False)
        print(RagVazio().montar_prompt(projetos[0], PROMPT_PLANEJADOR, entrada=entrada))
        return

    sem = rodar(AgentePlanejador(rag=RagVazio()), "SEM RAG", prazo, projetos)
    if args.com_rag:
        com = rodar(AgentePlanejador(), "COM RAG", prazo, projetos)
        print(f"\nResumo: sem RAG {sem}/{len(projetos)} | com RAG {com}/{len(projetos)}")


if __name__ == "__main__":
    main()
