"""
agent.py — Clara, agente de atendimento da Interagente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Grafo LangGraph executado a cada mensagem do visitante:

    START → extrair → atualizar_fase → responder → END

  • extrair         lê a última resposta do visitante e devolve, em JSON, os dados
                    que ele informou (nome, cargo, área...). Grava no PostgreSQL.
  • atualizar_fase  decide a etapa da conversa (escolha → coleta → concluido)
                    com regras em Python, sem depender do LLM.
  • responder       gera a resposta da Clara com o prompt da fase atual.

O estado completo vem do banco a cada mensagem (API stateless), então a Clara
"lembra" da conversa mesmo após reinícios do servidor.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

import faq
from db import repositorio as repo

load_dotenv()
logger = logging.getLogger("clara.agent")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CONSENTIMENTO_VERSAO = os.getenv("CONSENTIMENTO_VERSAO", "v1-2026-10")

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY não encontrada. Configure no .env ou no Railway.")

# Temperatura baixa na extração (precisão) e moderada na conversa (naturalidade)
llm_conversa = ChatGroq(model=GROQ_MODEL, temperature=0.4, api_key=GROQ_API_KEY)
llm_extracao = ChatGroq(model=GROQ_MODEL, temperature=0, api_key=GROQ_API_KEY)


# ══════════════════════════════════════════════════════════════════════════════
#  Perguntas — mesma ordem e mesmo conteúdo do formulário da landing page
# ══════════════════════════════════════════════════════════════════════════════

# (coluna no banco, como a Clara pergunta)
PERGUNTAS_OBRIGATORIAS: list[tuple[str, str]] = [
    ("nome",              "Qual é o seu nome?"),
    ("email",             "Qual é o seu e-mail?"),
    ("cargo",             "Qual é o seu cargo?"),
    ("empresa",           "Qual é o nome da empresa?"),
    ("qtd_colaboradores", "Quantos colaboradores a empresa tem, aproximadamente?"),
    ("area_interesse",    "Qual área vocês têm interesse em automatizar? (financeiro, vendas, RH, logística, atendimento ou outra)"),
    ("possui_processo",   "Já existe algum processo para essa área? Pode ser um processo definido, algo manual ou informal, ou ainda nada."),
]
OPCIONAIS = ("telefone", "descricao_processo")

ROTULOS = {
    "nome": "Nome", "email": "E-mail", "cargo": "Cargo", "telefone": "Telefone",
    "empresa": "Empresa", "qtd_colaboradores": "Colaboradores",
    "area_interesse": "Área de interesse", "possui_processo": "Processo atual",
    "descricao_processo": "Sobre o processo", "urgencia": "Urgência",
}

TEXTO_OPCOES = {
    "qtd_colaboradores": {"1-10": "1 a 10", "11-50": "11 a 50", "51-200": "51 a 200",
                          "201-500": "201 a 500", "501-1000": "501 a 1.000", "1000+": "mais de 1.000"},
    "area_interesse": {"financeiro": "Financeiro", "vendas": "Vendas e pré-venda", "rh": "RH e recrutamento",
                       "logistica": "Logística e estoque", "atendimento": "Atendimento ao cliente", "outra": "Outra área"},
    "possui_processo": {"definido": "Sim, definido", "informal": "Sim, manual ou informal", "nao": "Ainda não"},
}


# ══════════════════════════════════════════════════════════════════════════════
#  Estado do grafo
# ══════════════════════════════════════════════════════════════════════════════

class EstadoClara(TypedDict):
    sessao_id: str
    messages: Annotated[list[BaseMessage], add_messages]
    lead: dict                  # dados já salvos no banco
    fase: str                   # escolha | coleta | concluido
    modo: Optional[str]         # formulario | conversa
    extraido: dict              # o que foi extraído nesta mensagem
    resposta: str               # texto final da Clara


# ══════════════════════════════════════════════════════════════════════════════
#  Extração estruturada
# ══════════════════════════════════════════════════════════════════════════════

class DadosExtraidos(BaseModel):
    """Dados que o VISITANTE informou na última mensagem. Deixe null o que não foi dito."""

    escolha_modo: Optional[Literal["formulario", "conversa"]] = Field(
        None, description="Se o visitante escolheu formulário rápido (A) ou conversa (B).")
    nome: Optional[str] = Field(None, description="Nome da pessoa.")
    email: Optional[str] = Field(None, description="E-mail da pessoa.")
    cargo: Optional[str] = Field(None, description="Cargo ou função na empresa.")
    telefone: Optional[str] = Field(None, description="Telefone ou WhatsApp.")
    empresa: Optional[str] = Field(None, description="Nome da empresa.")
    qtd_colaboradores: Optional[str] = Field(
        None, description="Quantidade de colaboradores como o visitante disse (ex.: '50', 'uns 300', '11-50').")
    area_interesse: Optional[Literal["financeiro", "vendas", "rh", "logistica", "atendimento", "outra"]] = Field(
        None, description="Área que quer automatizar. comercial/pré-venda=vendas; recursos humanos=rh; "
                          "estoque/entregas=logistica; suporte/SAC=atendimento; qualquer outra=outra.")
    possui_processo: Optional[Literal["definido", "informal", "nao"]] = Field(
        None, description="definido=processo documentado; informal=existe mas é manual/informal; nao=não existe.")
    descricao_processo: Optional[str] = Field(None, description="Detalhes sobre como o processo funciona hoje.")
    urgencia: Optional[str] = Field(None, description="Quando precisa da solução (ex.: 'este mês', 'sem pressa').")
    confirmou_resumo: Optional[bool] = Field(
        None, description="true somente se a Clara mostrou um resumo dos dados e o visitante confirmou que está correto.")


_PROMPT_EXTRACAO = """\
Você extrai dados de uma conversa de atendimento.
Considere SOMENTE o que o VISITANTE afirmou na última mensagem dele.
A pergunta anterior da Clara serve apenas para entender a resposta
(ex.: se a Clara perguntou o cargo e ele respondeu "Diretor", cargo = "Diretor").
Nunca invente nem complete dados. Se algo não foi dito, deixe null.
"""

_extrator = llm_extracao.with_structured_output(DadosExtraidos)


def _faixa_colaboradores(valor: str | None) -> str | None:
    """Converte '50', 'uns 300 funcionários', 'mais de mil' em uma das faixas do banco."""
    if not valor:
        return None
    texto = valor.lower().replace(".", "").strip()
    if texto in TEXTO_OPCOES["qtd_colaboradores"]:
        return texto
    if "mil" in texto and not re.search(r"\d", texto):
        return "1000+"
    numeros = [int(n) for n in re.findall(r"\d+", texto)]
    if not numeros:
        return None
    n = max(numeros)
    if "mil" in texto and n < 100:
        n *= 1000
    for limite, faixa in ((10, "1-10"), (50, "11-50"), (200, "51-200"), (500, "201-500"), (1000, "501-1000")):
        if n <= limite:
            return faixa
    return "1000+"


def _email_valido(valor: str | None) -> str | None:
    if valor and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]{2,}", valor.strip()):
        return valor.strip().lower()
    return None


def extrair_dados(ultima_pergunta: str, mensagem_usuario: str) -> dict:
    """Chama o LLM em modo estruturado e normaliza o resultado."""
    try:
        dados: DadosExtraidos = _extrator.invoke([
            SystemMessage(content=_PROMPT_EXTRACAO),
            HumanMessage(content=f"Última pergunta da Clara:\n{ultima_pergunta or '(nenhuma)'}\n\n"
                                 f"Última mensagem do visitante:\n{mensagem_usuario}"),
        ])
    except Exception as exc:  # extração falhou → a conversa continua sem salvar nada
        logger.warning("Extração falhou: %s", exc)
        return {}

    resultado = {k: v for k, v in dados.model_dump().items() if v not in (None, "")}
    if "qtd_colaboradores" in resultado:
        faixa = _faixa_colaboradores(resultado["qtd_colaboradores"])
        resultado["qtd_colaboradores"] = faixa
    if "email" in resultado:
        resultado["email"] = _email_valido(resultado["email"])
    return {k: v for k, v in resultado.items() if v not in (None, "")}


# ══════════════════════════════════════════════════════════════════════════════
#  Prompts da Clara
# ══════════════════════════════════════════════════════════════════════════════

# VALIDAR: apresentação da Interagente e texto do aviso de privacidade
_PERSONA = """\
Você é a Clara, agente de atendimento da Interagente, solução de agentes de IA do Grupo Algar.
Responda sempre em português do Brasil, com tom cordial, profissional e consultivo.

REGRAS QUE VOCÊ NUNCA QUEBRA
- Mensagens curtas: no máximo 3 frases curtas, e no máximo UMA pergunta por mensagem.
- Nunca invente preços, prazos, garantias, testes grátis, integrações ou funcionalidades.
  Para dúvidas sobre a Interagente, use a ferramenta consultar_faq. Se ela mandar ENCAMINHAR,
  diga que um especialista do time vai responder diretamente.
- Nunca peça um dado que já está em "Dados já coletados".
- Exemplos de agentes: Nina (financeiro), Léo (vendas), Sofia (RH), Maya (logística).
  Também é possível desenhar um agente para outra área. Não cite outros agentes.
"""

_PROMPT_ESCOLHA = _PERSONA + """
ETAPA: boas-vindas.
Apresente-se em uma frase. Diga que, para entender como ajudar, vai fazer algumas perguntas
sobre a pessoa e a empresa, e que os dados serão usados apenas para o contato do nosso time,
conforme a política de privacidade.
Depois pergunte, em duas linhas, como ela prefere seguir:
A) Formulário rápido, com perguntas diretas
B) Conversa, em um bate-papo mais livre
Não faça nenhuma outra pergunta.
"""

_PROMPT_FORMULARIO = _PERSONA + """
ETAPA: coleta em modo FORMULÁRIO RÁPIDO.
Confirme a resposta anterior em poucas palavras ("Anotado!") e faça a próxima pergunta,
exatamente com este sentido:

PRÓXIMA PERGUNTA: {proxima_pergunta}

Se o visitante fizer uma pergunta no meio, responda (consultar_faq) e depois retome a próxima pergunta.

Dados já coletados:
{dados}
"""

_PROMPT_CONVERSA = _PERSONA + """
ETAPA: coleta em modo CONVERSA.
Converse de forma consultiva para entender o negócio e a necessidade. Ao longo da conversa,
obtenha naturalmente os dados que faltam, um por vez, sem parecer um questionário.
Também vale entender a urgência (quando a pessoa precisa da solução).

Dados que ainda faltam: {faltando}
Sugestão de próximo dado a buscar: {proxima_pergunta}

ENCERRAMENTOS ESPECIAIS (use a ferramenta registrar_encerramento):
- duvida_tecnica: pergunta técnica profunda que você não sabe responder. Anote a dúvida
  em "observacao" e diga que um especialista técnico fará contato.
- irritacao: se a pessoa ficar irritada ou impaciente, peça desculpas, pare as perguntas
  e diga que alguém do time vai assumir o atendimento.
- fora_escopo: se a pessoa quiser algo sem relação com IA ou automação, agradeça e encerre.

Dados já coletados:
{dados}
"""

_PROMPT_CONFIRMACAO = _PERSONA + """
ETAPA: confirmação.
Todos os dados obrigatórios foram coletados. Mostre o resumo abaixo exatamente como está,
em lista, e pergunte se está tudo certo. Se ainda faltar telefone ou detalhes do processo,
diga em uma frase que a pessoa pode acrescentar, se quiser.
Se o visitante corrigir algum dado, agradeça e mostre o resumo atualizado.

RESUMO:
{resumo}
"""

_PROMPT_CONCLUIDO = _PERSONA + """
ETAPA: atendimento concluído.
Os dados já foram registrados e um especialista do time vai entrar em contato.
Responda dúvidas de forma breve (consultar_faq) e não peça mais dados.
Se for a primeira mensagem desta etapa, agradeça e confirme o próximo passo.
"""


def _faltando(lead: dict) -> list[tuple[str, str]]:
    return [(campo, pergunta) for campo, pergunta in PERGUNTAS_OBRIGATORIAS if not lead.get(campo)]


def _formatar_dados(lead: dict) -> str:
    linhas = []
    for campo, rotulo in ROTULOS.items():
        valor = lead.get(campo)
        if valor:
            valor = TEXTO_OPCOES.get(campo, {}).get(valor, valor)
            linhas.append(f"- {rotulo}: {valor}")
    return "\n".join(linhas) or "(nenhum ainda)"


def _montar_prompt(estado: EstadoClara) -> str:
    fase, lead = estado["fase"], estado["lead"]
    faltando = _faltando(lead)

    if fase == "escolha":
        return _PROMPT_ESCOLHA
    if fase == "concluido":
        return _PROMPT_CONCLUIDO
    if not faltando:
        return _PROMPT_CONFIRMACAO.format(resumo=_formatar_dados(lead))

    proxima = faltando[0][1]
    if estado["modo"] == "formulario":
        return _PROMPT_FORMULARIO.format(proxima_pergunta=proxima, dados=_formatar_dados(lead))
    return _PROMPT_CONVERSA.format(
        faltando=", ".join(ROTULOS[c] for c, _ in faltando),
        proxima_pergunta=proxima,
        dados=_formatar_dados(lead),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Ferramentas da Clara (criadas por sessão, para saber onde gravar)
# ══════════════════════════════════════════════════════════════════════════════

def _ferramentas(sessao_id: str) -> list:

    @tool
    def consultar_faq(pergunta: str) -> str:
        """Consulta as respostas aprovadas sobre a Interagente (sistemas, prazos de projeto,
        dados, autonomia do agente, como começar, exemplos de agentes). Use antes de responder
        qualquer dúvida sobre a empresa ou o serviço."""
        return faq.buscar_resposta(pergunta)

    @tool
    def registrar_encerramento(
        situacao: Literal["duvida_tecnica", "irritacao", "fora_escopo"],
        observacao: str = "",
    ) -> str:
        """Registra que o atendimento foi encerrado e repassado ao time humano.
        situacao: duvida_tecnica | irritacao | fora_escopo.
        observacao: resumo curto do motivo (ex.: a dúvida técnica feita)."""
        repo.encerrar_atendimento(sessao_id, situacao, observacao or None)
        logger.info("Encerramento | sessao=%s | %s", sessao_id, situacao)
        return "Registrado. Informe ao visitante o próximo passo, sem pedir mais dados."

    return [consultar_faq, registrar_encerramento]


# ══════════════════════════════════════════════════════════════════════════════
#  Nós do grafo
# ══════════════════════════════════════════════════════════════════════════════

def _ultima(mensagens: list[BaseMessage], tipo) -> str:
    for msg in reversed(mensagens):
        if isinstance(msg, tipo):
            return _texto(msg.content)
    return ""


def no_extrair(estado: EstadoClara) -> dict:
    mensagens = estado["messages"]
    if not mensagens or not isinstance(mensagens[-1], HumanMessage):
        return {"extraido": {}}  # saudação inicial: nada a extrair

    pergunta = _ultima(mensagens[:-1], AIMessage)
    extraido = extrair_dados(pergunta, _texto(mensagens[-1].content))

    campos_lead = {k: v for k, v in extraido.items() if k in repo.CAMPOS_LEAD}
    lead = estado["lead"]
    if campos_lead:
        lead = repo.salvar_dados_do_chat(estado["sessao_id"], campos_lead) or lead

    logger.info("Extraído | sessao=%s | campos=%s", estado["sessao_id"], sorted(extraido))
    return {"extraido": extraido, "lead": dict(lead or {})}


def no_atualizar_fase(estado: EstadoClara) -> dict:
    fase, modo = estado["fase"], estado["modo"]
    extraido, lead = estado["extraido"], estado["lead"]
    sessao_id = estado["sessao_id"]

    # 1. Escolha do modo. Seguir a conversa após o aviso conta como aceite.
    #    VALIDAR com o jurídico se esse aceite é suficiente.
    if fase == "escolha" and (extraido.get("escolha_modo") or len(extraido) > 0):
        modo = extraido.get("escolha_modo") or "conversa"
        fase = "coleta"
        repo.registrar_consentimento_sessao(sessao_id, CONSENTIMENTO_VERSAO)

    # 2. Confirmação do resumo → lead qualificado
    if fase == "coleta" and not _faltando(lead) and extraido.get("confirmou_resumo") is True:
        lead = repo.encerrar_atendimento(sessao_id, "qualificado") or lead
        fase = "concluido"

    if (fase, modo) != (estado["fase"], estado["modo"]):
        repo.atualizar_sessao(sessao_id, fase=fase, modo=modo)
        logger.info("Fase | sessao=%s | %s → %s | modo=%s", sessao_id, estado["fase"], fase, modo)

    return {"fase": fase, "modo": modo, "lead": dict(lead or {})}


def no_responder(estado: EstadoClara) -> dict:
    agente = create_agent(
        model=llm_conversa,
        tools=_ferramentas(estado["sessao_id"]),
        system_prompt=_montar_prompt(estado),
    )
    try:
        resultado = agente.invoke({"messages": estado["messages"]})
        resposta = _texto(resultado["messages"][-1].content)
    except Exception as exc:
        logger.exception("Erro ao gerar resposta: %s", exc)
        resposta = ""

    if not resposta:
        resposta = "Desculpe, tive um problema para responder agora. Pode repetir, por favor?"

    # Se uma ferramenta encerrou o atendimento, a fase no banco já mudou
    sessao = repo.obter_ou_criar_sessao(estado["sessao_id"])
    return {"resposta": resposta, "fase": sessao["fase"], "messages": [AIMessage(content=resposta)]}


# ══════════════════════════════════════════════════════════════════════════════
#  Grafo
# ══════════════════════════════════════════════════════════════════════════════

_builder = StateGraph(EstadoClara)
_builder.add_node("extrair", no_extrair)
_builder.add_node("atualizar_fase", no_atualizar_fase)
_builder.add_node("responder", no_responder)
_builder.add_edge(START, "extrair")
_builder.add_edge("extrair", "atualizar_fase")
_builder.add_edge("atualizar_fase", "responder")
_builder.add_edge("responder", END)

grafo = _builder.compile()


# ══════════════════════════════════════════════════════════════════════════════
#  Utilitários e API pública (usada pelo app.py)
# ══════════════════════════════════════════════════════════════════════════════

def _texto(conteudo) -> str:
    """Normaliza o retorno do LLM (string ou lista de blocos) para texto puro."""
    if isinstance(conteudo, list):
        partes = [b.get("text", "") if isinstance(b, dict) else str(b) for b in conteudo]
        conteudo = " ".join(p for p in partes if p)
    texto = str(conteudo or "")
    # Remove marcações de chamada de função que alguns modelos deixam vazar no texto
    texto = re.sub(r"<function=[^>]+>.*?</function>", "", texto, flags=re.DOTALL)
    return texto.strip()


def _historico(sessao_id: str) -> list[BaseMessage]:
    return [
        HumanMessage(content=m["conteudo"]) if m["papel"] == "human" else AIMessage(content=m["conteudo"])
        for m in repo.carregar_mensagens(sessao_id)
    ]


def processar_mensagem(sessao_id: str, mensagem: Optional[str]) -> dict:
    """
    Processa uma mensagem do visitante (ou gera a saudação, se mensagem=None)
    e grava tudo no banco. Retorna {"resposta", "fase", "lead"}.
    """
    sessao = repo.obter_ou_criar_sessao(sessao_id)
    mensagens = _historico(sessao_id)
    if mensagem:
        mensagens.append(HumanMessage(content=mensagem))

    estado_inicial: EstadoClara = {
        "sessao_id": sessao_id,
        "messages": mensagens,
        "lead": dict(repo.obter_lead_da_sessao(sessao_id) or {}),
        "fase": sessao["fase"],
        "modo": sessao["modo"],
        "extraido": {},
        "resposta": "",
    }

    final = grafo.invoke(estado_inicial)

    novas = [("human", mensagem)] if mensagem else []
    novas.append(("ai", final["resposta"]))
    repo.salvar_mensagens(sessao_id, novas)

    return {"resposta": final["resposta"], "fase": final["fase"], "lead": final["lead"]}


def historico_publico(sessao_id: str) -> list[dict]:
    """Histórico no formato do chat.js (papel 'user' | 'ai')."""
    return [
        {"role": "user" if m["papel"] == "human" else "ai", "content": m["conteudo"]}
        for m in repo.carregar_mensagens(sessao_id)
    ]


# ── Teste rápido no terminal:  python agent.py ─────────────────────────────────
if __name__ == "__main__":
    import uuid

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    repo.abrir_pool()
    repo.aplicar_schema()
    sid = f"cli-{uuid.uuid4()}"
    print("\nClara (digite 'sair' para encerrar)\n")
    print("Clara:", processar_mensagem(sid, None)["resposta"], "\n")
    try:
        while (texto := input("Você: ").strip()).lower() != "sair":
            if texto:
                r = processar_mensagem(sid, texto)
                print(f"\nClara: {r['resposta']}\n   [fase={r['fase']}]\n")
    finally:
        repo.fechar_pool()
