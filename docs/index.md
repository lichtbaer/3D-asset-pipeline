# Purzel ML Asset Pipeline

Modularer Experimentierrahmen für KI-gestützte 3D-Asset-Erzeugung: **FastAPI**-Backend, **React**-Frontend und **PostgreSQL**.

## Schnellnavigation

| Thema | Seite |
|--------|--------|
| Installation & Docker | [Erste Schritte](getting-started.md) |
| Systemüberblick | [Architektur](architecture.md) |
| API & Router | [Backend](backend.md) |
| UI & Client | [Frontend](frontend.md) |
| Umgebungsvariablen | [Konfiguration](configuration.md) |
| Rigging ohne HF-Space | [UniRig lokal](unirig-local.md) |
| Interaktive API-Docs | [API-Referenz](api-reference.md) |
| Beiträge & Konventionen | [Konventionen (Agenten)](agents.md) |

## Projekt & Qualität

Audits, Pläne und PoCs liegen unter **Projekt & Qualität** in der linken Navigation (Technical Debt, Security, UX, Blender-PoC).

## Lokale Vorschau

```bash
pip install -r requirements-docs.txt
python3 -m mkdocs serve
```

Standardadresse der Doku: **http://127.0.0.1:8001** (in `mkdocs.yml` gesetzt, damit sie nicht mit der API auf Port 8000 kollidiert).
