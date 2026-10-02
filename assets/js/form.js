/**
 * form.js
 * Formulário de contato da landing page.
 *  - Perguntas iguais às colunas da tabela "leads" no banco
 *  - Validação ao sair do campo e no envio (texto, select, rádio e checkbox)
 *  - Máscara de telefone
 *  - Pré-seleciona a área quando o visitante escolhe um agente
 *  - Envio assíncrono (endpoint será ligado na etapa do backend)
 */

'use strict';

import { $, $$, INTEREST_EVENT } from './utils.js';

/* ── Regras: chaves = atributo "name" = coluna no banco ─────── */
const RULES = {
  nome:               { required: true,  minLength: 3, label: 'Nome' },
  cargo:              { required: true,  minLength: 2, label: 'Cargo' },
  email:              { required: true,  pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, label: 'E-mail' },
  telefone:           { required: false, pattern: /^\(\d{2}\) \d{4,5}-\d{4}$/, label: 'Telefone' },
  empresa:            { required: true,  minLength: 2, label: 'Nome da empresa' },
  qtd_colaboradores:  { required: true,  label: 'Quantidade de colaboradores' },
  area_interesse:     { required: true,  label: 'Área de interesse' },
  possui_processo:    { required: true,  label: 'Esta pergunta' },
  descricao_processo: { required: false, label: 'Descrição' },
  consentimento:      { required: true,  label: 'O consentimento' },
};

const MESSAGES = {
  required:  (label) => `${label} é obrigatório.`,
  choose:    (label) => `${label} precisa de uma resposta.`,
  consent:   () => 'Para enviar, é preciso concordar com o uso dos dados.',
  minLength: (label, n) => `${label} deve ter pelo menos ${n} caracteres.`,
  pattern:   (label) => `${label} inválido. Confira o formato.`,
};

// Área vinda do agents.js ("financeiro", "vendas", "RH", "logística") → valor do <select>
const AREA_POR_AGENTE = {
  financeiro: 'financeiro',
  vendas: 'vendas',
  rh: 'rh',
  'logística': 'logistica',
  logistica: 'logistica',
};

const form = $('#contact-form');
if (form) initForm(form);

function initForm(form) {
  const names = Object.keys(RULES);
  const inputsOf = (name) => [...form.querySelectorAll(`[name="${name}"]`)];
  const errorOf = (name) =>
    inputsOf(name)[0]?.closest('.form-group')?.querySelector('.form-error');

  /* ── Lê o valor de qualquer tipo de campo ─────────────── */
  const valueOf = (name) => {
    const inputs = inputsOf(name);
    const first = inputs[0];
    if (!first) return '';
    if (first.type === 'radio') return inputs.find((i) => i.checked)?.value ?? '';
    if (first.type === 'checkbox') return first.checked ? first.value : '';
    return first.value.trim();
  };

  /* ── Mostra/limpa erro do campo (ou do grupo de rádios) ─ */
  const setError = (name, msg = '') => {
    const inputs = inputsOf(name);
    const err = errorOf(name);

    if (err && !err.id) err.id = `${name}-erro`;

    inputs.forEach((input) => {
      input.classList.toggle('is-invalid', Boolean(msg));
      input.setAttribute('aria-invalid', msg ? 'true' : 'false');
      if (err) input.setAttribute('aria-describedby', err.id);
    });

    inputs[0]?.closest('.form-group')?.classList.toggle('has-error', Boolean(msg));
    if (err) err.textContent = msg;
  };

  /* ── Valida um campo pelo name ────────────────────────── */
  const validate = (name) => {
    const rule = RULES[name];
    const first = inputsOf(name)[0];
    if (!rule || !first) return true;

    const value = valueOf(name);
    const isChoice = first.type === 'radio' || first.tagName === 'SELECT';

    if (rule.required && !value) {
      if (first.type === 'checkbox') setError(name, MESSAGES.consent());
      else setError(name, isChoice ? MESSAGES.choose(rule.label) : MESSAGES.required(rule.label));
      return false;
    }
    if (value && rule.minLength && value.length < rule.minLength) {
      setError(name, MESSAGES.minLength(rule.label, rule.minLength));
      return false;
    }
    if (value && rule.pattern && !rule.pattern.test(value)) {
      setError(name, MESSAGES.pattern(rule.label));
      return false;
    }

    setError(name);
    return true;
  };

  /* ── Validação em tempo real ──────────────────────────── */
  names.forEach((name) => {
    inputsOf(name).forEach((input) => {
      const isToggle = input.type === 'radio' || input.type === 'checkbox' || input.tagName === 'SELECT';
      // Seleções validam ao mudar; textos, ao sair do campo
      input.addEventListener(isToggle ? 'change' : 'blur', () => validate(name));
      if (!isToggle) {
        input.addEventListener('input', () => {
          if (input.classList.contains('is-invalid')) setError(name);
        });
      }
    });
  });

  /* ── Máscara de telefone: (11) 91234-5678 ─────────────── */
  const telefone = inputsOf('telefone')[0];

  telefone?.addEventListener('input', () => {
    const digits = telefone.value.replace(/\D/g, '').slice(0, 11);
    const ddd = digits.slice(0, 2);
    const rest = digits.slice(2);

    if (digits.length <= 2) {
      telefone.value = ddd ? `(${ddd}` : '';
    } else if (rest.length <= 4) {
      telefone.value = `(${ddd}) ${rest}`;
    } else {
      const split = rest.length === 9 ? 5 : 4; // celular (9 dígitos) ou fixo (8)
      telefone.value = `(${ddd}) ${rest.slice(0, split)}-${rest.slice(split)}`;
    }
  });

  /* ── Agente escolhido → pré-seleciona a área ──────────── */
  const area = inputsOf('area_interesse')[0];

  document.addEventListener(INTEREST_EVENT, (e) => {
    const chave = String(e.detail?.area ?? '').toLowerCase();
    const valor = AREA_POR_AGENTE[chave];
    // Só preenche se o visitante ainda não escolheu nada
    if (area && valor && !area.value) {
      area.value = valor;
      setError('area_interesse');
    }
  });

  /* ── Monta o payload no formato do banco ──────────────── */
  const buildPayload = () => {
    const payload = {};
    names.forEach((name) => {
      const value = valueOf(name);
      if (value) payload[name] = value;
    });
    payload.consentimento = valueOf('consentimento') === 'sim';
    return payload;
  };

  /* ── Envio ────────────────────────────────────────────── */
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const results = names.map(validate);
    if (!results.every(Boolean)) {
      form.querySelector('.is-invalid')?.focus();
      return;
    }

    const submitBtn = form.querySelector('[type="submit"]');
    const originalLabel = submitBtn.textContent.trim();

    try {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Enviando…';

      const payload = buildPayload();

      // ── Integração ──────────────────────────────────────
      // VALIDAR: será ligado ao endpoint /api/leads na etapa do backend.
      //
      // const response = await fetch(`${API_BASE}/api/leads`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(payload),
      // });
      // if (!response.ok) throw new Error('Erro no servidor.');

      await new Promise((resolve) => setTimeout(resolve, 1200)); // simulação
      console.info('[form.js] Dados do formulário:', payload);

      showToast('Recebemos seus dados. Nosso time vai entrar em contato.', 'success');
      form.reset();
      names.forEach((name) => setError(name));
    } catch (err) {
      console.error('[form.js] Erro ao enviar:', err);
      showToast('Não foi possível enviar agora. Tente novamente ou fale com a Clara.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
  });
}

/* ── Toast de feedback ──────────────────────────────────── */
// Cores com contraste AA para texto branco
const TOAST_COLORS = { success: '#1A7A6D', error: '#CC0000' };

function showToast(message, type = 'success') {
  document.querySelector('.form-toast')?.remove();

  const toast = document.createElement('div');
  toast.className = `form-toast form-toast--${type}`;
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
  toast.textContent = message;

  Object.assign(toast.style, {
    position: 'fixed',
    bottom: '1.5rem',
    right: '1.5rem',
    maxWidth: 'min(420px, calc(100vw - 3rem))',
    padding: '1rem 1.25rem',
    borderRadius: '10px',
    fontFamily: 'inherit',
    fontSize: '0.95rem',
    fontWeight: '600',
    color: '#FFFFFF',
    background: TOAST_COLORS[type] ?? TOAST_COLORS.success,
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.2)',
    zIndex: '9999',
  });

  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 6000);
}
