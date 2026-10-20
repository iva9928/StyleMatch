"""Tests for in-memory clothing management and image utilities."""

from hashlib import sha256

import pytest
from PIL import Image

from stylematch.images import (
    ImageValidationError,
    create_thumbnail,
    validate_image,
)
from stylematch.services.clothing_manager import ClothingManager


def _create_image(path, image_format="PNG", size=(120, 80)):
    Image.new("RGB", size, color="plum").save(path, format=image_format)
    return path


def test_add_item_trims_name_and_assigns_unique_ids(tmp_path):
    manager = ClothingManager()
    image_path = _create_image(tmp_path / "shirt.png")

    first = manager.add_item("  Pink T-shirt  ", "Tops", image_path)
    second = manager.add_item("Blue jeans", "Bottoms", image_path)

    assert first.name == "Pink T-shirt"
    assert first.category == "Tops"
    assert first.image_path == str(image_path)
    assert first.id != second.id


@pytest.mark.parametrize("name", ("", " ", "\t\n"))
def test_add_item_rejects_empty_name(tmp_path, name):
    manager = ClothingManager()
    image_path = _create_image(tmp_path / "shirt.png")

    with pytest.raises(ValueError, match="clothing name"):
        manager.add_item(name, "Tops", image_path)

    assert manager.list_items() == []


def test_add_item_rejects_invalid_category(tmp_path):
    manager = ClothingManager()
    image_path = _create_image(tmp_path / "shirt.png")

    with pytest.raises(ValueError, match="category"):
        manager.add_item("Shirt", "Accessories", image_path)


def test_add_item_rejects_missing_image_path():
    manager = ClothingManager()

    with pytest.raises(ValueError, match="Choose an image"):
        manager.add_item("Shirt", "Tops", None)


def test_add_item_rejects_unavailable_image(tmp_path):
    manager = ClothingManager()

    with pytest.raises(ImageValidationError, match="could not be found"):
        manager.add_item("Shirt", "Tops", tmp_path / "missing.png")


@pytest.mark.parametrize("image_format, extension", [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")])
def test_supported_formats_validate_and_create_thumbnail(
    tmp_path,
    image_format,
    extension,
):
    image_path = _create_image(
        tmp_path / f"clothing{extension}",
        image_format=image_format,
    )

    validate_image(image_path)
    thumbnail = create_thumbnail(image_path, (60, 60))

    assert thumbnail.size == (60, 40)


def test_manager_rejects_corrupt_and_unsupported_image_files(tmp_path):
    manager = ClothingManager()
    corrupt_path = tmp_path / "corrupt.png"
    corrupt_path.write_text("not an image", encoding="utf-8")
    unsupported_path = _create_image(
        tmp_path / "unsupported.gif",
        image_format="GIF",
    )

    for image_path in (corrupt_path, unsupported_path):
        with pytest.raises(ImageValidationError):
            manager.add_item("Item", "Tops", image_path)

    assert manager.list_items() == []


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((80, 160), (30, 60)),
        ((160, 80), (60, 30)),
    ],
)
def test_thumbnail_preserves_portrait_and_landscape_proportions(
    tmp_path,
    size,
    expected,
):
    image_path = _create_image(tmp_path / "item.png", size=size)

    thumbnail = create_thumbnail(image_path, (60, 60))

    assert thumbnail.size == expected
    assert thumbnail.width / thumbnail.height == pytest.approx(
        size[0] / size[1]
    )


def test_image_utilities_handle_unavailable_path(tmp_path):
    missing_path = tmp_path / "missing.webp"

    with pytest.raises(ImageValidationError, match="could not be found"):
        validate_image(missing_path)
    with pytest.raises(ImageValidationError, match="could not be found"):
        create_thumbnail(missing_path, (60, 60))


def test_thumbnail_does_not_modify_original_image(tmp_path):
    image_path = _create_image(tmp_path / "original.png", size=(180, 120))
    original_hash = sha256(image_path.read_bytes()).digest()

    create_thumbnail(image_path, (60, 60))

    assert sha256(image_path.read_bytes()).digest() == original_hash
    with Image.open(image_path) as original:
        assert original.size == (180, 120)


def test_list_all_and_filter_by_category(tmp_path):
    manager = ClothingManager()
    image_path = _create_image(tmp_path / "item.png")
    top = manager.add_item("Top", "Tops", image_path)
    shoes = manager.add_item("Shoes", "Shoes", image_path)

    assert manager.list_items() == [top, shoes]
    assert manager.list_items("Tops") == [top]
    assert manager.list_items("Shoes") == [shoes]


def test_delete_existing_and_nonexistent_items(tmp_path):
    manager = ClothingManager()
    image_path = _create_image(tmp_path / "item.png")
    item = manager.add_item("Top", "Tops", image_path)

    assert manager.delete_item(item.id) is True
    assert manager.list_items() == []
    assert manager.delete_item(item.id) is False
    assert manager.delete_item("unknown-id") is False
