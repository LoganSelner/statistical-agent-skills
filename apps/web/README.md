# statskills-web

The clickable demo UI for the statskills harness (ROADMAP §11): upload a dataset, pick a
skill-delivery mode (**off / injected / agentic**), watch the agent's steps stream live,
and read the composed, traceable [`Report`](../../src/statskills/reporting/). Flipping the
delivery toggle and re-running is the demo — _watch_ the assumption check appear and the
conclusion change.

Built with **Vite + Svelte 5 + TypeScript**. It is a Node package **outside** the Python
workspace and depends only on the HTTP API (`web → api → statskills`); the JS stack never
touches the core. All requests use **relative URLs**, so the same build works in dev (the
Vite server proxies `/runs` to the API) and in production (the API serves the built assets
same-origin) — no CORS, no base-URL config.

## Develop

```bash
npm ci          # or: make web-install  (from the repo root)
npm run dev      # Vite on :5173, proxying /runs + /healthz to the API on :8000
```

Run the API separately: `ANTHROPIC_API_KEY=… uv run uvicorn statskills_api.app:app`.

## Gate

```bash
npm run check        # svelte-check (types + a11y)
npm run format:check # prettier
npm run test         # vitest
npm run build        # vite build → dist/
```

The same checks run in the `web` CI job. To serve the built SPA from the API on one origin:
`make web-build` then `STATSKILLS_WEB_DIST=apps/web/dist uv run uvicorn statskills_api.app:app`.

## Layout

- `src/lib/types.ts` — TS mirrors of the backend payloads (`StepEvent`, `Report`, …).
- `src/lib/api.ts` — typed client: `submitRun`, `streamEvents` (SSE), `fetchRun`, `figureUrl`.
- `src/components/` — `RunForm`, `StepStream`, `ReportView`.
- `src/App.svelte` — the phase machine: submit → stream steps → fetch + render the report.
