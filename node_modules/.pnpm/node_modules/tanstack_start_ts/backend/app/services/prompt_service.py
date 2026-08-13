"""Serviço de pré-prompt para o agente de AI.

Lê o arquivo de pré-prompt (`backend/prompts/triage_prompt.txt`) e monta
mensagens dinâmicas substituindo as variáveis `{{variavel}}` pelos dados
do contexto (cliente, agente de destino, status, etc).
"""

import re
from pathlib import Path
from typing import Optional

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "triage_prompt.txt"

_cache: Optional[str] = None


def get_prompt_template() -> str:
    """Retorna o template do pré-prompt (com cache)."""
    global _cache
    if _cache is None:
        if PROMPT_PATH.exists():
            _cache = PROMPT_PATH.read_text(encoding="utf-8")
        else:
            _cache = ""
    return _cache


def render_prompt(variables: dict[str, str]) -> str:
    """Substitui as variáveis `{{nome}}` no template pelos valores fornecidos.

    Variáveis ausentes são substituídas por string vazia.
    """
    template = get_prompt_template()

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        return variables.get(key, "")

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, template)


def build_triage_prompt(
    *,
    client_name: str = "",
    masked_document: str = "",
    target_agent: str = "triage",
    auth_status: str = "unauthenticated",
    intent: str = "",
) -> str:
    """Monta o pré-prompt do agente de triagem com as variáveis preenchidas."""
    return render_prompt(
        {
            "client_name": client_name,
            "masked_document": masked_document,
            "target_agent": target_agent,
            "auth_status": auth_status,
            "intent": intent,
        }
    )