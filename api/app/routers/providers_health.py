"""
Provider-Gesundheits-Dashboard: Zeigt an, welche Provider konfiguriert und erreichbar sind.

Verwendet ausschließlich Konfigurationsprüfungen (keine echten API-Aufrufe),
um eine schnelle und kostengünstige Statusübersicht zu liefern.
Results are cached for 60 seconds.
"""

import logging
import os
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.bgremoval_providers.registry import (
    list_available_keys as list_bgremoval_keys,
)
from app.services.image_providers.registry import (
    list_available_keys as list_image_keys,
)
from app.services.mesh_providers.registry import (
    list_available_keys as list_mesh_keys,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])

ProviderStatus = Literal["healthy", "degraded", "unavailable"]

_CACHE_TTL = 60.0  # Sekunden
_cache: dict | None = None
_cache_ts: float = 0.0


class ProviderHealthInfo(BaseModel):
    """Gesundheitsstatus eines einzelnen Providers."""

    key: str
    display_name: str
    provider_type: str  # image | mesh | bgremoval | rigging | animation
    status: ProviderStatus
    reason: str | None = None


class ProvidersHealthResponse(BaseModel):
    """Übersicht über alle Provider-Status."""

    providers: list[ProviderHealthInfo]
    cached: bool = False
    checked_at: float  # Unix-Timestamp


def _check_image_providers() -> list[ProviderHealthInfo]:
    """Prüft Image-Provider via Konfigurationscheck."""
    results: list[ProviderHealthInfo] = []

    picsart_key = os.getenv("PICSART_API_KEY", "")
    picsart_status: ProviderStatus = "healthy" if picsart_key else "unavailable"
    picsart_reason = None if picsart_key else "PICSART_API_KEY nicht gesetzt"

    picsart_providers = {
        "picsart-default": "PicsArt Standard",
        "picsart-flux-dev": "PicsArt Flux Dev",
        "picsart-flux-max": "PicsArt Flux Max",
        "picsart-dalle3": "PicsArt DALL-E 3",
        "picsart-ideogram": "PicsArt Ideogram",
    }
    available = list_image_keys()
    for key, name in picsart_providers.items():
        if key in available:
            results.append(ProviderHealthInfo(
                key=key,
                display_name=name,
                provider_type="image",
                status=picsart_status,
                reason=picsart_reason,
            ))

    # HF Inference
    hf_token = os.getenv("HF_TOKEN", "")
    if "hf-inference" in available:
        results.append(ProviderHealthInfo(
            key="hf-inference",
            display_name="HF Inference",
            provider_type="image",
            status="healthy" if hf_token else "unavailable",
            reason=None if hf_token else "HF_TOKEN nicht gesetzt",
        ))

    # Replicate
    replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    if "replicate" in available:
        results.append(ProviderHealthInfo(
            key="replicate",
            display_name="Replicate",
            provider_type="image",
            status="healthy" if replicate_token else "unavailable",
            reason=None if replicate_token else "REPLICATE_API_TOKEN nicht gesetzt",
        ))

    return results


def _check_mesh_providers() -> list[ProviderHealthInfo]:
    """Prüft Mesh-Provider via Konfigurationscheck."""
    results: list[ProviderHealthInfo] = []
    available = list_mesh_keys()

    hf_token = os.getenv("HF_TOKEN", "")
    piapi_key = os.getenv("PIAPI_API_KEY", "")

    mesh_config = {
        "hunyuan3d-2": ("Hunyuan3D-2 (HF Space)", "healthy" if hf_token else "unavailable", None if hf_token else "HF_TOKEN nicht gesetzt"),
        "triposr": ("TripoSR (lokal)", "healthy", None),
        "trellis2": ("TRELLIS.2 (HF Space)", "healthy" if hf_token else "unavailable", None if hf_token else "HF_TOKEN nicht gesetzt"),
        "trellis-piapi": ("TRELLIS PiAPI", "healthy" if piapi_key else "unavailable", None if piapi_key else "PIAPI_API_KEY nicht gesetzt"),
    }

    for key, (name, status, reason) in mesh_config.items():
        if key in available:
            results.append(ProviderHealthInfo(
                key=key,
                display_name=name,
                provider_type="mesh",
                status=status,
                reason=reason,
            ))

    return results


def _check_bgremoval_providers() -> list[ProviderHealthInfo]:
    """Prüft BgRemoval-Provider via Konfigurationscheck."""
    results: list[ProviderHealthInfo] = []
    available = list_bgremoval_keys()

    bgremoval_config = {
        "rembg-local": ("rembg (lokal)", "healthy", None),
        "birefnet": ("BiRefNet (HF Space)", "healthy" if os.getenv("HF_TOKEN") else "degraded", None if os.getenv("HF_TOKEN") else "HF_TOKEN fehlt – BiRefNet könnte Rate-Limits haben"),
    }

    for key, (name, status, reason) in bgremoval_config.items():
        if key in available:
            results.append(ProviderHealthInfo(
                key=key,
                display_name=name,
                provider_type="bgremoval",
                status=status,
                reason=reason,
            ))

    return results


def _check_rigging_providers() -> list[ProviderHealthInfo]:
    """Prüft Rigging-Provider via Konfigurationscheck."""
    results: list[ProviderHealthInfo] = []

    hf_token = os.getenv("HF_TOKEN", "")
    unirig_model_path = os.getenv("UNIRIG_MODEL_PATH", "")
    blender_exec = os.getenv("BLENDER_EXECUTABLE", "")

    try:
        from app.providers.rigging import list_rigging_providers  # noqa: PLC0415
        providers = list_rigging_providers()
        for p in providers:
            if p.key == "unirig":
                status: ProviderStatus = "healthy" if (hf_token or unirig_model_path) else "unavailable"
                reason = None if (hf_token or unirig_model_path) else "HF_TOKEN oder UNIRIG_MODEL_PATH erforderlich"
            elif p.key == "blender-rigify":
                status = "healthy" if blender_exec else "unavailable"
                reason = None if blender_exec else "BLENDER_EXECUTABLE nicht gesetzt"
            else:
                status = "healthy"
                reason = None
            results.append(ProviderHealthInfo(
                key=p.key,
                display_name=p.display_name,
                provider_type="rigging",
                status=status,
                reason=reason,
            ))
    except Exception as e:
        logger.warning("Fehler beim Prüfen der Rigging-Provider: %s", e)

    return results


def _check_animation_providers() -> list[ProviderHealthInfo]:
    """Prüft Animation-Provider via Konfigurationscheck."""
    results: list[ProviderHealthInfo] = []

    hf_token = os.getenv("HF_TOKEN", "")

    try:
        from app.providers.animation import list_animation_providers  # noqa: PLC0415
        providers = list_animation_providers()
        for p in providers:
            status: ProviderStatus = "healthy" if hf_token else "unavailable"
            reason = None if hf_token else "HF_TOKEN nicht gesetzt"
            results.append(ProviderHealthInfo(
                key=p.key,
                display_name=p.display_name,
                provider_type="animation",
                status=status,
                reason=reason,
            ))
    except Exception as e:
        logger.warning("Fehler beim Prüfen der Animation-Provider: %s", e)

    return results


@router.get("/health", response_model=ProvidersHealthResponse)
async def get_providers_health() -> ProvidersHealthResponse:
    """
    Gibt den Gesundheitsstatus aller konfigurierten Provider zurück.

    Prüft Konfigurationsvariablen (API Keys, Tokens, Executable-Pfade).
    Ergebnisse werden 60 Sekunden gecacht.

    Status-Werte:
    - `healthy`: Provider ist konfiguriert und sollte funktionieren
    - `degraded`: Provider ist verfügbar, aber ohne optionale Konfiguration eingeschränkt
    - `unavailable`: Erforderliche Konfiguration fehlt
    """
    global _cache, _cache_ts

    now = time.time()
    if _cache is not None and (now - _cache_ts) < _CACHE_TTL:
        return ProvidersHealthResponse(**_cache, cached=True)

    providers: list[ProviderHealthInfo] = []
    providers.extend(_check_image_providers())
    providers.extend(_check_mesh_providers())
    providers.extend(_check_bgremoval_providers())
    providers.extend(_check_rigging_providers())
    providers.extend(_check_animation_providers())

    response_data = {
        "providers": [p.model_dump() for p in providers],
        "checked_at": now,
    }
    _cache = response_data
    _cache_ts = now

    return ProvidersHealthResponse(providers=providers, cached=False, checked_at=now)
