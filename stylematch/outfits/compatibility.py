"""Small explainable heuristics for color and style compatibility."""

from dataclasses import dataclass
from itertools import combinations

from stylematch.models.clothing import ClothingItem

_NEUTRAL_COLORS = {"Black", "White", "Gray", "Navy", "Beige", "Brown"}
_COMPATIBLE_COLORS = {
    frozenset(pair)
    for pair in (
        ("Black", "White"),
        ("Black", "Red"),
        ("Black", "Blue"),
        ("Navy", "Beige"),
        ("Navy", "White"),
        ("Red", "Navy"),
        ("Brown", "Blue"),
        ("Brown", "Green"),
        ("Beige", "Blue"),
        ("Green", "Beige"),
        ("Gray", "Pink"),
        ("Purple", "Gray"),
    )
}
_CONFLICTING_COLORS = {
    frozenset(("Red", "Green")),
    frozenset(("Yellow", "Purple")),
}
_COMPATIBLE_STYLES = {
    frozenset(pair)
    for pair in (
        ("Casual", "Streetwear"),
        ("Casual", "Outdoor"),
        ("Casual", "Sporty"),
        ("Formal", "Business"),
        ("Outdoor", "Sporty"),
    )
}
_CONFLICTING_STYLES = {
    frozenset(("Formal", "Sporty")),
    frozenset(("Formal", "Outdoor")),
    frozenset(("Business", "Streetwear")),
}


@dataclass(frozen=True)
class CompatibilityResult:
    """A heuristic score and a short explanation of its evidence."""

    score: int
    explanation: str


def _color_pair_score(first: str, second: str) -> tuple[float, str]:
    pair = frozenset((first, second))
    if first == second:
        return 1.0, f"matching {first}"
    if pair in _CONFLICTING_COLORS:
        return 0.2, f"strong contrast between {first} and {second}"
    if pair in _COMPATIBLE_COLORS:
        return 0.9, f"{first} pairs with {second}"
    if first in _NEUTRAL_COLORS or second in _NEUTRAL_COLORS:
        return 0.75, f"neutral pairing with {first} and {second}"
    return 0.5, f"no specific color rule for {first} and {second}"


def _style_pair_score(first: str, second: str) -> tuple[float, str]:
    pair = frozenset((first, second))
    if first == second:
        return 1.0, f"matching {first} styles"
    if pair in _CONFLICTING_STYLES:
        return 0.2, f"{first} and {second} are a declared style contrast"
    if pair in _COMPATIBLE_STYLES:
        return 0.9, f"{first} works with {second}"
    return 0.5, f"no specific style rule for {first} and {second}"


def score_compatibility(items: list[ClothingItem]) -> CompatibilityResult:
    """Score a valid outfit with explicit user-metadata rules, not fashion judgment."""
    from stylematch.outfits.builder import OutfitBuilder

    OutfitBuilder.validate_items(items)

    color_pairs = [
        _color_pair_score(first.primary_color, second.primary_color)
        for first, second in combinations(items, 2)
        if first.primary_color is not None and second.primary_color is not None
    ]
    style_pairs = [
        _style_pair_score(first.style, second.style)
        for first, second in combinations(items, 2)
        if first.style is not None and second.style is not None
    ]

    color_score = (
        sum(score for score, _ in color_pairs) / len(color_pairs)
        if color_pairs
        else 0.5
    )
    style_score = (
        sum(score for score, _ in style_pairs) / len(style_pairs)
        if style_pairs
        else 0.5
    )
    score = round((color_score * 0.6 + style_score * 0.4) * 100)

    explanations = []
    if color_pairs:
        descriptions = list(dict.fromkeys(text for _, text in color_pairs))
        explanations.append("Colors: " + "; ".join(descriptions[:2]))
    else:
        explanations.append("Color metadata incomplete; no color penalty")
    if style_pairs:
        descriptions = list(dict.fromkeys(text for _, text in style_pairs))
        explanations.append("Styles: " + "; ".join(descriptions[:2]))
    else:
        explanations.append("Style metadata incomplete; no style penalty")
    return CompatibilityResult(score, ". ".join(explanations) + ".")
