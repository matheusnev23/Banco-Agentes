"""Serviço de crédito."""

import uuid
from datetime import datetime

from app.models.session import session_store
from app.schemas.credit import CreditLimit, CreditRequest, CreditRequestType
from app.services.client_db import update_client_limits, get_clients
from app.services.credit_request_service import register_credit_request
from app.services.score_service import get_credit_data


def get_credit_limit(session_id: str) -> CreditLimit:
    """Retorna o limite de crédito do cliente autenticado na sessão.

    Sempre consulta o banco (CSV) para garantir dados atualizados,
    em vez de confiar apenas na sessão em memória.
    """
    session = session_store.get(session_id)
    if session is None or session.client is None:
        return CreditLimit(available=0, total=0)

    # Consulta o banco (CSV) para obter os dados mais recentes
    cpf = _get_client_cpf(session)
    if cpf:
        for client in get_clients():
            if client.cpf == cpf:
                # Atualiza a sessão em memória com os dados do banco
                session.client.limite_total = client.limite_total
                # limite_disponivel = limite_total - limite_usado
                session.client.limite_disponivel = client.limite_total - client.limite_usado
                return CreditLimit(
                    available=client.limite_total - client.limite_usado,
                    total=client.limite_total,
                )

    # Fallback: usa dados da sessão
    return CreditLimit(available=session.client.limite_disponivel, total=session.client.limite_total)


def _get_client_cpf(session) -> str | None:
    """Retorna o CPF do cliente da sessão (sem pontuação)."""
    cpf = getattr(session, "client_cpf", None)
    if cpf:
        return cpf
    # Fallback: tenta extrair do client
    client = getattr(session, "client", None)
    if client is not None:
        masked = getattr(client, "masked_document", "")
        # masked_document é mascarado, então não serve. Usa client_cpf se disponível.
        return None
    return None


def _check_score_rule(cpf: str, requested_limit: float, current_limit: float) -> tuple[bool, str | None]:
    """Verifica regras de negócio para aumento de limite.

    Regra: score menor que 800 não libera aumento.
    """
    credit_data = get_credit_data(cpf)
    if credit_data and credit_data["score"] < 800:
        return False, (
            f"Seu score de crédito é {credit_data['score']}, que é inferior ao mínimo de 800 "
            "necessário para aumento de limite. "
            "Gostaria de fazer uma entrevista financeira para atualizar seu score e tentar aumentar seu limite?"
        )
    return True, None


def request_credit_change(
    session_id: str,
    requested_limit: float,
    request_type: CreditRequestType = "increase",
) -> CreditRequest:
    """Solicita alteração de limite de crédito (aumento ou diminuição).

    Regras:
    - Aumento: pode aumentar indefinidamente (regra de score futura).
    - Diminuição: não pode diminuir o limite total abaixo do limite utilizado.
    """
    session = session_store.get(session_id)
    if session is None or session.client is None:
        return CreditRequest(
            id=f"req_{uuid.uuid4().hex[:8]}",
            requested_limit=requested_limit,
            status="rejected",
            request_type=request_type,
            message="Cliente não autenticado.",
            created_at=datetime.now().isoformat(),
        )

    # Consulta o banco (CSV) para obter os dados mais recentes
    cpf = _get_client_cpf(session)
    if cpf:
        for client in get_clients():
            if client.cpf == cpf:
                # Atualiza a sessão em memória com os dados do banco
                session.client.limite_total = client.limite_total
                # limite_disponivel = limite_total - limite_usado
                session.client.limite_disponivel = client.limite_total - client.limite_usado
                break

    current_total = session.client.limite_total
    current_available = session.client.limite_disponivel
    used_limit = current_total - current_available

    approved = False
    message = ""

    if request_type == "decrease":
        # Regra: não pode diminuir o limite total abaixo do limite utilizado
        if requested_limit < used_limit:
            approved = False
            message = (
                f"Não é possível diminuir o limite para R$ {requested_limit:,.2f} "
                f"pois o valor utilizado é de R$ {used_limit:,.2f}. "
                f"O novo limite deve ser de pelo menos R$ {used_limit:,.2f}."
            )
        elif requested_limit >= current_total:
            approved = False
            message = (
                f"O valor solicitado (R$ {requested_limit:,.2f}) é maior ou igual ao "
                f"limite atual (R$ {current_total:,.2f}). Para diminuir, informe um valor menor."
            )
        else:
            approved = True
            message = "Seu novo limite já está disponível para uso."
    else:  # increase
        # Regra de negócio futura: score < 800 não libera aumento
        score_ok, score_message = _check_score_rule(cpf or "", requested_limit, current_total)
        if not score_ok:
            approved = False
            message = score_message or "Não foi possível aprovar o aumento neste momento."
        else:
            approved = True
            message = "Seu novo limite já está disponível para uso."

    if approved:
        # Atualiza a sessão em memória
        session.client.limite_total = requested_limit
        # Recalcula limite_disponivel = limite_total - limite_usado
        if request_type == "decrease":
            # Para diminuição, mantém o mesmo limite_usado (dívida)
            session.client.limite_disponivel = requested_limit - used_limit
        else:
            # Para aumento, mantém o mesmo limite_usado (dívida) e recalcula disponível
            session.client.limite_disponivel = requested_limit - used_limit

        # Atualiza o CSV: salva limite_total e limite_usado
        if cpf:
            update_client_limits(cpf, requested_limit, used_limit)

    # Registra a solicitação no CSV
    if cpf:
        register_credit_request(
            cpf_cliente=cpf,
            limite_atual=current_total,
            novo_limite_solicitado=requested_limit,
            status_pedido="aprovado" if approved else "rejeitado",
        )

    return CreditRequest(
        id=f"req_{uuid.uuid4().hex[:8]}",
        requested_limit=requested_limit,
        status="approved" if approved else "rejected",
        request_type=request_type,
        message=message,
        new_total=requested_limit if approved else None,
        new_available=(requested_limit - used_limit) if approved else None,
        created_at=datetime.now().isoformat(),
    )


def request_credit_increase(session_id: str, requested_limit: float) -> CreditRequest:
    """Solicita aumento de limite de crédito (mantém compatibilidade)."""
    return request_credit_change(session_id, requested_limit, request_type="increase")


def request_credit_decrease(session_id: str, requested_limit: float) -> CreditRequest:
    """Solicita diminuição de limite de crédito."""
    return request_credit_change(session_id, requested_limit, request_type="decrease")