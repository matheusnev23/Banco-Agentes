"""Rotas de crédito."""

from fastapi import APIRouter, HTTPException

from app.models.session import session_store
from app.schemas.credit import CreditIncreaseRequest, CreditLimit, CreditRequest
from app.services import credit_service

router = APIRouter()


@router.get("/credit/limit", response_model=CreditLimit)
async def get_credit_limit(session_id: str) -> CreditLimit:
    """Retorna o limite de crédito do cliente."""
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if session.client is None:
        raise HTTPException(status_code=401, detail="Cliente não autenticado")
    return credit_service.get_credit_limit(session_id)


@router.post("/credit/increase", response_model=CreditRequest)
async def request_credit_increase(payload: CreditIncreaseRequest) -> CreditRequest:
    """Solicita aumento de limite de crédito."""
    session = session_store.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if session.client is None:
        raise HTTPException(status_code=401, detail="Cliente não autenticado")
    return credit_service.request_credit_increase(payload.session_id, payload.requested_limit)