# Frontend

## Tech-Stack

- **React 19** mit **TypeScript**
- **Vite** als Build- und Dev-Server
- **TanStack Query** für Server-State
- **Three.js** für 3D-Ansichten (z. B. MeshViewer, AnimationMeshViewer)

## Projektstruktur (Auszug)

```
frontend/src/
├── api/           # HTTP-Client (Axios), Basis-URL über VITE_API_URL
├── components/    # UI-Bausteine
├── pages/         # Routen-Seiten (u. a. Pipeline)
└── store/         # PipelineStore (Pipeline-State)
```

## API-Basis-URL

In Docker Compose ist für das Frontend typischerweise gesetzt:

- `VITE_API_URL=http://localhost:8000`

Lokale Entwicklung ohne Docker: in `frontend/.env` bzw. `.env.local` denselben Wert setzen, falls die API auf einem anderen Host/Port läuft.

## Lint und Tests

```bash
cd frontend
npm ci
npm run lint
npm run test
```

## UX und Design

Geplante und besprochene Verbesserungen sind in [UX Improvement Plan](UX_IMPROVEMENT_PLAN.md) und [Design & UX Review](DESIGN_UX_REVIEW.md) dokumentiert.

Vorschau der gesamten Doku im Repo-Root: `python3 -m mkdocs serve` (siehe [Startseite](index.md)).
