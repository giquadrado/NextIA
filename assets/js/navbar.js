/**
 * navbar.js
 * Comportamentos da barra de navegação:
 *  - Scroll shadow
 *  - Hamburger / menu mobile
 *  - Active link por seção visível (IntersectionObserver)
 *  - Fechar menu ao clicar em link
 */

'use strict';

import { $, $$, debounce, createObserver } from './utils.js';

const navbar      = $('#navbar');
const hamburger   = $('.navbar__hamburger');
const mobileMenu  = $('#mobile-menu');
const navLinks    = $$('.navbar__link');

// ── Scroll shadow ──────────────────────────────────────────
const handleScroll = debounce(() => {
  navbar.classList.toggle('is-scrolled', window.scrollY > 10);
}, 50);

window.addEventListener('scroll', handleScroll, { passive: true });


// ── Hamburger ──────────────────────────────────────────────
const toggleMenu = () => {
  const isOpen = mobileMenu.classList.toggle('is-open');
  hamburger.setAttribute('aria-expanded', String(isOpen));
  mobileMenu.setAttribute('aria-hidden',  String(!isOpen));
  document.body.style.overflow = isOpen ? 'hidden' : '';
};

hamburger?.addEventListener('click', toggleMenu);

// Fecha menu ao clicar em um link
navLinks.forEach(link => {
  link.addEventListener('click', () => {
    if (mobileMenu.classList.contains('is-open')) toggleMenu();
  });
});

// Fecha menu ao pressionar Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && mobileMenu.classList.contains('is-open')) {
    toggleMenu();
    hamburger.focus();
  }
});


// ── Active link por seção ──────────────────────────────────
const sections = $$('section[id], div[id]');

const sectionObserver = createObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;

    const id = entry.target.getAttribute('id');
    navLinks.forEach(link => {
      const href = link.getAttribute('href')?.replace('#', '');
      link.classList.toggle('is-active', href === id);
    });
  });
}, { threshold: 0.4 });

sections.forEach(section => sectionObserver.observe(section));
