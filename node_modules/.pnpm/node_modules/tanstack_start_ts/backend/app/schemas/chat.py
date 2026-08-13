"""Schemas do chat - espelham os tipos TypeScript do frontend."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AgentState = Literal["triage", "credit", "credit_interview", "exchange"]

ServiceStatus = Literal[
    "unauthenticated",
    "authenticating",
    "authenticated",
    "processing",
    "completed",
    "error",
]


class ChatRequest(BaseModel):
    """Corpo de `POST /api/chat`."""

    session_id: str = Field(..., description="ID da sessão de conversa")
    message: str = Field(..., description="Mensagem do usuário")


class ChatResponse(BaseModel):
    """Resposta de `POST /api/chat`."""

    session_id: str
    message: str
    status: ServiceStatus
    authenticated: bool
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados: agent, widget, client, pendingIntent, etc.",
    )