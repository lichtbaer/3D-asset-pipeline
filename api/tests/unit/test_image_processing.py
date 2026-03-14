"""
Unit-Tests für image_processing_service.
Alle Operationen sind nicht-destruktiv — Original-Dateien werden nie überschrieben.
"""

import json
import uuid

import pytest

from app.services import image_processing_service


def test_crop_does_not_overwrite_original(sample_asset_with_image: str, tmp_storage_paths):
    """Crop speichert image_cropped.png, Original bleibt."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    original_path = asset_dir / "image_original.png"
    original_content = original_path.read_bytes()

    output_file, *_ = image_processing_service.crop(
        sample_asset_with_image, "image_original.png", 0, 0, 50, 50
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "image_cropped.png"
    assert (asset_dir / output_file).exists()


def test_resize_does_not_overwrite_original(sample_asset_with_image: str, tmp_storage_paths):
    """Resize speichert image_resized.png, Original bleibt."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    original_path = asset_dir / "image_original.png"
    original_content = original_path.read_bytes()

    output_file, *_ = image_processing_service.resize(
        sample_asset_with_image, "image_original.png", 50, 50, maintain_aspect=True
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "image_resized.png"


def test_pad_to_square_does_not_overwrite_original(
    sample_asset_with_image: str, tmp_storage_paths
):
    """pad_to_square speichert image_squared.png, Original bleibt."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    original_path = asset_dir / "image_original.png"
    original_content = original_path.read_bytes()

    output_file, w, h, _ = image_processing_service.pad_to_square(
        sample_asset_with_image, "image_original.png", background="white"
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "image_squared.png"
    assert w == h == 100


def test_center_subject_creates_new_file(sample_asset_with_image: str, tmp_storage_paths):
    """center_subject speichert image_centered.png."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    original_path = asset_dir / "image_original.png"
    original_content = original_path.read_bytes()

    output_file, *_ = image_processing_service.center_subject(
        sample_asset_with_image, "image_original.png", padding=0.1
    )

    assert original_path.read_bytes() == original_content
    assert output_file == "image_centered.png"


def test_resize_invalid_dimensions_raises(sample_asset_with_image: str, tmp_storage_paths):
    """Breite/Höhe < 1 wirft ValueError."""
    with pytest.raises(ValueError, match="größer 0"):
        image_processing_service.resize(
            sample_asset_with_image, "image_original.png", 0, 50
        )


def test_crop_dimensions_correct(sample_asset_with_image: str, tmp_storage_paths):
    """Crop erzeugt Bild mit exakten Dimensionen."""
    from PIL import Image

    image_processing_service.crop(
        sample_asset_with_image, "image_original.png", x=0, y=0, width=50, height=30
    )
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    img = Image.open(asset_dir / "image_cropped.png")
    assert img.size == (50, 30)


def test_resize_maintains_aspect_ratio(sample_asset_with_image: str, tmp_storage_paths):
    """Resize mit maintain_aspect=True skaliert ins Zielformat, behält Seitenverhältnis."""
    from PIL import Image

    image_processing_service.resize(
        sample_asset_with_image,
        "image_original.png",
        width=50,
        height=50,
        maintain_aspect=True,
    )
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    img = Image.open(asset_dir / "image_resized.png")
    assert img.size == (50, 50)


def test_pad_to_square_rectangular_image(tmp_storage_paths, tmp_assets_dir):
    """pad_to_square macht 100x200 Bild zu 200x200."""
    from PIL import Image

    asset_id = str(uuid.uuid4())
    asset_path = tmp_assets_dir / asset_id
    asset_path.mkdir(parents=True)
    img = Image.new("RGBA", (100, 200), (255, 0, 0, 255))
    img.save(asset_path / "image.png", "PNG")
    (asset_path / "metadata.json").write_text(
        json.dumps(
            {
                "asset_id": asset_id,
                "steps": {},
                "created_at": "x",
                "updated_at": "x",
                "image_processing": [],
            }
        ),
        encoding="utf-8",
    )
    image_processing_service.pad_to_square(asset_id, "image.png")
    result_img = Image.open(asset_path / "image_squared.png")
    assert result_img.size[0] == result_img.size[1] == 200


def test_original_not_overwritten(sample_asset_with_image: str, tmp_storage_paths):
    """Crop überschreibt Original nicht."""
    from app.services import asset_service

    asset_dir = asset_service.get_asset_dir(sample_asset_with_image)
    original_content = (asset_dir / "image_original.png").read_bytes()
    image_processing_service.crop(
        sample_asset_with_image, "image_original.png", 0, 0, 50, 50
    )
    assert (asset_dir / "image_original.png").read_bytes() == original_content
