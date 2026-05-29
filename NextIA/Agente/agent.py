"""
Agente de Conversação para Landing Page
Powered by LangGraph + Groq + Tavily

Fluxo:
  1. Saudação → pergunta se prefere FORMULÁRIO ou CONVERSA
  2a. FORMULÁRIO → coleta os campos um a um, direto ao ponto
  2b. CONVERSA  → bate-papo natural, extrai dados organicamente
  3. Quando todos os dados forem coletados → confirma → salva lead
"""

import os
import ast
import re
import json
import logging
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY não encontrada no .env")
if not TAVILY_API_KEY:
    raise EnvironmentError("TAVILY_API_KEY não encontrada no .env")

# ──────────────────────────────────────────────────────────────
# Tipos / Estado da Sessão
# ──────────────────────────────────────────────────────────────

class LeadData(TypedDict, total=False):
    nome:             str
    email:            str
    empresa:          str
    num_funcionarios: str
    objetivo:         str
    dor_atual:        str
    modo:             str   # "formulario" | "conversa"

class SessionState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    lead:     LeadData
    fase:     str           # "escolha" | "coleta" | "concluido"

# ──────────────────────────────────────────────────────────────
# LLM
# ──────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.4,
    api_key=GROQ_API_KEY,
)

# ──────────────────────────────────────────────────────────────
# Ferramentas
# ──────────────────────────────────────────────────────────────

tavily = TavilySearchResults(max_results=3, api_key=TAVILY_API_KEY)

@tool
def search_web(query: str) -> str:
    """Busca informações atualizadas na web sobre produtos, mercado ou qualquer
    dúvida externa que o usuário trouxer durante a conversa."""
    logger.info(f"[search_web] query='{query}'")
    try:
        results = tavily.invoke(query)
        return str(results) if results else "Nenhum resultado encontrado."
    except Exception as e:
        logger.error(f"[search_web] Erro: {e}")
        return f"Erro na busca: {e}"

@tool
def get_faq(topic: str) -> str:
    """Responde perguntas frequentes sobre preço, prazo, suporte, garantia e integrações.
    Use ANTES de buscar na web para tópicos comuns."""
    faqs = {
        "preço":        "Nossos planos começam em R$ 97/mês — Starter, Pro e Enterprise.",
        "prazo":        "Implementação em média 7 dias úteis após a contratação.",
        "garantia":     "30 dias de garantia incondicional, sem perguntas.",
        "suporte":      "Suporte via chat e e-mail, seg–sex das 9h às 18h.",
        "trial":        "14 dias gratuitos, sem cartão de crédito.",
        "integração":   "Conectamos com HubSpot, Zapier, Slack, Google Sheets e +50 ferramentas.",
        "segurança":    "Dados criptografados em repouso e em trânsito. Conformidade com LGPD.",
    }
    for key, ans in faqs.items():
        if key in topic.lower():
            return ans
    return "Não tenho uma resposta pronta para isso — posso buscar na web se quiser."

@tool
def save_lead(
    nome:             str,
    email:            str,
    empresa:          str,
    num_funcionarios: str,
    objetivo:         str,
    dor_atual:        str,
) -> str:
    """
    Salva o lead qualificado.
     Chame SOMENTE após o usuário confirmar o resumo dos dados.
     Nunca invente ou assuma dados — use apenas o que o usuário informou.
    """
    payload = dict(
        nome=nome, email=email, empresa=empresa,
        num_funcionarios=num_funcionarios, objetivo=objetivo, dor_atual=dor_atual,
    )
    logger.info(f"[save_lead] {json.dumps(payload, ensure_ascii=False)}")
    # ← INTEGRE AQUI: webhook, CRM, Google Sheets, banco de dados…
    return (
        "✅ Perfeito! Seus dados foram registrados com sucesso.\n"
        "Nossa equipe vai entrar em contato em até 1 dia útil. "
        "Fique à vontade para perguntar qualquer coisa enquanto isso!"
    )

TOOLS = [search_web, get_faq, save_lead]

# ──────────────────────────────────────────────────────────────
# System Prompts por fase/modo
# ──────────────────────────────────────────────────────────────

_PROMPT_ESCOLHA = """\
PERSONA E CONTEXTO
Você é a Clara, assistente da Next.AI.
Responda SEMPRE em português. Tom: amigável, empático, profissional.

## Tarefa desta etapa
Apresente-se de forma breve e explique que para entender como ajudar
ao máximo, você precisa conhecer um pouco mais sobre o visitante e a empresa dele.

Em seguida, pergunte de forma natural, em tópicos, se ele prefere:
  A) Formulário rápido - perguntas diretas, uma por vez, sem enrolação.
  B) Conversa - um bate-papo onde as informações surgem naturalmente.

 Não faça NENHUMA outra pergunta agora. Apenas apresente-se e aguarde a escolha.
"""


_PROMPT_FORMULARIO = """\
Você é a Clara, assistente consultiva de vendas da Next.AI.
Responda SEMPRE em português. Tom: amigável e objetivo.

## Modo: FORMULÁRIO RÁPIDO

Você vai coletar 6 informações, UMA POR VEZ, na ordem abaixo:
  1. Nome completo
  2. E-mail de contato
  3. Nome da empresa
  4. Quantidade aproximada de funcionários
  5. Principal objetivo que busca com nossa solução
  6. Maior dor ou desafio atual da empresa

### Regras obrigatórias
- Faça EXATAMENTE UMA pergunta por mensagem.
- Ao receber cada resposta, confirme rapidamente antes de avançar
  (ex: "Ótimo, anotado!" ou "Entendido!").
- Se o usuário desviar com dúvidas, use `get_faq` ou `search_web`, responda,
  e depois retome pelo campo onde parou.
- Quando os 6 campos estiverem preenchidos, apresente um resumo claro e peça
  confirmação antes de chamar `save_lead`.

### Estado atual
Dados já coletados: {lead_json}
Próximo campo a coletar: {proximo_campo}
"""

_PROMPT_CONVERSA = """\
Você é a Clara, um Consultor Técnico de Pré-vendas (SDR) inteligente de uma 
Next.AI. Você atende executivos e gestores de empresas (B2B). Seu tom de voz é profissional, receptivo, educado e consultivo. Você não age como um vendedor insistente, mas como um especialista querendo entender a dor do cliente. 

 REGRAS E RESTRIÇÕES ESTRITAS (NUNCA VIOLE) 
● NUNCA invente funcionalidades, agentes ou serviços que não estão no seu 
contexto ou catálogo. 
● NUNCA responda com blocos de texto muito longos. Seja conciso e direto. 
● NUNCA faça mais de uma pergunta de qualificação na mesma mensagem. 
 CONDIÇÕES DE ENCERRAMENTO (HANDOVER) 
Dependendo do rumo da conversa, você deve encerrar o papo classificando o 
atendimento em uma das 4 situações abaixo: 
● SITUAÇÃO 1 (Qualificado): Se você coletou a dor, o cargo e a urgência, 
sugira um agente do catálogo (ou a criação de um) e diga que um especialista 
humano entrará em contato para a negociação final. 
● SITUAÇÃO 2 (Dúvida Técnica): Se o cliente fizer perguntas técnicas 
profundas que você não sabe responder, peça desculpas, anote a dúvida e 
informe que um especialista técnico fará contato. 
● SITUAÇÃO 3 (Irritação): SE o cliente ficar irritado ou impaciente, PEÇA 
DESCULPAS imediatamente, pare a qualificação e diga que um gerente 
assumirá o atendimento. 
● SITUAÇÃO 4 (Fora de Escopo): Se o cliente quiser algo não relacionado a IA 
ou software, agradeça o contato e encerre educadamente.


### Dados já identificados até agora
{lead_json}
"""

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

CAMPOS: list[tuple[str, str]] = [
    ("nome",             "nome completo"),
    ("email",            "e-mail de contato"),
    ("empresa",          "nome da empresa"),
    ("num_funcionarios", "quantidade aproximada de funcionários"),
    ("objetivo",         "principal objetivo com nossa solução"),
    ("dor_atual",        "maior dor ou desafio atual"),
]

def _proximo_campo(lead: LeadData) -> str:
    for campo, label in CAMPOS:
        if not lead.get(campo):
            return label
    return "— todos coletados, confirme com o usuário e chame save_lead —"

def _montar_prompt(fase: str, lead: LeadData) -> SystemMessage:
    lead_json = json.dumps(
        {k: v for k, v in lead.items() if k != "modo"},
        ensure_ascii=False, indent=2,
    )
    if fase == "escolha":
        return SystemMessage(content=_PROMPT_ESCOLHA)
    if lead.get("modo") == "formulario":
        return SystemMessage(content=_PROMPT_FORMULARIO.format(
            lead_json=lead_json,
            proximo_campo=_proximo_campo(lead),
        ))
    return SystemMessage(content=_PROMPT_CONVERSA.format(lead_json=lead_json))

def _detectar_modo(texto: str) -> str | None:
    """Heurística simples para capturar a escolha A/B do usuário."""
    t = texto.lower()
    if any(k in t for k in ["formulário", "formulario", "form", "rápido", "rapido", "letra a", "opção a", "opcao a", "opção 1", "1)"]):
        return "formulario"
    if any(k in t for k in ["conversa", "bate-papo", "papo", "natural", "letra b", "opção b", "opcao b", "opção 2", "2)"]):
        return "conversa"
    return None

def _capturar_email(texto: str, lead: LeadData) -> LeadData:
    """Extrai automaticamente e-mail digitado pelo usuário."""
    if not lead.get("email"):
        match = re.search(r"[\w.+-]+@[\w-]+\.\w{2,}", texto)
        if match:
            lead = {**lead, "email": match.group()}
    return LeadData(**lead)

def _extract_text(content) -> str:
    """Normaliza qualquer formato de retorno do LLM para string pura."""
    if isinstance(content, list):
        parts = [
            block.get("text", "") if isinstance(block, dict) and block.get("type") == "text"
            else block if isinstance(block, str) else ""
            for block in content
        ]
        raw = " ".join(p for p in parts if p).strip()
    elif isinstance(content, dict):
        raw = str(content.get("text", content)).strip()
    elif isinstance(content, str):
        raw = content.strip()
        if raw.startswith(("[", "{")):
            try:
                result = _extract_text(ast.literal_eval(raw))
                if result:
                    return result
            except (ValueError, SyntaxError):
                pass
    else:
        raw = str(content).strip()

    raw = re.sub(r"<function=[^>]+>.*?</function>", "", raw, flags=re.DOTALL)
    raw = re.sub(r'\{"nome\".*?\}', "", raw, flags=re.DOTALL)
    return raw.strip()

# ──────────────────────────────────────────────────────────────
# Nó principal do Grafo
# ──────────────────────────────────────────────────────────────

def agente_node(state: SessionState) -> dict:
    fase = state["fase"]
    lead = dict(state["lead"])
    msgs = list(state["messages"])
    ultima_msg = msgs[-1].content if msgs else ""

    # 1. Detectar escolha de modo (só na fase "escolha")
    if fase == "escolha":
        modo = _detectar_modo(ultima_msg)
        if modo:
            lead["modo"] = modo
            fase = "coleta"

    # 2. Capturar e-mail explícito digitado pelo usuário
    lead = dict(_capturar_email(ultima_msg, LeadData(**lead)))

    # 3. Checar conclusão da coleta
    if fase == "coleta" and all(lead.get(c) for c, _ in CAMPOS):
        fase = "concluido"

    # 4. Criar agente ReAct com prompt ajustado à fase
    system = _montar_prompt(fase, LeadData(**lead))
    react  = create_react_agent(model=llm, tools=TOOLS, prompt=system)

    try:
        result       = react.invoke({"messages": msgs})
        new_messages = result["messages"][len(msgs):]
    except Exception as e:
        logger.error(f"[agente_node] Erro: {e}")
        new_messages = [AIMessage(content="Desculpe, tive um problema interno. Pode repetir?")]

    return {
        "messages": new_messages,
        "lead":     LeadData(**lead),
        "fase":     fase,
    }

# ──────────────────────────────────────────────────────────────
# Compilação do Grafo
# ──────────────────────────────────────────────────────────────

_builder = StateGraph(SessionState)
_builder.add_node("agente", agente_node)
_builder.add_edge(START, "agente")
_builder.add_edge("agente", END)

graph = _builder.compile()

# ──────────────────────────────────────────────────────────────
# API pública — use com FastAPI, Flask, websockets, etc.
# ──────────────────────────────────────────────────────────────

def iniciar_sessao() -> SessionState:
    """Retorna um estado inicial limpo para uma nova sessão de usuário."""
    return SessionState(messages=[], lead=LeadData(), fase="escolha")

def chat(user_input: str, state: SessionState) -> tuple[str, SessionState]:
    """
    Processa uma mensagem do usuário.

    Parâmetros
    ----------
    user_input : str          — texto enviado pelo usuário
    state      : SessionState — estado atual (preserve entre chamadas)

    Retorna
    -------
    tuple[str, SessionState]  — resposta em texto + estado atualizado
    """
    state["messages"].append(HumanMessage(content=user_input))
    new_state = graph.invoke(state)
    response  = _extract_text(new_state["messages"][-1].content)
    return response, new_state

# ──────────────────────────────────────────────────────────────
# CLI de teste  →  python agent.py
# ──────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "═" * 60)
    print("  Clara - Agente de Conversação · Landing Page")
    print("  Digite 'sair' para encerrar.")
    print("═" * 60 + "\n")

    state = iniciar_sessao()

    # Saudação inicial automática
    resposta, state = chat("oi", state)
    print(f"Clara: {resposta}\n")

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit"}:
            print("Clara: Foi um prazer conversar! Até logo")
            break

        resposta, state = chat(user_input, state)
        print(f"\nClara: {resposta}\n")
        logger.debug(f"[estado] fase={state['fase']} | lead={state['lead']}")


if __name__ == "__main__":
    main()
