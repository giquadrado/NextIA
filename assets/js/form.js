/**
 * form.js
 * Formulário de contato:
 *  - Validação ao sair do campo e no envio
 *  - Máscara de telefone
 *  - Preenchimento automático quando o visitante escolhe um agente
 *  - Envio assíncrono (endpoint ainda não configurado: ver bloco "Integração")
 */

'use strict';

import { $, $$, INTEREST_EVENT } from './utils.js';

const form = $('#contact-form');

if (form) initForm(form);

function initForm(form) {
  /* ── Regras de validação ──────────────────────────────── */
  const RULES = {
    nome:     { required: true,  minLength: 3, label: 'Nome' },
    email:    { required: true,  pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, label: 'E-mail' },
    telefone: { required: false, pattern: /^\(\d{2}\) \d{4,5}-\d{4}$/, label: 'Telefone' },
    empresa:  { required: false, label: 'Empresa' },
    desafio:  { required: true,  minLength: 10, label: 'Descrição do processo' },
  };

  const MESSAGES = {
    required:  (label) => `${label} é obrigatório.`,
    minLength: (label, n) => `${label} deve ter pelo menos ${n} caracteres.`,
    pattern:   (label) => `${label} inválido. Confira o formato.`,
  };

  /* ── Helpers ──────────────────────────────────────────── */
  const fields = [...$$('[name]', form)];
  const getField = (name) => form.querySelector(`[name="${name}"]`);
  const getError = (input) => input.closest('.form-group')?.querySelector('.form-error');

  const setError = (input, msg = '') => {
    input.classList.toggle('is-invalid', Boolean(msg));
    input.setAttribute('aria-invalid', msg ? 'true' : 'false');

    const err = getError(input);
    if (err) {
      // Liga a mensagem ao campo para leitores de tela
      if (!err.id) err.id = `${input.id}-erro`;
      input.setAttribute('aria-describedby', err.id);
      err.textContent = msg;
    }
  };

  const validateField = (input) => {
    const rule = RULES[input.name];
    if (!rule) return true;

    const value = input.value.trim();

    if (rule.required && !value) {
      setError(input, MESSAGES.required(rule.label));
      return false;
    }
    if (value && rule.minLength && value.length < rule.minLength) {
      setError(input, MESSAGES.minLength(rule.label, rule.minLength));
      return false;
    }
    if (value && rule.pattern && !rule.pattern.test(value)) {
      setError(input, MESSAGES.pattern(rule.label));
      return false;
    }

    setError(input);
    return true;
  };

  /* ── Validação em tempo real ──────────────────────────── */
  fields.forEach((field) => {
    field.addEventListener('blur', () => validateField(field));
    field.addEventListener('input', () => {
      if (field.classList.contains('is-invalid')) setError(field);
    });
  });

  /* ── Máscara de telefone: (11) 91234-5678 ─────────────── */
  const telefone = getField('telefone');

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

  /* ── Preenchimento a partir da escolha de agente ──────── */
  const desafio = getField('desafio');

  document.addEventListener(INTEREST_EVENT, (e) => {
    if (!desafio) return;
    const { agent, area, article } = e.detail ?? {};
    // Só preenche se o visitante ainda não escreveu nada
    if (!desafio.value.trim() && agent) {
      desafio.value = `Tenho interesse em um agente de ${area}, como ${article} ${agent}. `;
    }
  });

  /* ── Envio ────────────────────────────────────────────── */
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const isValid = fields.map(validateField).every(Boolean);
    if (!isValid) {
      form.querySelector('.is-invalid')?.focus();
      return;
    }

    const submitBtn = form.querySelector('[type="submit"]');
    const originalLabel = submitBtn.textContent.trim();

    try {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Enviando…';

      const payload = Object.fromEntries(new FormData(form));

      // ── Integração ──────────────────────────────────────
      // VALIDAR: o formulário ainda não envia para nenhum lugar.
      // Substitua a simulação abaixo pelo endpoint real, por exemplo:
      //
      // const response = await fetch('/api/contato', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(payload),
      // });
      // if (!response.ok) throw new Error('Erro no servidor.');

      await new Promise((resolve) => setTimeout(resolve, 1200)); // simulação
      console.info('[form.js] Dados do formulário:', payload);

      showToast('Recebemos seus dados. Nosso time vai entrar em contato.', 'success');
      form.reset();
      fields.forEach((f) => setError(f));
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
// Cores com contraste AA para texto branco:
// sucesso #1A7A6D (verde Algar escurecido), erro #CC0000
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
    left: 'auto',
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
