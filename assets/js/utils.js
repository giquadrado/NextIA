/**
 * utils.js
 * Funções utilitárias reutilizáveis em todo o projeto.
 */

'use strict';

/**
 * Seleciona um elemento no DOM (atalho para querySelector).
 * @param {string} selector
 * @param {Element|Document} [scope=document]
 * @returns {Element|null}
 */
export const $ = (selector, scope = document) =>
  scope.querySelector(selector);

/**
 * Seleciona múltiplos elementos no DOM.
 * @param {string} selector
 * @param {Element|Document} [scope=document]
 * @returns {NodeList}
 */
export const $$ = (selector, scope = document) =>
  scope.querySelectorAll(selector);

/**
 * Adiciona múltiplos event listeners de uma vez.
 * @param {Element} el
 * @param {string[]} events
 * @param {Function} handler
 */
export const onEvents = (el, events, handler) =>
  events.forEach(evt => el.addEventListener(evt, handler));

/**
 * Cria um IntersectionObserver simples.
 * @param {Function} callback
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
 * @param {number} delay - ms
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
 * Formata número com separador de milhar pt-BR.
 * @param {number} n
 * @returns {string}
 */
export const formatNumber = (n) =>
  new Intl.NumberFormat('pt-BR').format(n);
