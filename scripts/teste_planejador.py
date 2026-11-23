import json
from datetime import date, timedelta

from destrava.agents.planejador import AgentePlanejador, ErroPlanejador
from destrava.core.llm_client import ErroLLM


PROJETOS = [
    (
        "Construir uma API de cadastro de alunos com nome, RA e email. "
        "Permitir cadastrar, listar, atualizar e excluir alunos."
    ),
    (
        "Construir uma página de portfólio com apresentação pessoal, "
        "lista de projetos e informações de contato, sem backend."
    ),
    (
        "Construir um aplicativo de lista de tarefas com criação, "
        "marcação de conclusão e armazenamento local."
    ),
    (
        "Construir um sistema de biblioteca com cadastro de livros, "
        "cadastro de leitores, empréstimos e devoluções."
    ),
    (
        "Construir um programa de terminal que leia um CSV de notas "
        "e gere um relatório com a média de cada aluno."
    ),
]


def main():
    agente = AgentePlanejador()
    prazo = (date.today() + timedelta(days=14)).isoformat()
    validos = 0

    for numero, projeto in enumerate(PROJETOS, start=1):
        print(f"\nCASO {numero}: {projeto}")

        try:
            resultado = agente.executar(projeto, prazo)
        except ErroPlanejador as erro:
            print(f"FALHA DE FORMATO OU CONTRATO: {erro}")
            print("Resposta original:")
            print(erro.resposta_original)
        except ErroLLM as erro:
            print(f"FALHA NA CHAMADA AO MODELO: {erro}")
        else:
            validos += 1
            print(json.dumps(resultado, ensure_ascii=False, indent=2))

    print(f"\nRespostas aprovadas na validação: {validos}/{len(PROJETOS)}")


if __name__ == "__main__":
    main()