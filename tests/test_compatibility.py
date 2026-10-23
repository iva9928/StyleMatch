"""Focused tests for explainable color and style compatibility heuristics."""

import pytest

from stylematch.models.clothing import ClothingItem
from stylematch.outfits.compatibility import score_compatibility


def _items(top_color, bottom_color, shoe_color, top_style="Casual"):
    return [
        ClothingItem("top", "Top", "Tops", primary_color=top_color, style=top_style),
        ClothingItem(
            "bottom",
            "Bottom",
            "Bottoms",
            primary_color=bottom_color,
            style="Casual",
        ),
        ClothingItem(
            "shoes",
            "Shoes",
            "Shoes",
            primary_color=shoe_color,
            style="Casual",
        ),
    ]


def test_color_rules_prefer_matching_and_neutral_pairings():
    matching = score_compatibility(_items("Black", "Black", "Black"))
    neutrals = score_compatibility(_items("Black", "Beige", "Navy"))
    clashing = score_compatibility(_items("Red", "Green", "Green"))

    assert matching.score > neutrals.score > clashing.score
    assert "matching Black" in matching.explanation
    assert "neutral pairing" in neutrals.explanation
    assert "strong contrast" in clashing.explanation


def test_style_rules_prefer_matching_and_compatible_styles():
    matching = score_compatibility(_items("Blue", "Pink", "Purple"))
    matching_style = score_compatibility(_items("Black", "White", "Gray"))
    compatible_style = score_compatibility(
        _items("Black", "White", "Gray", top_style="Streetwear")
    )
    conflicting_style = score_compatibility(
        [
            ClothingItem("top", "Top", "Tops", style="Formal"),
            ClothingItem("bottom", "Bottom", "Bottoms", style="Sporty"),
            ClothingItem("shoes", "Shoes", "Shoes", style="Formal"),
        ]
    )

    assert "matching Casual styles" in matching.explanation
    assert matching_style.score > compatible_style.score
    assert compatible_style.score > conflicting_style.score
    assert "declared style contrast" in conflicting_style.explanation


def test_missing_metadata_is_neutral_and_explained():
    result = score_compatibility(
        [
            ClothingItem("top", "Top", "Tops"),
            ClothingItem("bottom", "Bottom", "Bottoms", primary_color="Navy"),
            ClothingItem("shoes", "Shoes", "Shoes", style="Casual"),
        ]
    )

    assert result.score == 50
    assert "no color penalty" in result.explanation
    assert "no style penalty" in result.explanation


def test_compatibility_rejects_invalid_category_combinations():
    with pytest.raises(ValueError, match="Top and Bottom"):
        score_compatibility(
            [
                ClothingItem("top", "Top", "Tops"),
                ClothingItem("shoes", "Shoes", "Shoes"),
            ]
        )
