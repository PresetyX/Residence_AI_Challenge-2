"""Avaliação do RAG com o ragas (métricas de qualidade, usando um LLM como juiz).

Para cada pergunta de um arquivo JSON, roda o RAG de verdade (busca + resposta)
e entrega ao ragas a pergunta, os trechos recuperados e a resposta gerada. O
ragas então usa um LLM "juiz" para dar notas de 0 a 1:

    faithfulness                  Fidelidade: as afirmações da resposta estão
                                  apoiadas nos trechos? (baixa = o modelo inventou)
    answer_relevancy              Relevância da resposta: ela responde ao que foi
                                  perguntado? (precisa do modelo de embeddings)
    llm_context_precision_without_reference
                                  Precisão do contexto: os trechos recuperados são
                                  úteis para a resposta? (avalia a BUSCA)
    context_recall                Cobertura do contexto: os trechos trazem tudo o
                                  que a resposta de referência diz? (só entra se
                                  TODAS as perguntas tiverem "referencia")

Para que serve: comparar configurações com números em vez de impressão. Rode,
mude um parâmetro (RAG_TAMANHO_MAX_TRECHO, RAG_TOP_K, RAG_SIMILARIDADE_MINIMA,
o texto da base...) e rode de novo.

Arquivo de perguntas (JSON), uma lista de objetos:
    [{"pergunta": "...", "referencia": "resposta esperada (opcional)"}, ...]
Exemplo pronto: scripts/avaliacao/planejador.json

Uso (na raiz do projeto, com o Ollama ligado):
    python -m scripts.avaliar_rag planejador
    python -m scripts.avaliar_rag planejador --perguntas minhas_perguntas.json -k 3
    python -m scripts.avaliar_rag planejador --juiz gemma2:9b

Limitações (leia antes de confiar nos números):
    - O juiz padrão é o próprio config.MODELO (gemma2:2b). Um modelo pequeno é um
      juiz fraco: o ragas pede respostas em JSON e com raciocínio em várias
      etapas, e modelos pequenos erram com frequência. Notas "nan" significam
      que o juiz não conseguiu responder no formato. Use --juiz com um modelo
      maior, se tiver, e compare sempre com o MESMO juiz.
    - Os prompts internos do ragas são em inglês; as notas ainda valem para
      texto em português, mas o juiz trabalha um pouco pior.
    - É lento: várias chamadas ao LLM por pergunta. Poucas perguntas bastam.
    - Perguntas para as quais a busca não acha nada não chegam ao LLM (o RAG
      responde com o texto fixo) e ficam fora das métricas; o script as lista.

Este script NÃO faz parte do RAG em uso: é uma ferramenta de desenvolvimento,
separada para que o ragas (pesado) nunca seja carregado pelos agentes.
"""

import argparse
import json
import os
import warnings
from pathlib import Path

# O ragas envia estatísticas de uso pela internet, a menos que esta variável
# exista. Precisa ser definida ANTES de importar o ragas.
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

# O ragas 0.4 avisa que as métricas de `ragas.metrics` e os wrappers do
# LangChain (LangchainLLMWrapper/LangchainEmbeddingsWrapper) sairão na versão
# 1.0. A alternativa nova dele exige um cliente da OpenAI, o que tiraria o
# LangChain do caminho. Por isso o requirements.txt fixa ragas<0.5, e aqui
# os avisos são silenciados para não poluir a saída.
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*deprecated.*")

from langchain_ollama import ChatOllama  # noqa: E402
from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    Faithfulness,
    LLMContextPrecisionWithoutReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from destrava.core import config  # noqa: E402
from destrava.core.llm_client import ErroLLM, criar_chat, criar_embeddings  # noqa: E402
from destrava.rag import Rag  # noqa: E402

PASTA_PERGUNTAS = Path(__file__).resolve().parent / "avaliacao"


def ler_perguntas(arquivo: Path) -> list[dict]:
    """Lê e valida o arquivo de perguntas.

    Raises:
        SystemExit: Se o arquivo não existir ou estiver fora do formato.
    """
    if not arquivo.is_file():
        raise SystemExit(f"Arquivo de perguntas não encontrado: {arquivo}")
    itens = json.loads(arquivo.read_text(encoding="utf-8"))
    if not isinstance(itens, list) or not all(
        isinstance(i, dict) and isinstance(i.get("pergunta"), str) and i["pergunta"].strip()
        for i in itens
    ):
        raise SystemExit('Formato esperado: [{"pergunta": "...", "referencia": "..."}, ...]')
    return itens


def montar_amostras(rag: Rag, itens: list[dict], k: int | None) -> list[SingleTurnSample]:
    """Roda o RAG em cada pergunta e guarda o que o ragas precisa avaliar.

    Uma ``SingleTurnSample`` é uma interação de uma rodada: pergunta do usuário
    (user_input), trechos recuperados (retrieved_contexts), resposta gerada
    (response) e, opcionalmente, a resposta esperada (reference).
    """
    amostras = []
    for n, item in enumerate(itens, start=1):
        pergunta = item["pergunta"]
        print(f"[{n}/{len(itens)}] {pergunta}")
        resposta = rag.responder(pergunta, k)
        if not resposta.usou_llm:
            print("    nenhum trecho encontrado: fica fora da avaliação")
            continue
        amostras.append(
            SingleTurnSample(
                user_input=pergunta,
                # O ragas recebe só o texto dos trechos, como o LLM recebeu.
                retrieved_contexts=[t.texto for t in resposta.trechos],
                response=resposta.resposta,
                reference=item.get("referencia"),
            )
        )
    return amostras


def escolher_metricas(amostras: list[SingleTurnSample], com_embeddings: bool) -> list:
    """As métricas que fazem sentido com os dados disponíveis."""
    # Fidelidade e precisão do contexto só precisam de pergunta, trechos e resposta.
    metricas = [Faithfulness(), LLMContextPrecisionWithoutReference()]
    # A relevância gera perguntas a partir da resposta e compara com a original
    # por embeddings; sem o modelo de embeddings, não dá para calcular.
    if com_embeddings:
        metricas.append(ResponseRelevancy())
    # A cobertura compara os trechos com a resposta esperada.
    if amostras and all(a.reference for a in amostras):
        metricas.append(LLMContextRecall())
    return metricas


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o RAG de uma base com o ragas.")
    parser.add_argument("base", choices=sorted(config.RAG_BASES), help="base de conhecimento")
    parser.add_argument(
        "--perguntas",
        type=Path,
        default=None,
        help="arquivo JSON de perguntas (padrão: scripts/avaliacao/<base>.json)",
    )
    parser.add_argument("-k", type=int, default=None, help="trechos por pergunta")
    parser.add_argument(
        "--juiz", default=None, help=f"modelo do Ollama usado como juiz (padrão: {config.MODELO})"
    )
    args = parser.parse_args()

    itens = ler_perguntas(args.perguntas or PASTA_PERGUNTAS / f"{args.base}.json")

    # 1. O RAG em avaliação, exatamente como os agentes o usam.
    rag = Rag(args.base)
    modo = "palavras-chave + embeddings" if rag.usa_embeddings else "só palavras-chave"
    print(f"Base '{args.base}': {rag.total_trechos} trechos, busca por {modo}.\n")

    try:
        amostras = montar_amostras(rag, itens, args.k)
    except ErroLLM as erro:
        raise SystemExit(f"O RAG não conseguiu responder: {erro}") from None
    if not amostras:
        raise SystemExit("Nenhuma pergunta teve trechos recuperados; nada a avaliar.")

    # 2. Juiz e embeddings para o ragas. Os wrappers adaptam objetos do
    #    LangChain (ChatOllama, Embeddings) à interface que o ragas espera.
    chat = criar_chat()
    if args.juiz:
        chat = ChatOllama(model=args.juiz, base_url=chat.base_url, client_kwargs=chat.client_kwargs)
    juiz = LangchainLLMWrapper(chat)
    embeddings = LangchainEmbeddingsWrapper(criar_embeddings()) if rag.usa_embeddings else None

    metricas = escolher_metricas(amostras, com_embeddings=embeddings is not None)
    print(f"\nAvaliando {len(amostras)} respostas com {[m.name for m in metricas]}")
    print(f"Juiz: {chat.model} (pode levar alguns minutos)\n")

    # 3. A avaliação. max_workers=1: um LLM local atende uma chamada por vez;
    #    chamadas em paralelo só disputariam a mesma GPU/CPU e estourariam o
    #    tempo limite.
    resultado = evaluate(
        dataset=EvaluationDataset(samples=amostras),
        metrics=metricas,
        llm=juiz,
        embeddings=embeddings,
        run_config=RunConfig(timeout=config.TIMEOUT_LLM, max_workers=1),
        show_progress=True,
    )

    # 4. Notas por pergunta e a média de cada métrica.
    tabela = resultado.to_pandas()
    colunas = [m.name for m in metricas]
    print("\nNotas por pergunta (0 a 1; nan = o juiz não respondeu no formato):")
    for _, linha in tabela.iterrows():
        notas = "  ".join(f"{c}={linha[c]:.2f}" for c in colunas)
        print(f"- {linha['user_input'][:60]}\n    {notas}")
    print(f"\nMédias: {resultado}")


if __name__ == "__main__":
    main()
