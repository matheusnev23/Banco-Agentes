"""Serviço de consulta de score e limite de crédito.

Lê os dados do arquivo `clientes.csv`, que é a fonte de verdade
atualizada pela entrevista de crédito.
"""

import csv
from pathlib import Path


CLIENTES_FILE = Path(__file__).resolve().parents[2] / "data" / "clientes.csv"


def get_credit_data(cpf: str) -> dict | None:
    """Busca score e limite do cliente pelo CPF.

    Lê do arquivo `clientes.csv` (fonte de verdade atualizada pela entrevista).
    """
    if not CLIENTES_FILE.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {CLIENTES_FILE}")

    with CLIENTES_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["cpf"].strip() == cpf:
                return {
                    "score": int(float(row.get("score", "0"))),
                    "limite_total": float(row.get("limite_total", "0")),
                }

    return None