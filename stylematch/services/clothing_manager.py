"""Clothing management with optional local persistence."""

from pathlib import Path
from uuid import uuid4

from stylematch.images import validate_image
from stylematch.models.clothing import CATEGORIES, ClothingItem
from stylematch.storage.json_store import StorageError
from stylematch.storage.wardrobe_persistence import (
    PostCommitStorageError,
    WardrobePersistence,
)


class ClothingManager:
    """Own clothing items, optionally saving changes to local storage."""

    def __init__(self, persistence: WardrobePersistence | None = None) -> None:
        self.persistence = persistence
        self._items: dict[str, ClothingItem] = {}
        if persistence is not None:
            self._items = {
                item.id: item for item in persistence.load_items()
            }

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

        managed_path = (
            self.persistence.import_image(normalized_path)
            if self.persistence is not None
            else normalized_path
        )
        item = ClothingItem(
            id=str(uuid4()),
            name=normalized_name,
            category=category,
            image_path=managed_path,
        )

        if self.persistence is not None:
            try:
                self.persistence.save_items([*self._items.values(), item])
            except StorageError as error:
                try:
                    self.persistence.remove_managed_image(managed_path)
                except StorageError as cleanup_error:
                    raise StorageError(
                        f"{error} The imported image also could not be "
                        f"removed: {cleanup_error}"
                    ) from error
                raise

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
        item = self._items.get(item_id)
        if item is None:
            return False

        if self.persistence is not None:
            remaining_items = [
                existing
                for existing_id, existing in self._items.items()
                if existing_id != item_id
            ]
            self.persistence.save_items(remaining_items)

        del self._items[item_id]
        if self.persistence is not None:
            try:
                self.persistence.remove_managed_image(item.image_path)
            except StorageError as error:
                raise PostCommitStorageError(
                    f"The clothing item was deleted, but its managed image "
                    f"could not be removed: {error}"
                ) from error
        return True
