"""
Sketchfab-Service: Upload und Download von 3D-Modellen.
API-Dokumentation: https://sketchfab.com/developers/data-api/v3
"""

import asyncio
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import httpx
import trimesh

from app.services import asset_service

logger = logging.getLogger(__name__)

# Regex für UID aus Sketchfab-URL: /models/{uid} oder /3d-models/name-{uid}
SKETCHFAB_UID_PATTERN = re.compile(
    r"(?:sketchfab\.com/(?:3d-models/[^/]+-)?|/models/)([a-zA-Z0-9]{8,})"
)


class SketchfabUploadResult:
    """Ergebnis eines erfolgreichen Sketchfab-Uploads."""

    def __init__(
        self,
        uid: str,
        url: str,
        embed_url: str,
    ):
        self.uid = uid
        self.url = url
        self.embed_url = embed_url


def _extract_uid(url_or_uid: str) -> str | None:
    """Extrahiert Sketchfab-Model-UID aus URL oder gibt UID zurück wenn bereits UID."""
    url_or_uid = url_or_uid.strip()
    # Direkte UID (alphanumerisch, typisch 8+ Zeichen)
    if re.fullmatch(r"[a-zA-Z0-9]{8,}", url_or_uid):
        return url_or_uid
    m = SKETCHFAB_UID_PATTERN.search(url_or_uid)
    return m.group(1) if m else None


class SketchfabService:
    """Sketchfab API-Client für Upload und Download."""

    BASE_URL = "https://api.sketchfab.com/v3"

    def __init__(self, api_token: str):
        self._token = api_token
        self._headers = {"Authorization": f"Token {api_token}"}

    async def upload_model(
        self,
        asset_id: str,
        source_file: str,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        is_private: bool = False,
    ) -> SketchfabUploadResult:
        """
        Lädt GLB aus Asset-Ordner zu Sketchfab hoch.
        Pollt bis Processing abgeschlossen, gibt uid, url, embed_url zurück.
        """
        tags = tags or []
        path = asset_service.get_file_path(asset_id, source_file)
        if not path or not path.exists():
            raise FileNotFoundError(f"Datei {source_file} nicht in Asset {asset_id}")

        file_bytes = path.read_bytes()

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Multipart: modelFile + Form-Felder
            files = {"modelFile": (source_file, file_bytes, "model/gltf-binary")}
            data: dict[str, str | int] = {
                "name": name,
                "description": description or "",
                "private": 1 if is_private else 0,
            }
            if tags:
                # Sketchfab erwartet tags als kommasepariert oder JSON
                data["tags"] = ",".join(t.strip() for t in tags if t.strip())

            response = await client.post(
                f"{self.BASE_URL}/models",
                headers=self._headers,
                data=data,
                files=files,
            )

            if response.status_code != 201:
                err_body = response.text
                try:
                    err_json = response.json()
                    err_msg = err_json.get("detail", err_json.get("error", err_body))
                except (ValueError, json.JSONDecodeError):
                    logger.debug("Sketchfab error response not JSON")
                    err_msg = err_body
                raise RuntimeError(f"Sketchfab Upload fehlgeschlagen: {err_msg}")

            location = response.headers.get("Location", "")
            # Location: https://api.sketchfab.com/v3/models/{uid}
            uid = location.rstrip("/").split("/")[-1] if location else ""
            if not uid:
                raise RuntimeError("Sketchfab gab keine Model-UID zurück")

            # Polling bis processing done
            url, embed_url = await self._poll_until_ready(client, uid)
            return SketchfabUploadResult(uid=uid, url=url, embed_url=embed_url)

    async def _poll_until_ready(
        self, client: httpx.AsyncClient, uid: str
    ) -> tuple[str, str]:
        """Pollt GET /models/{uid} bis processing abgeschlossen."""
        max_attempts = 60
        interval = 5.0

        for _ in range(max_attempts):
            resp = await client.get(
                f"{self.BASE_URL}/models/{uid}",
                headers=self._headers,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Sketchfab Model-Abfrage fehlgeschlagen: {resp.status_code}"
                )
            data = resp.json()

            processing = data.get("processing", "")
            if processing and processing.lower() != "done":
                await asyncio.sleep(interval)
                continue

            # Erfolg: url und embed_url aus Response
            url = data.get("viewerUrl", f"https://sketchfab.com/3d-models/{uid}")
            thumbnails = data.get("thumbnails", {}).get("images", [])
            embed_url = ""
            if thumbnails:
                # Größtes Thumbnail für Embed
                sorted_thumbs = sorted(
                    thumbnails, key=lambda t: t.get("width", 0), reverse=True
                )
                if sorted_thumbs:
                    embed_url = sorted_thumbs[0].get("url", "")

            return url, embed_url

        raise RuntimeError("Sketchfab Processing-Timeout: Modell wurde nicht rechtzeitig fertig")

    async def download_model(
        self,
        sketchfab_url_or_uid: str,
        target_name: str | None = None,
    ) -> str:
        """
        Lädt Modell von Sketchfab herunter, legt neues Asset an.
        Gibt asset_id des neu erstellten Assets zurück.
        Konvertiert ggf. OBJ/glTF zu GLB via trimesh.
        """
        uid = _extract_uid(sketchfab_url_or_uid)
        if not uid:
            raise ValueError(
                "Ungültige Sketchfab-URL oder UID. Erwartet: "
                "https://sketchfab.com/3d-models/... oder Model-UID"
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/models/{uid}/download",
                headers=self._headers,
            )
            if resp.status_code == 403:
                raise RuntimeError(
                    "Modell ist nicht zum Download freigegeben. "
                    "Nur eigene Modelle oder Modelle mit 'Downloadable'-Flag können importiert werden."
                )
            if resp.status_code == 404:
                raise RuntimeError("Sketchfab-Modell nicht gefunden")
            if resp.status_code != 200:
                err = resp.text
                try:
                    err_json = resp.json()
                    err = err_json.get("detail", err_json.get("error", err))
                except (ValueError, json.JSONDecodeError):
                    pass
                raise RuntimeError(f"Sketchfab Download fehlgeschlagen: {err}")

            data = resp.json()
            gltf_info = data.get("gltf", {})
            download_url = gltf_info.get("url")
            if not download_url:
                raise RuntimeError("Sketchfab lieferte keine Download-URL")

            # ZIP herunterladen
            dl_resp = await client.get(download_url)
            dl_resp.raise_for_status()
            zip_bytes = dl_resp.content

        # Neues Asset anlegen
        asset_id = asset_service.create_asset()
        asset_dir = asset_service.get_asset_dir(asset_id)

        # ZIP entpacken und zu GLB konvertieren
        glb_path = await asyncio.to_thread(
            _extract_and_convert_to_glb, zip_bytes, asset_dir
        )
        if not glb_path:
            asset_service.delete_asset(asset_id)
            raise RuntimeError("Konvertierung zu GLB fehlgeschlagen")

        # metadata.json erweitern: source, sketchfab_*
        model_info = await self._get_model_info(uid)
        now = datetime.now(timezone.utc).isoformat()
        metadata_update: dict[str, Any] = {
            "source": "sketchfab",
            "sketchfab_uid": uid,
            "sketchfab_url": f"https://sketchfab.com/3d-models/{uid}",
            "downloaded_at": now,
        }
        if model_info:
            metadata_update["sketchfab_author"] = model_info.get("user", {}).get(
                "username", ""
            )

        # Mesh-Step anlegen (analog persist_mesh_job, aber ohne job_id)
        step_data: dict[str, Any] = {
            "provider_key": "sketchfab",
            "source_file": glb_path.name,
            "file": glb_path.name,
            "generated_at": now,
        }
        await asset_service.update_step(
            asset_id, "mesh", step_data, file_bytes=glb_path.read_bytes(), filename=glb_path.name
        )

        # Top-Level Metadata-Felder schreiben
        _update_metadata_fields(asset_id, metadata_update)

        logger.info("Sketchfab-Import: %s -> Asset %s", uid, asset_id)
        return asset_id

    async def _get_model_info(self, uid: str) -> dict[str, Any] | None:
        """Holt Model-Infos von Sketchfab (für Author etc.)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/models/{uid}",
                    headers=self._headers,
                )
                if resp.status_code == 200:
                    return cast(dict[str, Any], resp.json())
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.debug("Sketchfab Model-Info nicht abrufbar: %s", e)
        return None

    async def list_my_models(self) -> list[dict[str, Any]]:
        """Listet eigene Sketchfab-Modelle mit Thumbnail, Name, Vertex/Face-Count."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/me/models",
                headers=self._headers,
            )
            if resp.status_code != 200:
                err = resp.text
                try:
                    err_json = resp.json()
                    err = err_json.get("detail", err_json.get("error", err))
                except (ValueError, json.JSONDecodeError):
                    pass
                raise RuntimeError(f"Sketchfab Me/Models fehlgeschlagen: {err}")

            data = resp.json()
            results = data.get("results", [])

        models: list[dict[str, Any]] = []
        for m in results:
            uid = m.get("uid", "")
            thumbnails = m.get("thumbnails", {}).get("images", [])
            thumb_url = ""
            if thumbnails:
                sorted_thumbs = sorted(
                    thumbnails, key=lambda t: t.get("width", 0), reverse=True
                )
                if sorted_thumbs:
                    thumb_url = sorted_thumbs[0].get("url", "")

            models.append(
                {
                    "uid": uid,
                    "name": m.get("name", ""),
                    "url": m.get("viewerUrl", f"https://sketchfab.com/3d-models/{uid}"),
                    "thumbnail_url": thumb_url,
                    "vertex_count": m.get("vertexCount", 0),
                    "face_count": m.get("faceCount", 0),
                    "is_downloadable": m.get("isDownloadable", False),
                    "created_at": m.get("createdAt", ""),
                }
            )
        return models


def _extract_and_convert_to_glb(zip_bytes: bytes, target_dir: Path) -> Path | None:
    """
    Entpackt Sketchfab-ZIP (glTF oder OBJ), konvertiert zu GLB, speichert in target_dir.
    Gibt Pfad zur erstellten GLB-Datei zurück.
    """
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        # Suche scene.gltf, scene.bin oder .obj
        gltf_file = next((n for n in names if n.endswith(".gltf")), None)
        obj_files = [n for n in names if n.lower().endswith(".obj")]

        if gltf_file:
            # glTF: Entpacken, dann mit trimesh laden und als GLB exportieren
            extract_dir = target_dir / "_sketchfab_extract"
            extract_dir.mkdir(exist_ok=True)
            zf.extractall(extract_dir)
            gltf_path = extract_dir / gltf_file
            if not gltf_path.exists():
                gltf_path = extract_dir / Path(gltf_file).name
            try:
                scene = trimesh.load(str(gltf_path), file_type="gltf")
                if isinstance(scene, trimesh.Scene):
                    # Alle Meshes zu einem zusammenführen falls nötig
                    meshes = list(scene.geometry.values())
                    if len(meshes) == 1:
                        mesh = meshes[0]
                    else:
                        mesh = trimesh.util.concatenate(meshes)
                else:
                    mesh = scene
                out_path = target_dir / "mesh.glb"
                mesh.export(str(out_path))
                _cleanup_extract(extract_dir)
                return out_path
            except (ValueError, OSError) as e:
                logger.warning("glTF-Konvertierung fehlgeschlagen: %s", e)
                _cleanup_extract(extract_dir)

        if obj_files:
            extract_dir = target_dir / "_sketchfab_extract"
            extract_dir.mkdir(exist_ok=True)
            zf.extractall(extract_dir)
            obj_path = extract_dir / obj_files[0]
            if not obj_path.exists():
                obj_path = extract_dir / Path(obj_files[0]).name
            try:
                mesh = trimesh.load(str(obj_path), file_type="obj")
                if isinstance(mesh, trimesh.Scene):
                    meshes = list(mesh.geometry.values())
                    mesh = trimesh.util.concatenate(meshes) if meshes else None
                if mesh is not None:
                    out_path = target_dir / "mesh.glb"
                    mesh.export(str(out_path))
                    _cleanup_extract(extract_dir)
                    return out_path
            except (ValueError, OSError) as e:
                logger.warning("OBJ-Konvertierung fehlgeschlagen: %s", e)
                _cleanup_extract(extract_dir)

    return None


def _cleanup_extract(extract_dir: Path) -> None:
    """Löscht temporäres Extraktionsverzeichnis."""
    try:
        import shutil

        shutil.rmtree(extract_dir, ignore_errors=True)
    except OSError:
        pass


def _update_metadata_fields(asset_id: str, fields: dict[str, Any]) -> None:
    """Aktualisiert Top-Level-Felder in metadata.json."""
    asset_service.update_metadata_fields(asset_id, fields)
