"""OutfitBuilder placeholder.

This module will contain logic to compose outfits from ClothingItem instances.
For now it exposes a minimal class to keep the UI decoupled from future logic.
"""
from typing import List
from stylematch.models.clothing import ClothingItem


class OutfitBuilder:
    """Simple placeholder for outfit-building logic."""

    def __init__(self):
        self.current_items: List[ClothingItem] = []

    def add_item(self, item: ClothingItem) -> None:
        self.current_items.append(item)

    def remove_item(self, item_id: str) -> None:
        self.current_items = [i for i in self.current_items if i.id != item_id]

    def clear(self) -> None:
        self.current_items.clear()

    def to_dict(self) -> dict:
        return {"items": [i.to_dict() for i in self.current_items]}

    def load_from_dict(self, data: dict) -> None:
        self.current_items = [ClothingItem.from_dict(d) for d in data.get("items", [])]
