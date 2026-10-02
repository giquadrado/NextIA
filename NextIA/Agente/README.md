# Clara · Agente de atendimento da Interagente

Backend da Clara, a agente que conversa com os visitantes da landing page,
coleta os dados de contato e qualifica os leads.

## Como funciona

A cada mensagem, um grafo **LangGraph** executa três etapas:

```
START → extrair → atualizar_fase → responder → END
```

| Etapa | O que faz |
|---|---|
| `extrair` | O LLM lê a última resposta do visitante e devolve, em JSON, os dados informados. Eles são gravados no PostgreSQL na hora. |
| `atualizar_fase` | Regras em Python decidem a etapa: `escolha` → `coleta` → `concluido`. |
| `responder` | A Clara responde com o prompt da etapa atual. Ferramentas: `consultar_faq` e `registrar_encerramento`. |

O histórico e os dados vêm do banco a cada mensagem, então a Clara lembra da
conversa mesmo depois de o servidor reiniciar.

## Perguntas coletadas

As mesmas do formulário da landing page:

| Coluna | Pergunta | Obrigatória |
|---|---|---|
| `nome` | Nome | Sim |
| `email` | E-mail | Sim |
| `cargo` | Cargo | Sim |
| `telefone` | Telefone | Não |
| `empresa` | Nome da empresa | Sim |
| `qtd_colaboradores` | Quantidade de colaboradores (faixas) | Sim |
| `area_interesse` | Área de interesse em automatizar | Sim |
| `possui_processo` | Já tem algum processo? | Sim |
| `descricao_processo` | Detalhes do processo | Não |

## Estrutura

```
Agente/
├── app.py            API FastAPI
├── agent.py          Grafo LangGraph, prompts e extração
├── faq.py            Respostas aprovadas (sem preços nem prazos inventados)
├── db/
│   ├── schema.sql    Tabelas leads, sessoes, mensagens + view do painel
│   └── repositorio.py
├── testar_db.py      Teste da camada de banco
├── requirements.txt
├── Procfile          Comando de inicialização no Railway
└── .env.example
```

## Endpoints

| Método | Rota | Uso |
|---|---|---|
| POST | `/api/session/init` | Saudação ou retomada da conversa (`chat.js`) |
| POST | `/api/chat` | Mensagem do visitante (`chat.js`) |
| POST | `/api/leads` | Formulário da landing page (`form.js`) |
| GET | `/health` | Verifica API e banco |
| GET | `/api/admin/sessao/{id}` | Depuração; exige o cabeçalho `X-Admin-Token` |

## Rodando no seu computador

```bash
cd NextIA/Agente
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
cp .env.example .env            # e preencha as variáveis

python testar_db.py             # 1. testa o banco
python agent.py                 # 2. conversa com a Clara no terminal
uvicorn app:app --reload        # 3. sobe a API em http://localhost:8000
```

## Antes de publicar

- [ ] Revisar `faq.py` com o time (marcado com VALIDAR)
- [ ] Revisar a apresentação e o aviso de privacidade em `agent.py` (VALIDAR)
- [ ] Definir o prazo de retenção de dados no fim do `schema.sql`
- [ ] Configurar `ALLOWED_ORIGINS` com o domínio real da landing page
