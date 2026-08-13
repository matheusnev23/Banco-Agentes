"""Serviço de registro de solicitações de alteração de limite em CSV."""

import csv
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "solicitacoes_aumento_limite.csv"

CSV_FIELDNAMES = [
    "cpf_cliente",
    "data_hora_solicitacao",
    "limite_atual",
    "novo_limite_solicitado",
    "status_pedido",
]


def _ensure_csv_exists() -> None:
    """Cria o arquivo CSV com cabeçalho se não existir."""
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()


def register_credit_request(
    *,
    cpf_cliente: str,
    limite_atual: float,
    novo_limite_solicitado: float,
    status_pedido: str = "pendente",
) -> bool:
    """Registra uma solicitação de alteração de limite no CSV.

    Args:
        cpf_cliente: CPF do cliente (apenas dígitos).
        limite_atual: Limite total atual do cliente.
        novo_limite_solicitado: Novo limite total solicitado.
        status_pedido: Status do pedido ('pendente', 'aprovado' ou 'rejeitado').

    Returns:
        True se o registro foi salvo com sucesso.
    """
    _ensure_csv_exists()

    row = {
        "cpf_cliente": cpf_cliente,
        "data_hora_solicitacao": datetime.now().isoformat(),
        "limite_atual": f"{limite_atual:.2f}",
        "novo_limite_solicitado": f"{novo_limite_solicitado:.2f}",
        "status_pedido": status_pedido,
    }

    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            writer.writerow(row)
        return True
    except OSError as exc:
        print(f"[CREDIT_REQUEST] Erro ao registrar solicitação: {exc}")
        return False