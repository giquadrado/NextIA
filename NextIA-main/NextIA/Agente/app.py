"""
app.py — API FastAPI para o Agente de Conversação Clara
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Arquitetura stateless:
  • O Front-end gera um session_id (UUID) no primeiro carregamento.
  • Cada requisição ao /api/chat reconstrói o SessionState do LangGraph
    a partir do histórico salvo no SQLite — sem memória em servidor.
  • Após a invocação do grafo, persiste as novas mensagens e atualiza
    os dados do lead extraídos pela Clara.

Decisões de design:
  • Apenas sqlite3 nativo — sem ORM, sem SQLAlchemy.
  • Conexão por thread (check_same_thread=False + threading.local).
  • CORS liberado para o domínio da landing page via variável de ambiente.
  • Todas as queries parametrizadas — sem interpolação de strings.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────────────────────────────────────

import os
import sqlite3
import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage

# Importa a interface pública do agente
from agent import chat, iniciar_sessao, SessionState, LeadData, _extract_text

# ──────────────────────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("clara.api")

DB_PATH      = os.getenv("DB_PATH", "database.db")
ALLOWED_CORS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ──────────────────────────────────────────────────────────────────────────────
# Camada de Banco de Dados
# ──────────────────────────────────────────────────────────────────────────────

# Uma conexão por thread — evita conflito em cenários com múltiplos workers.
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Retorna (ou cria) a conexão SQLite da thread atual."""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL;")   # melhor concorrência
        _local.conn.execute("PRAGMA foreign_keys=ON;")
    return _local.conn


@contextmanager
def db():
    """Context manager que entrega a conexão e faz commit/rollback automático."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    """Cria as tabelas caso ainda não existam."""
    ddl = """
    CREATE TABLE IF NOT EXISTS leads (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        nome             TEXT,
        email            TEXT UNIQUE,
        empresa          TEXT,
        num_funcionarios TEXT,
        objetivo         TEXT,
        dor_atual        TEXT,
        criado_em        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id              TEXT PRIMARY KEY,          -- UUID gerado pelo front-end
        lead_id         INTEGER REFERENCES leads(id) ON DELETE SET NULL,
        fase            TEXT NOT NULL DEFAULT 'escolha',
        modo_abordagem  TEXT,                      -- 'formulario' | 'conversa'
        atualizado_em   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        role        TEXT NOT NULL CHECK(role IN ('human','ai')),
        content     TEXT NOT NULL,
        criado_em   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
    );

    CREATE INDEX IF NOT EXISTS idx_messages_session
        ON chat_messages(session_id, criado_em);
    """
    with db() as conn:
        conn.executescript(ddl)
    logger.info("Banco de dados inicializado em '%s'", DB_PATH)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de persistência
# ──────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upsert_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row:
    """Garante que a sessão exista; cria se necessário."""
    conn.execute(
        """
        INSERT INTO sessions (id, fase, atualizado_em)
        VALUES (?, 'escolha', ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, _now_iso()),
    )
    return conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()


def _load_state_from_db(conn: sqlite3.Connection, session_id: str) -> SessionState:
    """
    Reconstrói o SessionState completo do LangGraph a partir do SQLite.
    Retorna um estado inicial limpo se a sessão não tiver histórico.
    """
    session = _upsert_session(conn, session_id)

    # ── Mensagens → formato Langchain ──────────────────────────────────────
    rows = conn.execute(
        """
        SELECT role, content FROM chat_messages
        WHERE  session_id = ?
        ORDER  BY criado_em ASC, id ASC
        """,
        (session_id,),
    ).fetchall()

    messages = []
    for row in rows:
        if row["role"] == "human":
            messages.append(HumanMessage(content=row["content"]))
        else:
            messages.append(AIMessage(content=row["content"]))

    # ── Dados do lead ──────────────────────────────────────────────────────
    lead: LeadData = LeadData()
    if session["lead_id"]:
        lead_row = conn.execute(
            "SELECT * FROM leads WHERE id = ?", (session["lead_id"],)
        ).fetchone()
        if lead_row:
            lead = LeadData(
                nome=lead_row["nome"]             or "",
                email=lead_row["email"]            or "",
                empresa=lead_row["empresa"]        or "",
                num_funcionarios=lead_row["num_funcionarios"] or "",
                objetivo=lead_row["objetivo"]      or "",
                dor_atual=lead_row["dor_atual"]    or "",
                modo=session["modo_abordagem"]     or "",
            )
    elif session["modo_abordagem"]:
        lead["modo"] = session["modo_abordagem"]

    fase = session["fase"] or "escolha"

    logger.debug(
        "Estado reconstruído | session=%s | fase=%s | msgs=%d",
        session_id, fase, len(messages),
    )
    return SessionState(messages=messages, lead=lead, fase=fase)


def _persist_new_messages(
    conn: sqlite3.Connection,
    session_id: str,
    human_text: str,
    ai_text: str,
) -> None:
    """Salva a mensagem do usuário e a resposta da Clara."""
    now = _now_iso()
    conn.executemany(
        "INSERT INTO chat_messages (session_id, role, content, criado_em) VALUES (?,?,?,?)",
        [
            (session_id, "human", human_text, now),
            (session_id, "ai",    ai_text,    now),
        ],
    )


def _upsert_lead(
    conn: sqlite3.Connection,
    session_id: str,
    lead: LeadData,
    fase: str,
) -> None:
    """
    Cria ou atualiza o registro de lead associado à sessão.
    Só persiste campos que foram preenchidos — nunca sobrescreve com vazio.
    """
    campos_lead = {k: v for k, v in lead.items() if k != "modo" and v}
    modo        = lead.get("modo") or None

    # Atualiza metadados da sessão
    conn.execute(
        """
        UPDATE sessions
        SET    fase = ?, modo_abordagem = ?, atualizado_em = ?
        WHERE  id   = ?
        """,
        (fase, modo, _now_iso(), session_id),
    )

    if not campos_lead:
        return  # Nada de lead para persistir ainda

    session = conn.execute(
        "SELECT lead_id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()

    if session["lead_id"]:
        # ── UPDATE: só atualiza colunas com valor real ─────────────────────
        set_clause  = ", ".join(f"{col} = ?" for col in campos_lead)
        set_vals    = list(campos_lead.values())
        conn.execute(
            f"UPDATE leads SET {set_clause} WHERE id = ?",  # noqa: S608 — colunas são chaves fixas do TypedDict
            [*set_vals, session["lead_id"]],
        )
        logger.debug("Lead atualizado | id=%s", session["lead_id"])
    else:
        # ── INSERT com ON CONFLICT no e-mail ───────────────────────────────
        cols      = ", ".join(campos_lead.keys())
        placeh    = ", ".join("?" * len(campos_lead))
        vals      = list(campos_lead.values())

        # Se o e-mail já existir, faz merge dos campos novos
        update_part = ", ".join(
            f"{col} = COALESCE(excluded.{col}, leads.{col})"
            for col in campos_lead
        )
        conn.execute(
            f"""
            INSERT INTO leads ({cols}) VALUES ({placeh})
            ON CONFLICT(email) DO UPDATE SET {update_part}
            """,
            vals,
        )
        lead_id = conn.execute(
            "SELECT id FROM leads WHERE email = ?",
            (campos_lead.get("email"),),
        ).fetchone()

        # Vincula lead à sessão se conseguirmos o id
        if lead_id:
            conn.execute(
                "UPDATE sessions SET lead_id = ? WHERE id = ?",
                (lead_id["id"], session_id),
            )
            logger.info("Lead vinculado | lead_id=%s | session=%s", lead_id["id"], session_id)


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI — Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64, description="UUID gerado pelo front-end")
    message:    str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply:      str
    fase:       str
    lead:       dict


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI — Aplicação
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Clara — Agente de Conversação Next.AI",
    version="1.0.0",
    description="API stateless que envelopa o LangGraph da Clara com persistência SQLite.",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_CORS,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-ID"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    logger.info("Clara API pronta.")


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def endpoint_chat(payload: ChatRequest) -> ChatResponse:
    """
    Ponto de entrada principal do chat.

    Fluxo por requisição:
      1. Abre conexão SQLite da thread.
      2. Reconstrói SessionState a partir do histórico.
      3. Invoca graph.invoke() via agent.chat().
      4. Persiste novas mensagens e dados do lead.
      5. Retorna resposta + estado resumido ao front-end.
    """
    session_id  = payload.session_id.strip()
    user_input  = payload.message.strip()

    logger.info("→ /api/chat | session=%s | len_msg=%d", session_id, len(user_input))

    try:
        with db() as conn:
            # ── 1. Reconstruir estado ─────────────────────────────────────
            state = _load_state_from_db(conn, session_id)

            # ── 2. Invocar o agente ───────────────────────────────────────
            ai_reply, new_state = chat(user_input, state)

            # ── 3. Persistir mensagens ────────────────────────────────────
            _persist_new_messages(conn, session_id, user_input, ai_reply)

            # ── 4. Persistir lead + fase ──────────────────────────────────
            _upsert_lead(conn, session_id, new_state["lead"], new_state["fase"])

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro interno | session=%s | %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Erro interno no agente. Tente novamente.")

    lead_público = {k: v for k, v in new_state["lead"].items() if k != "modo"}

    logger.info(
        "← /api/chat | session=%s | fase=%s | lead_fields=%s",
        session_id,
        new_state["fase"],
        [k for k, v in lead_público.items() if v],
    )

    return ChatResponse(
        session_id=session_id,
        reply=ai_reply,
        fase=new_state["fase"],
        lead=lead_público,
    )


@app.post("/api/session/init", response_model=ChatResponse)
async def endpoint_init(payload: ChatRequest) -> ChatResponse:
    """
    Dispara a saudação inicial da Clara automaticamente.
    O front-end chama este endpoint ao exibir o chat pela primeira vez,
    sem necessitar que o usuário escreva nada.

    Usa a mensagem de inicialização 'oi' internamente (igual ao CLI).
    """
    # Reutilizamos o endpoint de chat com a saudação padrão
    init_payload = ChatRequest(session_id=payload.session_id, message="oi")
    return await endpoint_chat(init_payload)


@app.get("/api/session/{session_id}")
async def endpoint_session(session_id: str) -> JSONResponse:
    """
    Retorna o estado atual de uma sessão (útil para debug e retomada de chat).
    """
    try:
        with db() as conn:
            session = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if not session:
                raise HTTPException(status_code=404, detail="Sessão não encontrada.")

            messages = conn.execute(
                """
                SELECT role, content, criado_em FROM chat_messages
                WHERE  session_id = ?
                ORDER  BY criado_em ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

            lead_data = None
            if session["lead_id"]:
                lead_row = conn.execute(
                    "SELECT * FROM leads WHERE id = ?", (session["lead_id"],)
                ).fetchone()
                if lead_row:
                    lead_data = dict(lead_row)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro ao buscar sessão '%s': %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Erro ao recuperar sessão.")

    return JSONResponse({
        "session_id":     session_id,
        "fase":           session["fase"],
        "modo_abordagem": session["modo_abordagem"],
        "atualizado_em":  session["atualizado_em"],
        "lead":           lead_data,
        "messages":       [dict(m) for m in messages],
    })


@app.get("/health")
async def health() -> JSONResponse:
    """Health check simples para monitoramento e load balancers."""
    return JSONResponse({"status": "ok", "agent": "Clara v1.0"})


# ──────────────────────────────────────────────────────────────────────────────
# Entrypoint direto (uvicorn embutido para desenvolvimento)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info",
    )
