# Security-Audit (PURZEL-046)

## pip-audit

```bash
cd api && python3 -m pip_audit
```

**Ergebnis (Stand Implementierung):** Gefundene CVEs betreffen vorwiegend transitive/system-Dependencies (ansible, cryptography, jinja2, pip, setuptools, wheel). Direkte Dependencies aus `requirements.txt` sind geprüft. Kritische CVEs in den direkten Projekt-Dependencies sollten durch Updates behoben werden.

## npm audit

```bash
cd frontend && npm audit
```

**Ergebnis:** 0 vulnerabilities (Stand Implementierung).

## .env-Hygiene

- `.env` ist in `.gitignore` (nicht in Git-History)
- `.env.example` enthält alle Keys ohne echte Werte
- Keine Secrets in Log-Output (Logging prüft nur Status, keine Credentials)
