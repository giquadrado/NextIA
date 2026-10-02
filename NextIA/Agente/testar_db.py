"""
testar_db.py — Teste rápido da camada de banco.
Uso:  DATABASE_URL=postgresql://... python testar_db.py
ATENÇÃO: cria e apaga dados de teste. Rode em um banco de desenvolvimento.
"""
import uuid
from db import repositorio as repo

repo.abrir_pool()
repo.aplicar_schema()
repo.aplicar_schema()  # segunda vez: precisa continuar funcionando (idempotente)

FORM_OK = {
    "nome": "Ana Teste", "email": "Ana@Teste.com", "cargo": "Gerente Financeira",
    "telefone": "(11) 91234-5678", "empresa": "Empresa X", "qtd_colaboradores": "51-200",
    "area_interesse": "financeiro", "possui_processo": "informal",
    "descricao_processo": "Conciliação feita em planilha toda semana.",
}

# 1. Formulário completo
f = repo.salvar_lead_do_formulario(FORM_OK, "v1-2026-10")
assert f["origem"] == "formulario" and f["email"] == "ana@teste.com"
assert f["qtd_colaboradores"] == "51-200" and f["consentimento_versao"] == "v1-2026-10"

# 2. Formulário sem campo obrigatório é recusado
try:
    repo.salvar_lead_do_formulario({**FORM_OK, "cargo": ""}, "v1")
    raise AssertionError("deveria recusar sem cargo")
except ValueError as e:
    assert "cargo" in str(e)

# 3. Opção fora da lista é recusada no formulário e ignorada no chat
try:
    repo.salvar_lead_do_formulario({**FORM_OK, "area_interesse": "marketing"}, "v1")
    raise AssertionError("deveria recusar área inválida")
except ValueError as e:
    assert "area_interesse" in str(e)

# 4. Chat: dados chegando aos poucos, mesma pessoa reconhecida pelo e-mail
s1 = f"teste-{uuid.uuid4()}"
repo.obter_ou_criar_sessao(s1)
repo.salvar_mensagens(s1, [("human", "oi"), ("ai", "Olá! Sou a Clara.")])
lead = repo.salvar_dados_do_chat(s1, {"urgencia": "este mês", "area_interesse": "Marketing"})
assert lead["urgencia"] == "este mês" and lead["area_interesse"] is None
lead = repo.salvar_dados_do_chat(s1, {"email": "ana@teste.com", "possui_processo": "DEFINIDO"})
assert lead["id"] == f["id"]                       # uniu com o lead do formulário
assert lead["possui_processo"] == "definido"       # normalizou maiúsculas
assert lead["cargo"] == "Gerente Financeira"       # manteve o que já existia
assert lead["urgencia"] == "este mês"              # trouxe o dado do chat

fim = repo.encerrar_atendimento(s1, "qualificado")
assert fim["status"] == "qualificado"

with repo.conexao() as c:
    print(c.execute(
        "SELECT nome, cargo, empresa, qtd_colaboradores, area_interesse, possui_processo, "
        "urgencia, origem, status, total_sessoes FROM vw_leads_painel WHERE id = %s",
        (f["id"],)).fetchone())
    c.execute("DELETE FROM sessoes WHERE id = %s", (s1,))
    c.execute("DELETE FROM leads WHERE id = %s", (f["id"],))

repo.fechar_pool()
print("✅ Todos os testes passaram.")
