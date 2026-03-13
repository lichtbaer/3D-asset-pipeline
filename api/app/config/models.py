"""
Modell-Mapping für PicsArt GenAI API.
AIR-URNs aus docs.picsart.io/docs/ai-providers-hub-introduction
"""

MODEL_MAP: dict[str, str | None] = {
    "picsart-default": None,  # kein model-Parameter → PicsArt default
    "flux-dev": "urn:air:sdxl:model:fluxai:flux_kontext_pro@1",
    "flux-max": "urn:air:sdxl:model:fluxai:flux_kontext_max@1",
    "dalle3": "urn:air:openai:model:openai:dall-e-3@1",
    "ideogram-2a": "urn:air:ideogram:model:ideogram:ideogram-2a@1",
}
