"""Schemas de autenticação do cliente."""

from typing import Optional

from pydantic import BaseModel, Field


class AuthenticationPayload(BaseModel):
    """Dados enviados pelo cliente para autenticação."""

    session_id: Optional[str] = Field(default=None, description="ID da sessão de conversa")
    document: str = Field(..., description="CPF do cliente")
    birth_date: str = Field(..., description="Data de nascimento (YYYY-MM-DD)")


class Client(BaseModel):
    """Cliente autenticado."""

    id: str
    name: str
    masked_document: str = Field(..., description="CPF mascarado - nunca armazenar completo")
    authenticated: bool = True
    limite_total: float = 0.0
    limite_disponivel: float = 0.0
    limite_usado: float = 0.0
