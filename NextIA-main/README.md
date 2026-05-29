# NextIA Landing Page

Landing page da NextIA – Agentes de IA que automatizam, reduzem custos e escalam seu negócio.

---

## 📁 Árvore de arquivos

```
nextia-landing/
│
├── index.html                  # Ponto de entrada – estrutura semântica HTML5
│
├── assets/
│   │
│   ├── css/
│   │   ├── reset.css           # Normalização cross-browser (Modern CSS Reset)
│   │   ├── variables.css       # Design Tokens – cores, tipografia, espaçamentos
│   │   ├── base.css            # Estilos globais e tipografia base
│   │   ├── layout.css          # Container, grid helpers, utilitários de layout
│   │   ├── components.css      # Componentes reutilizáveis (btn, card, form…)
│   │   ├── sections.css        # Estilos específicos por seção (hero, navbar…)
│   │   └── responsive.css      # Media queries / breakpoints (mobile-first)
│   │
│   ├── js/
│   │   ├── utils.js            # Funções utilitárias puras (helpers, debounce…)
│   │   ├── navbar.js           # Scroll shadow, hamburger, active link
│   │   ├── animations.js       # Animações de entrada via IntersectionObserver
│   │   ├── counter.js          # Contador animado nas métricas
│   │   └── form.js             # Validação, máscara de telefone, envio async
│   │
│   ├── images/
│   │   ├── logo.svg            # Logotipo da marca
│   │   ├── hero-bg.jpg         # Imagem de fundo do Hero
│   │   ├── demo-preview.png    # Screenshot / vídeo-thumb do agente
│   │   ├── agent-avatar.svg    # Avatar do NextIA Assistant
│   │   ├── timeline-visual.png # Imagem central da seção História
│   │   ├── icon-automation.svg # Ícone – tarefas automáticas
│   │   ├── icon-efficiency.svg # Ícone – eficiência
│   │   ├── icon-data.svg       # Ícone – dados em tempo real
│   │   ├── icon-focus.svg      # Ícone – time focado
│   │   ├── icon-scale.svg      # Ícone – escala
│   │   ├── icon-response.svg   # Ícone – respostas rápidas
│   │   ├── icon-time.svg       # Ícone – redução de tempo
│   │   ├── icon-cost.svg       # Ícone – redução de custos
│   │   └── icon-satisfaction.svg # Ícone – satisfação
│   │
│   └── fonts/                  # Fontes locais (opcional – projeto usa Google Fonts)
│
└── README.md                   # Este arquivo
```

---

## 🎨 Arquitetura CSS

| Arquivo          | Responsabilidade |
|------------------|-----------------|
| `reset.css`      | Zera margens, normaliza box-model, remove estilos de agente |
| `variables.css`  | Único ponto de verdade para tokens de design (CSS Custom Properties) |
| `base.css`       | Body, tipografia base, utilitários de cor, foco visível |
| `layout.css`     | `.container`, grid helpers, flex utilities |
| `components.css` | Botões, cards, stats, testimonials, formulário, timeline |
| `sections.css`   | Navbar, Hero, Diferencial, Demo, Métricas, História, Contato, Footer |
| `responsive.css` | Mobile-first breakpoints (≥768px tablet, ≥1024px desktop) |

---

## ⚡ Arquitetura JavaScript (ES Modules)

| Arquivo          | Responsabilidade |
|------------------|-----------------|
| `utils.js`       | Funções puras: `$()`, `$$()`, `debounce()`, `createObserver()` |
| `navbar.js`      | Scroll shadow, hamburger menu, active link por IntersectionObserver |
| `animations.js`  | Animações de entrada escalonadas via IntersectionObserver |
| `counter.js`     | Animação dos números de métricas com easing cúbico |
| `form.js`        | Validação em tempo real, máscara telefone, envio assíncrono, toast |

---

## 🚀 Como usar

1. **Clone / copie** a pasta `nextia-landing/` para seu servidor ou abra com Live Server.
2. **Substitua** os placeholders em `assets/images/` pelas imagens reais.
3. **Configure o endpoint** de envio do formulário em `assets/js/form.js` (comentário `// Integração com backend`).
4. Para produção, rode um **bundler** (Vite, Parcel ou Webpack) ou sirva os ES Modules diretamente via HTTP/2.

---

## ✅ Boas práticas aplicadas

- **Semântica HTML5** – `<header>`, `<main>`, `<section>`, `<article>`, `<footer>`, `<nav>`
- **Acessibilidade** – `aria-label`, `aria-expanded`, `aria-hidden`, `aria-live`, `role`, `:focus-visible`
- **Performance** – `loading="lazy"` nas imagens, `defer` nos scripts, `IntersectionObserver` em vez de scroll listener
- **Mobile-first** – layout começa simples e expande com media queries
- **Design Tokens** – todas as cores, fontes e espaçamentos em `variables.css`
- **ES Modules** – imports/exports nativos, sem framework necessário
- **Formulário robusto** – validação client-side, máscara, feedback acessível, pronto para async/await

---

## 🔗 Dependências externas

- [Google Fonts – Roboto + Roboto Condensed](https://fonts.google.com/)  
  Nenhuma outra dependência de terceiros.
