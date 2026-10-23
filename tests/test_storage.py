"""Tests for local wardrobe JSON and managed image persistence."""

import json
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

import stylematch.app as app_module
from stylematch.models.clothing import ClothingItem
from stylematch.services.clothing_manager import ClothingManager
from stylematch.storage import data_paths
from stylematch.storage.json_store import JSONStore, StorageError
from stylematch.storage.wardrobe_persistence import WardrobePersistence


def _create_image(path: Path, image_format: str = "PNG") -> Path:
    Image.new("RGB", (48, 72), color="plum").save(path, format=image_format)
    return path


def test_empty_wardrobe_is_saved_and_loaded(tmp_path):
    persistence = WardrobePersistence(tmp_path)

    assert persistence.load_items() == []
    persistence.save_items([])

    assert json.loads((tmp_path / "wardrobe.json").read_text(encoding="utf-8")) == {
        "version": 1,
        "clothing": [],
    }
    assert persistence.load_items() == []


def test_persistent_manager_restores_items_and_imported_images(tmp_path):
    source = _create_image(tmp_path / "original.png")
    original_hash = sha256(source.read_bytes()).digest()
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence=persistence)

    first = manager.add_item("White Shirt", "Tops", source)
    second = manager.add_item("Plum Dress", "Dresses", source)
    document = json.loads(
        (persistence.data_dir / "wardrobe.json").read_text(encoding="utf-8")
    )

    assert document["version"] == 1
    assert [record["id"] for record in document["clothing"]] == [
        first.id,
        second.id,
    ]
    assert [record["category"] for record in document["clothing"]] == [
        "Tops",
        "Dresses",
    ]
    assert all(
        record["image_path"].startswith("images/")
        for record in document["clothing"]
    )
    assert first.image_path != second.image_path
    assert Path(first.image_path).is_file()
    assert Path(second.image_path).is_file()
    assert source.is_file()
    assert sha256(source.read_bytes()).digest() == original_hash

    restored = ClothingManager(
        persistence=WardrobePersistence(persistence.data_dir)
    )
    assert restored.list_items() == [first, second]


def test_jackets_are_added_and_restored_without_changing_outerwear(tmp_path):
    source = _create_image(tmp_path / "original.png")
    data_dir = tmp_path / "application-data"
    manager = ClothingManager(persistence=WardrobePersistence(data_dir))

    outerwear = manager.add_item("Raincoat", "Outerwear", source)
    jacket = manager.add_item("Leather jacket", "Jackets", source)
    document = json.loads(
        (data_dir / "wardrobe.json").read_text(encoding="utf-8")
    )
    restored = ClothingManager(persistence=WardrobePersistence(data_dir))

    assert document["version"] == 1
    assert [record["category"] for record in document["clothing"]] == [
        "Outerwear",
        "Jackets",
    ]
    assert restored.list_items() == [outerwear, jacket]
    assert restored.list_items("Outerwear") == [outerwear]
    assert restored.list_items("Jackets") == [jacket]
    assert source.is_file()
    assert Path(outerwear.image_path).is_file()
    assert Path(jacket.image_path).is_file()


def test_legacy_wardrobe_metadata_defaults_and_update_round_trip(tmp_path):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    (data_dir / "images").mkdir()
    image_path = _create_image(data_dir / "images" / "managed.png")
    record = {
        "version": 1,
        "clothing": [
            {
                "id": "legacy-top",
                "name": "Legacy shirt",
                "category": "Tops",
                "image_path": "images/managed.png",
            }
        ],
    }
    wardrobe_path = data_dir / "wardrobe.json"
    original_data = json.dumps(record, indent=2)
    wardrobe_path.write_text(original_data, encoding="utf-8")
    persistence = WardrobePersistence(data_dir)
    manager = ClothingManager(persistence)
    item = manager.list_items()[0]

    assert item.primary_color is None
    assert item.style is None
    assert wardrobe_path.read_text(encoding="utf-8") == original_data
    original_managed_path = item.image_path
    updated = manager.update_metadata(item.id, "White", "Business")
    document = json.loads(wardrobe_path.read_text(encoding="utf-8"))
    restored = ClothingManager(WardrobePersistence(data_dir)).list_items()[0]

    assert updated.id == "legacy-top"
    assert updated.image_path == original_managed_path
    assert Path(original_managed_path).is_file()
    assert document["version"] == 1
    assert document["clothing"][0]["primary_color"] == "White"
    assert document["clothing"][0]["style"] == "Business"
    assert restored == updated
    assert image_path.is_file()


def test_metadata_update_persistence_failure_keeps_memory_and_image_safe(
    tmp_path,
    monkeypatch,
):
    source = _create_image(tmp_path / "original.png")
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence)
    item = manager.add_item("Shirt", "Tops", source)
    original_json = persistence.store.path.read_bytes()
    managed_image = Path(item.image_path)

    def fail_save(_items):
        raise StorageError("simulated metadata update failure")

    monkeypatch.setattr(persistence, "save_items", fail_save)
    with pytest.raises(StorageError, match="metadata update failure"):
        manager.update_metadata(item.id, "Navy", "Casual")

    assert manager.list_items() == [item]
    assert managed_image.is_file()
    assert source.is_file()
    assert persistence.store.path.read_bytes() == original_json


def test_persistence_rejects_invalid_metadata_before_writing(tmp_path):
    persistence = WardrobePersistence(tmp_path / "application-data")
    original = persistence.store.path
    item = ClothingItem(
        "invalid-color",
        "Shirt",
        "Tops",
        primary_color="Chartreuse",
    )

    with pytest.raises(StorageError, match="invalid primary color"):
        persistence.save_items([item])

    assert not original.exists()


@pytest.mark.parametrize(
    ("image_format", "extension"),
    [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")],
)
def test_each_supported_format_is_imported_and_restored(
    tmp_path,
    image_format,
    extension,
):
    source = _create_image(tmp_path / f"source{extension}", image_format)
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence=persistence)

    item = manager.add_item("Format test", "Tops", source)
    restored = ClothingManager(
        persistence=WardrobePersistence(persistence.data_dir)
    ).list_items()

    assert Path(item.image_path).suffix == extension
    assert Path(item.image_path).is_file()
    assert restored == [item]


def test_normal_app_startup_loads_one_manager_before_calling_ui(
    tmp_path,
    monkeypatch,
):
    source = _create_image(tmp_path / "source.png")
    persistence = WardrobePersistence(tmp_path / "application-data")
    expected = ClothingManager(persistence=persistence).add_item(
        "Stored item",
        "Tops",
        source,
    )
    captured = {}

    def start_ui(*, manager, startup_warning):
        captured["manager"] = manager
        captured["items_at_ui_start"] = manager.list_items()
        captured["warning"] = startup_warning

    monkeypatch.setattr(app_module, "WardrobePersistence", lambda: persistence)
    monkeypatch.setattr(app_module, "main", start_ui)

    app_module.run()

    assert captured["items_at_ui_start"] == [expected]
    assert captured["manager"].persistence is persistence
    assert captured["warning"] is None


def test_delete_persists_before_removing_managed_copy(tmp_path):
    source = _create_image(tmp_path / "original.webp", image_format="WEBP")
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence=persistence)
    item = manager.add_item("Shoes", "Shoes", source)
    managed_copy = Path(item.image_path)

    assert manager.delete_item(item.id) is True
    assert manager.list_items() == []
    assert not managed_copy.exists()
    assert source.is_file()
    assert json.loads(
        (persistence.data_dir / "wardrobe.json").read_text(encoding="utf-8")
    )["clothing"] == []
    assert ClothingManager(
        persistence=WardrobePersistence(persistence.data_dir)
    ).list_items() == []


def test_failed_add_save_keeps_memory_unchanged_and_cleans_import(
    tmp_path,
    monkeypatch,
):
    source = _create_image(tmp_path / "source.jpg", image_format="JPEG")
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence=persistence)

    def fail_save(_items):
        raise StorageError("test write failure")

    monkeypatch.setattr(persistence, "save_items", fail_save)
    with pytest.raises(StorageError, match="test write failure"):
        manager.add_item("Top", "Tops", source)

    assert manager.list_items() == []
    assert list(persistence.image_dir.glob("*")) == []
    assert source.is_file()


def test_failed_delete_save_preserves_item_and_managed_image(tmp_path, monkeypatch):
    source = _create_image(tmp_path / "source.png")
    persistence = WardrobePersistence(tmp_path / "application-data")
    manager = ClothingManager(persistence=persistence)
    item = manager.add_item("Top", "Tops", source)
    managed_copy = Path(item.image_path)

    def fail_save(_items):
        raise StorageError("test write failure")

    monkeypatch.setattr(persistence, "save_items", fail_save)
    with pytest.raises(StorageError, match="test write failure"):
        manager.delete_item(item.id)

    assert manager.list_items() == [item]
    assert managed_copy.is_file()
    assert source.is_file()


def test_atomic_json_write_failure_preserves_old_file_and_cleans_temp(
    tmp_path,
    monkeypatch,
):
    store = JSONStore(tmp_path / "wardrobe.json")
    store.save({"version": 1, "clothing": []})
    old_data = store.path.read_text(encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("stylematch.storage.json_store.os.replace", fail_replace)
    with pytest.raises(StorageError, match="simulated replace failure"):
        store.save({"version": 1, "clothing": [{"id": "new"}]})

    assert store.path.read_text(encoding="utf-8") == old_data
    assert list(tmp_path.iterdir()) == [store.path]


def test_corrupted_json_is_preserved_under_backup_and_warned(tmp_path):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    original = data_dir / "wardrobe.json"
    original.write_text("{not valid json", encoding="utf-8")
    persistence = WardrobePersistence(data_dir)

    manager = ClothingManager(persistence=persistence)

    backups = list(data_dir.glob("wardrobe.json.corrupt-*.bak"))
    assert manager.list_items() == []
    assert not original.exists()
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not valid json"
    assert persistence.startup_warning is not None
    assert "preserved" in persistence.startup_warning


def test_missing_managed_image_does_not_drop_clothing_record(tmp_path):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    (data_dir / "wardrobe.json").write_text(
        json.dumps(
            {
                "version": 1,
                "clothing": [
                    {
                        "id": "item-1",
                        "name": "Missing image top",
                        "category": "Tops",
                        "image_path": "images/missing.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = ClothingManager(persistence=WardrobePersistence(data_dir))

    assert len(manager.list_items()) == 1
    assert manager.list_items()[0].id == "item-1"
    assert manager.list_items()[0].image_path == str(
        (data_dir / "images" / "missing.png").resolve()
    )


def test_unsafe_image_reference_is_backed_up_instead_of_loaded(tmp_path):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    (data_dir / "wardrobe.json").write_text(
        json.dumps(
            {
                "version": 1,
                "clothing": [
                    {
                        "id": "item-1",
                        "name": "Unsafe image",
                        "category": "Tops",
                        "image_path": "images/../../outside.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    persistence = WardrobePersistence(data_dir)

    assert persistence.load_items() == []
    assert persistence.startup_warning is not None
    assert len(list(data_dir.glob("wardrobe.json.corrupt-*.bak"))) == 1


@pytest.mark.parametrize(
    "document",
    [
        {"version": 2, "clothing": []},
        {
            "version": 1,
            "clothing": [{"id": "missing-fields", "name": "Incomplete"}],
        },
    ],
)
def test_invalid_schema_or_record_is_preserved_before_recovery(
    tmp_path,
    document,
):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    original = data_dir / "wardrobe.json"
    original.write_text(json.dumps(document), encoding="utf-8")
    persistence = WardrobePersistence(data_dir)

    assert persistence.load_items() == []

    backups = list(data_dir.glob("wardrobe.json.corrupt-*.bak"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == document
    assert persistence.startup_warning is not None


def test_save_rejects_nested_managed_path_that_cannot_round_trip(tmp_path):
    persistence = WardrobePersistence(tmp_path / "application-data")
    nested_image = persistence.image_dir / "nested" / "item.png"
    nested_image.parent.mkdir(parents=True)
    _create_image(nested_image)

    item = ClothingItem(
        id="nested-image",
        name="Nested image",
        category="Tops",
        image_path=str(nested_image),
    )

    with pytest.raises(StorageError, match="directly in the images directory"):
        persistence.save_items([item])

    assert not persistence.store.path.exists()


@pytest.mark.parametrize(
    ("operating_system", "environment", "expected"),
    [
        ("Windows", {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}, "StyleMatch"),
        ("Darwin", {}, "Library/Application Support/StyleMatch"),
        ("Linux", {"XDG_DATA_HOME": "relative/path"}, ".local/share/StyleMatch"),
    ],
)
def test_data_directory_uses_platform_user_location(
    tmp_path,
    monkeypatch,
    operating_system,
    environment,
    expected,
):
    monkeypatch.setattr(
        data_paths.platform,
        "system",
        lambda: operating_system,
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    result = data_paths.get_app_data_dir()

    assert result.name == "StyleMatch"
    if operating_system == "Windows":
        assert result == Path(environment["LOCALAPPDATA"]) / "StyleMatch"
    elif operating_system == "Darwin":
        assert result == tmp_path / expected
    else:
        assert result == tmp_path / expected


def test_json_null_is_invalid_data_and_is_not_treated_as_empty(tmp_path):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    original = data_dir / "wardrobe.json"
    original.write_text("null", encoding="utf-8")
    persistence = WardrobePersistence(data_dir)

    assert persistence.load_items() == []

    backups = list(data_dir.glob("wardrobe.json.corrupt-*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "null"
    assert persistence.startup_warning is not None


def test_corrupted_data_is_not_overwritten_when_backup_fails(
    tmp_path,
    monkeypatch,
):
    data_dir = tmp_path / "application-data"
    data_dir.mkdir()
    original = data_dir / "wardrobe.json"
    original.write_text("{broken", encoding="utf-8")

    def fail_backup(_source, _destination):
        raise OSError("simulated backup failure")

    monkeypatch.setattr(
        "stylematch.storage.wardrobe_persistence.os.replace",
        fail_backup,
    )
    persistence = WardrobePersistence(data_dir)

    assert persistence.load_items() == []
    assert persistence.writes_enabled is False
    assert original.read_text(encoding="utf-8") == "{broken"
    assert persistence.startup_warning is not None
    assert "disabled" in persistence.startup_warning
