"""
Unit-Tests für image_processing_service.
Alle Operationen sind nicht-destruktiv — Original-Dateien werden nie überschrieben.
"""

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
