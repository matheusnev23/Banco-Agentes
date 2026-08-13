"""Utilitários compartilhados do backend Banco Ágil."""

from typing import Any


def to_camel(snake: str) -> str:
    """Converte um nome no formato snake_case para camelCase.

    Exemplo: ``updated_at`` -> ``updatedAt``
    """
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_camel_dict(model: Any) -> dict:
    """Converte um modelo Pydantic (ou qualquer objeto) para dict com chaves em camelCase.

    A API Python usa snake_case (ex: ``updated_at``, ``masked_document``)
    mas o frontend TypeScript espera camelCase (ex: ``updatedAt``,
    ``maskedDocument``). Esta função realiza a conversão para que os
    widgets e metadados sejam compatíveis com os tipos do frontend.
    """
    if hasattr(model, "model_dump"):
        raw: dict = model.model_dump()  # type: ignore[union-attr]
    else:
        raw = dict(model)
    return {to_camel(key): value for key, value in raw.items()}
