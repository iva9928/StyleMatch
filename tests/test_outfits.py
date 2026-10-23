"""Focused tests for outfit rules and separate JSON persistence."""

import json

import pytest
from PIL import Image

from stylematch.outfits.builder import OutfitBuilder
from stylematch.services.clothing_manager import ClothingManager
from stylematch.services.outfit_manager import OutfitManager
from stylematch.storage.outfit_persistence import OutfitPersistence
from stylematch.storage.wardrobe_persistence import WardrobePersistence


def _manager(tmp_path):
    data_dir = tmp_path / "application-data"
    wardrobe = WardrobePersistence(data_dir)
    clothing = ClothingManager(wardrobe)
    outfit_store = OutfitPersistence(data_dir)
    outfits = OutfitManager(clothing, outfit_store)
    image_path = tmp_path / "clothing.png"
    Image.new("RGB", (32, 48), color="beige").save(image_path)
    return data_dir, clothing, outfits, image_path


def _add(clothing, image_path, category, name):
    return clothing.add_item(name, category, image_path)


@pytest.mark.parametrize(
    "categories",
    [
        ("Tops", "Bottoms", "Shoes"),
        ("Tops", "Bottoms", "Shoes", "Outerwear"),
        ("Tops", "Bottoms", "Shoes", "Jackets"),
        ("Dresses", "Shoes"),
        ("Dresses", "Shoes", "Outerwear"),
        ("Dresses", "Shoes", "Jackets"),
    ],
)
def test_builder_accepts_supported_outfit_structures(
    tmp_path,
    categories,
):
    _, clothing, outfits, image_path = _manager(tmp_path)
    items = [
        _add(clothing, image_path, category, f"Item {index}")
        for index, category in enumerate(categories)
    ]

    assert outfits.builder.resolve_items([item.id for item in items]) == items


@pytest.mark.parametrize(
    ("categories", "message"),
    [
        (("Tops", "Shoes"), "Top and Bottom"),
        (("Bottoms", "Shoes"), "Top and Bottom"),
        (("Dresses",), "Shoes"),
        (("Dresses", "Tops", "Shoes"), "cannot be combined"),
        (("Dresses", "Bottoms", "Shoes"), "cannot be combined"),
        (
            ("Tops", "Bottoms", "Shoes", "Outerwear", "Jackets"),
            "Outerwear and Jackets",
        ),
        (("Dresses", "Shoes", "Outerwear", "Jackets"), "Outerwear and Jackets"),
    ],
)
def test_builder_rejects_incomplete_or_incompatible_structures(
    tmp_path,
    categories,
    message,
):
    _, clothing, outfits, image_path = _manager(tmp_path)
    items = [
        _add(clothing, image_path, category, f"Item {index}")
        for index, category in enumerate(categories)
    ]

    with pytest.raises(ValueError, match=message):
        outfits.builder.resolve_items([item.id for item in items])


def test_builder_rejects_unknown_and_duplicate_item_ids(tmp_path):
    _, clothing, outfits, image_path = _manager(tmp_path)
    top = _add(clothing, image_path, "Tops", "Top")
    bottom = _add(clothing, image_path, "Bottoms", "Bottom")
    shoes = _add(clothing, image_path, "Shoes", "Shoes")

    with pytest.raises(ValueError, match="no longer in your wardrobe"):
        outfits.builder.resolve_items([top.id, bottom.id, shoes.id, "missing"])
    with pytest.raises(ValueError, match="same item twice"):
        outfits.builder.resolve_items([top.id, top.id, bottom.id, shoes.id])


def test_suggestions_are_complete_and_try_another_changes_combination(tmp_path):
    _, clothing, outfits, image_path = _manager(tmp_path)
    _add(clothing, image_path, "Tops", "Top one")
    _add(clothing, image_path, "Tops", "Top two")
    _add(clothing, image_path, "Bottoms", "Bottom")
    _add(clothing, image_path, "Shoes", "Shoes")

    first = outfits.builder.suggest_outfit()
    second = outfits.builder.try_another()

    assert first is not None
    assert second is not None
    assert {item.category for item in first} == {"Tops", "Bottoms", "Shoes"}
    assert {item.id for item in first} != {item.id for item in second}


def test_suggestions_rank_high_compatibility_first_and_try_another_advances(
    tmp_path,
):
    _, clothing, outfits, image_path = _manager(tmp_path)
    best_top = clothing.add_item(
        "Navy tee",
        "Tops",
        image_path,
        primary_color="Navy",
        style="Casual",
    )
    lower_top = clothing.add_item(
        "Red blouse",
        "Tops",
        image_path,
        primary_color="Red",
        style="Formal",
    )
    clothing.add_item(
        "Beige trousers",
        "Bottoms",
        image_path,
        primary_color="Beige",
        style="Casual",
    )
    clothing.add_item(
        "Navy shoes",
        "Shoes",
        image_path,
        primary_color="Navy",
        style="Casual",
    )

    first = outfits.builder.suggest_outfit()
    first_score = outfits.builder.current_compatibility.score
    assert outfits.builder.has_alternative()
    second = outfits.builder.try_another()

    assert first is not None and second is not None
    assert best_top in first
    assert lower_top not in first
    assert {item.id for item in first} != {item.id for item in second}
    assert outfits.builder.current_compatibility is not None
    assert first_score > outfits.builder.current_compatibility.score
    assert not outfits.builder.has_alternative()


def test_try_another_does_not_repeat_after_ranked_suggestions_are_exhausted(
    tmp_path,
):
    _, clothing, outfits, image_path = _manager(tmp_path)
    _add(clothing, image_path, "Tops", "Top")
    _add(clothing, image_path, "Bottoms", "Bottom")
    _add(clothing, image_path, "Shoes", "Shoes")

    first = outfits.builder.suggest_outfit()

    assert first is not None
    assert outfits.builder.try_another() is None
    assert outfits.builder.try_another() is None


def test_suggestion_search_has_a_fixed_evaluation_limit(tmp_path, monkeypatch):
    _, clothing, outfits, image_path = _manager(tmp_path)
    for index in range(4):
        _add(clothing, image_path, "Tops", f"Top {index}")
    _add(clothing, image_path, "Bottoms", "Bottom")
    _add(clothing, image_path, "Shoes", "Shoes")
    monkeypatch.setattr(OutfitBuilder, "MAX_CANDIDATES", 2)

    suggestion = outfits.builder.suggest_outfit()

    assert suggestion is not None
    assert outfits.builder.evaluated_candidate_count == 2
    assert outfits.builder.search_was_limited


def test_suggestion_handles_insufficient_wardrobe(tmp_path):
    _, clothing, outfits, image_path = _manager(tmp_path)
    _add(clothing, image_path, "Tops", "Top")

    assert outfits.builder.suggest_outfit() is None
    assert outfits.builder.try_another() is None


def test_suggestions_include_jackets_without_combining_optional_categories(
    tmp_path,
):
    _, clothing, outfits, image_path = _manager(tmp_path)
    _add(clothing, image_path, "Tops", "Top")
    _add(clothing, image_path, "Bottoms", "Bottom")
    _add(clothing, image_path, "Shoes", "Shoes")
    jacket = _add(clothing, image_path, "Jackets", "Jacket")
    outerwear = _add(clothing, image_path, "Outerwear", "Coat")

    suggestions = [outfits.builder.suggest_outfit()]
    suggestions.extend(
        outfits.builder.try_another()
        for _ in range(outfits.builder._candidate_count() - 1)
    )

    assert all(suggestion is not None for suggestion in suggestions)
    assert any(jacket in suggestion for suggestion in suggestions)
    assert any(outerwear in suggestion for suggestion in suggestions)
    assert all(
        not {"Outerwear", "Jackets"}.issubset(
            {item.category for item in suggestion}
        )
        for suggestion in suggestions
    )
    assert len({tuple(sorted(item.id for item in suggestion)) for suggestion in suggestions}) == len(
        suggestions
    )


def test_outfits_persist_without_changing_wardrobe_and_keep_missing_references(
    tmp_path,
):
    data_dir, clothing, outfits, image_path = _manager(tmp_path)
    top = _add(clothing, image_path, "Tops", "Top")
    bottom = _add(clothing, image_path, "Bottoms", "Bottom")
    shoes = _add(clothing, image_path, "Shoes", "Shoes")
    wardrobe_before = (data_dir / "wardrobe.json").read_text(encoding="utf-8")

    outfit = outfits.save_outfit("  Everyday  ", [top.id, bottom.id, shoes.id])
    restored = OutfitManager(
        ClothingManager(WardrobePersistence(data_dir)),
        OutfitPersistence(data_dir),
    )
    available, missing = restored.available_items(restored.list_outfits()[0])

    assert outfit.name == "Everyday"
    assert len(restored.list_outfits()) == 1
    assert (data_dir / "wardrobe.json").read_text(encoding="utf-8") == wardrobe_before
    assert [item.id for item in available] == [top.id, bottom.id, shoes.id]
    assert missing == []

    assert restored.clothing_manager.delete_item(top.id)
    after_delete = OutfitManager(
        ClothingManager(WardrobePersistence(data_dir)),
        OutfitPersistence(data_dir),
    )
    remaining, unavailable = after_delete.available_items(
        after_delete.list_outfits()[0]
    )

    assert len(after_delete.list_outfits()) == 1
    assert [item.id for item in remaining] == [bottom.id, shoes.id]
    assert unavailable == [top.id]


def test_metadata_update_preserves_saved_outfit_clothing_references(tmp_path):
    data_dir, clothing, outfits, image_path = _manager(tmp_path)
    top = _add(clothing, image_path, "Tops", "Top")
    bottom = _add(clothing, image_path, "Bottoms", "Bottom")
    shoes = _add(clothing, image_path, "Shoes", "Shoes")
    saved = outfits.save_outfit("Existing", [top.id, bottom.id, shoes.id])

    clothing.update_metadata(top.id, "Navy", "Casual")
    restored = OutfitManager(
        ClothingManager(WardrobePersistence(data_dir)),
        OutfitPersistence(data_dir),
    )

    assert restored.list_outfits() == [saved]
    available, missing = restored.available_items(restored.list_outfits()[0])
    assert [item.id for item in available] == [top.id, bottom.id, shoes.id]
    assert available[0].primary_color == "Navy"
    assert missing == []


def test_existing_saved_outfits_load_and_jacket_outfits_persist(tmp_path):
    data_dir, clothing, _, image_path = _manager(tmp_path)
    top = _add(clothing, image_path, "Tops", "Top")
    bottom = _add(clothing, image_path, "Bottoms", "Bottom")
    shoes = _add(clothing, image_path, "Shoes", "Shoes")
    jacket = _add(clothing, image_path, "Jackets", "Jacket")
    legacy_record = {
        "version": 1,
        "outfits": [
            {
                "id": "existing-outfit",
                "name": "Saved before Jackets",
                "clothing_item_ids": [top.id, bottom.id, shoes.id],
            }
        ],
    }
    (data_dir / "outfits.json").write_text(
        json.dumps(legacy_record),
        encoding="utf-8",
    )

    restored = OutfitManager(
        clothing,
        OutfitPersistence(data_dir),
    )
    assert [outfit.id for outfit in restored.list_outfits()] == ["existing-outfit"]
    legacy_available, legacy_missing = restored.available_items(
        restored.list_outfits()[0]
    )
    assert legacy_available == [top, bottom, shoes]
    assert legacy_missing == []

    new_outfit = restored.save_outfit(
        "Winter outfit",
        [top.id, bottom.id, shoes.id, jacket.id],
    )
    reloaded = OutfitManager(
        ClothingManager(WardrobePersistence(data_dir)),
        OutfitPersistence(data_dir),
    )
    assert [outfit.id for outfit in reloaded.list_outfits()] == [
        "existing-outfit",
        new_outfit.id,
    ]
    new_available, new_missing = reloaded.available_items(
        reloaded.list_outfits()[1]
    )
    assert [item.category for item in new_available] == [
        "Tops",
        "Bottoms",
        "Shoes",
        "Jackets",
    ]
    assert new_missing == []


def test_outfit_delete_persists(tmp_path):
    data_dir, clothing, outfits, image_path = _manager(tmp_path)
    top = _add(clothing, image_path, "Tops", "Top")
    bottom = _add(clothing, image_path, "Bottoms", "Bottom")
    shoes = _add(clothing, image_path, "Shoes", "Shoes")
    outfit = outfits.save_outfit("Look", [top.id, bottom.id, shoes.id])

    assert outfits.delete_outfit(outfit.id)
    restored = OutfitManager(
        ClothingManager(WardrobePersistence(data_dir)),
        OutfitPersistence(data_dir),
    )
    assert restored.list_outfits() == []


def test_corrupted_outfits_are_preserved_without_touching_wardrobe(tmp_path):
    data_dir, clothing, _, image_path = _manager(tmp_path)
    _add(clothing, image_path, "Tops", "Top")
    wardrobe_contents = (data_dir / "wardrobe.json").read_bytes()
    outfits_path = data_dir / "outfits.json"
    outfits_path.write_text("null", encoding="utf-8")
    persistence = OutfitPersistence(data_dir)

    assert persistence.load_outfits() == []
    assert persistence.writes_enabled is False
    assert persistence.startup_warning is not None
    assert len(list(data_dir.glob("outfits.json.corrupt-*.bak"))) == 1
    assert (data_dir / "wardrobe.json").read_bytes() == wardrobe_contents
    assert json.loads(
        next(data_dir.glob("outfits.json.corrupt-*.bak")).read_text(
            encoding="utf-8"
        )
    ) is None
