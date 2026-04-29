/**
 * animations.js
 * Animações de entrada baseadas em IntersectionObserver.
 * Adiciona classe `.is-visible` quando o elemento entra na viewport.
 * As transições CSS são definidas em components.css / sections.css.
 */

'use strict';

import { $$, createObserver } from './utils.js';

// Elementos que devem animar ao entrar na viewport
const ANIMATED_SELECTORS = [
  '.card',
  '.stat',
  '.testimonial',
  '.timeline__item',
  '.demo__wrapper',
  '.form-card',
];

// Adiciona estilo base via JS para não depender de CSS extra
const injectBaseStyles = () => {
  const style = document.createElement('style');
  style.textContent = `
    [data-animate] {
      opacity: 0;
      transform: translateY(24px);
      transition: opacity 0.55s ease, transform 0.55s ease;
    }
    [data-animate].is-visible {
      opacity: 1;
      transform: translateY(0);
    }
  `;
  document.head.appendChild(style);
};

const setupAnimations = () => {
  injectBaseStyles();

  const elements = document.querySelectorAll(ANIMATED_SELECTORS.join(', '));

  const observer = createObserver((entries) => {
    entries.forEach((entry, i) => {
      if (!entry.isIntersecting) return;

      const el = entry.target;

      // Delay escalonado entre irmãos
      const siblings = [...(el.parentElement?.children ?? [])];
      const index    = siblings.indexOf(el);
      el.style.transitionDelay = `${index * 80}ms`;

      el.classList.add('is-visible');
      observer.unobserve(el); // anima apenas uma vez
    });
  });

  elements.forEach(el => {
    el.setAttribute('data-animate', '');
    observer.observe(el);
  });
};

// Inicia após o DOM estar pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupAnimations);
} else {
  setupAnimations();
}
