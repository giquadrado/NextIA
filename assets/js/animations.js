/**
 * animations.js
 * Entrada suave dos blocos quando aparecem na tela.
 * - Anima uma única vez por elemento
 * - Desligado por completo quando o usuário prefere menos movimento
 */

'use strict';

import { $$, createObserver, prefersReducedMotion } from './utils.js';

const ANIMATED_SELECTORS = [
  '.card',
  '.agent-card',
  '.metric',
  '.cenario',
  '.step',
  '.form-card',
];

const MAX_STAGGER_ITEMS = 4; // evita atrasos longos em grids grandes
const STAGGER_MS = 80;

const injectBaseStyles = () => {
  const style = document.createElement('style');
  style.textContent = `
    [data-animate] {
      opacity: 0;
      transform: translateY(16px);
      transition: opacity 0.5s ease, transform 0.5s ease;
    }
    [data-animate].is-visible {
      opacity: 1;
      transform: none;
    }
  `;
  document.head.appendChild(style);
};

const setupAnimations = () => {
  if (prefersReducedMotion() || !('IntersectionObserver' in window)) return;

  const elements = $$(ANIMATED_SELECTORS.join(', '));
  if (!elements.length) return;

  injectBaseStyles();

  const observer = createObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;

      const el = entry.target;
      const siblings = [...(el.parentElement?.children ?? [])];
      const index = Math.min(siblings.indexOf(el), MAX_STAGGER_ITEMS - 1);

      el.style.transitionDelay = `${Math.max(index, 0) * STAGGER_MS}ms`;
      el.classList.add('is-visible');
      observer.unobserve(el);
    });
  });

  elements.forEach((el) => {
    el.setAttribute('data-animate', '');
    observer.observe(el);
  });
};

setupAnimations();
