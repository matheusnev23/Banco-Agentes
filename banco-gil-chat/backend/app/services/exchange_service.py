"""Serviço de câmbio."""

from app.schemas.exchange import ExchangeRate

# Cotações mockadas.
# TODO: integrar com API de câmbio real (ex: AwesomeAPI, ExchangeRate-API)
MOCK_EXCHANGE_RATES: list[ExchangeRate] = [
    ExchangeRate(base="USD", quote="BRL", rate=5.42, variation=0.42),
    ExchangeRate(base="EUR", quote="BRL", rate=5.89, variation=-0.18),
    ExchangeRate(base="GBP", quote="BRL", rate=6.94, variation=0.11),
    ExchangeRate(base="ARS", quote="BRL", rate=0.0061, variation=-0.9),
]


def get_exchange_rate(base: str = "USD", quote: str = "BRL") -> ExchangeRate:
    """Retorna a cotação da moeda solicitada."""
    base = base.upper()
    quote = quote.upper()
    for rate in MOCK_EXCHANGE_RATES:
        if rate.base == base and rate.quote == quote:
            return rate
    # Fallback para USD/BRL se a moeda não for encontrada
    return MOCK_EXCHANGE_RATES[0]