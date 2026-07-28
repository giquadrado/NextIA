const agentsData = {
  nina: {
    article: 'a',
    name: 'Nina',
    tagline: 'Sua assistente financeira',
    desc: 'Imagine um agente assim dentro da sua rotina financeira: integrado ao seu ERP e às suas planilhas, conciliando lançamentos, acompanhando o fluxo de caixa e alertando desvios antes que virem problema. É esse tipo de solução que construímos sob medida pra sua empresa.',
    checklist: [
      'Conciliação bancária automática',
      'Previsão de fluxo de caixa em tempo real',
      'Alertas de inadimplência e vencimentos'
    ],
    ctaText: 'Criar meu agente financeiro',
    avatar: '💰',
    protocol: 'Protocolo #4432',
    status: 'Processamento ativo...',
    msg1: 'Olá, identifiquei 3 faturas vencendo nos próximos 2 dias com risco de atraso. Deseja que eu dispare a régua de cobrança?',
    msg2: 'Sim, Nina. Priorize clientes com histórico de atraso.',
    msg3: 'Entendido. 12 clientes selecionados. Iniciando régua de cobrança...'
  },
  leo: {
    article: 'o',
    name: 'Léo',
    tagline: 'Seu assistente de vendas',
    desc: 'Imagine um agente assim cuidando da sua pré-venda: integrado ao seu CRM, qualificando leads, agendando reuniões e reengajando oportunidades que ficariam esquecidas no funil. Podemos construir esse agente pra sua operação de vendas.',
    checklist: [
      'Qualificação automática de leads (lead scoring)',
      'Agendamento de reuniões via WhatsApp e e-mail',
      'Reengajamento de oportunidades paradas no funil'
    ],
    ctaText: 'Criar meu agente de vendas',
    avatar: '📈',
    protocol: 'Protocolo #7715',
    status: 'Monitorando funil...',
    msg1: 'Olá, encontrei 8 leads quentes sem contato há mais de 5 dias. Deseja que eu inicie o reengajamento?',
    msg2: 'Sim, Léo. Priorize os leads de ticket alto.',
    msg3: 'Entendido. 5 leads selecionados. Agendando follow-ups...'
  },
  sofia: {
    article: 'a',
    name: 'Sofia',
    tagline: 'Sua assistente de recrutamento',
    desc: 'Imagine um agente assim agilizando o seu recrutamento: analisando currículos, agendando entrevistas e organizando o feedback do time em um só lugar. É esse tipo de agente que construímos sob medida pra sua área de RH.',
    checklist: [
      'Triagem de currículos por compatibilidade com a vaga',
      'Agendamento automático de entrevistas',
      'Organização de feedback dos entrevistadores'
    ],
    ctaText: 'Criar meu agente de RH',
    avatar: '🧑‍💼',
    protocol: 'Protocolo #2290',
    status: 'Triagem em andamento...',
    msg1: 'Olá, analisei 64 currículos para a vaga de Analista de Dados. 9 têm alta compatibilidade.',
    msg2: 'Ótimo, Sofia. Agende entrevistas com os 9 para essa semana.',
    msg3: 'Entendido. Enviando convites de entrevista...'
  },
  maya: {
    article: 'a',
    name: 'Maya',
    tagline: 'Sua assistente de logística',
    desc: 'Imagine um agente assim monitorando sua logística: rastreando pedidos, antecipando rupturas de estoque e sinalizando atrasos antes que cheguem ao seu cliente. Podemos construir esse agente pra sua operação.',
    checklist: [
      'Rastreamento de pedidos em tempo real',
      'Previsão de ruptura de estoque',
      'Alertas automáticos de atraso na entrega'
    ],
    ctaText: 'Criar meu agente de logística',
    avatar: '📦',
    protocol: 'Protocolo #5561',
    status: 'Monitorando rotas...',
    msg1: "Olá, identifiquei risco de ruptura no SKU 'Filtro X200' em 3 dias.",
    msg2: 'Entendido, Maya. Acione o fornecedor backup.',
    msg3: 'Entendido. Pedido de reposição emitido ao fornecedor B...'
  }
};

function renderAgentDetail(agentId) {
  const data = agentsData[agentId];
  if (!data) return;

  document.getElementById('agent-detail-article').textContent = data.article;
  document.getElementById('agent-detail-name').textContent = data.name;
  document.getElementById('agent-detail-tagline').textContent = data.tagline;
  document.getElementById('agent-detail-desc').textContent = data.desc;
  document.getElementById('agent-detail-cta').textContent = data.ctaText;
  document.getElementById('agent-detail-avatar').textContent = data.avatar;
  document.getElementById('agent-detail-protocol').textContent = data.protocol;
  document.getElementById('agent-detail-status').textContent = data.status;
  document.getElementById('agent-detail-msg1').textContent = data.msg1;
  document.getElementById('agent-detail-msg2').textContent = data.msg2;
  document.getElementById('agent-detail-msg3').textContent = data.msg3;

  const checklistEl = document.getElementById('agent-detail-checklist');
  checklistEl.innerHTML = data.checklist
    .map(item => `<li>✅ ${item}</li>`)
    .join('');
}

function initAgentsShowcase() {
  const cards = document.querySelectorAll('.agent-card');
  const panel = document.querySelector('.agent-detail__panel');
  const chat = document.querySelector('.agent-detail__chat');

  cards.forEach(card => {
    card.addEventListener('click', () => {
      if (card.classList.contains('is-active')) return;

      cards.forEach(c => c.classList.remove('is-active'));
      card.classList.add('is-active');

      panel.classList.add('is-updating');
      chat.classList.add('is-updating');

      setTimeout(() => {
        renderAgentDetail(card.dataset.agent);
        panel.classList.remove('is-updating');
        chat.classList.remove('is-updating');
      }, 150); // combina com a transição de opacity no CSS
    });
  });

  // render inicial (Nina, já marcada como is-active no HTML)
  renderAgentDetail('nina');
}

document.addEventListener('DOMContentLoaded', initAgentsShowcase);
