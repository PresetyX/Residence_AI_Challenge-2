"""Testes do RAG (sem Ollama e sem internet).

As bases de conhecimento oficiais são mantidas por outra pessoa do grupo e podem
mudar, então os testes usam uma base fictícia, criada numa pasta temporária.

O Ollama é simulado: toda requisição HTTP é bloqueada (como se o Ollama
estivesse desligado), e os testes que precisam de vetores usam um modelo de
embeddings falso. O Chroma e o SQLite da Indexing API são reais, gravados na
pasta temporária de cada teste. Rodam em qualquer máquina:

    python -m pytest tests/test_rag.py

Os dados do NLTK (stopwords e RSLP) precisam estar baixados; ver
destrava/rag/texto.py.
"""

from unittest.mock import patch

import httpx
import ollama
import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

import destrava.rag.rag as modulo_rag
from destrava.core import config, llm_client
from destrava.core.llm_client import EmbeddingsOllama, ErroLLM
from destrava.prompts.rag import RESPOSTA_SEM_CONTEXTO
from destrava.rag import Rag, RespostaRag, TrechoEncontrado, obter_rag
from destrava.rag import indice as modulo_indice
from destrava.rag import recuperador
from destrava.rag.banco_vetorial import BancoVetorial
from destrava.rag.chunker import dividir_texto
from destrava.rag.indice import construir_indice, ler_fontes, listar_arquivos
from destrava.rag.texto import tokenizar


# ---------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _isolar(tmp_path, monkeypatch):
    """Nenhum teste escreve na raiz do projeto nem chega ao Ollama de verdade."""
    monkeypatch.setattr(config, "PASTA_INDICES_RAG", tmp_path / ".indices")
    obter_rag.cache_clear()

    # O cliente do Ollama (usado pelo langchain-ollama) faz as requisições com
    # httpx. Bloqueando o envio, toda chamada se comporta como "Ollama fora".
    def _sem_rede(*args, **kwargs):
        raise httpx.ConnectError("rede bloqueada nos testes")

    monkeypatch.setattr(httpx.Client, "send", _sem_rede)


DOC_AGENDA = """# Agenda

## Criar evento

Para marcar um dentista ou uma reunião, crie o evento com título, início e fim.

## Horários livres

O agente visualizar devolve os horários livres de um período.
"""

DOC_FERIADOS = """Feriados nacionais não bloqueiam a agenda.

Aniversários também aparecem como eventos de dia inteiro."""


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Base fictícia com duas bases configuradas (supervisor com conteúdo, planejador vazia)."""
    (tmp_path / "base" / "sub").mkdir(parents=True)
    (tmp_path / "base" / "agenda.md").write_text(DOC_AGENDA, encoding="utf-8")
    (tmp_path / "base" / "sub" / "feriados.txt").write_text(DOC_FERIADOS, encoding="utf-8")
    (tmp_path / "vazia").mkdir()

    monkeypatch.setattr(config, "RAIZ_PROJETO", tmp_path)
    monkeypatch.setattr(
        config, "RAG_BASES", {"supervisor": ("base",), "planejador": ("vazia",)}
    )
    return tmp_path


def _vetor_falso(texto: str) -> list[float]:
    """Eixo 0 = criar/marcar; eixo 1 = horários livres; eixo 2 = o resto."""
    t = texto.lower()
    v = [
        1.0 if any(p in t for p in ("criar", "marcar", "xablau")) else 0.0,
        1.0 if any(p in t for p in ("livre", "visualizar")) else 0.0,
        0.0,
    ]
    return v if any(v) else [0.0, 0.0, 1.0]


class EmbeddingsFalso(Embeddings):
    """Modelo de embeddings falso: vetores previsíveis e registro das chamadas.

    Attributes:
        lotes: Os textos de cada chamada a embed_documents (um item por lote).
        consultas: Os textos recebidos por embed_query.
        fora: Se True, simula o Ollama desligado.
        falhar_no_lote: Se for um número n, a n-ésima chamada a embed_documents
            falha (simula o Ollama caindo no meio da indexação).
    """

    def __init__(self, vetor=_vetor_falso):
        self.vetor = vetor
        self.lotes: list[list[str]] = []
        self.consultas: list[str] = []
        self.fora = False
        self.falhar_no_lote: int | None = None

    def embed_documents(self, texts):
        if self.fora or len(self.lotes) + 1 == self.falhar_no_lote:
            raise ConnectionError("Ollama fora")
        self.lotes.append(list(texts))
        return [self.vetor(t) for t in texts]

    def embed_query(self, text):
        if self.fora:
            raise ConnectionError("Ollama fora")
        self.consultas.append(text)
        return self.vetor(text)

    @property
    def total_indexado(self) -> int:
        return sum(len(lote) for lote in self.lotes)


def _usar(falso: EmbeddingsFalso):
    """Faz o RAG usar o modelo falso (com os prefixos e a tradução de erros reais)."""
    return patch.object(modulo_indice, "criar_embeddings", lambda: EmbeddingsOllama(base=falso))


# ------------------------------------------------------------------ texto


def test_tokenizar_tira_acento_maiuscula_e_stopwords():
    tokens = tokenizar("Quero as REUNIÕES de amanhã")

    assert not {"quero", "as", "de"} & set(tokens)
    assert all(t == t.lower() and t.isascii() for t in tokens)


def test_tokenizar_aproxima_variacoes_da_mesma_palavra():
    assert tokenizar("agendar") == tokenizar("agenda") == tokenizar("agendamento")
    # "criação" gera dois radicais (com e sem acento); um deles é o de "criar".
    assert set(tokenizar("criar")) <= set(tokenizar("criação"))


def test_tokenizar_palavra_sem_acento_encontra_a_com_acento():
    assert set(tokenizar("reuniao")) & set(tokenizar("reunião"))
    assert set(tokenizar("amanha")) & set(tokenizar("amanhã"))


def test_tokenizar_mantem_numeros_e_tira_stopwords_do_projeto():
    assert "15h" in tokenizar("às 15h")
    assert tokenizar("quero preciso você vc") == []


# ------------------------------------------------ chunking: por seção


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
    trechos = dividir_texto(MD, "doc.md")

    assert [t.secao for t in trechos] == [
        "Doc",
        "Doc > Seção A",
        "Doc > Seção A > Sub A1",
        "Doc > Seção B",
    ]
    assert all(t.fonte == "doc.md" for t in trechos)


def test_chunker_mantem_o_codigo_na_secao_dele():
    secao_b = dividir_texto(MD, "doc.md")[-1]

    assert secao_b.texto == '```json\n{"a": 1}\n\n{"b": 2}\n```\n\nDepois do código.'


def test_chunker_nao_corta_bloco_de_codigo_nem_trata_titulo_dentro_dele():
    md = "# T\n\n```\n# isto não é título\n\nlinha após branco\n```\n"
    trechos = dividir_texto(md, "x.md", tamanho_max=100, sobreposicao=10)

    assert len(trechos) == 1
    assert "# isto não é título" in trechos[0].texto
    assert "linha após branco" in trechos[0].texto


def test_chunker_preserva_indentacao():
    trechos = dividir_texto("# T\n\n- item\n  - subitem\n", "x.md")

    assert trechos[0].texto == "- item\n  - subitem"


def test_chunker_ignora_secao_sem_texto():
    assert dividir_texto("# Só título\n\n## Outro\n", "x.md") == []


def test_chunker_texto_sem_titulos_usa_o_nome_do_arquivo_como_secao():
    trechos = dividir_texto("Um parágrafo.\n\nOutro parágrafo.", "notas.txt")

    assert len(trechos) == 1
    assert trechos[0].secao == "notas.txt"


# ------------------------------- chunking: seções e blocos grandes


def test_chunker_divide_secao_grande_por_paragrafo_sem_perder_texto():
    paragrafos = [f"parágrafo {i} " + "x" * 50 for i in range(6)]
    md = "# T\n\n" + "\n\n".join(paragrafos)

    trechos = dividir_texto(md, "x.md", tamanho_max=130, sobreposicao=0)

    assert len(trechos) > 1
    assert all(t.secao == "T" for t in trechos)
    assert all(len(t.texto) <= 130 for t in trechos)
    assert "\n\n".join(t.texto for t in trechos) == "\n\n".join(paragrafos)


def _paragrafo_longo(n: int = 120) -> str:
    return " ".join(f"Frase número {i} do parágrafo longo." for i in range(n))


def test_chunker_paragrafo_maior_que_o_limite_e_dividido_em_frases():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=60)

    assert len(trechos) > 5
    assert all(len(t.texto) <= 300 for t in trechos)
    # Cada parte começa e termina em fronteira de frase (nunca no meio dela).
    assert all(t.texto.startswith("Frase") and t.texto.endswith("longo.") for t in trechos)


def test_chunker_sobreposicao_repete_o_fim_de_cada_parte_na_seguinte():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=60)

    for anterior, seguinte in zip(trechos, trechos[1:]):
        ultima_frase = anterior.texto.rsplit(". ", 1)[-1]
        assert seguinte.texto.startswith(ultima_frase), (anterior.texto[-60:], seguinte.texto[:60])


def test_chunker_sem_sobreposicao_as_partes_nao_se_repetem():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=0)

    assert " ".join(t.texto for t in trechos) == _paragrafo_longo()


def test_chunker_todas_as_frases_aparecem_em_algum_trecho():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=60)
    texto_todo = "\n".join(t.texto for t in trechos)

    assert all(f"Frase número {i} do" in texto_todo for i in range(120))


def test_chunker_palavra_gigante_e_cortada_no_limite():
    trechos = dividir_texto("# T\n\n" + "a" * 1000, "x.md", tamanho_max=300, sobreposicao=0)

    assert [len(t.texto) for t in trechos] == [300, 300, 300, 100]


def test_chunker_tabela_grande_e_dividida_por_linha_mantendo_as_linhas_inteiras():
    linhas = [f"| linha {i} | valor {i} |" for i in range(40)]
    trechos = dividir_texto("# T\n\n" + "\n".join(linhas), "x.md", tamanho_max=200, sobreposicao=0)

    assert len(trechos) > 1
    assert all(len(t.texto) <= 200 for t in trechos)
    assert "\n".join(t.texto for t in trechos).split("\n") == linhas


@pytest.mark.parametrize("tamanho, sobreposicao", [(0, 0), (-5, 0), (100, 100), (100, 150), (100, -1)])
def test_chunker_rejeita_parametros_invalidos(tamanho, sobreposicao):
    with pytest.raises(ValueError):
        dividir_texto("# T\n\ntexto", "x.md", tamanho_max=tamanho, sobreposicao=sobreposicao)


# ---------------------------------------------------------- banco vetorial


def _banco(tmp_path, vetores: dict[str, list[float]]) -> BancoVetorial:
    """Banco com um documento por texto; o vetor de cada texto vem do dicionário."""
    embeddings = EmbeddingsOllama(
        base=EmbeddingsFalso(vetor=lambda t: vetores[t]), prefixo_documento="", prefixo_consulta=""
    )
    banco = BancoVetorial(tmp_path / "banco", embeddings)
    if vetores:
        textos = [t for t in vetores if not t.startswith("?")]
        banco.vector_store.add_documents([Document(page_content=t) for t in textos])
    return banco


def test_banco_ordena_por_cosseno_e_respeita_minimo_e_k(tmp_path):
    banco = _banco(tmp_path, {"t0": [1, 0], "t1": [1, 1], "t2": [0, 1], "?q": [1, 0]})

    todos = banco.buscar("?q", k=10)
    assert [d.page_content for d, _ in todos] == ["t0", "t1", "t2"]
    assert [round(s, 3) for _, s in todos] == [1.0, 0.707, 0.0]

    assert [d.page_content for d, _ in banco.buscar("?q", k=10, minimo=0.5)] == ["t0", "t1"]
    assert [d.page_content for d, _ in banco.buscar("?q", k=1)] == ["t0"]


def test_banco_cosseno_nao_depende_do_comprimento_do_vetor(tmp_path):
    banco = _banco(tmp_path, {"longe": [10, 0], "perto": [0, 0.001], "?q": [0.5, 0]})

    doc, similaridade = banco.buscar("?q", k=2)[0]

    assert doc.page_content == "longe" and similaridade == pytest.approx(1.0)


def test_banco_vazio_nao_quebra_a_busca(tmp_path):
    banco = _banco(tmp_path, {})

    assert banco.total() == 0 and banco.buscar("qualquer", k=3) == []


# ------------------------------------------ indexação: fontes (arquivos)


def test_listar_arquivos_entra_em_pastas_filtra_extensao_e_ignora_ocultos(tmp_path):
    (tmp_path / "base" / "sub").mkdir(parents=True)
    (tmp_path / "base" / ".oculta").mkdir()
    for nome in ("a.md", "b.txt", "c.pdf", "sub/d.MD", ".oculto.md", ".oculta/e.md"):
        (tmp_path / "base" / nome).write_text("x", encoding="utf-8")
    (tmp_path / "solto.md").write_text("x", encoding="utf-8")

    achados = listar_arquivos(("base", "solto.md"), tmp_path)

    assert achados == ["base/a.md", "base/b.txt", "base/sub/d.MD", "solto.md"]


def test_listar_arquivos_pasta_vazia_e_valida(tmp_path):
    (tmp_path / "vazia").mkdir()
    (tmp_path / "vazia" / ".gitkeep").write_text("", encoding="utf-8")

    assert listar_arquivos(("vazia",), tmp_path) == []


def test_listar_arquivos_fonte_inexistente_da_erro_claro(tmp_path):
    with pytest.raises(FileNotFoundError, match="nao_existe"):
        listar_arquivos(("nao_existe",), tmp_path)


def test_ler_fontes_aceita_bom_do_windows(tmp_path):
    (tmp_path / "a.md").write_bytes("﻿# Título\n\ntexto".encode("utf-8"))

    assert ler_fontes(("a.md",), tmp_path) == {"a.md": "# Título\n\ntexto"}


def test_ler_fontes_arquivo_fora_de_utf8_diz_qual_e(tmp_path):
    (tmp_path / "ruim.md").write_bytes("ação".encode("latin-1"))

    with pytest.raises(ValueError, match="ruim.md"):
        ler_fontes(("ruim.md",), tmp_path)


# ------------------------- indexação: Indexing API (lotes, reuso, limpeza)


def test_embeddings_sao_gerados_em_lotes(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_LOTE_EMBEDDING", 2)
    falso = EmbeddingsFalso()

    with _usar(falso):
        indice = construir_indice("supervisor")

    assert len(indice.trechos) > 2
    assert all(len(lote) <= 2 for lote in falso.lotes)
    assert falso.total_indexado == len(indice.trechos) == indice.banco.total()


def test_prefixo_de_documento_e_aplicado_na_indexacao_e_o_de_consulta_na_busca(base):
    falso = EmbeddingsFalso()

    with _usar(falso):
        Rag("supervisor").buscar("marcar dentista")

    indexados = [t for lote in falso.lotes for t in lote]
    assert indexados and all(t.startswith(config.RAG_PREFIXO_DOCUMENTO) for t in indexados)
    assert falso.consultas == [config.RAG_PREFIXO_CONSULTA + "marcar dentista"]


def test_texto_indexado_inclui_o_caminho_de_titulos(base):
    falso = EmbeddingsFalso()

    with _usar(falso):
        construir_indice("supervisor")

    indexados = [t for lote in falso.lotes for t in lote]
    assert config.RAG_PREFIXO_DOCUMENTO + "Agenda > Criar evento\nPara marcar" in "\n".join(
        indexados
    )


def test_base_sem_mudanca_nao_gera_embeddings_de_novo(base):
    falso = EmbeddingsFalso()

    with _usar(falso):
        primeiro = construir_indice("supervisor")
        chamadas = len(falso.lotes)
        segundo = construir_indice("supervisor")

    assert len(falso.lotes) == chamadas
    assert primeiro.estatisticas["num_added"] == len(primeiro.trechos)
    assert segundo.estatisticas == {
        "num_added": 0,
        "num_updated": 0,
        "num_skipped": len(segundo.trechos),
        "num_deleted": 0,
    }


def test_editar_um_arquivo_so_reprocessa_os_trechos_dele(base):
    falso = EmbeddingsFalso()
    with _usar(falso):
        construir_indice("supervisor")
        (base / "base" / "sub" / "feriados.txt").write_text("Texto novo dos feriados.", encoding="utf-8")
        falso.lotes.clear()
        novo = construir_indice("supervisor")

    # Só o trecho do arquivo editado foi para o modelo de embeddings.
    assert falso.total_indexado == 1
    assert "Texto novo dos feriados." in falso.lotes[0][0]
    assert novo.estatisticas["num_added"] == 1 and novo.estatisticas["num_deleted"] == 1
    assert novo.banco.total() == len(novo.trechos)


def test_arquivo_novo_e_arquivo_apagado_sao_refletidos_no_banco(base):
    falso = EmbeddingsFalso()
    with _usar(falso):
        antigo = construir_indice("supervisor")
        (base / "base" / "sub" / "feriados.txt").unlink()
        (base / "base" / "novo.md").write_text("# Novo\n\nOutro arquivo.\n", encoding="utf-8")
        novo = construir_indice("supervisor")

    fontes = {t.fonte for t in novo.trechos}
    assert "base/novo.md" in fontes and "base/sub/feriados.txt" not in fontes
    assert novo.estatisticas["num_deleted"] == sum(
        t.fonte == "base/sub/feriados.txt" for t in antigo.trechos
    )
    assert novo.banco.total() == len(novo.trechos)


def test_trocar_o_modelo_de_embeddings_cria_banco_novo_e_apaga_o_antigo(base, monkeypatch):
    falso = EmbeddingsFalso()
    with _usar(falso):
        construir_indice("supervisor")
        pastas_antes = list((config.PASTA_INDICES_RAG / "supervisor").iterdir())
        monkeypatch.setattr(config, "MODELO_EMBEDDING", "outro-modelo")
        novo = construir_indice("supervisor")
    pastas_depois = list((config.PASTA_INDICES_RAG / "supervisor").iterdir())

    assert len(pastas_antes) == len(pastas_depois) == 1
    assert pastas_antes != pastas_depois
    assert novo.estatisticas["num_added"] == len(novo.trechos)


def test_mudar_o_tamanho_do_trecho_refaz_o_chunking(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_SOBREPOSICAO", 10)
    falso = EmbeddingsFalso()
    with _usar(falso):
        antigo = construir_indice("supervisor")
        monkeypatch.setattr(config, "RAG_TAMANHO_MAX_TRECHO", 50)
        novo = construir_indice("supervisor")

    assert len(novo.trechos) > len(antigo.trechos)
    assert all(len(t.texto) <= 50 for t in novo.trechos)
    assert novo.banco.total() == len(novo.trechos)


def test_config_com_sobreposicao_maior_que_o_trecho_da_erro_claro(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_TAMANHO_MAX_TRECHO", 50)  # sobreposição padrão é 150

    with pytest.raises(ValueError, match="RAG_SOBREPOSICAO"):
        construir_indice("supervisor", usar_embeddings=False)


def test_ollama_fora_na_indexacao_segue_sem_banco_e_tenta_de_novo_depois(base):
    # Sem _usar(...): o modelo de embeddings real, com a rede bloqueada.
    sem = construir_indice("supervisor")
    assert sem.banco is None and sem.trechos

    falso = EmbeddingsFalso()
    with _usar(falso):
        com = construir_indice("supervisor")
    assert com.banco is not None and com.banco.total() == len(com.trechos)


def test_ollama_cai_no_meio_da_indexacao_e_a_proxima_continua_de_onde_parou(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_LOTE_EMBEDDING", 1)
    falso = EmbeddingsFalso()
    falso.falhar_no_lote = 2   # o 1º trecho entra; o 2º derruba a indexação

    with _usar(falso):
        parcial = construir_indice("supervisor")
        falso.falhar_no_lote = None
        completo = construir_indice("supervisor")

    assert parcial.banco is None
    assert completo.estatisticas["num_skipped"] == 1
    assert completo.estatisticas["num_added"] == len(completo.trechos) - 1


def test_embeddings_obrigatorios_propagam_o_erro(base):
    with pytest.raises(ErroLLM, match="conectar"):
        construir_indice("supervisor", usar_embeddings=True)


def test_base_vazia_gera_indice_vazio_sem_chamar_o_ollama(base):
    falso = EmbeddingsFalso()

    with _usar(falso):
        indice = construir_indice("planejador", usar_embeddings=True)

    assert falso.lotes == []
    assert indice.trechos == [] and indice.banco is None


def test_base_desconhecida_lista_as_configuradas(base):
    with pytest.raises(ValueError, match="supervisor, planejador"):
        construir_indice("inexistente")


def test_fonte_inexistente_da_erro_claro(base, monkeypatch):
    monkeypatch.setitem(config.RAG_BASES, "supervisor", ("pasta_que_nao_existe",))

    with pytest.raises(FileNotFoundError, match="pasta_que_nao_existe"):
        construir_indice("supervisor", usar_embeddings=False)


# ------------------------------------------ busca por palavras-chave


@pytest.fixture
def rag(base):
    return Rag("supervisor", usar_embeddings=False)


def test_rag_indexa_arquivos_md_e_txt_de_subpastas(rag):
    fontes = {t.fonte for t in rag.buscar("agenda", k=10)}

    assert not rag.usa_embeddings and not rag.vazia
    assert fontes == {"base/agenda.md", "base/sub/feriados.txt"}


@pytest.mark.parametrize(
    "pergunta, secao_esperada",
    [
        ("Quero marcar um dentista", "Agenda > Criar evento"),
        ("Quais horários livres tenho?", "Agenda > Horários livres"),
        ("Feriado bloqueia a agenda?", "feriados.txt"),
    ],
)
def test_busca_lexica_acha_o_trecho_certo_em_primeiro(rag, pergunta, secao_esperada):
    assert rag.buscar(pergunta, k=1)[0].secao.endswith(secao_esperada)


def test_busca_traz_fonte_nota_e_metodo_ordenados(rag):
    resultado = rag.buscar("agenda eventos", k=3)

    assert resultado and all(isinstance(t, TrechoEncontrado) for t in resultado)
    assert all(t.metodo == "lexico" and t.score > 0 for t in resultado)
    assert [t.score for t in resultado] == sorted((t.score for t in resultado), reverse=True)


def test_busca_respeita_k(rag):
    assert len(rag.buscar("agenda", k=1)) == 1


def test_busca_sem_palavra_em_comum_devolve_vazio(rag):
    assert rag.buscar("xyzzy plugh") == []
    assert rag.contexto("xyzzy plugh") == ""


def test_busca_so_com_stopwords_devolve_vazio(rag):
    assert rag.buscar("quero de a o") == []


@pytest.mark.parametrize("pergunta", ["", "   ", "\n"])
def test_busca_rejeita_pergunta_vazia(rag, pergunta):
    with pytest.raises(ValueError):
        rag.buscar(pergunta)


def test_busca_rejeita_tipos_invalidos(rag):
    with pytest.raises(TypeError):
        rag.buscar(123)
    for k in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            rag.buscar("agenda", k=k)


def test_base_vazia_devolve_nada_e_nao_quebra(base):
    rag = Rag("planejador", usar_embeddings=False)

    assert rag.vazia and rag.total_trechos == 0
    assert rag.buscar("qualquer coisa") == []
    assert rag.contexto("qualquer coisa") == ""


# ----------------------------------------------- busca com embeddings


def test_busca_hibrida_acha_por_significado_sem_palavra_em_comum(base):
    with _usar(EmbeddingsFalso()):
        rag = Rag("supervisor")
        resultado = rag.buscar("xablau", k=3)

    assert rag.usa_embeddings
    assert [t.secao for t in resultado] == ["Agenda > Criar evento"]
    assert resultado[0].metodo == "hibrido"


def test_busca_hibrida_soma_as_duas_listas(base):
    with _usar(EmbeddingsFalso()):
        rag = Rag("supervisor")
        resultado = rag.buscar("marcar dentista", k=3)

    # Primeiro em palavras-chave e em significado: soma 1/61 + 1/61.
    assert resultado[0].secao == "Agenda > Criar evento"
    assert resultado[0].score == pytest.approx(2 / (recuperador.RRF_K + 1))


def test_ollama_fora_do_ar_na_indexacao_cai_para_palavras_chave(base):
    rag = Rag("supervisor")  # rede bloqueada; usar_embeddings=None: tenta e segue sem

    assert not rag.usa_embeddings
    assert rag.buscar("marcar dentista")[0].metodo == "lexico"


def test_rag_com_embeddings_obrigatorios_propaga_o_erro(base):
    with pytest.raises(ErroLLM):
        Rag("supervisor", usar_embeddings=True)


def test_ollama_cai_depois_de_indexar_so_aquela_busca_usa_palavras_chave(base):
    falso = EmbeddingsFalso()
    with _usar(falso):
        rag = Rag("supervisor")
    assert rag.usa_embeddings

    falso.fora = True
    resultado = rag.buscar("marcar dentista")

    assert resultado and all(t.metodo == "lexico" for t in resultado)


def test_ollama_cai_depois_de_indexar_com_embeddings_obrigatorios_propaga(base):
    falso = EmbeddingsFalso()
    with _usar(falso):
        rag = Rag("supervisor", usar_embeddings=True)

    falso.fora = True
    with pytest.raises(ErroLLM):
        rag.buscar("marcar dentista")


def test_usar_embeddings_false_nunca_chama_o_ollama(base):
    falso = EmbeddingsFalso()
    with _usar(falso):
        Rag("supervisor", usar_embeddings=False).buscar("marcar dentista")

    assert falso.lotes == [] and falso.consultas == []
    assert not config.PASTA_INDICES_RAG.exists()


# ---------------------------------- contexto, prompt e geração da resposta


def test_contexto_numera_trechos_e_cita_a_fonte(rag):
    contexto = rag.contexto("agenda", k=2)

    assert contexto.startswith("[1] Fonte: base/")
    assert "\n\n[2] Fonte: base/" in contexto


def test_montar_prompt_padrao_injeta_contexto_e_pergunta(rag):
    prompt = rag.montar_prompt("Quero marcar um dentista", k=1)

    assert "Para marcar um dentista" in prompt
    assert prompt.rstrip().endswith("Quero marcar um dentista")
    assert "{contexto}" not in prompt and "{pergunta_do_usuario}" not in prompt


def test_montar_prompt_aceita_template_do_agente_com_campos_extras(rag):
    template = "Projeto: {entrada}\nRegras:\n{contexto}\nPedido: {pergunta_do_usuario} {{ok}}"

    prompt = rag.montar_prompt("marcar dentista", template=template, k=1, entrada='{"p": 1}')

    assert prompt.startswith('Projeto: {"p": 1}\nRegras:\n[1] Fonte:')
    assert prompt.endswith("Pedido: marcar dentista {ok}")


def test_montar_prompt_sem_contexto_avisa_em_vez_de_deixar_a_lacuna_vazia(rag):
    prompt = rag.montar_prompt("xyzzy plugh")

    assert "(nenhum trecho relevante encontrado)" in prompt


def test_contexto_com_chaves_nao_quebra_o_prompt(base):
    (base / "base" / "json.md").write_text(
        '# JSON\n\nExemplo de entrada: {"titulo": "x"} para marcar dentista.\n', encoding="utf-8"
    )
    rag = Rag("supervisor", usar_embeddings=False)

    assert '{"titulo": "x"}' in rag.montar_prompt("exemplo json dentista", k=1)


def _chat_falso(resposta: str = "Crie o evento.", erro: Exception | None = None):
    """Substitui o ChatOllama na cadeia LCEL e guarda os prompts recebidos.

    Um RunnableLambda entra na cadeia com ``|`` como qualquer modelo: recebe o
    prompt já montado (ChatPromptValue) e devolve uma AIMessage.
    """
    prompts: list[str] = []

    def gerar(valor_do_prompt):
        # Na cadeia do rag.py chega um ChatPromptValue; no perguntar(), o texto puro.
        if not isinstance(valor_do_prompt, str):
            valor_do_prompt = valor_do_prompt.to_string()
        prompts.append(valor_do_prompt)
        if erro is not None:
            raise erro
        return AIMessage(content=resposta)

    return RunnableLambda(gerar), prompts


def test_responder_busca_monta_o_prompt_e_chama_o_llm(rag):
    chat, prompts = _chat_falso("  Crie o evento.  ")
    with patch.object(modulo_rag, "criar_chat", return_value=chat):
        resposta = rag.responder("Quero marcar um dentista", k=1)

    assert len(prompts) == 1
    assert "Para marcar um dentista" in prompts[0] and "Quero marcar um dentista" in prompts[0]
    assert isinstance(resposta, RespostaRag)
    assert resposta.resposta == "Crie o evento." and resposta.usou_llm
    assert [t.secao for t in resposta.trechos] == ["Agenda > Criar evento"]


def test_responder_sem_contexto_nao_chama_o_llm(rag):
    chat, prompts = _chat_falso()
    with patch.object(modulo_rag, "criar_chat", return_value=chat):
        resposta = rag.responder("xyzzy plugh")

    assert prompts == []
    assert resposta.resposta == RESPOSTA_SEM_CONTEXTO
    assert resposta.trechos == [] and not resposta.usou_llm


def test_responder_com_ollama_fora_levanta_erro_llm(rag):
    # Sem patch: o ChatOllama real, com a rede bloqueada.
    with pytest.raises(ErroLLM, match="conectar"):
        rag.responder("Quero marcar um dentista")


def test_responder_modelo_nao_instalado_orienta_o_pull(rag):
    chat, _ = _chat_falso(erro=ollama.ResponseError("model not found", 404))
    with patch.object(modulo_rag, "criar_chat", return_value=chat):
        with pytest.raises(ErroLLM, match="ollama pull"):
            rag.responder("Quero marcar um dentista")


def test_responder_resposta_vazia_vira_erro_llm(rag):
    chat, _ = _chat_falso("   ")
    with patch.object(modulo_rag, "criar_chat", return_value=chat):
        with pytest.raises(ErroLLM, match="vazia"):
            rag.responder("Quero marcar um dentista")


# ---------------------------------------------- obter_rag e bases do projeto


def test_obter_rag_reaproveita_o_mesmo_objeto(base):
    assert obter_rag("supervisor") is obter_rag("supervisor")
    assert obter_rag("supervisor") is not obter_rag("planejador")


def test_obter_rag_base_desconhecida(base):
    with pytest.raises(ValueError, match="inexistente"):
        obter_rag("inexistente")


def test_bases_oficiais_do_projeto_existem_e_constroem(monkeypatch):
    """Supervisor e Planejador têm pasta própria; vazia ou preenchida, o RAG sobe."""
    assert set(config.RAG_BASES) == {"supervisor", "planejador"}

    for nome in config.RAG_BASES:
        rag = Rag(nome, usar_embeddings=False)
        assert rag.total_trechos >= 0
        assert rag.buscar("pergunta qualquer") is not None


# ------------------------------------------------ llm_client: embeddings


def test_embeddings_ollama_aplica_os_prefixos():
    falso = EmbeddingsFalso()
    embeddings = EmbeddingsOllama(base=falso, prefixo_documento="doc: ", prefixo_consulta="q: ")

    embeddings.embed_documents(["um", "dois"])
    embeddings.embed_query("pergunta")

    assert falso.lotes == [["doc: um", "doc: dois"]]
    assert falso.consultas == ["q: pergunta"]


def test_criar_embeddings_usa_o_modelo_e_o_endereco_do_config():
    embeddings = llm_client.criar_embeddings()

    assert embeddings.base.model == config.MODELO_EMBEDDING
    assert embeddings.base.base_url == config.OLLAMA_URL


@pytest.mark.parametrize(
    "entrada, erro",
    [("texto", TypeError), ([1, 2], TypeError), ([], ValueError), (["ok", "  "], ValueError)],
)
def test_embeddings_valida_a_entrada(entrada, erro):
    with pytest.raises(erro):
        EmbeddingsOllama(base=EmbeddingsFalso()).embed_documents(entrada)


def test_embeddings_erro_de_conexao_vira_erro_llm():
    # O autouse _isolar bloqueia a rede: o OllamaEmbeddings real não conecta.
    with pytest.raises(ErroLLM, match="conectar"):
        llm_client.criar_embeddings().embed_documents(["oi"])


def test_embeddings_modelo_nao_instalado_orienta_o_pull():
    falso = EmbeddingsFalso()
    falso.embed_documents = lambda textos: (_ for _ in ()).throw(
        ollama.ResponseError("model 'x' not found", 404)
    )

    with pytest.raises(ErroLLM, match="ollama pull"):
        EmbeddingsOllama(base=falso).embed_documents(["oi"])


def test_embeddings_tempo_esgotado_vira_erro_llm():
    falso = EmbeddingsFalso()
    falso.embed_query = lambda texto: (_ for _ in ()).throw(httpx.ReadTimeout("lento"))

    with pytest.raises(ErroLLM, match="tempo limite"):
        EmbeddingsOllama(base=falso).embed_query("oi")


def test_embeddings_resposta_incompleta_vira_erro_llm():
    falso = EmbeddingsFalso()
    falso.embed_documents = lambda textos: [[0.1]]

    with pytest.raises(ErroLLM, match="para cada texto"):
        EmbeddingsOllama(base=falso).embed_documents(["um", "dois"])


# ---------------------------------------------------- llm_client: chat


def test_perguntar_devolve_o_texto_do_modelo():
    chat, prompts = _chat_falso("  Olá!  ")
    with patch.object(llm_client, "criar_chat", return_value=chat):
        assert llm_client.perguntar("Diga olá") == "Olá!"

    assert prompts == ["Diga olá"]


def test_perguntar_valida_o_prompt():
    with pytest.raises(TypeError):
        llm_client.perguntar(123)
    with pytest.raises(ValueError):
        llm_client.perguntar("  ")


def test_perguntar_com_ollama_fora_levanta_erro_llm():
    with pytest.raises(ErroLLM, match="conectar"):
        llm_client.perguntar("oi")


def test_criar_chat_usa_o_modelo_do_config_e_valida_a_configuracao(monkeypatch):
    chat = llm_client.criar_chat()
    assert chat.model == config.MODELO and chat.base_url == config.OLLAMA_URL

    monkeypatch.setattr(config, "MODELO", "  ")
    with pytest.raises(ErroLLM, match="MODELO"):
        llm_client.criar_chat()
    monkeypatch.setattr(config, "MODELO", "gemma2:2b")
    monkeypatch.setattr(config, "TIMEOUT_LLM", 0)
    with pytest.raises(ErroLLM, match="TIMEOUT_LLM"):
        llm_client.criar_chat()
