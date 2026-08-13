"""Teste de validação das correções."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.session import session_store
from app.services.agent import handle_message as triage_handle
from app.services.credit_service import request_credit_increase, get_credit_limit
from app.services.client_db import authenticate, update_client_limits, get_clients
from app.routers.auth import _to_client

print("=" * 60)
print("TESTE 1: Autenticação e fluxo autenticado sem pedir CPF")
print("=" * 60)

session = session_store.create()
resp1 = triage_handle(session, "CPF: 111.444.777-35")
print(f"1. Envio CPF: status={resp1.status}")
assert resp1.status == "authenticating", "Deveria estar autenticando"

resp2 = triage_handle(session, "15/03/1988")
print(f"2. Envio data: status={resp2.status}, authenticated={resp2.authenticated}")
assert resp2.status == "authenticated", "Deveria estar autenticado"
assert resp2.authenticated == True

# Verifica que session.client_cpf foi setado
assert session.client_cpf == "11144477735", f"CPF deveria ser 11144477735, got {session.client_cpf}"
print(f"   ✅ session.client_cpf = {session.client_cpf}")

# Agora envia mensagem de limite - NÃO deve pedir CPF novamente
resp3 = triage_handle(session, "Qual meu limite de crédito?")
print(f"3. Consulta limite: status={resp3.status}")
assert "CPF" not in resp3.message and "data de nascimento" not in resp3.message, \
    "Não deveria pedir CPF/data novamente!"
assert resp3.metadata.get("agent") == "credit", "Deveria redirecionar para agente credit"
print(f"   ✅ Não pediu CPF novamente. Agente: {resp3.metadata.get('agent')}")

print("\n" + "=" * 60)
print("TESTE 2: Aumento de limite atualiza o CSV")
print("=" * 60)

# Verifica limite inicial da Marina (8000)
limit_before = get_credit_limit(session.id)
print(f"Limite antes: R$ {limit_before.total:,.2f}")

# Solicita aumento para 5000 (deve ser aprovado: <= 15000)
result = request_credit_increase(session.id, 5000)
print(f"Solicitação: R$ {result.requested_limit:,.2f}")
print(f"Status: {result.status}")
assert result.status == "approved", "Deveria ser aprovado"

# Verifica se o CSV foi atualizado
clients = get_clients()
marina = [c for c in clients if c.cpf == "11144477735"]
assert len(marina) == 1, "Marina deveria estar no CSV"
marina_record = marina[0]
print(f"Marina limite_total no CSV: R$ {marina_record.limite_total:,.2f}")
assert marina_record.limite_total == 5000, f"CSV não atualizado! Esperado 5000, got {marina_record.limite_total}"
print(f"   ✅ CSV atualizado: limite_total = {marina_record.limite_total}")
assert marina_record.limite_disponivel == 5000, f"CSV não atualizado! Esperado 5000 disp, got {marina_record.limite_disponivel}"
print(f"   ✅ CSV atualizado: limite_disponivel = {marina_record.limite_disponivel}")

# Verifica se a sessão foi atualizada em memória
limit_after = get_credit_limit(session.id)
print(f"Limite depois (sessão): R$ {limit_after.total:,.2f}")
assert limit_after.total == 5000, f"Sessão não atualizada! Esperado 5000, got {limit_after.total}"
print(f"   ✅ Sessão atualizada em memória")

print("\n" + "=" * 60)
print("TESTE 3: Aumento reprovado não altera o CSV")
print("=" * 60)

# Solicita aumento para 20000 (deve ser reprovado: > 15000)
result2 = request_credit_increase(session.id, 20000)
print(f"Solicitação: R$ {result2.requested_limit:,.2f}")
print(f"Status: {result2.status}")
assert result2.status == "rejected", "Deveria ser rejeitado"

# Verifica que o CSV NÃO foi alterado
clients2 = get_clients()
marina2 = [c for c in clients2 if c.cpf == "11144477735"]
assert len(marina2) == 1
assert marina2[0].limite_total == 5000, f"CSV não deveria ter mudado! Got {marina2[0].limite_total}"
print(f"   ✅ CSV permanece com R$ {marina2[0].limite_total} (não alterado)")

print("\n" + "=" * 60)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 60)
print("\nResumo das correções:")
print("1. ✅ session.client_cpf setado após autenticação")
print("2. ✅ Agente de triagem não pede CPF quando autenticado")
print("3. ✅ Aumento aprovado atualiza o CSV")
print("4. ✅ Aumento reprovado não altera o CSV")

</parameter>
<task_progress>
- [x] Analisar a estrutura do projeto e arquivos existentes
- [x] Entender o fluxo de integração do agente de crédito
- [x] Executar testes para validar a integração
- [x] Corrigir eventuais bugs encontrados (widget key + camelCase)
- [x] Verificar frontend (widget handling)
- [x] Implementar persistência de limite aprovado + fix CPF quando autenticado
- [ ] Atualizar frontend para novos campos
- [ ] Testar e documentar
</task_progress>
</write_to_file>