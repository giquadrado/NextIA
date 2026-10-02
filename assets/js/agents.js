/**
 * agents.js
 * Vitrine de agentes:
 *  - Troca o painel "Simulação de uso" ao selecionar um card
 *  - Atalhos abaixo do hero selecionam o agente e rolam até a simulação
 *  - CTAs de interesse avisam o formulário qual agente foi escolhido
 *
 * Os textos de conversa são ILUSTRATIVOS (o HTML exibe esse aviso no chat).
 */

'use strict';

import { $, $$, prefersReducedMotion, scrollToElement, INTEREST_EVENT } from './utils.js';

const agentsData = {
  nina: {
    article: 'a',
    name: 'Nina',
    area: 'financeiro',
    tagline: 'Sua assistente financeira',
    desc: 'Integrada ao seu ERP e às suas planilhas, ela concilia lançamentos, acompanha o fluxo de caixa e avisa sobre desvios antes que virem problema.',
    checklist: [
      'Conciliação bancária diária',
      'Acompanhamento do fluxo de caixa',
      'Alertas de vencimento e inadimplência',
    ],
    ctaText: 'Quero um agente financeiro',
    protocol: 'Protocolo #4432',
    status: 'Analisando contas a receber',
    msg1: 'Identifiquei 3 faturas que vencem nos próximos 2 dias com histórico de atraso. Quer que eu envie o lembrete de cobrança?',
    msg2: 'Sim, Nina. Comece pelos clientes com mais atrasos.',
    msg3: 'Combinado. Enviando os lembretes e registrando cada envio.',
  },
  leo: {
    article: 'o',
    name: 'Léo',
    area: 'vendas',
    tagline: 'Seu assistente de pré-venda',
    desc: 'Integrado ao seu CRM, ele qualifica leads, agenda reuniões e retoma oportunidades que ficariam esquecidas no funil.',
    checklist: [
      'Qualificação de leads com critérios do seu time',
      'Agendamento de reuniões por WhatsApp e e-mail',
      'Retomada de oportunidades paradas',
    ],
    ctaText: 'Quero um agente de vendas',
    protocol: 'Protocolo #7715',
    status: 'Monitorando o funil',
    msg1: 'Encontrei 8 leads qualificados sem contato há mais de 5 dias. Quer que eu retome a conversa com eles?',
    msg2: 'Sim, Léo. Priorize os de maior potencial.',
    msg3: 'Combinado. Enviando mensagens e oferecendo horários na agenda do time.',
  },
  sofia: {
    article: 'a',
    name: 'Sofia',
    area: 'RH',
    tagline: 'Sua assistente de recrutamento',
    desc: 'Ela analisa currículos com os critérios da vaga, agenda entrevistas e organiza o feedback do time em um só lugar.',
    checklist: [
      'Triagem de currículos por critérios da vaga',
      'Agendamento de entrevistas',
      'Feedback dos entrevistadores organizado',
    ],
    ctaText: 'Quero um agente de RH',
    protocol: 'Protocolo #2290',
    status: 'Triagem em andamento',
    msg1: 'Analisei os currículos da vaga de Analista de Dados. 9 atendem a todos os requisitos obrigatórios.',
    msg2: 'Ótimo, Sofia. Proponha horários de entrevista para esta semana.',
    msg3: 'Combinado. Enviando convites com os horários livres da gestora.',
  },
  maya: {
    article: 'a',
    name: 'Maya',
    area: 'logística',
    tagline: 'Sua assistente de logística',
    desc: 'Ela acompanha pedidos, sinaliza risco de ruptura de estoque e avisa sobre atrasos antes que cheguem ao seu cliente.',
    checklist: [
      'Acompanhamento de pedidos',
      'Alerta de risco de ruptura de estoque',
      'Aviso antecipado de atrasos na entrega',
    ],
    ctaText: 'Quero um agente de logística',
    protocol: 'Protocolo #5561',
    status: 'Monitorando estoque',
    msg1: 'O item Filtro X200 pode acabar em 3 dias no ritmo atual de saída. Quer que eu prepare um pedido de reposição?',
    msg2: 'Sim, Maya. Mande para aprovação do comprador.',
    msg3: 'Combinado. Pedido enviado para aprovação.',
  },
};

/* ── Elementos ───────────────────────────────────────────── */
const cards     = $$('.agent-card');
const shortcuts = $$('[data-agent-link]');
const panel     = $('.agent-detail__panel');
const chat      = $('.agent-detail__chat');
const detailCta = $('#agent-detail-cta');
const detailSection = $('#agent-detail-section');

let currentAgent = 'nina';

const setText = (id, value) => {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

/* ── Renderização do painel ──────────────────────────────── */
const renderAgentDetail = (agentId) => {
  const data = agentsData[agentId];
  if (!data) return;

  setText('agent-detail-article', data.article);
  setText('agent-detail-name', data.name);
  setText('agent-detail-tagline', data.tagline);
  setText('agent-detail-desc', data.desc);
  setText('agent-detail-cta', data.ctaText);
  setText('agent-detail-avatar', data.name.charAt(0)); // inicial no lugar de emoji
  setText('agent-detail-protocol', data.protocol);
  setText('agent-detail-status', data.status);
  setText('agent-detail-msg1', data.msg1);
  setText('agent-detail-msg2', data.msg2);
  setText('agent-detail-msg3', data.msg3);

  // Checklist montada com textContent (sem innerHTML); o ícone vem do CSS
  const checklist = document.getElementById('agent-detail-checklist');
  if (checklist) {
    checklist.replaceChildren(
      ...data.checklist.map((item) => {
        const li = document.createElement('li');
        li.textContent = item;
        return li;
      })
    );
  }
};

/* ── Seleção de agente ───────────────────────────────────── */
const updateCardsState = (agentId) => {
  cards.forEach((card) => {
    const isActive = card.dataset.agent === agentId;
    card.classList.toggle('is-active', isActive);
    card.querySelector('.agent-card__select')?.setAttribute('aria-pressed', String(isActive));
  });
};

const selectAgent = (agentId) => {
  if (!agentsData[agentId] || agentId === currentAgent) return;
  currentAgent = agentId;
  updateCardsState(agentId);

  // Sem animação: troca direto
  if (prefersReducedMotion() || !panel || !chat) {
    renderAgentDetail(agentId);
    return;
  }

  panel.classList.add('is-updating');
  chat.classList.add('is-updating');

  setTimeout(() => {
    renderAgentDetail(agentId);
    panel.classList.remove('is-updating');
    chat.classList.remove('is-updating');
  }, 150); // combina com a transição de opacity no CSS
};

/* ── Interesse → formulário ──────────────────────────────── */
const announceInterest = (agentId) => {
  const data = agentsData[agentId];
  if (!data) return;
  document.dispatchEvent(new CustomEvent(INTEREST_EVENT, {
    detail: { agent: data.name, area: data.area, article: data.article },
  }));
};

/* ── Eventos ─────────────────────────────────────────────── */
cards.forEach((card) => {
  const agentId = card.dataset.agent;

  // Botão "Ver X em ação": seleciona e leva à simulação
  card.querySelector('.agent-card__select')?.addEventListener('click', () => {
    selectAgent(agentId);
    scrollToElement(detailSection);
  });

  // Link "Quero X": seleciona e avisa o formulário (a âncora #contato faz a rolagem)
  card.querySelector('a[href="#contato"]')?.addEventListener('click', () => {
    selectAgent(agentId);
    announceInterest(agentId);
  });
});

// Atalhos abaixo do hero
shortcuts.forEach((shortcut) => {
  shortcut.addEventListener('click', (e) => {
    e.preventDefault();
    selectAgent(shortcut.dataset.agentLink);
    scrollToElement(detailSection);
  });
});

// CTA do painel de simulação
detailCta?.addEventListener('click', () => {
  announceInterest(currentAgent);
  scrollToElement('#contato');
});

/* ── Estado inicial ──────────────────────────────────────── */
updateCardsState(currentAgent);
renderAgentDetail(currentAgent);
