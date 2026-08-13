import sys
sys.path.insert(0, r'C:\Users\Kabum\Desktop\Meus testes\backend')

with open('backend/app/services/client_db.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_line = """    dd_mm_yyyy = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", value)
    if dd_mm_yyyy:
        day, month, year = dd_mm_yyyy.groups()
        return f"{year}-{month}-{day}"
    return value"""

new_line = """    # Try DD/MM/YYYY format (with slashes) first
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
    return value"""

if old_line in content:
    content = content.replace(old_line, new_line)
    with open('backend/app/services/client_db.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Atualizado com sucesso')
else:
    print('Não encontrou a linha exata')
    idx = content.find('def _normalize_birth_date')
    print(content[idx:idx+300])