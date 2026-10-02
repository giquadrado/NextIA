-- ═══════════════════════════════════════════════════════════════════════
--  Clara · Interagente — Schema PostgreSQL
--  Idempotente: pode rodar várias vezes sem apagar dados.
--  Requer PostgreSQL 13+ (gen_random_uuid nativo).
-- ═══════════════════════════════════════════════════════════════════════


-- ── Função utilitária: mantém "atualizado_em" sempre correto ────────────
CREATE OR REPLACE FUNCTION set_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════════════════════
--  LEADS — uma linha por pessoa/empresa interessada
--  Origem pode ser o chat da Clara ou o formulário da landing page.
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS leads (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- ── Perguntas do formulário (mesmas que a Clara coleta no chat) ──
  nome                  TEXT,
  email                 TEXT,
  cargo                 TEXT,
  telefone              TEXT,
  empresa               TEXT,

  -- Quantidade de colaboradores, em faixas
  qtd_colaboradores     TEXT
                        CHECK (qtd_colaboradores IN ('1-10', '11-50', '51-200',
                                                     '201-500', '501-1000', '1000+')),

  -- Área de interesse em automatizar
  area_interesse        TEXT
                        CHECK (area_interesse IN ('financeiro', 'vendas', 'rh', 'logistica',
                                                  'atendimento', 'outra')),

  -- Já tem algum processo?
  --   definido = processo definido/documentado
  --   informal = existe, mas é manual ou informal
  --   nao      = ainda não existe
  possui_processo       TEXT
                        CHECK (possui_processo IN ('definido', 'informal', 'nao')),
  descricao_processo    TEXT,          -- detalhes livres sobre o processo

  -- ── Coletados só pela Clara na conversa ──
  urgencia              TEXT,          -- quando precisa ("este mês", "sem pressa")

  -- ── Controle comercial ──
  origem                TEXT NOT NULL DEFAULT 'chat'
                        CHECK (origem IN ('chat', 'formulario')),
  status                TEXT NOT NULL DEFAULT 'novo'
                        CHECK (status IN ('novo', 'em_qualificacao', 'qualificado',
                                          'encaminhado', 'descartado')),
  -- As 4 situações de encerramento definidas no prompt da Clara
  encerramento          TEXT
                        CHECK (encerramento IN ('qualificado', 'duvida_tecnica',
                                                'irritacao', 'fora_escopo')),
  observacoes           TEXT,          -- ex.: dúvida técnica anotada pela Clara

  -- LGPD: quando e com qual versão do aviso a pessoa concordou
  consentimento_em      TIMESTAMPTZ,
  consentimento_versao  TEXT,

  criado_em             TIMESTAMPTZ NOT NULL DEFAULT now(),
  atualizado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- E-mail único sem diferenciar maiúsculas; leads sem e-mail são permitidos
CREATE UNIQUE INDEX IF NOT EXISTS ux_leads_email
  ON leads (lower(email)) WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_leads_status_criado
  ON leads (status, criado_em DESC);

DROP TRIGGER IF EXISTS trg_leads_atualizado ON leads;
CREATE TRIGGER trg_leads_atualizado
  BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();


-- ═══════════════════════════════════════════════════════════════════════
--  SESSOES — uma conversa no chat (id gerado pelo navegador no chat.js)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sessoes (
  id                    TEXT PRIMARY KEY
                        CHECK (char_length(id) BETWEEN 8 AND 64),
  lead_id               UUID REFERENCES leads(id) ON DELETE SET NULL,

  fase                  TEXT NOT NULL DEFAULT 'escolha'
                        CHECK (fase IN ('escolha', 'coleta', 'concluido')),
  modo                  TEXT
                        CHECK (modo IN ('formulario', 'conversa')),

  -- Consentimento dado no chat antes de existir um lead
  consentimento_em      TIMESTAMPTZ,
  consentimento_versao  TEXT,

  criado_em             TIMESTAMPTZ NOT NULL DEFAULT now(),
  atualizado_em         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_sessoes_lead ON sessoes (lead_id);

DROP TRIGGER IF EXISTS trg_sessoes_atualizado ON sessoes;
CREATE TRIGGER trg_sessoes_atualizado
  BEFORE UPDATE ON sessoes
  FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();


-- ═══════════════════════════════════════════════════════════════════════
--  MENSAGENS — histórico do chat, usado para a Clara "lembrar" da conversa
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS mensagens (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sessao_id   TEXT NOT NULL REFERENCES sessoes(id) ON DELETE CASCADE,
  papel       TEXT NOT NULL CHECK (papel IN ('human', 'ai')),
  conteudo    TEXT NOT NULL CHECK (char_length(conteudo) <= 8000),
  criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A ordem é garantida pelo id (mensagens salvas no mesmo instante não se embaralham)
CREATE INDEX IF NOT EXISTS ix_mensagens_sessao ON mensagens (sessao_id, id);


-- ═══════════════════════════════════════════════════════════════════════
--  VIEW para o time comercial: leads com resumo da conversa
-- ═══════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW vw_leads_painel AS
SELECT
  l.id,
  l.nome,
  l.email,
  l.cargo,
  l.telefone,
  l.empresa,
  l.qtd_colaboradores,
  l.area_interesse,
  l.possui_processo,
  l.descricao_processo,
  l.urgencia,
  l.origem,
  l.status,
  l.encerramento,
  l.observacoes,
  l.criado_em,
  l.atualizado_em,
  count(DISTINCT s.id)     AS total_sessoes,
  count(m.id)              AS total_mensagens,
  max(m.criado_em)         AS ultima_mensagem_em
FROM leads l
LEFT JOIN sessoes   s ON s.lead_id   = l.id
LEFT JOIN mensagens m ON m.sessao_id = s.id
GROUP BY l.id;


-- ═══════════════════════════════════════════════════════════════════════
--  RETENÇÃO (LGPD) — rodar periodicamente, prazo a definir com o jurídico
--  Exemplo: apagar conversas sem lead com mais de 90 dias.
--  VALIDAR: confirmar o prazo antes de agendar.
-- ═══════════════════════════════════════════════════════════════════════
-- DELETE FROM sessoes
--  WHERE lead_id IS NULL
--    AND atualizado_em < now() - INTERVAL '90 days';
