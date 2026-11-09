"""Testes do AgentePlanejador, sem Ollama.

O RAG é trocado por um falso que só renderiza o template de verdade (o mesmo
ChatPromptTemplate do RAG), e o LLM é trocado por uma resposta fixa.
"""

import json

import pytest

from destrava.agents import planejador as modulo
from destrava.agents.planejador import AgentePlanejador, ErroPlanejador
from destrava.prompts.planejador import PROMPT_PLANEJADOR
from destrava.rag.rag import criar_template

PRAZO = "2026-12-01"


class RagFalso:
    """Monta o prompt com o template real, sem buscar nada na base."""

    def __init__(self):
        self.prompt = None

    def montar_prompt(self, pergunta, template, **campos):
        mensagens = criar_template(template).format_messages(
            contexto="(contexto de teste)", **campos
        )
        self.prompt = mensagens[0].content
        return self.prompt


def tarefa(etapa=1, dependencia=0, **outros):
    dados = {
        "etapa": etapa,
        "titulo": f"Implementar a funcionalidade {etapa}",
        "objetivo": "Permitir que o usuário faça algo.",
        "entregaveis": "Código e testes.",
        "demonstracao": "Rodar o programa e mostrar o resultado.",
        "dependencia": dependencia,
        "story_points": 3,
    }
    dados.update(outros)
    return dados


def executar(monkeypatch, resposta):
    """Roda o agente com o LLM devolvendo `resposta` (dict vira JSON)."""
    if not isinstance(resposta, str):
        resposta = json.dumps(resposta, ensure_ascii=False)
    chamadas = []

    def perguntar_falso(prompt, formato=None):
        chamadas.append(formato)
        return resposta

    monkeypatch.setattr(modulo, "perguntar", perguntar_falso)
    rag = RagFalso()
    plano = AgentePlanejador(rag=rag).executar("Uma API de alunos.", PRAZO)
    # O agente sempre pede a saída no formato do esquema do Plano.
    assert chamadas == [modulo.ESQUEMA_PLANO]
    return plano, rag


def test_prompt_renderiza_com_o_json_de_exemplo():
    """As chaves do JSON de exemplo são texto, não lacunas do template."""
    texto = criar_template(PROMPT_PLANEJADOR).format_messages(
        contexto="CTX", entrada="ENT"
    )[0].content

    assert '"etapa": 1' in texto
    assert '"story_points": 1' in texto
    assert "{{" not in texto
    assert "CTX" in texto and "ENT" in texto


def test_plano_valido(monkeypatch):
    resposta = {"tarefas": [tarefa(1), tarefa(2, dependencia=1)]}

    plano, rag = executar(monkeypatch, resposta)

    assert plano == resposta
    assert "Uma API de alunos." in rag.prompt


def test_aceita_bloco_markdown(monkeypatch):
    resposta = "```json\n" + json.dumps({"tarefas": [tarefa(1)]}) + "\n```"

    plano, _ = executar(monkeypatch, resposta)

    assert plano["tarefas"][0]["etapa"] == 1


@pytest.mark.parametrize(
    "tarefas, trecho_erro",
    [
        ([], "tarefas"),
        ([tarefa(1), tarefa(3)], "1 até N"),
        ([tarefa(2)], "1 até N"),
        ([tarefa(1, dependencia=1)], "não é anterior"),
        ([tarefa(1), tarefa(2, dependencia=3)], "não é anterior"),
        ([tarefa(1, dependencia=-1)], "dependencia"),
        ([tarefa(1, story_points=0)], "story_points"),
        ([tarefa(1, story_points="3")], "story_points"),
        ([tarefa(1, objetivo="   ")], "objetivo vazio"),
        ([tarefa(1, tipo="backend")], "tipo"),
        ([{k: v for k, v in tarefa(1).items() if k != "demonstracao"}], "demonstracao"),
    ],
)
def test_plano_invalido(monkeypatch, tarefas, trecho_erro):
    with pytest.raises(ErroPlanejador, match=trecho_erro) as erro:
        executar(monkeypatch, {"tarefas": tarefas})

    assert erro.value.resposta_original


def test_resposta_que_nao_e_json(monkeypatch):
    with pytest.raises(ErroPlanejador):
        executar(monkeypatch, "não sei")


@pytest.mark.parametrize("prazo", ["01/12/2026", "2026-02-30", 20261201])
def test_prazo_invalido(prazo):
    with pytest.raises(ValueError, match="prazo"):
        AgentePlanejador(rag=RagFalso()).executar("Projeto.", prazo)


def test_esquema_enviado_ao_ollama_exige_os_sete_campos():
    tarefa_esquema = modulo.ESQUEMA_PLANO["$defs"]["Tarefa"]

    assert set(tarefa_esquema["required"]) == {
        "etapa", "titulo", "objetivo", "entregaveis",
        "demonstracao", "dependencia", "story_points",
    }
    assert tarefa_esquema["additionalProperties"] is False
