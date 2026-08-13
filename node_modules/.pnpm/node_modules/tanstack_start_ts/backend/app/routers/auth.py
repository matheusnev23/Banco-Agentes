"""Rotas de autenticação do agente de triagem."""

from fastapi import APIRouter

from app.models.session import session_store
from app.schemas.auth import AuthenticationPayload, Client
from app.schemas.chat import ChatResponse
from app.services.agent import build_response
from app.services.client_db import ClientRecord, authenticate as authenticate_client
from app.utils import to_camel_dict

router = APIRouter()

AUTH_ERROR = {
    "title": "Não foi possível autenticar.",
    "description": "CPF ou data de nascimento não conferem. Verifique os dados e tente novamente.",
    "retryable": True,
}


def _format_masked_document(cpf: str) -> str:
    """Mascara o CPF no formato ***.***.789-**."""
    digits = cpf
    if len(digits) != 11:
        return f"***.***.{digits[-3:]}-**" if digits else "**"
    return f"***.***.{digits[6:9]}-**"


def _to_client(record: ClientRecord) -> Client:
    """Converte um registro do CSV no schema de cliente autenticado."""
    limite_disponivel = record.limite_total - record.limite_usado
    return Client(
        id=f"cli_{record.cpf[-4:]}",
        name=record.nome,
        masked_document=_format_masked_document(record.cpf),
        limite_total=record.limite_total,
        limite_disponivel=limite_disponivel,
        limite_usado=record.limite_usado,
    )


@router.post("/auth", response_model=ChatResponse)
async def authenticate(payload: AuthenticationPayload) -> ChatResponse:
    """Autentica o cliente (CPF + data de nascimento) e direciona para o agente apropriado."""
    session_id = payload.session_id or payload.document
    session = session_store.get_or_create(session_id)

    client = authenticate_client(payload.document, payload.birth_date)

    if client is None:
        # Incrementa tentativas e encerra após 3 falhas.
        session.auth_attempts += 1
        if session.auth_attempts >= 3:
            session.client = None
            session.status = "completed"
            return build_response(
                session.id,
                "Número máximo de tentativas excedido. Encerramos o atendimento por segurança. "
                "Se precisar, inicie uma nova conversa.",
                "completed",
                False,
                {"agent": "triage", "widget": {"kind": "closing"}},
            )

        # Bloqueia: limpa qualquer autenticação anterior e mantém a sessão desautenticada.
        session.client = None
        session.status = "unauthenticated"
        return build_response(
            session.id,
            f"Não encontrei um cadastro com esses dados. "
            f"Tentativa {session.auth_attempts} de 3. Tente novamente.",
            "unauthenticated",
            False,
            {
                "agent": "triage",
                "widget": {"kind": "error", "error": AUTH_ERROR},
            },
        )

    # Autenticado com sucesso: zera o contador de tentativas.
    session.auth_attempts = 0
    session.client = _to_client(client)
    session.status = "authenticated"

    first_name = client.nome.split(" ")[0]
    return build_response(
        session.id,
        f"Tudo certo, {first_name}. Como posso ajudar?",
        "authenticated",
        True,
        {
            "agent": "triage",
            "client": to_camel_dict(session.client),
            "pendingIntent": session.pending_intent,
        },
    )
