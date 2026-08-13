import csv
import os
from pathlib import Path

# Atualizar o arquivo client_db.py
path = Path("backend/app/services/client_db.py")
new_function = '''

def update_client_limits(cpf: str, limite_total: float, limite_disponivel: float) -> bool:
    """Atualiza o limite total e disponível de um cliente no CSV."""
    import csv
    import re
    from pathlib import Path

    CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "clientes.csv"
    _cache: list | None = None

    def _normalize_cpf(cpf: str) -> str:
        return re.sub(r"\D", "", cpf or "")

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
                row["limite_disponivel"] = str(limite_disponivel)
                updated = True
            rows.append(row)

    if updated and fieldnames:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return updated
'''

content = path.read_text(encoding="utf-8")
if "def update_client_limits" not in content:
    path.write_text(content.rstrip() + "\n" + new_function + "\n", encoding="utf-8")
    print("✅ client_db.py atualizado com update_client_limits")
else:
    print("⚠️  update_client_limits já existe")