"""Agente de consulta de crédito com LLM."""

from app.models.session import Session
from app.schemas.chat import ChatResponse
from app.schemas.credit import CreditLimit, CreditRequest
from app.services.credit_service import (
    get_credit_limit,
    request_credit_increase,
    request_credit_decrease,
)
from app.services.prompt_service import build_triage_prompt
from app.services.llm import llm_response
from app.utils import to_camel_dict


def _log_agent(message: str) -> None:
    """Imprime no console qual agente está atendendo."""
    print(f"[AGENTE CREDITO] {message}")


def _build_response(session_id: str, message: str, status: str, authenticated: bool, metadata: dict) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        message=message,
        status=status,
        authenticated=authenticated,
        metadata=metadata,
    )


def _format_currency(value: float) -> str:
    return f"R$ {value:,.2f}"


def _parse_br_number(text: str) -> float | None:
    """Converte um número em formato brasileiro para float.

    Suporta:
    - "2000" -> 2000.0
    - "2.000" -> 2000.0 (ponto como separador de milhar)
    - "2.000,50" -> 2000.5 (vírgula como decimal)
    - "2,5" -> 2.5 (vírgula como decimal)
    - "R$ 2.000" -> 2000.0
    - "15k" -> 15000.0 (sufixo k/k para milhar)
    - "15K" -> 15000.0
    """
    text = text.strip().replace("R$", "").strip()
    if not text:
        return None

    # Suporte a sufixo k/K (milhar): "15k" -> 15000, "2.5k" -> 2500
    if text.lower().endswith("k"):
        number_part = text[:-1].strip()
        value = _parse_br_number(number_part)
        if value is not None:
            return value * 1000
        return None

    # Se tem vírgula, é separador decimal
    if "," in text:
        # Remove pontos (separadores de milhar) e troca vírgula por ponto
        cleaned = text.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    # Sem vírgula: se tem ponto(s), pode ser separador de milhar
    if "." in text:
        parts = text.split(".")
        # Se o último grupo tem 1-2 dígitos, pode ser decimal (ex: "2.5")
        # Mas se tem 3 dígitos, é milhar (ex: "2.000")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # "2.5" -> 2.5 (decimal)
            try:
                return float(text)
            except ValueError:
                return None
        # "2.000" -> 2000.0 (milhar)
        cleaned = text.replace(".", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    # Número simples
    try:
        return float(text)
    except ValueError:
        return None


def _extract_requested_limit(message: str) -> float | None:
    """Extrai o valor numérico da mensagem (último número encontrado).
    
    Ignora números que parecem ser datas (dd/mm/aaaa, dd-mm-aaaa, etc.) ou CPFs.
    Suporta "15 mil" -> 15000, "2 mil" -> 2000, "15k" -> 15000, etc.
    """
    import re

    # Remove padrões que parecem CPF (XXX.XXX.XXX-XX ou XXXXXXXXXXX)
    cleaned = re.sub(r"\b\d{3}[\.\-]?\d{3}[\.\-]?\d{3}[-\.]?\d{2}\b", "", message)
    
    # Remove padrões que parecem datas (dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa, etc.)
    cleaned = re.sub(r"\b\d{2}[./\-]\d{2}[./\-]\d{4}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{4}[./\-]\d{2}[./\-]\d{2}\b", "", cleaned)
    
    # Busca padrões de valores monetários: R$ 2.000, 2.000, 2000, 2.000,50, 15k, 15 mil, etc.
    patterns = [
        r"R\$\s*([\d.,]+k?)",        # R$ 2.000 ou R$ 15k
        r"([\d]{1,3}(?:\.\d{3})+(?:,\d+)?k?)",  # 2.000 ou 2.000,50 ou 15k
        r"(\d+(?:,\d+)?k?)",         # 2000 ou 2,5 ou 15k
        r"(\d+(?:[.,]\d+)?)\s*mil\b",  # 15 mil, 2 mil, 2,5 mil
    ]

    for pattern in patterns:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        if matches:
            # Pega o último match
            value = _parse_br_number(matches[-1])
            if value is not None:
                # Se o padrão era "X mil", multiplica por 1000
                if re.search(r"\d+\s*mil\b", matches[-1], re.IGNORECASE):
                    return value * 1000
                return value

    return None


def _is_additional_increase(message: str) -> bool:
    """Verifica se a mensagem indica um aumento ADICIONAL (ex: 'quero mais 2.000').

    Retorna True se o usuário quer ADICIONAR um valor ao limite atual,
    em vez de definir um novo limite total.
    """
    import re
    text = message.lower()
    # Padrões que indicam adição: "mais X", "adicionar X", "aumentar em X", "acrescentar X"
    return bool(re.search(r"(mais|adicionar|acrescentar|aumentar em|aumentar mais)\s+", text))


def _ask_for_value(session: Session, credit_limit: CreditLimit, intent: str) -> ChatResponse:
    """Pergunta ao cliente qual novo limite deseja solicitar."""
    system_prompt = build_triage_prompt(
        client_name=session.client.name,
        masked_document=session.client.masked_document,
        target_agent="credit",
        auth_status=session.status,
        intent=intent,
    )
    system_prompt += (
        f"\n\nO cliente {session.client.name} JÁ ESTÁ AUTENTICADO. "
        "NÃO peça CPF ou data de nascimento novamente. "
        "Responda diretamente à solicitação do cliente usando os dados de contexto fornecidos. "
        "Não mencione redirecionamento ou agentes internos."
        "\n\n## Dados de contexto\n"
        f"- Limite total atual: R$ {credit_limit.total:,.2f}\n"
        f"- Limite disponível atual: R$ {credit_limit.available:,.2f}\n"
        f"- Limite utilizado: R$ {credit_limit.total - credit_limit.available:,.2f}\n"
        "Pergunte ao cliente qual novo limite deseja solicitar."
    )

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
    llm_text = llm_response(chat_messages, system_prompt)

    if llm_text:
        session.add_message("assistant", llm_text)
        return _build_response(
            session.id,
            llm_text,
            "authenticated",
            True,
            {"agent": "credit"},
        )

    msg = (
        f"Seu limite atual é de {_format_currency(credit_limit.total)}.\n\n"
        f"Qual novo limite você gostaria de solicitar? "
        f"Por favor, informe o valor desejado."
    )
    session.add_message("assistant", msg)
    return _build_response(
        session.id,
        msg,
        "authenticated",
        True,
        {"agent": "credit"},
    )


def _process_credit_change(
    session: Session,
    requested_limit: float,
    result: CreditRequest,
    intent: str,
) -> ChatResponse:
    """Processa o resultado de uma solicitação de alteração de limite e gera resposta."""
    # Consulta o banco para obter os dados mais recentes
    credit_limit = get_credit_limit(session.id)

    if result.status == "approved":
        # Aprovado - resposta normal
        system_prompt = build_triage_prompt(
            client_name=session.client.name,
            masked_document=session.client.masked_document,
            target_agent="credit",
            auth_status=session.status,
            intent=intent,
        )
        system_prompt += (
            "\n\n## Dados de contexto\n"
            f"- Limite solicitado: R$ {requested_limit:,.2f}\n"
            f"- Novo limite total (do banco): R$ {credit_limit.total:,.2f}\n"
            f"- Novo limite disponível (do banco): R$ {credit_limit.available:,.2f}\n"
            f"- Status: aprovado\n"
            "Informe o cliente que a solicitação foi aprovada e o novo limite já está disponível. "
            "Use os valores do banco para informar o novo limite."
        )
    else:
        # Rejeitado - verifica se é por score baixo
        if result.message and "score" in result.message.lower():
            # Pergunta se quer fazer entrevista para melhorar o score
            system_prompt = build_triage_prompt(
                client_name=session.client.name,
                masked_document=session.client.masked_document,
                target_agent="credit",
                auth_status=session.status,
                intent=intent,
            )
            system_prompt += (
                "\n\nO cliente JÁ ESTÁ AUTENTICADO. NÃO peça CPF ou data de nascimento novamente."
                "\n\n## Dados de contexto\n"
                f"- Limite solicitado: R$ {requested_limit:,.2f}\n"
                f"- Limite atual (do banco): R$ {credit_limit.total:,.2f}\n"
                f"- Status: não aprovado\n"
                f"- Motivo: {result.message}\n"
                "Explique que a solicitação foi negada devido ao score baixo. "
                "Pergunte se o cliente gostaria de fazer uma entrevista financeira para atualizar seu score "
                "e tentar aumentar o limite novamente. "
                "Se o cliente disser SIM/quiser, retorne EXATAMENTE: 'REDIRECT_INTERVIEW'. "
                "Se o cliente disser NÃO/não quiser, retorne EXATAMENTE: 'BACK_TO_TRIAGE'."
            )

            chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
            llm_text = llm_response(chat_messages, system_prompt)

            if llm_text and "REDIRECT_INTERVIEW" in llm_text:
                # Cliente quer fazer entrevista - redireciona
                from app.agents.credit_interview_agent import INTERVIEW_QUESTIONS, handle_interview
                session.active_agent = "credit_interview"
                session._interview_state = None  # Reinicia estado da entrevista
                
                first_q = INTERVIEW_QUESTIONS[0]
                msg = f"{result.message}\n\nPerfeito! Vamos iniciar a entrevista financeira para atualizar seu score.\n\n{first_q.label}"
                session.add_message("assistant", msg)
                return _build_response(
                    session.id,
                    msg,
                    "authenticated",
                    True,
                    {"agent": "credit_interview"},
                )
            elif llm_text and "BACK_TO_TRIAGE" in llm_text:
                # Cliente não quer entrevista - oferece outras opções antes de encerrar
                msg = (
                    "Tudo certo! Entendo sua decisão.\n\n"
                    "Posso ajudá-lo com outras opções:\n"
                    "- Diminuir seu limite atual\n"
                    "- Consultar outras informações\n"
                    "- Ver cotações de moedas\n\n"
                    "Ou se preferir, podemos encerrar o atendimento. Como posso ajudar?"
                )
                session.add_message("assistant", msg)
                return _build_response(
                    session.id,
                    msg,
                    "authenticated",
                    True,
                    {"agent": "triage"},
                )

            # Fallback: usa o resultado sem redirecionamento
            msg = (
                "😔 Infelizmente, sua solicitação de alteração de limite não foi aprovada neste momento.\n\n"
                f"📊 Limite solicitado: {_format_currency(requested_limit)}\n"
                f"📊 Limite atual: {_format_currency(credit_limit.total)}\n"
                "❌ Status: Não aprovado\n\n"
                f"{result.message}\n\n"
                "Se deseja, podemos tentar com outro valor ou verificar outras opções."
            )
            session.add_message("assistant", msg)
            widget = {
                "kind": "credit_request",
                "creditRequest": to_camel_dict(result),
            }
            return _build_response(
                session.id,
                msg,
                "authenticated",
                True,
                {"agent": "credit", "widget": widget},
            )
        else:
            # Outros motivos de rejeição
            system_prompt += (
                "\n\nO cliente JÁ ESTÁ AUTENTICADO. NÃO peça CPF ou data de nascimento novamente."
                "\n\n## Dados de contexto\n"
                f"- Limite solicitado: R$ {requested_limit:,.2f}\n"
                f"- Limite atual (do banco): R$ {credit_limit.total:,.2f}\n"
                f"- Status: não aprovado\n"
                f"- Motivo: {result.message or 'Não informado'}\n"
                "Informe o cliente de forma respeitosa que a solicitação não foi aprovada, "
                "explicando o motivo."
            )

    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]
    llm_text = llm_response(chat_messages, system_prompt)

    if llm_text:
        session.add_message("assistant", llm_text)
        widget = {
            "kind": "credit_request",
            "creditRequest": to_camel_dict(result),
        }
        return _build_response(
            session.id,
            llm_text,
            "authenticated",
            True,
            {"agent": "credit", "widget": widget},
        )

    # Fallback sem LLM
    if result.status == "approved":
        msg = (
            f"🎉 Sua solicitação de alteração de limite foi aprovada!\n\n"
            f"📊 Novo limite: {_format_currency(credit_limit.total)}\n"
            f"✅ Limite disponível: {_format_currency(credit_limit.available)}\n"
            "✅ Status: Aprovado\n\n"
            "O novo limite já está disponível para uso. Precisa de mais alguma coisa?"
        )
    else:
        msg = (
            "😔 Infelizmente, sua solicitação de alteração de limite não foi aprovada neste momento.\n\n"
            f"📊 Limite solicitado: {_format_currency(requested_limit)}\n"
            f"📊 Limite atual: {_format_currency(credit_limit.total)}\n"
            "❌ Status: Não aprovado\n\n"
            f"{result.message or ''}\n\n"
            "Se deseja, podemos tentar com outro valor ou verificar outras opções."
        )

    session.add_message("assistant", msg)
    widget = {
        "kind": "credit_request",
        "creditRequest": to_camel_dict(result),
    }
    return _build_response(
        session.id,
        msg,
        "authenticated",
        True,
        {"agent": "credit", "widget": widget},
    )


def handle_credit_limit(session: Session, message: str) -> ChatResponse:
    """Consulta limite de crédito usando LLM com contexto."""
    _log_agent(f"Atendendo consulta de limite — sessão: {session.id}")
    if session.client is None:
        return _build_response(
            session.id,
            "Preciso que você esteja autenticado para consultar seu limite de crédito.",
            "unauthenticated",
            False,
            {"agent": "credit"},
        )

    credit_limit = get_credit_limit(session.id)

    # Constrói prompt com contexto
    system_prompt = build_triage_prompt(
        client_name=session.client.name,
        masked_document=session.client.masked_document,
        target_agent="credit",
        auth_status=session.status,
        intent="credit_limit",
    )
    system_prompt += (
        "\n\n## Dados de contexto\n"
        f"- Limite total: R$ {credit_limit.total:,.2f}\n"
        f"- Limite disponível: R$ {credit_limit.available:,.2f}\n"
        f"- Limite utilizado: R$ {credit_limit.total - credit_limit.available:,.2f}\n"
        "Responda de forma clara e amigável mencionando os limites."
    )

    # Constrói histórico de mensagens para o LLM
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in session.history]

    # Tenta usar LLM
    llm_text = llm_response(chat_messages, system_prompt)

    if llm_text:
        session.add_message("assistant", llm_text)
        widget = {
            "kind": "credit_limit",
            "creditLimit": to_camel_dict(credit_limit),
        }
        return _build_response(
            session.id,
            llm_text,
            "authenticated",
            True,
            {"agent": "credit", "widget": widget},
        )

    # Fallback sem LLM
    msg = (
        f"Olá {session.client.name.split(' ')[0]}! Aqui estão seus limites de crédito:\n\n"
        f"💰 Limite Total: {_format_currency(credit_limit.total)}\n"
        f"✅ Limite Disponível: {_format_currency(credit_limit.available)}\n"
        f"📊 Limite Utilizado: {_format_currency(credit_limit.total - credit_limit.available)}\n\n"
        "Posso ajudar com mais alguma coisa? Se deseja solicitar um aumento de limite, é só me pedir!"
    )
    session.add_message("assistant", msg)
    widget = {
        "kind": "credit_limit",
        "creditLimit": to_camel_dict(credit_limit),
    }
    return _build_response(
        session.id,
        msg,
        "authenticated",
        True,
        {"agent": "credit", "widget": widget},
    )


def handle_credit_increase(session: Session, message: str) -> ChatResponse:
    """Solicitação de aumento de limite usando LLM com contexto."""
    _log_agent(f"Atendendo solicitação de AUMENTO de limite — sessão: {session.id}")
    if session.client is None:
        return _build_response(
            session.id,
            "Preciso que você esteja autenticado para solicitar aumento de limite.",
            "unauthenticated",
            False,
            {"agent": "credit"},
        )

    # Extrai valores numéricos da mensagem
    requested_limit = _extract_requested_limit(message)

    # Se não encontrou valor, pede ao usuário
    if requested_limit is None:
        credit_limit = get_credit_limit(session.id)
        return _ask_for_value(session, credit_limit, "credit_increase")

    # Verifica se é um aumento ADICIONAL (ex: "quero mais 2.000")
    # Nesse caso, o valor extraído é ADICIONADO ao limite atual
    if _is_additional_increase(message):
        credit_limit = get_credit_limit(session.id)
        requested_limit = credit_limit.total + requested_limit

    # Busca o score do cliente ANTES de processar o aumento
    from app.services.score_service import get_credit_data
    cpf = getattr(session, "client_cpf", None)
    credit_data = get_credit_data(cpf) if cpf else None
    current_score = credit_data["score"] if credit_data else 0
    
    # Verifica se score >= 650
    if current_score < 650:
        # Score baixo - informa e oferece entrevista
        msg = (
            f"Para solicitar um aumento para {_format_currency(requested_limit)}, "
            f"é necessário que seu score de crédito seja igual ou superior a 650.\n\n"
            f"Seu score atual é: {current_score}\n\n"
            "Gostaria de fazer uma entrevista financeira para atualizar seu score e tentar aumentar o limite?"
        )
        session.add_message("assistant", msg)
        return _build_response(
            session.id,
            msg,
            "authenticated",
            True,
            {"agent": "credit", "score": current_score},
        )

    # Processa a solicitação com o valor encontrado
    result = request_credit_increase(session.id, requested_limit)

    return _process_credit_change(session, requested_limit, result, "credit_increase")


def handle_credit_decrease(session: Session, message: str) -> ChatResponse:
    """Solicitação de diminuição de limite usando LLM com contexto."""
    _log_agent(f"Atendendo solicitação de DIMINUIÇÃO de limite — sessão: {session.id}")
    if session.client is None:
        return _build_response(
            session.id,
            "Preciso que você esteja autenticado para solicitar diminuição de limite.",
            "unauthenticated",
            False,
            {"agent": "credit"},
        )

    # Extrai valores numéricos da mensagem
    requested_limit = _extract_requested_limit(message)

    # Se não encontrou valor, pede ao usuário
    if requested_limit is None:
        credit_limit = get_credit_limit(session.id)
        return _ask_for_value(session, credit_limit, "credit_decrease")

    # Processa a solicitação com o valor encontrado
    result = request_credit_decrease(session.id, requested_limit)

    return _process_credit_change(session, requested_limit, result, "credit_decrease")


def handle_message(session: Session, message: str, intent: str) -> ChatResponse:
    """Roteador principal do agente de crédito."""
    _log_agent(f"ATENDENDO — intenção: {intent} | sessão: {session.id}")
    if intent == "credit_increase":
        return handle_credit_increase(session, message)
    if intent == "credit_decrease":
        return handle_credit_decrease(session, message)
    return handle_credit_limit(session, message)
