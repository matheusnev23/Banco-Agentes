"""Schemas de crédito."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CreditLimit(BaseModel):
    """Limite de crédito do cliente."""

    available: float
    total: float
    currency: str = "BRL"
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


CreditRequestStatus = Literal["pending", "approved", "rejected"]
CreditRequestType = Literal["increase", "decrease"]


class CreditRequest(BaseModel):
    """Solicitação de alteração de limite (aumento ou diminuição)."""

    id: str
    requested_limit: float
    currency: str = "BRL"
    status: CreditRequestStatus
    request_type: CreditRequestType = "increase"
    message: Optional[str] = None
    # Novo limite após aprovação (presentes apenas quando aprovado)
    new_total: Optional[float] = None
    new_available: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreditIncreaseRequest(BaseModel):
    """Corpo de `POST /api/credit/increase`."""

    session_id: str
    requested_limit: float = Field(..., gt=0, description="Novo limite solicitado")


class CreditDecreaseRequest(BaseModel):
    """Corpo de `POST /api/credit/decrease`."""

    session_id: str
    requested_limit: float = Field(..., gt=0, description="Novo limite solicitado")