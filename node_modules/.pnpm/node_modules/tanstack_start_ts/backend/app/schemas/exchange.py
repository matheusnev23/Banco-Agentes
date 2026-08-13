"""Schemas de câmbio."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExchangeRate(BaseModel):
    """Cotação de uma moeda."""

    base: str
    quote: str
    rate: float
    variation: Optional[float] = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())