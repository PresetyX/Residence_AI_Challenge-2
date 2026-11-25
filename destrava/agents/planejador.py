# Converte os dados enviados ao modelo e a resposta dele para o formato JSON.
import json
import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from destrava.core.intencao import normalizar, pede_projeto
from destrava.core.llm_client import ErroLLM, perguntar
from destrava.prompts.planejador import PROMPT_PLANEJADOR
from destrava.rag import obter_rag


class Tarefa(BaseModel):
    # Define o contrato de uma tarefa retornada pela IA. Campos extras são
    # rejeitados e os valores devem ter os tipos esperados, sem conversão automática.
    model_config = ConfigDict(extra="forbid", strict=True)

    # A etapa deve ser positiva; a sequência 1..N é conferida no agente.
    etapa: int = Field(ge=1)
    # Os campos de texto devem ter pelo menos um caractere.
    titulo: str = Field(min_length=1)
    objetivo: str = Field(min_length=1)
    entregaveis: str = Field(min_length=1)
    demonstracao: str = Field(min_length=1)
    # A etapa de uma tarefa anterior, ou 0 quando a tarefa não depende de nenhuma.
    # Que ela aponte para uma etapa anterior é conferido no agente.
    dependencia: int = Field(ge=0)
    # O esforço estimado da tarefa, em story points.
    story_points: int = Field(ge=1)


# Campos de texto da tarefa que não podem ficar só com espaços.
CAMPOS_TEXTO = ("titulo", "objetivo", "entregaveis", "demonstracao")


class Plano(BaseModel):
    # O plano também rejeita campos extras e exige ao menos uma tarefa válida.
    model_config = ConfigDict(extra="forbid", strict=True)

    tarefas: list[Tarefa] = Field(min_length=1)


class NaoEntendi(BaseModel):
    # Saída de escape: o modelo não conseguiu interpretar o pedido.
    model_config = ConfigDict(extra="forbid", strict=True)

    nao_entendi: Literal[True]


# JSON Schema do Plano, gerado pelo Pydantic.
ESQUEMA_PLANO = Plano.model_json_schema()

# Esquema enviado ao Ollama como `format`: a resposta é um Plano ou um NaoEntendi.
ESQUEMA_RESPOSTA = TypeAdapter(Plano | NaoEntendi).json_schema()


MENSAGEM_NAO_ENTENDI = (
    "Não entendi. Pode me contar o que o software faz, onde ele roda "
    "(web, celular, terminal…), quais funcionalidades você quer e, "
    "se tiver, as tecnologias?"
)


class PedidoNaoEntendido(Exception):
    # O modelo não entendeu o pedido. A mensagem já é o texto final para o usuário.
    def __init__(self):
        super().__init__(MENSAGEM_NAO_ENTENDI)


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

# Pergunta ou pedido de informação: não é projeto (decidido sem chamar a LLM).
_PERGUNTA = re.compile(
    r"^\W*(?:qual|quais|quem|quando|onde|como|por que|porque|o que|me (?:conte|diga|explique))\b"
)
_TERMOS_DE_SOFTWARE = re.compile(
    r"\b(app|aplicativo|sistema|site|plataforma|api|software|programa|jogo|game|dashboard|chatbot|bot"
    r"|projeto|tcc|mvp|tela|cadastr\w*)\b"
)
# Título que só prepara o ambiente. "Configurar alertas" é funcionalidade e não entra.
_SO_CONFIGURACAO = re.compile(
    r"^(?:configur\w*\s+(?:(?:o|do|de)\s+)?(?:inicial|ambiente|projeto)|configurar e conectar"
    r"|ambiente|setup|instal\w*\s+(?:(?:o|do|as|das)\s+)?(?:ambiente|dependencias)"
    r"|(?:inicializ|prepar|estrutur)\w*\s+(?:(?:o|do|a|da)\s+)?(?:inicial|ambiente|projeto)"
    r"|(?:criar|modelar) o banco)\b"
)


def _e_pergunta_fora_do_assunto(projeto: str) -> bool:
    t = normalizar(projeto)
    return (bool(_PERGUNTA.search(t)) and not _TERMOS_DE_SOFTWARE.search(t)
            and not pede_projeto(projeto))


def problemas_do_plano(tarefas: list[dict], projeto: str) -> list[str]:
    """Regras do prompt que o esquema não cobre e que o modelo costuma quebrar."""
    problemas = []
    if _SO_CONFIGURACAO.search(normalizar(tarefas[0]["titulo"]).strip()):
        problemas.append(
            "A etapa 1 é só configuração. Ela deve ser a menor funcionalidade completa "
            "que o usuário consegue usar, já incluindo o ambiente."
        )
    if not re.search(r"apresentacao|landing", normalizar(projeto)):
        texto = normalizar(" ".join(f"{t['titulo']} {t['entregaveis']}" for t in tarefas))
        if re.search(r"pagina de apresentacao|landing page", texto):
            problemas.append("Há uma página de apresentação que a ENTRADA não pediu. Remova.")
    return problemas


def fundir_configuracao(tarefas: list[dict]) -> list[dict]:
    """Junta uma etapa 1 que é só configuração à etapa 2 e renumera o plano.

    É a regra do prompt (a etapa 1 é uma funcionalidade que já inclui o ambiente)
    garantida em código quando o modelo insiste em separar.
    """
    if len(tarefas) < 2 or not _SO_CONFIGURACAO.search(normalizar(tarefas[0]["titulo"]).strip()):
        return tarefas
    configuracao, primeira, *resto = tarefas
    fundida = {
        **primeira,
        "etapa": 1,
        "entregaveis": f"{configuracao['entregaveis']}, {primeira['entregaveis']}",
        "dependencia": 0,
        "story_points": configuracao["story_points"] + primeira["story_points"],
    }
    # As etapas 1 e 2 viram a 1; as demais (e quem depende delas) sobem uma posição.
    renumeradas = [
        {**t, "etapa": t["etapa"] - 1,
         "dependencia": 0 if t["dependencia"] == 0 else max(1, t["dependencia"] - 1)}
        for t in resto
    ]
    return [fundida, *renumeradas]


class AgentePlanejador:
    def __init__(self, rag=None):
        # O RAG pode ser injetado (testes). Sem ele, usa a base "planejador",
        # criada só na primeira execução (indexar pode chamar o Ollama).
        self._rag = rag

    def executar(self, projeto: str, prazo: str, modelo: str | None = None) -> dict:
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

        if _e_pergunta_fora_do_assunto(projeto):
            raise PedidoNaoEntendido()

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
        # O esquema vai como `format` para o Ollama: a resposta já sai como JSON
        # com a chave "tarefas" (sete campos por tarefa) ou com "nao_entendi".
        # As regras que o esquema não cobre (etapas de 1 a N, dependência
        # anterior, textos só com espaços) continuam sendo conferidas abaixo.
        opcoes = {"modelo": modelo} if modelo else {}
        plano = self._validar(perguntar(prompt, formato=ESQUEMA_RESPOSTA, **opcoes))

        # Uma segunda chance quando o plano quebra uma regra do prompt. Se a nova
        # resposta não for melhor, fica a primeira (que já cumpre o contrato).
        problemas = problemas_do_plano(plano["tarefas"], projeto)
        if problemas:
            correcao = "\n\nCORREÇÃO: refaça o plano. " + " ".join(problemas)
            try:
                novo = self._validar(
                    perguntar(prompt + correcao, formato=ESQUEMA_RESPOSTA, **opcoes)
                )
            except (ErroPlanejador, PedidoNaoEntendido, ErroLLM):
                novo = None
            if novo and len(problemas_do_plano(novo["tarefas"], projeto)) < len(problemas):
                plano = novo
        return {"tarefas": fundir_configuracao(plano["tarefas"])}

    def _validar(self, resposta: str) -> dict:
        """Converte a resposta da LLM em um plano que cumpre o contrato.

        Raises:
            PedidoNaoEntendido, ErroPlanejador.
        """
        try:
            texto_json = remover_bloco_markdown(resposta)
            dados = json.loads(texto_json)

            # O modelo sinalizou que não entendeu o pedido: não há plano a validar.
            # PedidoNaoEntendido não é ValueError, então escapa do except abaixo.
            if isinstance(dados, dict) and "nao_entendi" in dados:
                NaoEntendi.model_validate(dados)
                raise PedidoNaoEntendido()

            plano = Plano.model_validate(dados)

            # Confere se a lista já está numerada de 1 até N, sem saltos,
            # repetições ou tarefas fora de ordem. Não reordena a resposta.
            etapas = [tarefa.etapa for tarefa in plano.tarefas]
            esperado = list(range(1, len(plano.tarefas) + 1))

            if etapas != esperado:
                raise ValueError(
                    "As etapas devem estar numeradas de 1 até N."
                )

            for tarefa in plano.tarefas:
                # min_length não rejeita espaços sozinhos; esta checagem cobre esse caso.
                for campo in CAMPOS_TEXTO:
                    if not getattr(tarefa, campo).strip():
                        raise ValueError(
                            f"A etapa {tarefa.etapa} possui {campo} vazio."
                        )

                # Uma tarefa só pode depender de uma etapa anterior a ela
                # (0 = sem dependência). Isso também impede ciclos.
                if tarefa.dependencia >= tarefa.etapa:
                    raise ValueError(
                        f"A etapa {tarefa.etapa} depende da etapa "
                        f"{tarefa.dependencia}, que não é anterior a ela."
                    )

        except (ValueError, ValidationError) as erro:
            raise ErroPlanejador(
                f"Resposta inválida do Planejador: {erro}",
                resposta,
            ) from erro

        # Converte o plano validado em um dicionário comum para quem chamou o agente.
        return plano.model_dump()
