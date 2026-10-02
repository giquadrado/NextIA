/**
 * navbar.js
 * Comportamentos de navegação:
 *  - Sombra no header ao rolar
 *  - Menu mobile (hambúrguer), com Escape e fechamento ao clicar em link
 *  - Link ativo conforme a seção visível
 *  - Botão flutuante "Fale com a Clara" escondido quando o contato já está na tela
 */

'use strict';

import { $, $$, debounce, createObserver } from './utils.js';

const navbar     = $('#navbar');
const hamburger  = $('.navbar__hamburger');
const mobileMenu = $('#mobile-menu');
const navLinks   = $$('.navbar__link');
const floatChat  = $('.float-chat');
const contato    = $('#contato');

const DESKTOP_BREAKPOINT = 1024; // mesmo valor de --bp-desktop

/* ── Sombra ao rolar ─────────────────────────────────────── */
const handleScroll = debounce(() => {
  navbar?.classList.toggle('is-scrolled', window.scrollY > 10);
}, 50);

window.addEventListener('scroll', handleScroll, { passive: true });
handleScroll();

/* ── Menu mobile ─────────────────────────────────────────── */
const setMenuState = (isOpen) => {
  if (!mobileMenu || !hamburger) return;

  mobileMenu.classList.toggle('is-open', isOpen);
  mobileMenu.setAttribute('aria-hidden', String(!isOpen));
  mobileMenu.inert = !isOpen; // impede foco por teclado quando fechado
  hamburger.setAttribute('aria-expanded', String(isOpen));
  hamburger.setAttribute('aria-label', isOpen ? 'Fechar menu' : 'Abrir menu');
  document.body.style.overflow = isOpen ? 'hidden' : '';
};

const isMenuOpen = () => mobileMenu?.classList.contains('is-open') ?? false;

// Estado inicial: fechado e fora da ordem de foco
setMenuState(false);

hamburger?.addEventListener('click', () => setMenuState(!isMenuOpen()));

// Fecha ao clicar em qualquer link do menu mobile (inclui o botão de CTA)
mobileMenu?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => setMenuState(false));
});

// Fecha com Escape e devolve o foco ao botão
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && isMenuOpen()) {
    setMenuState(false);
    hamburger?.focus();
  }
});

// Fecha se a tela for redimensionada para desktop com o menu aberto
window.addEventListener('resize', debounce(() => {
  if (window.innerWidth >= DESKTOP_BREAKPOINT && isMenuOpen()) setMenuState(false);
}, 150));

/* ── Link ativo por seção ────────────────────────────────── */
const linkedIds = new Set(
  [...navLinks]
    .map((link) => link.getAttribute('href')?.replace('#', ''))
    .filter(Boolean)
);

const sectionObserver = createObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;

    const id = entry.target.id;
    navLinks.forEach((link) => {
      const isActive = link.getAttribute('href') === `#${id}`;
      link.classList.toggle('is-active', isActive);
      if (isActive) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  });
}, { threshold: 0.4 });

// Observa apenas as seções que têm link no menu
$$('section[id]').forEach((section) => {
  if (linkedIds.has(section.id)) sectionObserver.observe(section);
});

/* ── Botão flutuante da Clara ────────────────────────────── */
if (floatChat && contato) {
  const floatObserver = createObserver((entries) => {
    entries.forEach((entry) => {
      floatChat.classList.toggle('is-hidden', entry.isIntersecting);
    });
  }, { rootMargin: '0px', threshold: 0.2 });

  floatObserver.observe(contato);
}
