# Frontend — Semantic Book Recommender

React + Vite + TypeScript frontend for the IT4142 Semantic Book Recommender
(PRD §8). Search books by natural-language query, compare the five retrieval
methods side-by-side, inspect emotion profiles, and explore the evaluation
dashboard — with light/dark themes.

## Stack

- **React 19 + Vite + TypeScript**
- **Plain CSS** (warm-paper design system, oklch palette, light/dark) — no UI framework
- **Spectral / IBM Plex Sans / IBM Plex Mono** fonts (Google Fonts)
- Bespoke **SVG charts** (grouped bar, scatter, radar) — no chart library
- A lightweight `useAsync` hook stands in for TanStack Query

## Quick start

```bash
npm install
npm run dev
```

Open the URL Vite prints (default http://localhost:5173).

> **Demo mode:** with no backend configured, the app serves results from a
> built-in mock corpus + simulated API (`src/app/data.jsx`) so every screen is
> fully usable offline.

## Connecting the real backend

The frontend expects the FastAPI endpoints from PRD §7 (`POST /search`,
`GET /books/{isbn13}`). To point at a running backend:

```bash
cp .env.example .env
# edit .env:
VITE_API_BASE=http://localhost:8000
```

Restart `npm run dev`. When `VITE_API_BASE` is set, `apiSearch` / `apiBook`
hit the real backend; otherwise the mock engine is used. (Stats and evaluation
fixtures remain local presentation data.)

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the dev server with HMR |
| `npm run build` | Type-check (`tsc -b`) + production build to `dist/` |
| `npm run preview` | Preview the production build |
| `npm run lint` | Run ESLint |

## Structure

```
src/
├── main.tsx              # entry — mounts <App/>
├── index.css            # design system (CSS variables, light/dark, animations)
└── app/                 # the application (plain .jsx, ES modules)
    ├── data.jsx         # mock corpus + simulated API + VITE_API_BASE switch
    ├── ui.jsx           # primitives: Icon, Button, badges, CoverImage, useAsync…
    ├── charts.jsx       # bespoke SVG charts (bar / scatter / radar)
    ├── modal.jsx        # BookDetailModal (emotion bars + radar)
    ├── page_search.jsx  # Search page (route "#/")
    ├── page_compare.jsx # Compare-all-methods page (route "#/compare")
    ├── page_eval.jsx    # Evaluation dashboard (route "#/evaluation")
    └── app.jsx          # nav, hash router, theme, modal host
```

> The `app/` files are authored as `.jsx`; `tsconfig.app.json` sets
> `allowJs: true` / `checkJs: false`, so `tsc -b` type-checks the TS entry and
> Vite transpiles the JSX. This keeps the design code framework-free and easy
> to read.

## Routes

- `#/` — **Search**: natural-language query, 5 method selector, emotion filter,
  top-K, skeleton loading, responsive results grid.
- `#/compare` — **Compare**: one query across all 5 methods in parallel, with
  per-method latency and an auto-generated "what the differences tell us" panel.
- `#/evaluation` — **Evaluation**: takeaways, the vocabulary-mismatch demo,
  metrics table, grouped bar + latency-vs-P@5 scatter, and a per-genre radar.
