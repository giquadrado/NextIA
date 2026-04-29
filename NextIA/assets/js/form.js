/**
 * form.js
 * Validação do formulário de contato.
 *  - Validação em tempo real (blur) e no submit
 *  - Feedback visual via classes e mensagens de erro
 *  - Envio assíncrono (pronto para integrar com backend / API)
 */

'use strict';

import { $, $$ } from './utils.js';

const form = $('#contact-form');

if (!form) {
  // Sai silenciosamente se o formulário não existir na página
  throw new Error('[form.js] Formulário #contact-form não encontrado.');
}

// ── Regras de validação ────────────────────────────────────
const RULES = {
  nome: {
    required: true,
    minLength: 3,
    label: 'Nome',
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    label: 'E-mail',
  },
  telefone: {
    required: false,
    pattern: /^[\d\s()\-+]{8,}$/,
    label: 'Telefone',
  },
  empresa: {
    required: false,
    label: 'Empresa',
  },
  desafio: {
    required: true,
    minLength: 10,
    label: 'Desafio',
  },
};

// ── Helpers ────────────────────────────────────────────────
const getField = (name) => form.querySelector(`[name="${name}"]`);
const getError = (input) =>
  input.closest('.form-group')?.querySelector('.form-error');

const setError = (input, msg) => {
  input.classList.toggle('is-invalid', !!msg);
  input.setAttribute('aria-invalid', msg ? 'true' : 'false');
  const err = getError(input);
  if (err) err.textContent = msg ?? '';
};

const clearError = (input) => setError(input, '');

/**
 * Valida um campo individualmente.
 * @param {HTMLInputElement|HTMLTextAreaElement} input
 * @returns {boolean} true se válido
 */
const validateField = (input) => {
  const rule = RULES[input.name];
  if (!rule) return true;

  const value = input.value.trim();

  if (rule.required && !value) {
    setError(input, `${rule.label} é obrigatório.`);
    return false;
  }

  if (value && rule.minLength && value.length < rule.minLength) {
    setError(input, `${rule.label} deve ter pelo menos ${rule.minLength} caracteres.`);
    return false;
  }

  if (value && rule.pattern && !rule.pattern.test(value)) {
    setError(input, `${rule.label} inválido.`);
    return false;
  }

  clearError(input);
  return true;
};

// ── Validação em tempo real (ao sair do campo) ─────────────
const fields = $$('[name]', form);

fields.forEach(field => {
  field.addEventListener('blur', () => validateField(field));
  field.addEventListener('input', () => {
    // Remove erro assim que usuário começa a corrigir
    if (field.classList.contains('is-invalid')) clearError(field);
  });
});

// ── Máscara de telefone ────────────────────────────────────
const telefoneInput = getField('telefone');

telefoneInput?.addEventListener('input', () => {
  let v = telefoneInput.value.replace(/\D/g, '');
  if (v.length > 11) v = v.slice(0, 11);

  if (v.length <= 10) {
    v = v.replace(/^(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
  } else {
    v = v.replace(/^(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
  }

  telefoneInput.value = v;
});

// ── Submit ─────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  // Valida todos os campos
  const results = [...fields].map(validateField);
  const isValid = results.every(Boolean);

  if (!isValid) {
    // Foca o primeiro campo inválido
    const firstInvalid = form.querySelector('.is-invalid');
    firstInvalid?.focus();
    return;
  }

  const submitBtn = form.querySelector('[type="submit"]');
  const originalLabel = submitBtn.textContent.trim();

  try {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enviando…';

    const payload = Object.fromEntries(new FormData(form));

    // ── Integração com backend ─────────────────────────────
    // Descomente e adapte ao seu endpoint:
    //
    // const response = await fetch('/api/contato', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(payload),
    // });
    //
    // if (!response.ok) throw new Error('Erro no servidor.');

    // Simulação de delay (remova em produção)
    await new Promise(resolve => setTimeout(resolve, 1200));

    console.info('[form.js] Dados enviados:', payload);

    showSuccessMessage();
    form.reset();
    fields.forEach(f => f.classList.remove('is-invalid'));

  } catch (err) {
    console.error('[form.js] Erro ao enviar:', err);
    showErrorMessage();
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalLabel;
  }
});

// ── Feedback pós-envio ─────────────────────────────────────
const createToast = (message, type = 'success') => {
  const existing = document.querySelector('.form-toast');
  existing?.remove();

  const toast = document.createElement('div');
  toast.className = 'form-toast';
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');

  toast.style.cssText = `
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    padding: 1rem 1.5rem;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 500;
    color: white;
    background: ${type === 'success' ? '#28BEA5' : '#FA5975'};
    box-shadow: 0 4px 24px rgba(0,0,0,0.2);
    z-index: 9999;
    animation: slideInToast 0.3s ease;
  `;

  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 5000);
};

const showSuccessMessage = () =>
  createToast('✓ Mensagem enviada! Entraremos em contato em breve.', 'success');

const showErrorMessage = () =>
  createToast('Ocorreu um erro. Tente novamente ou entre em contato diretamente.', 'error');

// Estilo da animação do toast
const toastStyle = document.createElement('style');
toastStyle.textContent = `
  @keyframes slideInToast {
    from { opacity: 0; transform: translateX(40px); }
    to   { opacity: 1; transform: translateX(0); }
  }
`;
document.head.appendChild(toastStyle);
