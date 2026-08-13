import re

path = "backend/app/services/agent.py"
content = open(path, encoding="utf-8").read()

# Adiciona session.client_cpf = record.cpf após session.client = _to_client(record)
old = '''            session.auth_attempts = 0
            session.client = _to_client(record)
            session.status = "authenticated"'''

new = '''            session.auth_attempts = 0
            session.client = _to_client(record)
            session.client_cpf = record.cpf
            session.status = "authenticated"'''

if old in content and "session.client_cpf = record.cpf" not in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("✅ agent.py corrigido: session.client_cpf adicionado")
else:
    print("⚠️  session.client_cpf já existe ou padrão não encontrado")