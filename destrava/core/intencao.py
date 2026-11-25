"""Leitura determinística de mensagens curtas, sem LLM.

Respostas de sim/não, pedidos de projeto e consultas à agenda. O frontend tem
as mesmas regras em frontend/src/lib/intent.ts (mantenha as duas iguais).
"""

from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos."""
    letras = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


_SIM_FORTE = frozenset(
    "sim s ok okay pode confirmo confirma confirmado confirmar claro bora manda vai quero isso "
    "criar cria crie agendar agende encaixar encaixa encaixe beleza fechado".split()
)
_SIM_ACEITAS = _SIM_FORTE | frozenset(
    "podes agenda ser mesmo por favor ai la com certeza otimo perfeito o os evento eventos "
    "esse esses tudo".split()
)
_NAO = frozenset("nao n cancela cancelar cancele cancelado deixa negativo".split())
_NAO_ACEITAS = _NAO | frozenset(
    "pra para la melhor agora nada quero pode podes ok obrigado obrigada por favor isso tudo "
    "esse esses o os evento eventos criar cria crie agendar agende agenda encaixar encaixa "
    "encaixe vou mesmo entao".split()
)
_SIM_EXPLICITO = frozenset("sim confirmo confirma confirmado".split())


def classificar_confirmacao(texto: str) -> bool | None:
    """True = sim claro, False = não/cancelar, None = dúvida (perguntar de novo).

    Um "sim" só vale quando todas as palavras da resposta fazem parte de um sim.
    """
    palavras = re.findall(r"[a-z0-9]+", normalizar(texto))
    if not palavras or "?" in texto:
        return None
    if any(p in _NAO for p in palavras):
        if all(p in _NAO_ACEITAS for p in palavras):
            return False
        comeca_negando = palavras[0].startswith(("nao", "cancel"))
        return False if comeca_negando and not _SIM_EXPLICITO.intersection(palavras) else None
    todas_sim = all(p in _SIM_ACEITAS for p in palavras)
    return True if todas_sim and _SIM_FORTE.intersection(palavras) else None


_INTERVALO = re.compile(r"\b(?:das|de)\s+\d{1,2}(?:h|:)?\d{0,2}\s*(?:as|a|ate)\s+\d{1,2}")
_PEDIDO_PROJETO = re.compile(
    r"^\W*(?:(?:oi|ola|bom dia|boa tarde|boa noite)\W+)?"
    r"(?:(?:eu\s+)?(?:quero|queria|preciso|vou|gostaria|pretendo|planejo|me ajude|me ajuda|ajude-me)\s+"
    r"(?:(?:de|a)\s+)?)?"
    r"(?:(?:criar|crie|cria|desenvolver|desenvolva|construir|fazer|montar|programar|implementar|lancar"
    r"|entregar|planejar|planeje|dividir|organizar|agendar)\s+)?"
    r"(?:(?:um|uma|o|a|meu|minha|novo|nova|este|esse|pequeno|simples)\s+){0,3}"
    r"(?:projeto|app|aplicativo|sistema|site|plataforma|api|software|jogo|game|dashboard|chatbot|bot|mvp"
    # "programa uma reunião" é verbo, não um programa a construir.
    r"|tcc|monografia|programa(?!\s+(?:um|uma|o|a)\b)|startup)\b"
)
_CRIACAO_NO_INICIO = re.compile(
    r"^\W*(?:(?:por favor|pf)\W+)?(?:crie|criar|cria|agende|agendar|marque|marcar|marca|coloque|adicione)\b"
)
_CONSULTA = re.compile(
    r"\b(?:horarios? livres?|tempo livre|tenho tempo|tenho (?:algum )?horario|quais .{0,30}horarios?"
    r"|(?:ver|veja|mostre|mostrar|mostra|consultar|consulte) .{0,30}(?:agenda|horarios?|livres?)"
    r"|estou livre|tenho livre|de livre|minha agenda|disponibilidade)\b"
)


def pede_projeto(texto: str) -> bool:
    """O texto pede para planejar/construir um projeto (e não um evento avulso)."""
    t = normalizar(texto)
    # "O projeto atrasou, quais meus horários livres?" é uma pergunta sobre a agenda.
    pergunta_de_agenda = t.rstrip().endswith("?") and _CONSULTA.search(t)
    return bool(_PEDIDO_PROJETO.search(t)) and not _INTERVALO.search(t) and not pergunta_de_agenda


def consulta_agenda(texto: str) -> bool:
    """Pergunta sobre horários, mesmo que cite "marcar" ou "agendar" no meio."""
    t = normalizar(texto)
    return bool(_CONSULTA.search(t)) and not _CRIACAO_NO_INICIO.search(t)
