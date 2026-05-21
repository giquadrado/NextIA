# Agente Conversacional para Landing Page

Este diretório contém o agente conversacional da landing page da **NextIA**.

O agente foi desenvolvido para atender visitantes da página inicial, qualificar leads e coletar informações importantes de forma natural ou por meio de um formulário rápido.

## Objetivo

O objetivo do agente é ajudar na conversão de visitantes em leads qualificados.

Ele permite que o usuário escolha entre dois modos de atendimento:

1. **Formulário rápido**  
   O agente faz perguntas diretas, uma por vez, para coletar os dados necessários.

2. **Conversa natural**  
   O agente conduz um bate-papo consultivo, entendendo a necessidade do visitante e extraindo as informações organicamente.

## Funcionalidades

- Saudação inicial personalizada.
- Escolha entre modo formulário ou conversa.
- Coleta de dados do lead.
- Respostas para dúvidas frequentes.
- Busca na web usando Tavily.
- Uso de LLM via Groq.
- Controle de fluxo com LangGraph.
- Estrutura preparada para integração com CRM, webhook, Google Sheets ou banco de dados.

## Dados coletados

O agente coleta os seguintes dados:

- Nome completo
- E-mail de contato
- Nome da empresa
- Quantidade aproximada de funcionários
- Principal objetivo com a solução
- Maior dor ou desafio atual da empresa

## Tecnologias utilizadas

- Python
- LangGraph
- LangChain
- Groq
- Tavily
- python-dotenv

## Estrutura sugerida

```text
NextIA/
├── README.md
├── index.html
├── ativos/
└── agente/
    ├── agent.py
    ├── README.md
    ├── requirements.txt
    ├── .env.example
    └── .gitignore
