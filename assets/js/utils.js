/**
 * utils.js
 * Funções utilitárias compartilhadas pelos módulos da landing page.
 */

'use strict';

/**
 * Seleciona um elemento no DOM (atalho para querySelector).
 * @param {string} selector
 * @param {Element|Document} [scope=document]
 * @returns {Element|null}
 */
export const $ = (selector, scope = document) => scope.querySelector(selector);

/**
 * Seleciona múltiplos elementos no DOM.
 * @param {string} selector
 * @param {Element|Document} [scope=document]
 * @returns {NodeList}
 */
export const $$ = (selector, scope = document) => scope.querySelectorAll(selector);

/**
 * Indica se o usuário pediu menos animação no sistema operacional.
 * Usado para desligar transições e rolagens suaves.
 * @returns {boolean}
 */
export const prefersReducedMotion = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Cria um IntersectionObserver com valores padrão do projeto.
 * @param {IntersectionObserverCallback} callback
 * @param {IntersectionObserverInit} [options]
 * @returns {IntersectionObserver}
 */
export const createObserver = (callback, options = {}) =>
  new IntersectionObserver(callback, {
    rootMargin: '0px 0px -80px 0px',
    threshold: 0.1,
    ...options,
  });

/**
 * Debounce: limita a frequência de chamadas a uma função.
 * @param {Function} fn
 * @param {number} [delay=200] - ms
 * @returns {Function}
 */
export const debounce = (fn, delay = 200) => {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
};

/**
 * Rola a página até um elemento, descontando a altura do header fixo.
 * Respeita a preferência de movimento reduzido.
 * @param {Element|string} target - elemento ou seletor
 */
export const scrollToElement = (target) => {
  const el = typeof target === 'string' ? $(target) : target;
  if (!el) return;

  const navbar = $('#navbar');
  const offset = navbar ? navbar.offsetHeight + 16 : 0;
  const top = el.getBoundingClientRect().top + window.scrollY - offset;

  window.scrollTo({
    top,
    behavior: prefersReducedMotion() ? 'auto' : 'smooth',
  });
};

/**
 * Nome do evento disparado quando o visitante demonstra interesse
 * em um agente específico. O form.js escuta este evento para
 * preencher o formulário de contato.
 */
export const INTEREST_EVENT = 'interagente:interesse';
