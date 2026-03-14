"""
Bild-Nachbearbeitung: Crop, Resize, Zentrierung, Pad-to-Square.
Alle Operationen sind nicht-destruktiv — Original-Dateien werden nie überschrieben.
Implementierung via Pillow (bereits in requirements).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from app.services import asset_service

logger = logging.getLogger(__name__)


def _asset_image_path(asset_id: str, filename: str) -> Path:
    """Vollständiger Pfad zu Bild-Datei im Asset-Ordner."""
    path = asset_service.get_file_path(asset_id, filename)
    if not path:
        raise FileNotFoundError(f"Datei {filename} nicht in Asset {asset_id}")
    return path


def _load_image(path: Path) -> Image.Image:
    """Lädt Bild mit Alpha-Kanal falls vorhanden."""
    img = Image.open(path).convert("RGBA")
    return img


def _save_png(img: Image.Image, output_path: Path) -> None:
    """Speichert Bild als PNG."""
    img.save(output_path, "PNG", optimize=True)




def crop(
    asset_id: str,
    source_file: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> tuple[str, int, int, int]:
    """
    Schneidet Bild zu. Speichert image_cropped.png.
    Gibt (output_file, width, height, file_size_bytes) zurück.
    """
    source_path = _asset_image_path(asset_id, source_file)
    img = _load_image(source_path)
    w, h = img.size

    # Bounds prüfen
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    x2 = min(x + width, w)
    y2 = min(y + height, h)
    if x2 <= x or y2 <= y:
        raise ValueError("Ungültige Crop-Koordinaten: Bereich außerhalb des Bildes")

    cropped = img.crop((x, y, x2, y2))
    output_filename = "image_cropped.png"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    _save_png(cropped, output_path)

    file_size = output_path.stat().st_size
    asset_service.append_image_processing_entry(
        asset_id,
        {
            "operation": "crop",
            "params": {"x": x, "y": y, "width": x2 - x, "height": y2 - y},
            "source_file": source_file,
            "output_file": output_filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Asset %s: crop %s -> %s (%d×%d)", asset_id, source_file, output_filename, x2 - x, y2 - y)
    return output_filename, x2 - x, y2 - y, file_size


def resize(
    asset_id: str,
    source_file: str,
    width: int,
    height: int,
    maintain_aspect: bool = True,
) -> tuple[str, int, int, int]:
    """
    Skaliert Bild. Speichert image_resized.png.
    Bei maintain_aspect=True wird ins Zielformat skaliert und ggf. Padding.
    Gibt (output_file, width, height, file_size_bytes) zurück.
    """
    source_path = _asset_image_path(asset_id, source_file)
    img = _load_image(source_path)
    w, h = img.size

    if width < 1 or height < 1:
        raise ValueError("Breite und Höhe müssen größer 0 sein")

    if maintain_aspect:
        # Skalieren sodass Bild in Zielformat passt, Seitenverhältnis beibehalten
        scale = min(width / w, height / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Wenn kleiner als Ziel: Padding hinzufügen (transparent)
        if new_w < width or new_h < height:
            out_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            paste_x = (width - new_w) // 2
            paste_y = (height - new_h) // 2
            out_img.paste(resized, (paste_x, paste_y))
            resized = out_img
    else:
        resized = img.resize((width, height), Image.Resampling.LANCZOS)

    output_filename = "image_resized.png"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    _save_png(resized, output_path)

    file_size = output_path.stat().st_size
    asset_service.append_image_processing_entry(
        asset_id,
        {
            "operation": "resize",
            "params": {"width": width, "height": height, "maintain_aspect": maintain_aspect},
            "source_file": source_file,
            "output_file": output_filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Asset %s: resize %s -> %s (%d×%d)", asset_id, source_file, output_filename, resized.width, resized.height)
    return output_filename, resized.width, resized.height, file_size


def center_subject(
    asset_id: str,
    source_file: str,
    padding: float = 0.1,
) -> tuple[str, int, int, int]:
    """
    Erkennt Nicht-Transparent-Bereich, zentriert Subjekt, fügt Padding hinzu.
    Setzt voraus dass Bild bereits freigestellt ist (transparenter Hintergrund).
    Speichert image_centered.png.
    Gibt (output_file, width, height, file_size_bytes) zurück.
    """
    source_path = _asset_image_path(asset_id, source_file)
    img = _load_image(source_path)
    w, h = img.size

    # Bounding Box der nicht-transparenten Pixel finden
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        # Vollständig transparent — gesamtes Bild behalten
        bbox = (0, 0, w, h)

    x1, y1, x2, y2 = bbox
    subj_w = x2 - x1
    subj_h = y2 - y1

    # Padding als Anteil der Subjekt-Breite/Höhe
    pad_w = max(0, int(subj_w * padding))
    pad_h = max(0, int(subj_h * padding))
    new_w = subj_w + 2 * pad_w
    new_h = subj_h + 2 * pad_h

    # Subjekt aus dem Original ausschneiden und in neues Zentrum setzen
    out_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    cropped = img.crop((x1, y1, x2, y2))
    out_img.paste(cropped, (pad_w, pad_h))

    output_filename = "image_centered.png"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    _save_png(out_img, output_path)

    file_size = output_path.stat().st_size
    asset_service.append_image_processing_entry(
        asset_id,
        {
            "operation": "center",
            "params": {"padding": padding},
            "source_file": source_file,
            "output_file": output_filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Asset %s: center_subject %s -> %s (%d×%d)", asset_id, source_file, output_filename, new_w, new_h)
    return output_filename, new_w, new_h, file_size


def pad_to_square(
    asset_id: str,
    source_file: str,
    background: str = "white",
) -> tuple[str, int, int, int]:
    """
    Fügt Padding hinzu bis Bild quadratisch ist.
    Speichert image_squared.png.
    background: "white" | "black" | "transparent"
    Gibt (output_file, width, height, file_size_bytes) zurück.
    """
    source_path = _asset_image_path(asset_id, source_file)
    img = _load_image(source_path)
    w, h = img.size

    side = max(w, h)
    if side == 0:
        raise ValueError("Bild hat keine Größe")

    # Hintergrundfarbe
    if background == "white":
        fill = (255, 255, 255, 255)
    elif background == "black":
        fill = (0, 0, 0, 255)
    elif background == "transparent":
        fill = (0, 0, 0, 0)
    else:
        fill = (255, 255, 255, 255)

    out_img = Image.new("RGBA", (side, side), fill)
    paste_x = (side - w) // 2
    paste_y = (side - h) // 2
    out_img.paste(img, (paste_x, paste_y))

    output_filename = "image_squared.png"
    output_path = asset_service.get_asset_dir(asset_id) / output_filename
    _save_png(out_img, output_path)

    file_size = output_path.stat().st_size
    asset_service.append_image_processing_entry(
        asset_id,
        {
            "operation": "pad_square",
            "params": {"background": background},
            "source_file": source_file,
            "output_file": output_filename,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Asset %s: pad_to_square %s -> %s (%d×%d)", asset_id, source_file, output_filename, side, side)
    return output_filename, side, side, file_size
