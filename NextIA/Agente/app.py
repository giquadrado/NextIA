"""
app.py — API da Clara (FastAPI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Endpoints usados pela landing page:
  POST /api/session/init   saudação inicial ou retomada da conversa   (chat.js)
  POST /api/chat           mensagem do visitante → resposta da Clara    (chat.js)
  POST /api/leads          envio do formulário de contato               (form.js)
  GET  /health             verificação de funcionamento (Railway)

Endpoint interno (protegido por ADMIN_TOKEN):
  GET  /api/admin/sessao/{id}   histórico + lead, para depuração

Os endpoints são funções síncronas (def): o FastAPI os executa em threads,
então chamadas lentas ao LLM e ao banco não travam o servidor.
"""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("clara.api")

from db import repositorio as repo  # noqa: E402
import agent  # noqa: E402  (carrega o LLM; precisa do .env já lido)

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
CONSENTIMENTO_VERSAO = os.getenv("CONSENTIMENTO_VERSAO", "v1-2026-10")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Campos do lead que podem voltar para o navegador
CAMPOS_PUBLICOS = ("nome", "email", "cargo", "telefone", "empresa", "qtd_colaboradores",
                   "area_interesse", "possui_processo", "descricao_processo")


# ══════════════════════════════════════════════════════════════════════════════
#  Ciclo de vida: abre o banco ao iniciar, fecha ao desligar
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(_: FastAPI):
    repo.abrir_pool()
    repo.aplicar_schema()
    if not ALLOWED_ORIGINS:
        logger.warning("ALLOWED_ORIGINS vazio: nenhum site poderá chamar a API pelo navegador.")
    logger.info("Clara API pronta.")
    yield
    repo.fechar_pool()


app = FastAPI(
    title="Clara · Interagente",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENABLE_DOCS") == "1" else None,  # docs só quando ligado
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════════════════════════════════════

SessaoId = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class InitRequest(BaseModel):
    session_id: str = SessaoId
    message: Optional[str] = None  # ignorado; mantido por compatibilidade com o chat.js antigo


class ChatRequest(BaseModel):
    session_id: str = SessaoId
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    fase: str
    lead: dict
    historico: list[dict] = []   # preenchido só na retomada de conversa


class LeadForm(BaseModel):
    """Mesmas perguntas e opções do formulário da landing page."""
    nome: str = Field(..., min_length=3, max_length=120)
    email: EmailStr
    cargo: str = Field(..., min_length=2, max_length=120)
    telefone: Optional[str] = Field(None, max_length=20, pattern=r"^\(\d{2}\) \d{4,5}-\d{4}$")
    empresa: str = Field(..., min_length=2, max_length=160)
    qtd_colaboradores: Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
    area_interesse: Literal["financeiro", "vendas", "rh", "logistica", "atendimento", "outra"]
    possui_processo: Literal["definido", "informal", "nao"]
    descricao_processo: Optional[str] = Field(None, max_length=2000)
    consentimento: bool

    @field_validator("consentimento")
    @classmethod
    def exige_consentimento(cls, v: bool) -> bool:
        if not v:
            raise ValueError("É preciso concordar com o uso dos dados.")
        return v


def _lead_publico(lead: dict | None) -> dict:
    lead = lead or {}
    return {campo: lead.get(campo) for campo in CAMPOS_PUBLICOS if lead.get(campo)}


# ══════════════════════════════════════════════════════════════════════════════
#  Endpoints públicos
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/session/init", response_model=ChatResponse)
def iniciar_sessao(payload: InitRequest) -> ChatResponse:
    """
    Primeira chamada do chat.
    • Sessão nova: a Clara gera a saudação (sem gravar um "oi" falso do visitante).
    • Sessão existente: devolve o histórico para o chat.js mostrar a conversa de onde parou.
    """
    sid = payload.session_id
    try:
        historico = agent.historico_publico(sid)
        if historico:
            sessao = repo.obter_ou_criar_sessao(sid)
            ultima_da_clara = next((m["content"] for m in reversed(historico) if m["role"] == "ai"), "")
            return ChatResponse(
                session_id=sid,
                reply=ultima_da_clara,
                fase=sessao["fase"],
                lead=_lead_publico(repo.obter_lead_da_sessao(sid)),
                historico=historico,
            )

        r = agent.processar_mensagem(sid, None)
    except Exception:
        logger.exception("Erro no init | sessao=%s", sid)
        raise HTTPException(status_code=500, detail="Não foi possível iniciar a conversa.")

    return ChatResponse(session_id=sid, reply=r["resposta"], fase=r["fase"], lead=_lead_publico(r["lead"]))


@app.post("/api/chat", response_model=ChatResponse)
def conversar(payload: ChatRequest) -> ChatResponse:
    sid, texto = payload.session_id, payload.message.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")

    try:
        r = agent.processar_mensagem(sid, texto)
    except Exception:
        logger.exception("Erro no chat | sessao=%s", sid)
        raise HTTPException(status_code=500, detail="Erro interno no agente. Tente novamente.")

    logger.info("Chat | sessao=%s | fase=%s | campos=%s", sid, r["fase"], sorted(_lead_publico(r["lead"])))
    return ChatResponse(session_id=sid, reply=r["resposta"], fase=r["fase"], lead=_lead_publico(r["lead"]))


@app.post("/api/leads", status_code=201)
def receber_formulario(form: LeadForm) -> dict:
    """Formulário da landing page → mesma tabela de leads do chat."""
    dados = form.model_dump(exclude={"consentimento"})
    try:
        lead = repo.salvar_lead_do_formulario(dados, CONSENTIMENTO_VERSAO)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Erro ao salvar formulário")
        raise HTTPException(status_code=500, detail="Não foi possível salvar agora.")

    logger.info("Formulário | lead=%s | área=%s", lead["id"], lead["area_interesse"])
    return {"ok": True}  # não devolve dados pessoais nem o id


@app.get("/health")
def health() -> dict:
    try:
        with repo.conexao() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "banco": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Banco indisponível.")


# ══════════════════════════════════════════════════════════════════════════════
#  Endpoint interno (depuração) — desligado se ADMIN_TOKEN não estiver definido
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/sessao/{sessao_id}")
def ver_sessao(sessao_id: str, x_admin_token: str = Header(default="")) -> dict:
    if not ADMIN_TOKEN or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=404)  # 404 para não revelar que a rota existe

    lead = repo.obter_lead_da_sessao(sessao_id)
    sessao = repo.obter_ou_criar_sessao(sessao_id)
    return {
        "sessao": {k: str(v) if v is not None else None for k, v in sessao.items()},
        "lead": {k: str(v) if v is not None else None for k, v in (lead or {}).items()},
        "mensagens": agent.historico_publico(sessao_id),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
