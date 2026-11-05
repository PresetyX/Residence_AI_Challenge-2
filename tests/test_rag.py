"""Testes do RAG (sem Ollama e sem internet).

As bases de conhecimento oficiais são mantidas por outra pessoa do grupo e podem
estar vazias, então os testes usam uma base fictícia, criada numa pasta
temporária. O Ollama é simulado: nenhum teste faz chamada de rede. Rodam em
qualquer máquina:

    python -m pytest tests/test_rag.py
"""

import math
from unittest.mock import MagicMock, patch

import pytest
import requests

import destrava.rag.rag as modulo_rag
from destrava.core import config, llm_client
from destrava.core.llm_client import ErroLLM
from destrava.rag import Rag, RespostaRag, TrechoEncontrado, obter_rag
from destrava.rag import indice as modulo_indice
from destrava.rag import recuperador
from destrava.rag.banco_vetorial import BancoVetorialLocal
from destrava.rag.chunker import Trecho, dividir_texto
from destrava.rag.indice import (
    Indice,
    construir_indice,
    ler_fontes,
    listar_arquivos,
)
from destrava.rag.texto import tokenizar
from destrava.prompts.rag import RESPOSTA_SEM_CONTEXTO


# ---------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _isolar(tmp_path, monkeypatch):
    """Nenhum teste escreve na raiz do projeto nem chega ao Ollama de verdade."""
    monkeypatch.setattr(config, "PASTA_INDICES_RAG", tmp_path / ".indices")
    obter_rag.cache_clear()

    def _sem_rede(*args, **kwargs):
        raise requests.exceptions.ConnectionError("rede bloqueada nos testes")

    monkeypatch.setattr(llm_client.requests, "post", _sem_rede)


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


def _embedder_falso(textos: list[str]) -> list[list[float]]:
    return [_vetor_falso(t) for t in textos]


def _com_embeddings_falsos():
    return (
        patch.object(modulo_indice, "gerar_embeddings", _embedder_falso),
        patch.object(recuperador, "gerar_embeddings", _embedder_falso),
    )


# ------------------------------------------------------------------ texto


def test_tokenizar_tira_acento_stopword_e_plural():
    assert tokenizar("Quero as REUNIÕES de amanhã") == ["reunio", "amanha"]


def test_tokenizar_aproxima_variacoes_da_mesma_palavra():
    assert tokenizar("agendar") == tokenizar("agenda") == tokenizar("agendamento")


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


def test_chunker_nao_corta_bloco_de_codigo_nem_trata_titulo_dentro_dele():
    md = "# T\n\n```\n# isto não é título\n\nlinha após branco\n```\n"
    trechos = dividir_texto(md, "x.md", tamanho_max=100, sobreposicao=10)

    assert len(trechos) == 1
    assert "# isto não é título" in trechos[0].texto
    assert "linha após branco" in trechos[0].texto


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
    # Cada parte termina e começa em fim/início de frase (nunca no meio dela).
    assert all(t.texto.startswith("Frase") and t.texto.endswith("longo.") for t in trechos)


def test_chunker_sobreposicao_repete_o_fim_de_cada_parte_na_seguinte():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=60)

    for anterior, seguinte in zip(trechos, trechos[1:]):
        ultima_frase = anterior.texto.rsplit(". ", 1)[-1]
        assert seguinte.texto.startswith(ultima_frase), (anterior.texto[-60:], seguinte.texto[:60])


def test_chunker_sem_sobreposicao_as_partes_nao_se_repetem():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=0)

    juntas = " ".join(t.texto for t in trechos)
    assert juntas == _paragrafo_longo()


def test_chunker_todas_as_frases_aparecem_em_algum_trecho():
    trechos = dividir_texto("# T\n\n" + _paragrafo_longo(), "x.md", tamanho_max=300, sobreposicao=60)
    texto_todo = "\n".join(t.texto for t in trechos)

    assert all(f"Frase número {i} do" in texto_todo for i in range(120))


def test_chunker_palavra_gigante_e_cortada_no_limite():
    trechos = dividir_texto("# T\n\n" + "a" * 1000, "x.md", tamanho_max=300, sobreposicao=50)

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


def _trechos(n: int) -> list[Trecho]:
    return [Trecho(fonte="f.md", secao=f"S{i}", texto=f"t{i}") for i in range(n)]


def test_banco_ordena_por_cosseno_e_respeita_minimo_e_n():
    banco = BancoVetorialLocal(_trechos(3), [[1, 0], [1, 1], [0, 1]])

    todos = banco.buscar([1, 0])
    assert [i for i, _ in todos] == [0, 1, 2]
    assert [round(s, 3) for _, s in todos] == [1.0, 0.707, 0.0]

    assert [i for i, _ in banco.buscar([1, 0], minimo=0.5)] == [0, 1]
    assert [i for i, _ in banco.buscar([1, 0], n=1)] == [0]


def test_banco_cosseno_nao_depende_do_comprimento_do_vetor():
    banco = BancoVetorialLocal(_trechos(2), [[10, 0], [0, 0.001]])

    pares = banco.buscar([0.5, 0])

    assert pares[0] == (0, pytest.approx(1.0))


def test_banco_vazio_nao_quebra_a_busca():
    assert BancoVetorialLocal([], []).buscar([1, 2, 3]) == []


def test_banco_rejeita_dimensao_diferente_na_consulta():
    banco = BancoVetorialLocal(_trechos(1), [[1, 0]])

    with pytest.raises(ValueError, match="dimensões"):
        banco.buscar([1, 0, 0])


def test_banco_rejeita_vetores_inconsistentes():
    with pytest.raises(ValueError):
        BancoVetorialLocal(_trechos(2), [[1, 0]])
    with pytest.raises(ValueError):
        BancoVetorialLocal(_trechos(2), [[1, 0], [1, 0, 0]])


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


# ------------------------------------- indexação: embeddings, lotes, cache


def test_embeddings_sao_gerados_em_lotes(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_LOTE_EMBEDDING", 2)
    gerador = MagicMock(side_effect=_embedder_falso)

    with patch.object(modulo_indice, "gerar_embeddings", gerador):
        indice = construir_indice("supervisor")

    tamanhos = [len(c.args[0]) for c in gerador.call_args_list]
    assert len(indice.trechos) > 2
    assert all(t <= 2 for t in tamanhos)
    assert sum(tamanhos) == len(indice.trechos) == len(indice.embeddings)


def test_prefixo_de_documento_e_aplicado_na_indexacao_e_o_de_consulta_na_busca(base):
    textos_indexados, textos_consulta = [], []

    def indexar(textos):
        textos_indexados.extend(textos)
        return _embedder_falso(textos)

    def consultar(textos):
        textos_consulta.extend(textos)
        return _embedder_falso(textos)

    with patch.object(modulo_indice, "gerar_embeddings", indexar), patch.object(
        recuperador, "gerar_embeddings", consultar
    ):
        Rag("supervisor").buscar("marcar dentista")

    assert all(t.startswith(config.RAG_PREFIXO_DOCUMENTO) for t in textos_indexados)
    assert textos_consulta == [config.RAG_PREFIXO_CONSULTA + "marcar dentista"]


def test_indice_e_reaproveitado_do_disco_se_a_base_nao_mudou(base):
    gerador = MagicMock(side_effect=_embedder_falso)

    with patch.object(modulo_indice, "gerar_embeddings", gerador):
        primeiro = construir_indice("supervisor")
        segundo = construir_indice("supervisor")

    assert gerador.call_count == 1
    assert segundo == primeiro and segundo.embeddings is not None
    assert (config.PASTA_INDICES_RAG / "supervisor.json").is_file()


def test_cada_base_tem_o_seu_arquivo_de_indice(base):
    construir_indice("supervisor", usar_embeddings=False)
    construir_indice("planejador", usar_embeddings=False)

    assert sorted(p.name for p in config.PASTA_INDICES_RAG.iterdir()) == [
        "planejador.json",
        "supervisor.json",
    ]


def test_indice_e_refeito_quando_um_arquivo_muda_ou_e_adicionado(base):
    antigo = construir_indice("supervisor", usar_embeddings=False)

    (base / "base" / "agenda.md").write_text("# Agenda\n\nTexto novo.\n", encoding="utf-8")
    editado = construir_indice("supervisor", usar_embeddings=False)
    (base / "base" / "novo.md").write_text("# Novo\n\nOutro arquivo.\n", encoding="utf-8")
    ampliado = construir_indice("supervisor", usar_embeddings=False)

    assert len({antigo.assinatura, editado.assinatura, ampliado.assinatura}) == 3
    assert any("Texto novo" in t.texto for t in editado.trechos)
    assert any(t.fonte == "base/novo.md" for t in ampliado.trechos)


def test_indice_e_refeito_quando_um_arquivo_e_apagado(base):
    antigo = construir_indice("supervisor", usar_embeddings=False)
    (base / "base" / "sub" / "feriados.txt").unlink()

    novo = construir_indice("supervisor", usar_embeddings=False)

    assert len(novo.trechos) < len(antigo.trechos)
    assert all("feriados" not in t.fonte for t in novo.trechos)


def test_indice_e_refeito_quando_o_tamanho_do_trecho_muda(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_SOBREPOSICAO", 10)
    antigo = construir_indice("supervisor", usar_embeddings=False)
    monkeypatch.setattr(config, "RAG_TAMANHO_MAX_TRECHO", 50)

    novo = construir_indice("supervisor", usar_embeddings=False)

    assert novo.assinatura != antigo.assinatura
    assert len(novo.trechos) > len(antigo.trechos)


def test_config_com_sobreposicao_maior_que_o_trecho_da_erro_claro(base, monkeypatch):
    monkeypatch.setattr(config, "RAG_TAMANHO_MAX_TRECHO", 50)  # sobreposição padrão é 150

    with pytest.raises(ValueError, match="sobreposicao"):
        construir_indice("supervisor", usar_embeddings=False)


def test_indice_sem_embeddings_tenta_de_novo_quando_o_ollama_volta(base):
    sem = construir_indice("supervisor")
    assert sem.embeddings is None

    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        com = construir_indice("supervisor")

    assert com.embeddings is not None
    # E fica salvo: a próxima vez nem precisa do Ollama.
    assert construir_indice("supervisor", usar_embeddings=False).embeddings is not None


def test_cache_corrompido_e_ignorado_e_refeito(base):
    config.PASTA_INDICES_RAG.mkdir(parents=True)
    (config.PASTA_INDICES_RAG / "supervisor.json").write_text("{isto não é json", encoding="utf-8")

    indice = construir_indice("supervisor", usar_embeddings=False)

    assert isinstance(indice, Indice) and indice.trechos
    salvo = (config.PASTA_INDICES_RAG / "supervisor.json").read_text(encoding="utf-8")
    assert Indice.model_validate_json(salvo) == indice


def test_base_vazia_gera_indice_vazio_sem_chamar_o_ollama(base):
    gerador = MagicMock()

    with patch.object(modulo_indice, "gerar_embeddings", gerador):
        indice = construir_indice("planejador", usar_embeddings=True)

    gerador.assert_not_called()
    assert indice.trechos == [] and indice.embeddings is None


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
    p1, p2 = _com_embeddings_falsos()
    with p1, p2:
        rag = Rag("supervisor")
        resultado = rag.buscar("xablau", k=3)

    assert rag.usa_embeddings
    assert [t.secao for t in resultado] == ["Agenda > Criar evento"]
    assert resultado[0].metodo == "hibrido"


def test_busca_hibrida_soma_as_duas_listas(base):
    p1, p2 = _com_embeddings_falsos()
    with p1, p2:
        rag = Rag("supervisor")
        resultado = rag.buscar("marcar dentista", k=3)

    # Primeiro em palavras-chave e em significado: soma 1/61 + 1/61.
    assert resultado[0].secao == "Agenda > Criar evento"
    assert resultado[0].score == pytest.approx(2 / (recuperador.RRF_K + 1))


def test_ollama_fora_do_ar_na_indexacao_cai_para_palavras_chave(base):
    with patch.object(modulo_indice, "gerar_embeddings", side_effect=ErroLLM("fora")):
        rag = Rag("supervisor")  # usar_embeddings=None: tenta e segue sem

    assert not rag.usa_embeddings
    assert rag.buscar("marcar dentista")[0].metodo == "lexico"


def test_embeddings_obrigatorios_propagam_o_erro(base):
    with patch.object(modulo_indice, "gerar_embeddings", side_effect=ErroLLM("fora")):
        with pytest.raises(ErroLLM):
            Rag("supervisor", usar_embeddings=True)


def test_ollama_cai_depois_de_indexar_so_aquela_busca_usa_palavras_chave(base):
    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        rag = Rag("supervisor")
    assert rag.usa_embeddings

    with patch.object(recuperador, "gerar_embeddings", side_effect=ErroLLM("caiu")):
        resultado = rag.buscar("marcar dentista")

    assert resultado and all(t.metodo == "lexico" for t in resultado)


def test_modelo_de_embedding_com_outra_dimensao_nao_quebra_a_busca(base):
    with patch.object(modulo_indice, "gerar_embeddings", _embedder_falso):
        rag = Rag("supervisor")

    with patch.object(recuperador, "gerar_embeddings", lambda t: [[1.0, 0.0, 0.0, 0.0]]):
        resultado = rag.buscar("marcar dentista")

    assert resultado and all(t.metodo == "lexico" for t in resultado)


def test_usar_embeddings_false_nunca_chama_o_ollama(base):
    chamadas = MagicMock()
    with patch.object(modulo_indice, "gerar_embeddings", chamadas), patch.object(
        recuperador, "gerar_embeddings", chamadas
    ):
        Rag("supervisor", usar_embeddings=False).buscar("marcar dentista")

    chamadas.assert_not_called()


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


def test_responder_busca_monta_o_prompt_e_chama_o_llm(rag):
    with patch.object(modulo_rag, "perguntar", return_value="Crie o evento.") as perguntar:
        resposta = rag.responder("Quero marcar um dentista", k=1)

    prompt = perguntar.call_args.args[0]
    assert "Para marcar um dentista" in prompt and "Quero marcar um dentista" in prompt
    assert isinstance(resposta, RespostaRag)
    assert resposta.resposta == "Crie o evento." and resposta.usou_llm
    assert [t.secao for t in resposta.trechos] == ["Agenda > Criar evento"]


def test_responder_sem_contexto_nao_chama_o_llm(rag):
    with patch.object(modulo_rag, "perguntar") as perguntar:
        resposta = rag.responder("xyzzy plugh")

    perguntar.assert_not_called()
    assert resposta.resposta == RESPOSTA_SEM_CONTEXTO
    assert resposta.trechos == [] and not resposta.usou_llm


def test_responder_propaga_erro_do_llm(rag):
    with patch.object(modulo_rag, "perguntar", side_effect=ErroLLM("fora")):
        with pytest.raises(ErroLLM):
            rag.responder("Quero marcar um dentista")


# ---------------------------------------------- obter_rag e bases do projeto


def test_obter_rag_reaproveita_o_mesmo_objeto(base):
    assert obter_rag("supervisor") is obter_rag("supervisor")
    assert obter_rag("supervisor") is not obter_rag("planejador")


def test_obter_rag_base_desconhecida(base):
    with pytest.raises(ValueError, match="inexistente"):
        obter_rag("inexistente")


def test_bases_oficiais_do_projeto_existem_e_constroem_mesmo_vazias(monkeypatch):
    """Supervisor e Planejador têm pasta própria; vazia ou preenchida, o RAG sobe."""
    assert set(config.RAG_BASES) == {"supervisor", "planejador"}

    for nome in config.RAG_BASES:
        rag = Rag(nome, usar_embeddings=False)
        assert rag.total_trechos >= 0
        assert rag.buscar("pergunta qualquer") is not None


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
    assert post.call_args.args[0] == f"{config.OLLAMA_URL}/api/embed"
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
