"""
Auto-Tagging-Service: Ruft den Tagging-Agenten nach erfolgreicher Mesh-Generierung auf.
Wird als Background-Task nach persist_mesh_job ausgeführt.
"""

import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


async def auto_tag_asset_after_mesh(asset_id: str) -> None:
    """
    Schlägt automatisch Tags für ein Asset vor und persistiert sie in metadata.json.

    Wird nach erfolgreicher Mesh-Generierung aufgerufen.
    Überspringt stillschweigend wenn ANTHROPIC_API_KEY nicht gesetzt ist.
    """
    if not settings.agent_available:
        logger.debug("Auto-Tagging übersprungen: ANTHROPIC_API_KEY nicht gesetzt")
        return

    try:
        from app.agents.tagging_agent import get_tagging_agent
        from app.services import asset_service
        from app.services.metadata_service import get_metadata_service
        from pydantic_ai import BinaryContent

        meta = asset_service.get_asset(asset_id)
        if not meta:
            logger.warning("Auto-Tagging: Asset %s nicht gefunden", asset_id)
            return

        # Bereits vorhandene Tags nicht überschreiben
        if meta.tags:
            logger.debug(
                "Auto-Tagging übersprungen: Asset %s hat bereits Tags: %s",
                asset_id,
                meta.tags,
            )
            return

        # Prompt aus Image-Step extrahieren (falls vorhanden)
        prompt: str | None = None
        for step_data in meta.steps.values():
            if isinstance(step_data, dict) and step_data.get("prompt"):
                p = step_data["prompt"]
                if p and p != "[mesh from image]":
                    prompt = str(p)
                    break

        pipeline_steps = list(meta.steps.keys())

        # Nachricht für Tagging-Agent aufbauen
        parts = [f"Asset-ID: {asset_id}"]
        if prompt:
            parts.append(f"Generierungs-Prompt: {prompt}")
        if pipeline_steps:
            parts.append(f"Pipeline-Stand: {', '.join(pipeline_steps)}")
        message = "\n".join(parts)

        run_input: list[str | BinaryContent] = [message]

        # Vorschaubild für Vision-Analyse anfügen (wenn vorhanden)
        for step_name in ("bgremoval", "image"):
            if step_name in meta.steps and meta.steps[step_name].get("file"):
                filename = meta.steps[step_name]["file"]
                img_path = asset_service.get_file_path(asset_id, str(filename))
                if img_path and img_path.is_file():
                    suffix = Path(str(filename)).suffix.lower()
                    media_type = "image/png" if suffix == ".png" else "image/jpeg"
                    img_bytes = img_path.read_bytes()
                    run_input.append(BinaryContent(data=img_bytes, media_type=media_type))
                    break

        agent = get_tagging_agent()
        result = await agent.run(run_input)
        output = result.output
        if output is None or not output.tags:
            logger.debug("Auto-Tagging: keine Tags vorgeschlagen für Asset %s", asset_id)
            return

        get_metadata_service().update(asset_id, tags=output.tags)
        logger.info(
            "Auto-Tagging: Asset %s getaggt mit %s (confidence=%.2f)",
            asset_id,
            output.tags,
            output.confidence,
        )

    except Exception as e:
        # Auto-Tagging ist Best-Effort — Fehler dürfen Mesh-Job nicht beeinflussen
        logger.warning(
            "Auto-Tagging fehlgeschlagen für Asset %s: %s: %s",
            asset_id,
            type(e).__name__,
            e,
        )
