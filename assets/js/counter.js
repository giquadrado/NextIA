/**
 * counter.js
 * Anima os números das métricas de 0 até o valor alvo
 * quando a seção entra na viewport (dispara apenas uma vez).
 */

'use strict';

import { $$, createObserver } from './utils.js';

/**
 * Executa a animação de contagem para um elemento.
 * @param {Element} el - elemento com [data-target]
 */
const animateCounter = (el) => {
  const target   = parseInt(el.dataset.target, 10);
  const duration = 1800; // ms
  const start    = performance.now();

  const step = (now) => {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);

    // Easing: ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);

    el.textContent = Math.floor(eased * target).toString();

    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target.toString();
  };

  requestAnimationFrame(step);
};

// ── Setup ──────────────────────────────────────────────────
const counters = $$('[data-target]');

if (counters.length > 0) {
  const observer = createObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      animateCounter(entry.target);
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.6 });

  counters.forEach(el => observer.observe(el));
}
