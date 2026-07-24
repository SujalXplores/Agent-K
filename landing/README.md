# Agent K landing page

The marketing landing page for **Agent K**, a code-enforced incident-response
agent built for the "Agents of SigNoz" hackathon (Track 01, AI and Agent
Observability). It presents the product, the Three Laws, the ten-step
investigation flow, the four demonstration incidents, and the safety model.

This site is separate from the judged Agent K runtime. It is a static Next.js
app that deploys to Vercel.

## Stack

- Next.js (App Router) and React 19
- TypeScript
- Tailwind CSS v4 with CSS-first `@theme` tokens
- Motion for animation, gated by `prefers-reduced-motion`
- next-themes for dark and light modes (dark by default)
- Base UI for interactive primitives (dialog, tabs, accordion)
- shadcn/ui and Magic UI components
- Vitest and Testing Library for unit tests, Playwright for end-to-end tests
- axe-core for automated accessibility checks

## Getting started

```bash
npm install
npm run dev        # start the dev server on http://localhost:3000
```

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Start the development server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run typecheck` | TypeScript check (`tsc --noEmit`) |
| `npm run lint` | ESLint |
| `npm run test` | Unit tests (Vitest) |
| `npm run test:e2e` | End-to-end and accessibility tests (Playwright) |
| `npm run verify` | typecheck, lint, unit tests, and build in one step |

Playwright needs its browser once: `npx playwright install chromium`.

## Project structure

```
src/
  app/            layout, page, globals.css, opengraph-image, sitemap, robots
  components/
    layout/       navbar, footer, center rail, section, theme toggle
    sections/     one component per page section
    ui/           shadcn and Magic UI primitives
    seo/          JSON-LD
    icons/        brand and product icons
  hooks/          usePrefersReducedMotion, useActiveSection
  lib/config/     site.ts, content.ts, tech-stack.ts, theme.ts (single source of truth)
tests/e2e/        Playwright specs
```

All copy and links live in `src/lib/config`. Components never hardcode text or
URLs. Update `site.ts` links (GitHub, blog, demo) before shipping.

## Accessibility and performance

- Semantic HTML, labelled landmarks, and keyboard-operable controls.
- Every animation respects `prefers-reduced-motion` and renders a static end
  state instead.
- Automated axe checks report zero critical or serious issues in both themes.
- Full WCAG conformance still needs manual assistive-technology testing and
  expert review. Automated checks and semantic structure are validated here,
  not full compliance.

## Deployment

Deploys to Vercel with zero configuration. Set `NEXT_PUBLIC_SITE_URL` to the
production URL so metadata, the sitemap, and the Open Graph image use absolute
links.

## AI assistance disclosure

This landing page was built with AI coding assistance, disclosed here per the
hackathon rules. A human reviewed and directed the work. All product claims are
grounded in the project planning documents, and demonstration results are
described honestly as four out of four on four controlled scenarios, not as
general production accuracy.
