"""Testes do RAG do Supervisor (sem Ollama e sem internet).

O Ollama é simulado: nenhum teste faz chamada de rede. Rodam em qualquer máquina:

    python -m pytest tests/test_rag.py
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from destrava.core import config, llm_client
from destrava.core.llm_client import ErroLLM
from destrava.rag import RagSupervisor, TrechoEncontrado
from destrava.rag import indice as modulo_indice
from destrava.rag import recuperador
from destrava.rag.chunker import dividir_markdown
from destrava.rag.indice import Indice, construir_indice
from destrava.rag.texto import tokenizar


@pytest.fixture(autouse=True)
def _isolar(tmp_path, monkeypatch):
    """Nenhum teste escreve na raiz do projeto nem chega ao Ollama de verdade."""
    monkeypatch.setattr(config, "ARQUIVO_INDICE_RAG", tmp_path / "indice.json")

    def _sem_rede(*args, **kwargs):
        raise requests.exceptions.ConnectionError("rede bloqueada nos testes")

    monkeypatch.setattr(llm_client.requests, "post", _sem_rede)


# ------------------------------------------------------------------ texto


def test_tokenizar_tira_acento_stopword_e_plural():
    assert tokenizar("Quero as REUNIÕES de amanhã") == ["reunio", "amanha"]


def test_tokenizar_aproxima_variacoes_da_mesma_palavra():
    assert tokenizar("agendar") == tokenizar("agenda") == tokenizar("agendamento")


def test_tokenizar_mantem_numeros_e_horas():
    assert "15h" in tokenizar("dentista dia 15 às 15h")


# ---------------------------------------------------------------- chunker


MD = """# Doc

Introdução.

## Seção A

Texto da A.

### Sub A1

Texto da A1.

## Seção B

```json
{"a": 1}

{"b": 2}
```

Depois do código.
"""


def test_chunker_guarda_o_caminho_de_titulos():
    trechos = dividir_markdown(MD, "doc.md")

    assert [t.secao for t in trechos] == [
        "Doc",
        "Doc > Seção A",
        "Doc > Seção A > Sub A1",
        "Doc > Seção B",
    ]
    assert all(t.fonte == "doc.md" for t in trechos)


def test_chunker_nao_corta_bloco_de_codigo_nem_trata_titulo_dentro_dele():
    md = "# T\n\n```\n# isto não é título\n\nlinha após branco\n```\n"
    trechos = dividir_markdown(md, "x.md", tamanho_max=10)

    assert len(trechos) == 1
    assert "# isto não é título" in trechos[0].texto
    assert "linha após branco" in trechos[0].texto


def test_chunker_divide_secao_grande_por_paragrafo():
    paragrafos = [f"parágrafo {i} " + "x" * 50 for i in range(6)]
    md = "# T\n\n" + "\n\n".join(paragrafos)

    trechos = dividir_markdown(md, "x.md", tamanho_max=130)

    assert len(trechos) > 1
    assert all(t.secao == "T" for t in trechos)
    assert "\n\n".join(t.texto for t in trechos) == "\n\n".join(paragrafos)


def test_chunker_ignora_secao_sem_texto():
    assert dividir_markdown("# Só título\n\n## Outro\n", "x.md") == []


# ------------------------------------------- busca por palavras-chave (real)


@pytest.fixture(scope="module")
def rag_lexico(tmp_path_factory):
    """RAG sobre as fontes reais do projeto, só com palavras-chave."""
    cache = tmp_path_factory.mktemp("rag") / "indice.json"
    indice = construir_indice(usar_embeddings=False, arquivo_cache=cache)
    return RagSupervisor(usar_embeddings=False, indice=indice)


@pytest.mark.parametrize(
    "pedido, secao_esperada",
    [
        ("Tenho horário livre amanhã?", "Quando chamar o agente visualizar"),
        ("Quais são meus horários vagos na sexta?", "Quando chamar o agente visualizar"),
        ("Marca um dentista dia 15 às 15h", "Quando chamar o agente criar"),
        ("Agenda uma reunião amanhã das 10h às 11h", "Quando chamar o agente criar"),
        ("Cancela a reunião de sexta", "Quando chamar editar ou excluir"),
        ("Muda o horário da consulta", "Quando chamar editar ou excluir"),
        ("O que significa erro na etapa meio do fluxo?", "Contrato JSON dos agentes > Erros"),
        ("Qual a capital da França?", "Fora do escopo"),
    ],
)
def test_busca_lexica_acha_a_secao_certa_entre_os_3_primeiros(
    rag_lexico, pedido, secao_esperada
):
    secoes = [t.secao for t in rag_lexico.buscar(pedido, k=3)]

    assert any(s.endswith(secao_esperada) for s in secoes), secoes


def test_busca_traz_fonte_nota_e_metodo(rag_lexico):
    resultado = rag_lexico.buscar("marca dentista amanhã", k=2)

    assert 1 <= len(resultado) <= 2
    assert all(isinstance(t, TrechoEncontrado) for t in resultado)
    assert all(t.metodo == "lexico" and t.score > 0 for t in resultado)
    assert all(t.fonte in config.RAG_FONTES for t in resultado)
    assert [t.score for t in resultado] == sorted((t.score for t in resultado), reverse=True)


def test_busca_respeita_k(rag_lexico):
    assert len(rag_lexico.buscar("agenda", k=1)) == 1
    assert len(rag_lexico.buscar("agenda", k=3)) == 3


def test_busca_sem_palavra_em_comum_devolve_vazio(rag_lexico):
    assert rag_lexico.buscar("xyzzy plugh") == []
    assert rag_lexico.contexto("xyzzy plugh") == ""


@pytest.mark.parametrize("pergunta", ["", "   ", "\n"])
def test_busca_rejeita_pergunta_vazia(rag_lexico, pergunta):
    with pytest.raises(ValueError):
        rag_lexico.buscar(pergunta)


def test_busca_rejeita_tipos_invalidos(rag_lexico):
    with pytest.raises(TypeError):
        rag_lexico.buscar(123)
    for k in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            rag_lexico.buscar("agenda", k=k)


def test_contexto_numera_trechos_e_cita_a_fonte(rag_lexico):
    contexto = rag_lexico.contexto("marca dentista amanhã", k=2)

    assert contexto.startswith("[1] Fonte: ")
    assert "[2] Fonte: " in contexto
    assert "roteamento.md" in contexto


def test_fontes_do_rag_existem_e_geram_trechos(rag_lexico):
    assert rag_lexico.total_trechos > 10
    assert not rag_lexico.usa_embeddings


# ----------------------------------------------------- embeddings (simulados)


def _vetor_falso(texto: str) -> list[float]:
    """Eixo 0 = fala de criar/marcar evento; eixo 1 = o resto."""
    criar = any(p in texto.lower() for p in ("criar", "marca", "xablau"))
    return [1.0, 0.0] if criar else [0.0, 1.0]


def _embedder_falso(textos: list[str]) -> list[list[float]]:
    return [_vetor_falso(t) for t in textos]


def _com_embeddings_falsos():
    return (
        patch.object(modulo_indice, "gerar_embeddings", _embedder_falso),
        patch.object(recuperador, "gerar_embeddings", _embedder_falso),
    )


def test_busca_hibrida_acha_por_significado_sem_palavra_em_comum():
    p1, p2 = _com_embeddings_falsos()
    with p1, p2:
        rag = RagSupervisor()
        resultado = rag.buscar("xablau", k=3)

    assert rag.usa_embeddings
    assert resultado, "a busca por significado deveria achar trechos"
    assert all(t.metodo == "hibrido" for t in resultado)
    assert any("criar" in (t.secao + t.texto).lower() for t in resultado)


def test_busca_hibrida_combina_as_duas_listas():
    p1, p2 = _com_embeddings_falsos()
    with p1, p2:
        rag = RagSupervisor()
        so_significado = {t.secao for t in rag.buscar("xablau", k=40)}
        hibrido = rag.buscar("marca dentista amanhã", k=40)

    # Quem aparece nas duas listas soma as duas notas e fica na frente.
    assert hibrido[0].score > 1 / (recuperador.RRF_K + 1)
    assert so_significado


def test_ollama_fora_do_ar_na_indexacao_cai_para_palavras_chave():
    with patch.object(modulo_indice, "gerar_embeddings", side_effect=ErroLLM("fora")):
        rag = RagSupervisor()  # usar_embeddings=None: tenta e segue sem

    assert not rag.usa_embeddings
    assert rag.buscar("marca dentista amanhã")[0].metodo == "lexico"


def test_embeddings_obrigatorios_propagam_o_erro():
    with patch.object(modulo_indice, "gerar_embeddings", side_effect=ErroLLM("fora")):
        with pytest.raises(ErroLLM):
            RagSupervisor(usar_embeddings=True)


def test_ollama_cai_depois_de_indexar_so_aquela_busca_usa_palavras_chave():
    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        rag = RagSupervisor()
    assert rag.usa_embeddings

    with patch.object(recuperador, "gerar_embeddings", side_effect=ErroLLM("caiu")):
        resultado = rag.buscar("marca dentista amanhã")

    assert resultado and all(t.metodo == "lexico" for t in resultado)


def test_modelo_de_embedding_trocado_com_outra_dimensao_nao_quebra_a_busca():
    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        rag = RagSupervisor()

    with patch.object(recuperador, "gerar_embeddings", lambda t: [[1.0, 0.0, 0.0]]):
        resultado = rag.buscar("marca dentista amanhã")

    assert resultado and all(t.metodo == "lexico" for t in resultado)


def test_usar_embeddings_false_nunca_chama_o_ollama():
    chamadas = MagicMock()
    with patch.object(modulo_indice, "gerar_embeddings", chamadas), patch.object(
        recuperador, "gerar_embeddings", chamadas
    ):
        rag = RagSupervisor(usar_embeddings=False)
        rag.buscar("marca dentista amanhã")

    chamadas.assert_not_called()


# ------------------------------------------------------------------ cache


@pytest.fixture
def fonte_temporaria(tmp_path):
    raiz = tmp_path / "projeto"
    raiz.mkdir()
    (raiz / "a.md").write_text("# A\n\nTexto sobre agenda.\n", encoding="utf-8")
    return raiz


def test_indice_e_reaproveitado_do_disco_se_as_fontes_nao_mudaram(
    fonte_temporaria, tmp_path
):
    cache = tmp_path / "cache.json"
    gerador = MagicMock(side_effect=_embedder_falso)

    with patch.object(modulo_indice, "gerar_embeddings", gerador):
        primeiro = construir_indice(fontes=["a.md"], raiz=fonte_temporaria, arquivo_cache=cache)
        segundo = construir_indice(fontes=["a.md"], raiz=fonte_temporaria, arquivo_cache=cache)

    assert gerador.call_count == 1
    assert segundo == primeiro
    assert segundo.embeddings is not None


def test_indice_e_refeito_quando_uma_fonte_muda(fonte_temporaria, tmp_path):
    cache = tmp_path / "cache.json"

    antigo = construir_indice(False, ["a.md"], fonte_temporaria, cache)
    (fonte_temporaria / "a.md").write_text("# A\n\nTexto novo sobre criar.\n", encoding="utf-8")
    novo = construir_indice(False, ["a.md"], fonte_temporaria, cache)

    assert novo.assinatura != antigo.assinatura
    assert "novo" in novo.trechos[0].texto


def test_indice_sem_embeddings_tenta_de_novo_quando_o_ollama_volta(
    fonte_temporaria, tmp_path
):
    cache = tmp_path / "cache.json"

    sem = construir_indice(None, ["a.md"], fonte_temporaria, cache)
    assert sem.embeddings is None

    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        com = construir_indice(None, ["a.md"], fonte_temporaria, cache)

    assert com.embeddings is not None
    assert construir_indice(False, ["a.md"], fonte_temporaria, cache).embeddings is not None


def test_cache_corrompido_e_ignorado_e_refeito(fonte_temporaria, tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("{isto não é json", encoding="utf-8")

    indice = construir_indice(False, ["a.md"], fonte_temporaria, cache)

    assert isinstance(indice, Indice) and indice.trechos
    assert Indice.model_validate_json(cache.read_text(encoding="utf-8")) == indice


def test_fonte_inexistente_da_erro_claro(fonte_temporaria, tmp_path):
    with pytest.raises(FileNotFoundError, match="nao_existe.md"):
        construir_indice(False, ["nao_existe.md"], fonte_temporaria, tmp_path / "c.json")


# ----------------------------------------------- llm_client.gerar_embeddings


def _resposta(status=200, corpo=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = corpo
    if status >= 400:
        r.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status}")
    return r


def test_gerar_embeddings_envia_todos_os_textos_ao_endpoint_embed():
    resposta = _resposta(corpo={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    with patch.object(llm_client.requests, "post", return_value=resposta) as post:
        vetores = llm_client.gerar_embeddings(["um", "dois"])

    assert vetores == [[0.1, 0.2], [0.3, 0.4]]
    url = post.call_args.args[0]
    assert url == f"{config.OLLAMA_URL}/api/embed"
    assert post.call_args.kwargs["json"] == {
        "model": config.MODELO_EMBEDDING,
        "input": ["um", "dois"],
    }


@pytest.mark.parametrize(
    "entrada, erro",
    [("texto", TypeError), ([1, 2], TypeError), ([], ValueError), (["ok", "  "], ValueError)],
)
def test_gerar_embeddings_valida_a_entrada(entrada, erro):
    with pytest.raises(erro):
        llm_client.gerar_embeddings(entrada)


def test_gerar_embeddings_erro_de_conexao_vira_erro_llm():
    # O autouse _isolar já faz requests.post levantar ConnectionError.
    with pytest.raises(ErroLLM, match="conectar"):
        llm_client.gerar_embeddings(["oi"])


def test_gerar_embeddings_modelo_nao_instalado_orienta_o_pull():
    with patch.object(llm_client.requests, "post", return_value=_resposta(404, {})):
        with pytest.raises(ErroLLM, match="ollama pull"):
            llm_client.gerar_embeddings(["oi"])


def test_gerar_embeddings_resposta_incompleta_vira_erro_llm():
    resposta = _resposta(corpo={"embeddings": [[0.1]]})

    with patch.object(llm_client.requests, "post", return_value=resposta):
        with pytest.raises(ErroLLM, match="para cada texto"):
            llm_client.gerar_embeddings(["um", "dois"])
