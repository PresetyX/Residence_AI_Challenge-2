# Converte os dados enviados ao modelo e a resposta dele para o formato JSON.
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from destrava.core.llm_client import perguntar
from destrava.prompts.planejador import PROMPT_PLANEJADOR
from destrava.rag import obter_rag


class Tarefa(BaseModel):
    # Define o contrato de uma tarefa retornada pela IA. Campos extras são
    # rejeitados e os valores devem ter os tipos esperados, sem conversão automática.
    model_config = ConfigDict(extra="forbid", strict=True)

    # A ordem deve ser positiva e o título deve ter pelo menos um caractere.
    ordem: int = Field(ge=1)
    titulo: str = Field(min_length=1)
    # Literal limita a categoria da tarefa aos valores listados abaixo.
    tipo: Literal[
        "requisitos",
        "interface",
        "banco_de_dados",
        "backend",
        "frontend",
        "testes",
        "documentacao",
    ]
    # A dificuldade aceita apenas inteiros de 1 (baixa) a 3 (alta).
    dificuldade: int = Field(ge=1, le=3)


class Plano(BaseModel):
    # O plano também rejeita campos extras e exige ao menos uma tarefa válida.
    model_config = ConfigDict(extra="forbid", strict=True)

    tarefas: list[Tarefa] = Field(min_length=1)


class ErroPlanejador(ValueError):
    # Guarda a resposta recebida para facilitar a análise quando a IA retorna
    # um JSON inválido ou um plano que não segue o contrato esperado.
    def __init__(self, mensagem: str, resposta_original: str):
        super().__init__(mensagem)
        self.resposta_original = resposta_original

def remover_bloco_markdown(texto: str) -> str:
    texto = texto.strip()
    linhas = texto.splitlines()

    if (
        len(linhas) >= 3
        and linhas[0].strip().lower() in ("```json", "```")
        and linhas[-1].strip() == "```"
    ):
        return "\n".join(linhas[1:-1]).strip()

    return texto

class AgentePlanejador:
    def __init__(self, rag=None):
        # O RAG pode ser injetado (testes). Sem ele, usa a base "planejador",
        # criada só na primeira execução (indexar pode chamar o Ollama).
        self._rag = rag

    def executar(self, projeto: str, prazo: str) -> dict:
        # Impede o envio de uma descrição ausente, de outro tipo ou só com espaços.
        if not isinstance(projeto, str) or not projeto.strip():
            raise ValueError("Informe a descrição do projeto.")

        # Para este teste, o prazo deve chegar como AAAA-MM-DD.
        if not isinstance(prazo, str):
            raise ValueError("O prazo deve ser uma string AAAA-MM-DD.")

        try:
            # Verifica se o texto representa uma data existente no calendário.
            data_prazo = date.fromisoformat(prazo)
        except ValueError as erro:
            raise ValueError("Use o prazo no formato AAAA-MM-DD.") from erro

        # Exige a escrita exata AAAA-MM-DD, mesmo que o Python aceite outra forma.
        # Esta validação não verifica se o prazo está no futuro.
        if data_prazo.isoformat() != prazo:
            raise ValueError("Use o prazo no formato AAAA-MM-DD.")

        # Remove espaços nas pontas da descrição e serializa a entrada como JSON.
        # ensure_ascii=False mantém caracteres como acentos legíveis.
        entrada = json.dumps(
            {"projeto": projeto.strip(), "prazo": prazo},
            ensure_ascii=False,
        )

        # Busca na base do Planejador os trechos relevantes para o projeto e os
        # encaixa na lacuna {contexto} do prompt, junto com a {entrada}.
        # A descrição do projeto é a consulta feita ao RAG.
        rag = self._rag or obter_rag("planejador")
        prompt = rag.montar_prompt(
            projeto.strip(),
            template=PROMPT_PLANEJADOR,
            entrada=entrada,
        )
        resposta = perguntar(prompt)

        try:
          
            texto_json = remover_bloco_markdown(resposta)
            dados = json.loads(texto_json)
            plano = Plano.model_validate(dados)

            # Confere se a lista já está numerada de 1 até N, sem saltos,
            # repetições ou tarefas fora de ordem. Não reordena a resposta.
            ordens = [tarefa.ordem for tarefa in plano.tarefas]
            esperado = list(range(1, len(plano.tarefas) + 1))

            if ordens != esperado:
                raise ValueError(
                    "As tarefas devem estar ordenadas de 1 até N."
                )

            # min_length não rejeita espaços sozinhos; esta checagem cobre esse caso.
            if any(not tarefa.titulo.strip() for tarefa in plano.tarefas):
                raise ValueError("Uma tarefa possui título vazio.")

        except (ValueError, ValidationError) as erro:
            raise ErroPlanejador(
                f"Resposta inválida do Planejador: {erro}",
                resposta,
            ) from erro

        # Converte o plano validado em um dicionário comum para quem chamou o agente.
        return plano.model_dump()
