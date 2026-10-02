"""
faq.py — Respostas que a Clara pode dar com segurança.

REGRA: aqui só entra informação confirmada pelo time.
Preço, prazo, garantia e período de teste NÃO estão aqui de propósito:
a Clara deve dizer que um especialista vai responder.

VALIDAR: revisar todas as respostas com o time antes de publicar.
Os textos seguem o FAQ da landing page (index.html → "Possui alguma dúvida?").
"""

FAQ: dict[str, dict] = {
    "sistemas": {
        "palavras": ["sistema", "trocar", "erp", "crm", "planilha", "integra", "ferramenta"],
        "resposta": (
            "Não é preciso trocar de sistema. O agente é desenhado para trabalhar com as "
            "ferramentas que a empresa já usa, e no diagnóstico avaliamos quais integrações são possíveis."
        ),
    },
    "prazo": {
        "palavras": ["prazo", "tempo", "demora", "quando fica pronto", "quanto tempo"],
        "resposta": (
            "O prazo depende do processo e das integrações envolvidas. Ele é definido no diagnóstico, "
            "e o projeto sempre começa por um piloto de escopo menor."
        ),
    },
    "autonomia": {
        "palavras": ["sozinho", "decide", "decisão", "autonomia", "aprovação", "controle"],
        "resposta": (
            "O agente só age dentro das regras combinadas com a empresa. Ações sensíveis podem "
            "exigir aprovação de uma pessoa do time, e cada ação fica registrada."
        ),
    },
    "dados": {
        "palavras": ["dado", "segurança", "seguro", "lgpd", "privacidade", "acesso"],
        "resposta": (
            "O agente acessa apenas os sistemas e dados autorizados no projeto. As regras de acesso "
            "e de tratamento de dados são definidas junto com o time da empresa."
        ),
    },
    "como_comecar": {
        "palavras": ["começar", "comecar", "contratar", "próximo passo", "proximo passo"],
        "resposta": (
            "O primeiro passo é um diagnóstico com o nosso time. Posso registrar seus dados agora "
            "para que um especialista entre em contato e agende essa conversa."
        ),
    },
    "agentes": {
        "palavras": ["agente", "nina", "léo", "leo", "sofia", "maya", "exemplo", "catálogo", "catalogo"],
        "resposta": (
            "Alguns exemplos de ponto de partida: Nina (financeiro), Léo (vendas e pré-venda), "
            "Sofia (RH e recrutamento) e Maya (logística e estoque). Cada agente é ajustado às regras "
            "e aos sistemas da empresa, e também é possível desenhar um agente para outra área."
        ),
    },
}

# Assuntos que a Clara nunca responde por conta própria
ENCAMINHAR = ["preço", "preco", "valor", "custo", "quanto custa", "plano", "garantia",
              "teste grátis", "teste gratis", "trial", "contrato", "desconto", "proposta"]

RESPOSTA_ENCAMINHAR = (
    "ENCAMINHAR: não há informação aprovada sobre isso. Diga que um especialista do time "
    "vai responder diretamente e não cite valores, prazos, garantias ou condições."
)


def buscar_resposta(pergunta: str) -> str:
    """Retorna a resposta aprovada mais adequada, ou a instrução de encaminhar."""
    texto = pergunta.lower()

    if any(p in texto for p in ENCAMINHAR):
        return RESPOSTA_ENCAMINHAR

    for item in FAQ.values():
        if any(p in texto for p in item["palavras"]):
            return item["resposta"]

    return RESPOSTA_ENCAMINHAR
