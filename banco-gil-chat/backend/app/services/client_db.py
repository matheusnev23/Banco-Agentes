"""Base de dados de clientes em CSV.

O agente de triagem usa este módulo para:
1. Autenticar o cliente com CPF + data de nascimento.
2. Obter o limite de crédito do cliente.

O CSV fica em `backend/data/clientes.csv`.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "clientes.csv"


@dataclass
class ClientRecord:
    """Registro de um cliente no CSV."""

    nome: str
    cpf: str
    data_nascimento: str
    limite_total: float
    limite_usado: float


def _normalize_cpf(cpf: str) -> str:
    """Remove pontuação do CPF, mantendo apenas dígitos."""
    return re.sub(r"\D", "", cpf or "")


def _normalize_birth_date(value: str) -> str:
    """Normaliza a data de nascimento para o formato YYYY-MM-DD.

    Aceita:
      - 1988-03-15 (formato do CSV / ISO)
      - 15/03/1988 (formato dd/mm/aaaa enviado pelo formulário)
      - 19880315 (formato YYYYMMDD sem separadores)
      - 23122003 (formato DDMMYYYY sem separadores)
    """
    value = (value or "").strip()
    # Try DD/MM/YYYY format (with slashes) first
    dd_mm_yyyy = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value)
    if dd_mm_yyyy:
        day, month, year = dd_mm_yyyy.groups()
        return f"{year}-{month}-{day}"
    # Try YYYYMMDD or DDMMYYYY format (without separators, 8 digits)
    if re.match(r"^\d{8}$", value):
        # Try DDMMYYYY (day/month/year) - first 2 digits = day, next 2 = month, last 4 = year
        if value[2:4].isdigit() and value[4:6].isdigit():
            day = value[:2]
            month = value[2:4]
            year = value[4:8]
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                return f"{year}-{month}-{day}"
        # Try YYYYMMDD (year/month/day) - first 4 digits = year, next 2 = month, last 2 = day
        if value[:4].isdigit() and int(value[:4]) > 1900 and int(value[:4]) < 2030:
            year = value[:4]
            month = value[4:6]
            day = value[6:8]
            if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                return f"{year}-{month}-{day}"
    # Try ISO format YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    return value


def _to_float(value: str, default: float = 0.0) -> float:
    """Converte string para float, tratando formatos brasileiro e americano.

    Suporta:
    - "5000.0" -> 5000.0 (formato americano, ponto decimal)
    - "12000" -> 12000.0 (número inteiro)
    - "2.000,50" -> 2000.5 (formato brasileiro, vírgula decimal)
    - "2.000" -> 2000.0 (formato brasileiro, ponto milhar)
    """
    value = (value or "").strip()
    if not value:
        return default

    # Se tem vírgula, é formato brasileiro (vírgula decimal, ponto milhar)
    if "," in value:
        cleaned = value.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return default

    # Se tem ponto, pode ser decimal (formato americano) ou milhar (formato brasileiro)
    if "." in value:
        parts = value.split(".")
        # Se o último grupo tem 1-2 dígitos, é decimal (ex: "22000.0", "2.5")
        if len(parts) == 2 and len(parts[1]) <= 2:
            try:
                return float(value)
            except ValueError:
                return default
        # Se tem 3 dígitos no último grupo, é milhar (ex: "2.000")
        cleaned = value.replace(".", "")
        try:
            return float(cleaned)
        except ValueError:
            return default

    # Número simples
    try:
        return float(value)
    except ValueError:
        return default


def _load_clients() -> list[ClientRecord]:
    """Lê todos os clientes do arquivo CSV."""
    if not CSV_PATH.exists():
        return []

    clients: list[ClientRecord] = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clients.append(
                ClientRecord(
                    nome=row.get("nome", "").strip(),
                    cpf=_normalize_cpf(row.get("cpf", "")),
                    data_nascimento=_normalize_birth_date(row.get("data_nascimento", "")),
                    limite_total=_to_float(row.get("limite_total", "")),
                    limite_usado=_to_float(row.get("limite_usado", "")),
                )
            )

    return clients


_cache: Optional[list[ClientRecord]] = None


def get_clients() -> list[ClientRecord]:
    """Retorna os clientes do CSV (com cache simples)."""
    global _cache
    if _cache is None:
        _cache = _load_clients()
    return _cache


def authenticate(document: str, birth_date: str) -> Optional[ClientRecord]:
    """Autentica o cliente pelo CPF e data de nascimento.

    Retorna o registro do cliente se encontrado, ou None se as credenciais
    não corresponderem a nenhum cliente cadastrado.
    """
    cpf = _normalize_cpf(document)
    birth = _normalize_birth_date(birth_date)

    for client in get_clients():
        if client.cpf == cpf and client.data_nascimento == birth:
            return client

    return None


def update_client_limits(cpf: str, limite_total: float, limite_usado: float | None = None) -> bool:
    """Atualiza o limite total (e opcionalmente o usado) de um cliente no CSV.
    
    Se limite_usado for None, mantém o valor atual do CSV.
    """
    global _cache

    normalized_cpf = _normalize_cpf(cpf)
    updated = False

    rows: list[dict] = []
    fieldnames: list[str] | None = None

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if _normalize_cpf(row.get("cpf", "")) == normalized_cpf:
                row["limite_total"] = str(limite_total)
                if limite_usado is not None:
                    row["limite_usado"] = str(limite_usado)
                updated = True
            rows.append(row)

    if updated and fieldnames:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # Invalida o cache para que get_clients() re-leia o arquivo
        _cache = None

    return updated

