# Purzel Frontend

React-19-Oberfläche für die **Purzel ML Asset Pipeline** (TypeScript, Vite, TanStack Query, Three.js).

## Entwicklung

```bash
npm ci
npm run dev
```

Die API-URL setzt du mit `VITE_API_URL` (in Docker Compose: `http://localhost:8000`).

## Qualität

```bash
npm run lint
npm run test
```

## Dokumentation

Frontend-Kapitel der Projekt-Doku: [../docs/frontend.md](../docs/frontend.md) — Vorschau aller Docs: im Repo-Root `pip install -r requirements-docs.txt` und `python3 -m mkdocs serve`.
