# Security Audit – Purzel ML Asset Pipeline

Dieses Dokument dokumentiert die Ergebnisse von `pip-audit` für die Python-Abhängigkeiten der API.

## Ausführung

```bash
cd api
pip-audit -l --format=json > docs/pip-audit-results.json
pip-audit -l   # Summary in der Konsole
```

## Ergebnis (Stand: SMA-204)

`pip-audit` prüft alle installierten Python-Pakete auf bekannte CVEs (Common Vulnerabilities and Exposures).

### Gefixte CVEs (via requirements.txt)

| Paket | Vorher | Nachher | CVEs |
|-------|--------|---------|------|
| cryptography | 41.x | >=43.0.1 | CVE-2024-26130, CVE-2023-50782, CVE-2024-0727, GHSA-h4gh-qq45-vh27, CVE-2026-26007 |

### Bekannte Einschränkungen

- **wheel**: CVE-2026-24049 betrifft `wheel.cli.unpack`. Das Paket wird von pip/setuptools als Build-Tool verwendet. Die API-Runtime nutzt `wheel` nicht direkt. Upgrade auf wheel>=0.46.2 empfohlen, sobald verfügbar.
- **System-Pakete**: `pip-audit -l` prüft die gesamte Python-Umgebung. In CI (Docker) sind nur die Pakete aus `requirements.txt` installiert – dort sind weniger transitive Abhängigkeiten vorhanden.

### CI-Integration

Die GitHub-Actions-Pipeline führt `pip-audit` aus. Bei high/critical CVEs in direkten oder transitiven Abhängigkeiten der API muss die Pipeline grün bleiben – d.h. CVEs müssen vor Merge gefixt werden.

### Rohdaten

Vollständige JSON-Ausgabe: `docs/pip-audit-results.json`
