"""Rule-based outfit validation and deterministic suggestions."""

from stylematch.models.clothing import CATEGORIES, ClothingItem
from stylematch.services.clothing_manager import ClothingManager
from stylematch.outfits.compatibility import CompatibilityResult, score_compatibility


class OutfitBuilder:
    """Validate wardrobe references and suggest complete category combinations."""

    MAX_CANDIDATES = 5000
    MAX_RANKED_SUGGESTIONS = 20

    def __init__(self, manager: ClothingManager | None = None) -> None:
        self.manager = manager
        self.current_items: list[ClothingItem] = []
        self._ranked: list[tuple[list[ClothingItem], CompatibilityResult]] = []
        self._suggestion_index = -1
        self._wardrobe_signature: tuple[tuple[str, str, str | None, str | None], ...] | None = None
        self.evaluated_candidate_count = 0
        self.search_was_limited = False
        self.current_compatibility: CompatibilityResult | None = None

    @staticmethod
    def validate_items(items: list[ClothingItem]) -> list[ClothingItem]:
        """Return a valid outfit or raise ValueError with a useful explanation."""
        if not items:
            raise ValueError("Select clothing items for your outfit.")

        by_category: dict[str, ClothingItem] = {}
        seen_ids: set[str] = set()
        for item in items:
            if item.id in seen_ids:
                raise ValueError("An outfit cannot contain the same item twice.")
            seen_ids.add(item.id)
            if item.category not in CATEGORIES:
                raise ValueError(f"Unsupported clothing category: {item.category}.")
            if item.category in by_category:
                raise ValueError(
                    f"Select no more than one item from {item.category.lower()}."
                )
            by_category[item.category] = item

        categories = set(by_category)
        if {"Outerwear", "Jackets"}.issubset(categories):
            raise ValueError("Outerwear and Jackets cannot be used together.")
        if "Shoes" not in categories:
            raise ValueError("Every outfit needs Shoes.")
        if "Dresses" in categories:
            if categories & {"Tops", "Bottoms"}:
                raise ValueError("A Dress cannot be combined with a Top or Bottom.")
            return items
        if not {"Tops", "Bottoms"}.issubset(categories):
            raise ValueError("Select either a Top and Bottom, or a Dress.")
        return items

    def resolve_items(self, item_ids: list[str]) -> list[ClothingItem]:
        """Resolve IDs against the current wardrobe and validate the result."""
        if self.manager is None:
            raise ValueError("A wardrobe is required to resolve clothing items.")
        if any(not isinstance(item_id, str) or not item_id for item_id in item_ids):
            raise ValueError("Select valid clothing items from your wardrobe.")
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("An outfit cannot contain the same item twice.")
        wardrobe = {item.id: item for item in self.manager.list_items()}
        missing = [item_id for item_id in item_ids if item_id not in wardrobe]
        if missing:
            raise ValueError("One or more selected clothing items are no longer in your wardrobe.")
        return self.validate_items([wardrobe[item_id] for item_id in item_ids])

    def add_item(self, item: ClothingItem) -> None:
        if any(existing.id == item.id for existing in self.current_items):
            raise ValueError("This clothing item is already in the outfit.")
        self.current_items.append(item)

    def remove_item(self, item_id: str) -> None:
        self.current_items = [
            item for item in self.current_items if item.id != item_id
        ]

    def clear(self) -> None:
        self.current_items.clear()

    def to_dict(self) -> dict[str, list[dict]]:
        return {"items": [item.to_dict() for item in self.current_items]}

    def load_from_dict(self, data: dict) -> None:
        self.current_items = [
            ClothingItem.from_dict(item) for item in data.get("items", [])
        ]

    def _categories(self) -> dict[str, list[ClothingItem]]:
        if self.manager is None:
            return {category: [] for category in CATEGORIES}
        return {
            category: sorted(
                self.manager.list_items(category), key=lambda item: item.id
            )
            for category in CATEGORIES
        }

    @staticmethod
    def _count_candidates(categories: dict[str, list[ClothingItem]]) -> int:
        shoes = len(categories["Shoes"])
        optional_piece_choices = (
            1 + len(categories["Outerwear"]) + len(categories["Jackets"])
        )
        separates = (
            len(categories["Tops"]) * len(categories["Bottoms"]) * shoes
        )
        dresses = len(categories["Dresses"]) * shoes
        return (separates + dresses) * optional_piece_choices

    def _candidate_count(self) -> int:
        return self._count_candidates(self._categories())

    def has_alternative(self) -> bool:
        """Whether Try Another has another distinct ranked suggestion."""
        if self._suggestion_index < 0:
            return False
        self._ensure_ranked()
        return self._suggestion_index + 1 < len(self._ranked)

    @staticmethod
    def _candidate_at(
        index: int,
        categories: dict[str, list[ClothingItem]],
    ) -> list[ClothingItem]:
        tops, bottoms, dresses, shoes, outerwear, jackets = (
            categories[name]
            for name in CATEGORIES
        )
        optional_piece_options: list[ClothingItem | None] = [
            None,
            *outerwear,
            *jackets,
        ]
        optional_piece_count = len(optional_piece_options)
        separates_count = (
            len(tops) * len(bottoms) * len(shoes) * optional_piece_count
        )
        if index < separates_count:
            optional_piece_index = index % optional_piece_count
            combo_index = index // optional_piece_count
            shoe = shoes[combo_index % len(shoes)]
            combo_index //= len(shoes)
            bottom = bottoms[combo_index % len(bottoms)]
            top = tops[combo_index // len(bottoms)]
            selected = [top, bottom, shoe]
        else:
            combo_index = index - separates_count
            optional_piece_index = combo_index % optional_piece_count
            shoe_index = combo_index // optional_piece_count % len(shoes)
            dress_index = combo_index // (optional_piece_count * len(shoes))
            selected = [dresses[dress_index], shoes[shoe_index]]
        optional_piece = optional_piece_options[optional_piece_index]
        if optional_piece is not None:
            selected.append(optional_piece)
        return selected

    def _ensure_ranked(self) -> None:
        wardrobe_items = (
            self.manager.list_items() if self.manager is not None else []
        )
        wardrobe_signature = tuple(
            (
                item.id,
                item.category,
                item.primary_color,
                item.style,
            )
            for item in wardrobe_items
        )
        if wardrobe_signature == self._wardrobe_signature:
            return

        self._wardrobe_signature = wardrobe_signature
        self._ranked = []
        self._suggestion_index = -1
        self.current_compatibility = None
        categories = {
            category: sorted(
                (item for item in wardrobe_items if item.category == category),
                key=lambda item: item.id,
            )
            for category in CATEGORIES
        }
        candidate_count = self._count_candidates(categories)
        self.evaluated_candidate_count = min(
            candidate_count, self.MAX_CANDIDATES
        )
        self.search_was_limited = candidate_count > self.MAX_CANDIDATES
        ranked = []
        for index in range(self.evaluated_candidate_count):
            candidate = self._candidate_at(index, categories)
            self.validate_items(candidate)
            compatibility = score_compatibility(candidate)
            stable_ids = tuple(sorted(item.id for item in candidate))
            ranked.append((candidate, compatibility, stable_ids))
        ranked.sort(key=lambda entry: (-entry[1].score, entry[2]))
        self._ranked = [
            (items, compatibility)
            for items, compatibility, _ in ranked[: self.MAX_RANKED_SUGGESTIONS]
        ]

    def suggest_outfit(self) -> list[ClothingItem] | None:
        """Return the highest-ranked evaluated candidate, if one exists."""
        self._ensure_ranked()
        if not self._ranked:
            self.current_compatibility = None
            return None
        self._suggestion_index = 0
        items, self.current_compatibility = self._ranked[0]
        return list(items)

    def try_another(self) -> list[ClothingItem] | None:
        """Return the next distinct ranked candidate without cycling repeats."""
        if self._suggestion_index < 0:
            return None
        self._ensure_ranked()
        next_index = self._suggestion_index + 1
        if next_index >= len(self._ranked):
            return None
        self._suggestion_index = next_index
        items, self.current_compatibility = self._ranked[next_index]
        return list(items)
