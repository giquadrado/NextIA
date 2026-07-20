const agentsData = {
  nina: {
    article: 'a',
    name: 'Nina',
    tagline: 'Sua assistente financeira',
    desc: 'Desenvolvemos a Nina para automatizar a rotina financeira. Integrada a ERPs e planilhas, ela concilia lançamentos, monitora fluxo de caixa e alerta desvios antes que virem problema.',
    checklist: [
      'Conciliação bancária automática',
      'Previsão de fluxo de caixa em tempo real',
      'Alertas de inadimplência e vencimentos'
    ],
    ctaText: 'Falar com a Nina',
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
    desc: 'Desenvolvemos o Léo para acelerar a pré-venda. Integrado ao CRM, ele qualifica leads, agenda reuniões e reengaja oportunidades esquecidas com base no histórico de interação.',
    checklist: [
      'Qualificação automática de leads (lead scoring)',
      'Agendamento de reuniões via WhatsApp e e-mail',
      'Reengajamento de oportunidades paradas no funil'
    ],
    ctaText: 'Falar com o Léo',
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
    desc: 'Desenvolvemos a Sofia para agilizar a triagem de candidatos. Integrada aos sistemas de recrutamento, ela analisa currículos, agenda entrevistas e organiza feedback do time.',
    checklist: [
      'Triagem de currículos por compatibilidade com a vaga',
      'Agendamento automático de entrevistas',
      'Organização de feedback dos entrevistadores'
    ],
    ctaText: 'Falar com a Sofia',
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
    desc: 'Desenvolvemos a Maya para dar visibilidade à operação logística. Integrada ao WMS e transportadoras, ela rastreia pedidos, prevê rupturas de estoque e antecipa atrasos na entrega.',
    checklist: [
      'Rastreamento de pedidos em tempo real',
      'Previsão de ruptura de estoque',
      'Alertas automáticos de atraso na entrega'
    ],
    ctaText: 'Falar com a Maya',
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
