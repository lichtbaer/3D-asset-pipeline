"""Anthropic Claude API Client für LLM-Analyse."""

import json
import os

from anthropic import AsyncAnthropic

SYSTEM_PROMPT = """Du bist ein erfahrener Software-Architekt. Analysiere dieses Repository und antworte ausschließlich mit validem JSON.
Halte dich strikt an das vorgegebene Schema. Keine Erklärungen außerhalb des JSON."""

CHUNK1_PROMPT = """Analysiere die Repository-Struktur und Konfigurationsdateien.

Dateibaum und relevante Dateiinhalte:
{context}

Antworte mit JSON:
{{
  "detected_stack": ["Python 3.12", "FastAPI", "React", ...],
  "architecture_patterns": ["Repository Pattern", "Dependency Injection", ...]
}}"""

CHUNK2_PROMPT = """Analysiere Architektur-Patterns und Code-Qualität anhand der Code-Samples.

Code-Samples:
{context}

Ergänze die architecture_patterns falls nötig. Antworte mit JSON:
{{
  "architecture_patterns": ["...", "..."],
  "code_quality_notes": "Kurze Bewertung"
}}"""

CHUNK3_PROMPT = """Identifiziere fehlende Best Practices und technische Schulden.

Kontext aus vorherigen Analysen:
{context}

Antworte mit JSON:
{{
  "findings": [
    {{
      "title": "Kurzer Titel",
      "description": "Beschreibung",
      "severity": "critical|high|medium|low",
      "category": "security|performance|maintainability|testing|documentation",
      "file_path": "pfad/oder/null"
    }}
  ],
  "summary": "2-3 Sätze Zusammenfassung"
}}"""


class LLMClient:
    """Async Anthropic Client für strukturierte Analyse."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = AsyncAnthropic(api_key=api_key or os.getenv("ANALYZER_API_KEY"))
        self.model = model or os.getenv("ANALYZER_MODEL", "claude-haiku-4-5-20251001")

    async def analyze_chunk(self, prompt: str, context: str) -> dict:
        """Sendet einen Analyse-Chunk und parst die JSON-Antwort."""
        filled = prompt.format(context=context[:120_000])  # Token-Limit grob begrenzen
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": filled}],
        )
        text = response.content[0].text if response.content else ""
        # JSON aus Antwort extrahieren (falls Markdown-Codeblock)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
