"""
db/repositorio.py — Acesso ao PostgreSQL da Clara
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Regras deste módulo:
  • Todas as queries são parametrizadas (nada de f-string com valores).
  • Nomes de colunas dinâmicos só entram se estiverem na lista CAMPOS_LEAD.
  • Nunca sobrescreve um dado já salvo com valor vazio.
  • O pool de conexões é aberto uma vez (abrir_pool) e fechado no desligamento.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger("clara.db")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Campos do lead que a Clara (ou o formulário) pode preencher.
# É a lista branca usada para montar UPDATE/INSERT dinâmicos com segurança.
# A ordem segue as perguntas do formulário.
CAMPOS_LEAD: tuple[str, ...] = (
    "nome",
    "email",
    "cargo",
    "telefone",
    "empresa",
    "qtd_colaboradores",
    "area_interesse",
    "possui_processo",
    "descricao_processo",
    "urgencia",
    "observacoes",
)

# Campos com respostas fechadas: só esses valores são aceitos (iguais ao CHECK do schema).
OPCOES: dict[str, set[str]] = {
    "qtd_colaboradores": {"1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"},
    "area_interesse":    {"financeiro", "vendas", "rh", "logistica", "atendimento", "outra"},
    "possui_processo":   {"definido", "informal", "nao"},
}

# Obrigatórios no formulário da landing page (telefone e descrição são opcionais).
OBRIGATORIOS_FORMULARIO: tuple[str, ...] = (
    "nome",
    "email",
    "cargo",
    "empresa",
    "qtd_colaboradores",
    "area_interesse",
    "possui_processo",
)

STATUS_VALIDOS = {"novo", "em_qualificacao", "qualificado", "encaminhado", "descartado"}
ENCERRAMENTOS_VALIDOS = {"qualificado", "duvida_tecnica", "irritacao", "fora_escopo"}

_pool: Optional[ConnectionPool] = None


# ──────────────────────────────────────────────────────────────────────────────
# Conexão
# ──────────────────────────────────────────────────────────────────────────────

def abrir_pool() -> None:
    """Abre o pool de conexões usando DATABASE_URL (padrão do Railway e Supabase)."""
    global _pool
    if _pool is not None:
        return

    url = os.getenv("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL não definida. Configure no .env ou no Railway.")

    _pool = ConnectionPool(
        conninfo=url,
        min_size=1,
        max_size=int(os.getenv("DB_POOL_MAX", "5")),
        kwargs={"row_factory": dict_row},
        open=True,
    )
    _pool.wait(timeout=15)
    logger.info("Pool PostgreSQL aberto.")


def fechar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("Pool PostgreSQL fechado.")


@contextmanager
def conexao() -> Iterator[Connection]:
    """Entrega uma conexão em transação: commit no sucesso, rollback no erro."""
    if _pool is None:
        raise RuntimeError("Pool não iniciado. Chame abrir_pool() no startup.")
    with _pool.connection() as conn:
        with conn.transaction():
            yield conn


def aplicar_schema() -> None:
    """Cria/atualiza tabelas. Seguro para rodar a cada inicialização."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conexao() as conn:
        conn.execute(sql)
    logger.info("Schema aplicado.")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _limpar(dados: dict) -> dict:
    """
    Mantém só campos permitidos e com conteúdo real (sem string vazia).
    Campos de resposta fechada com valor fora das opções são descartados,
    para nunca violar o CHECK do banco.
    """
    limpos = {}
    for campo in CAMPOS_LEAD:
        valor = dados.get(campo)
        if isinstance(valor, str):
            valor = valor.strip()
        if not valor:
            continue
        if campo in OPCOES:
            valor = str(valor).lower()
            if valor not in OPCOES[campo]:
                logger.warning("Valor descartado | %s=%r", campo, valor)
                continue
        limpos[campo] = valor
    if "email" in limpos:
        limpos["email"] = limpos["email"].lower()
    return limpos


def _buscar_lead_por_email(conn: Connection, email: str) -> Optional[dict]:
    return conn.execute(
        "SELECT * FROM leads WHERE lower(email) = lower(%s)", (email,)
    ).fetchone()


def _atualizar_lead(conn: Connection, lead_id, campos: dict) -> None:
    if not campos:
        return
    # Nomes de coluna vêm só de CAMPOS_LEAD (lista branca) → seguro
    set_sql = ", ".join(f"{col} = %s" for col in campos)
    conn.execute(
        f"UPDATE leads SET {set_sql} WHERE id = %s",
        (*campos.values(), lead_id),
    )


def _inserir_lead(conn: Connection, campos: dict, origem: str) -> dict:
    colunas = ["origem", *campos.keys()]
    marcadores = ", ".join(["%s"] * len(colunas))
    return conn.execute(
        f"INSERT INTO leads ({', '.join(colunas)}) VALUES ({marcadores}) RETURNING *",
        (origem, *campos.values()),
    ).fetchone()


def _mesclar_leads(conn: Connection, origem_id, destino_id) -> None:
    """
    Quando a pessoa informa um e-mail que já existe em outro lead,
    os dados do lead temporário vão para o lead existente e ele é removido.
    """
    temp = conn.execute("SELECT * FROM leads WHERE id = %s", (origem_id,)).fetchone()
    if temp:
        _atualizar_lead(conn, destino_id, _limpar(temp))
    conn.execute("UPDATE sessoes SET lead_id = %s WHERE lead_id = %s", (destino_id, origem_id))
    conn.execute("DELETE FROM leads WHERE id = %s", (origem_id,))
    logger.info("Leads mesclados | %s → %s", origem_id, destino_id)


# ──────────────────────────────────────────────────────────────────────────────
# Sessões e mensagens
# ──────────────────────────────────────────────────────────────────────────────

def obter_ou_criar_sessao(sessao_id: str) -> dict:
    with conexao() as conn:
        conn.execute(
            "INSERT INTO sessoes (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            (sessao_id,),
        )
        return conn.execute("SELECT * FROM sessoes WHERE id = %s", (sessao_id,)).fetchone()


def atualizar_sessao(sessao_id: str, *, fase: str | None = None, modo: str | None = None) -> None:
    """Atualiza fase e/ou modo. Parâmetros None são ignorados."""
    with conexao() as conn:
        conn.execute(
            """
            UPDATE sessoes
               SET fase = COALESCE(%s, fase),
                   modo = COALESCE(%s, modo)
             WHERE id = %s
            """,
            (fase, modo, sessao_id),
        )


def registrar_consentimento_sessao(sessao_id: str, versao: str) -> None:
    with conexao() as conn:
        conn.execute(
            """
            UPDATE sessoes
               SET consentimento_em = COALESCE(consentimento_em, now()),
                   consentimento_versao = COALESCE(consentimento_versao, %s)
             WHERE id = %s
            """,
            (versao, sessao_id),
        )


def carregar_mensagens(sessao_id: str, limite: int = 40) -> list[dict]:
    """
    Retorna as últimas `limite` mensagens em ordem cronológica.
    O limite evita mandar conversas enormes ao LLM (custo e janela de contexto).
    """
    with conexao() as conn:
        linhas = conn.execute(
            """
            SELECT papel, conteudo FROM (
              SELECT id, papel, conteudo FROM mensagens
               WHERE sessao_id = %s
               ORDER BY id DESC
               LIMIT %s
            ) ultimas
            ORDER BY id ASC
            """,
            (sessao_id, limite),
        ).fetchall()
    return list(linhas)


def salvar_mensagens(sessao_id: str, mensagens: list[tuple[str, str]]) -> None:
    """Salva pares (papel, conteudo) na ordem recebida."""
    if not mensagens:
        return
    with conexao() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO mensagens (sessao_id, papel, conteudo) VALUES (%s, %s, %s)",
                [(sessao_id, papel, conteudo[:8000]) for papel, conteudo in mensagens],
            )


# ──────────────────────────────────────────────────────────────────────────────
# Leads
# ──────────────────────────────────────────────────────────────────────────────

def obter_lead(lead_id) -> Optional[dict]:
    if not lead_id:
        return None
    with conexao() as conn:
        return conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()


def obter_lead_da_sessao(sessao_id: str) -> Optional[dict]:
    with conexao() as conn:
        return conn.execute(
            """
            SELECT l.* FROM leads l
              JOIN sessoes s ON s.lead_id = l.id
             WHERE s.id = %s
            """,
            (sessao_id,),
        ).fetchone()


def salvar_dados_do_chat(sessao_id: str, dados: dict) -> Optional[dict]:
    """
    Grava os dados extraídos da conversa no lead ligado à sessão.

    • Cria o lead na primeira informação útil (mesmo sem e-mail).
    • Se o e-mail informado já pertence a outro lead, une os dois.
    • Copia o consentimento da sessão para o lead.
    Retorna o lead atualizado (ou None se não havia nada para salvar).
    """
    campos = _limpar(dados)
    if not campos:
        return obter_lead_da_sessao(sessao_id)

    with conexao() as conn:
        sessao = conn.execute(
            "SELECT * FROM sessoes WHERE id = %s FOR UPDATE", (sessao_id,)
        ).fetchone()
        if sessao is None:
            raise ValueError(f"Sessão inexistente: {sessao_id}")

        lead_id = sessao["lead_id"]

        # E-mail que já existe em outro lead → usar o lead existente
        if "email" in campos:
            existente = _buscar_lead_por_email(conn, campos["email"])
            if existente and existente["id"] != lead_id:
                if lead_id:
                    _mesclar_leads(conn, lead_id, existente["id"])
                lead_id = existente["id"]

        if lead_id:
            _atualizar_lead(conn, lead_id, campos)
        else:
            lead_id = _inserir_lead(conn, campos, origem="chat")["id"]

        conn.execute(
            """
            UPDATE leads
               SET status = CASE WHEN status = 'novo' THEN 'em_qualificacao' ELSE status END,
                   consentimento_em     = COALESCE(consentimento_em, %s),
                   consentimento_versao = COALESCE(consentimento_versao, %s)
             WHERE id = %s
            """,
            (sessao["consentimento_em"], sessao["consentimento_versao"], lead_id),
        )
        conn.execute("UPDATE sessoes SET lead_id = %s WHERE id = %s", (lead_id, sessao_id))

        return conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()


def encerrar_atendimento(sessao_id: str, encerramento: str, observacoes: str | None = None) -> Optional[dict]:
    """
    Registra como a conversa terminou (uma das 4 situações do prompt).
    'qualificado' também muda o status do lead para 'qualificado'.
    """
    if encerramento not in ENCERRAMENTOS_VALIDOS:
        raise ValueError(f"Encerramento inválido: {encerramento}")

    with conexao() as conn:
        sessao = conn.execute("SELECT lead_id FROM sessoes WHERE id = %s", (sessao_id,)).fetchone()
        conn.execute("UPDATE sessoes SET fase = 'concluido' WHERE id = %s", (sessao_id,))
        if not sessao or not sessao["lead_id"]:
            return None

        novo_status = "qualificado" if encerramento == "qualificado" else None
        conn.execute(
            """
            UPDATE leads
               SET encerramento = %s,
                   status       = COALESCE(%s, status),
                   observacoes  = CASE
                                    WHEN %s::text IS NULL THEN observacoes
                                    WHEN observacoes IS NULL THEN %s::text
                                    ELSE observacoes || E'\n' || %s::text
                                  END
             WHERE id = %s
            """,
            (encerramento, novo_status, observacoes, observacoes, observacoes, sessao["lead_id"]),
        )
        return conn.execute("SELECT * FROM leads WHERE id = %s", (sessao["lead_id"],)).fetchone()


def salvar_lead_do_formulario(dados: dict, consentimento_versao: str) -> dict:
    """
    Lead vindo do formulário da landing page.
    Se o e-mail já existir, completa o cadastro em vez de duplicar.
    """
    campos = _limpar(dados)
    faltando = [c for c in OBRIGATORIOS_FORMULARIO if c not in campos]
    if faltando:
        raise ValueError(f"Campos obrigatórios ausentes ou inválidos: {', '.join(faltando)}")

    with conexao() as conn:
        existente = _buscar_lead_por_email(conn, campos["email"])
        if existente:
            _atualizar_lead(conn, existente["id"], campos)
            lead_id = existente["id"]
        else:
            lead_id = _inserir_lead(conn, campos, origem="formulario")["id"]

        conn.execute(
            """
            UPDATE leads
               SET consentimento_em     = COALESCE(consentimento_em, now()),
                   consentimento_versao = COALESCE(consentimento_versao, %s)
             WHERE id = %s
            """,
            (consentimento_versao, lead_id),
        )
        return conn.execute("SELECT * FROM leads WHERE id = %s", (lead_id,)).fetchone()


def atualizar_status(lead_id, status: str) -> None:
    """Para uso do time comercial (ex.: marcar como 'encaminhado')."""
    if status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido: {status}")
    with conexao() as conn:
        conn.execute("UPDATE leads SET status = %s WHERE id = %s", (status, lead_id))
