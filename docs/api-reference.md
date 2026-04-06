# API-Referenz

Die laufende API stellt die **interaktive OpenAPI-Oberfläche** bereit:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

Geschäfts-Endpunkte liegen unter **`/api/v1/...`**. Wenn `API_KEY` gesetzt ist, ist für diese Routen ein **Bearer-Token** nötig — siehe [Konfiguration](configuration.md).

Health-Check ohne Auth-Pflicht der v1-Router:

- **GET** [http://localhost:8000/health](http://localhost:8000/health)
