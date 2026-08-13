import re

def normalize_birth_date(value):
    """Normaliza a data de nascimento para o formato YYYY-MM-DD."""
    value = (value or "").strip()
    dd_mm_yyyy = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value)
    if dd_mm_yyyy:
        day, month, year = dd_mm_yyyy.groups()
        return f"{year}-{month}-{day}"
    return value

# Test cases
print("Testando normalize_birth_date:")
print(f"'23122003' -> {normalize_birth_date('23122003')}")
print(f"'23/12/2003' -> {normalize_birth_date('23/12/2003')}")
print(f"'2003-12-23' -> {normalize_birth_date('2003-12-23')}")
print(f"'15/03/1988' -> {normalize_birth_date('15/03/1988')}")
print(f"'1988-03-15' -> {normalize_birth_date('1988-03-15')}")