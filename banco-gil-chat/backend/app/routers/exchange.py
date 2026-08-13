"""Rotas de câmbio."""

from fastapi import APIRouter, Query

from app.schemas.exchange import ExchangeRate
from app.services import exchange_service

router = APIRouter()


@router.get("/exchange/rate", response_model=ExchangeRate)
async def get_exchange_rate(
    base: str = Query(default="USD", description="Moeda base (ex: USD, EUR, GBP)"),
    quote: str = Query(default="BRL", description="Moeda de cotação (ex: BRL)"),
) -> ExchangeRate:
    """Retorna a cotação da moeda solicitada."""
    return exchange_service.get_exchange_rate(base, quote)