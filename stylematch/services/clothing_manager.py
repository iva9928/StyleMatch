"""In-memory clothing management for the current application session."""

from pathlib import Path
from uuid import uuid4

from stylematch.images import validate_image
from stylematch.models.clothing import ClothingItem

CATEGORIES = ("Tops", "Bottoms", "Dresses", "Shoes", "Outerwear")


class ClothingManager:
    """Own the session's clothing items and validate new items."""

    def __init__(self) -> None:
        self._items: dict[str, ClothingItem] = {}

    def add_item(
        self,
        name: str,
        category: str,
        image_path: str | Path | None,
    ) -> ClothingItem:
        """Validate and add an item, returning the stored model."""
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name:
            raise ValueError("Enter a clothing name.")
        if category not in CATEGORIES:
            raise ValueError("Select a valid clothing category.")
        if not image_path:
            raise ValueError("Choose an image for this clothing item.")

        normalized_path = str(Path(image_path).expanduser())
        validate_image(normalized_path)

        item = ClothingItem(
            id=str(uuid4()),
            name=normalized_name,
            category=category,
            image_path=normalized_path,
        )
        self._items[item.id] = item
        return item

    def list_items(self, category: str | None = None) -> list[ClothingItem]:
        """Return all items, optionally limited to one valid category."""
        if category is not None and category not in CATEGORIES:
            raise ValueError("Select a valid clothing category.")
        return [
            item
            for item in self._items.values()
            if category is None or item.category == category
        ]

    def delete_item(self, item_id: str) -> bool:
        """Delete an item by ID without affecting its source image."""
        return self._items.pop(item_id, None) is not None
