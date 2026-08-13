# -*- coding: utf-8 -*-
from app.models.session import session_store
from app.services import agent
import app.services.client_db as client_db
from app.services.score_service import get_credit_data

client_db._cache = None
cpf = "12345678909"
birth = "05/02/1990"

print("=" * 60)
print("Teste: score baixo + aumento de limite -> oferta de entrevista")
print("=" * 60)

session = session_store.get_or_create("conv_teste_aumento")
r1 = agent.handle_message(session, cpf + " " + birth)
print("[1]", r1.message[:80])

credit_data = get_credit_data(cpf)
print("Score atual:", credit_data["score"])

r2 = agent.handle_message(session, "Quero solicitar aumento de limite para 15000")
print("[2]", r2.message[:120])
print("    widget:", r2.metadata.get("widget", {}).get("kind"))

if "cpf" in r2.message.lower() and "nascimento" in r2.message.lower():
    print("  BUG: Pediu CPF/data novamente!")
elif "entrevista" in r2.message.lower() or "score" in r2.message.lower():
    print("  OK: Mensagem clara sobre score, oferecendo entrevista")

widget_kind = r2.metadata.get("widget", {}).get("kind")
if widget_kind == "interview":
    print("  OK: Widget interview enviado (botoes no frontend)")
else:
    print("  ATENCAO: Widget esperado interview, recebido:", widget_kind)

print()
print("=" * 60)
print("Teste: cliente com score alto (Matheus - 850)")
print("=" * 60)

session2 = session_store.get_or_create("conv_teste_alto")
r3 = agent.handle_message(session2, "45573022890 23/12/2003")
print("[3]", r3.message[:80])

r4 = agent.handle_message(session2, "Quero solicitar aumento de limite para 20000")
print("[4]", r4.message[:120])
print("    widget:", r4.metadata.get("widget", {}).get("kind"))
print("    status:", r4.metadata.get("widget", {}).get("creditRequest", {}).get("status"))

print()
print("Testes concluidos!")
</arg_value>
<task_progress>
- [x] Corrigir: `_ask_for_value` não pedir CPF/data novamente
- [x] Corrigir: `_process_credit_change` para score baixo + oferta entrevista
- [x] Investigar: get_credit_limit lê CSV correto
- [ ] Testar o fluxo de aumento com score baixo
- [ ] Testar o fluxo completo
</task_progress>
</write_to_file>