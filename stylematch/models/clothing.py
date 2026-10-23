"""Clothing item data model.

This module defines simple data structures and helpers for clothing items. Business logic remains intentionally minimal for the starter step.
"""
from dataclasses import dataclass
from typing import Optional

CATEGORIES = ("Tops", "Bottoms", "Dresses", "Shoes", "Outerwear", "Jackets")
PRIMARY_COLORS = (
    "Black",
    "White",
    "Gray",
    "Navy",
    "Beige",
    "Brown",
    "Red",
    "Blue",
    "Green",
    "Yellow",
    "Pink",
    "Purple",
)
STYLES = ("Casual", "Formal", "Business", "Sporty", "Outdoor", "Streetwear")


@dataclass
class ClothingItem:
    """Represents a clothing item stored in the wardrobe.

    Fields:
    - id: simple identifier (string)
    - name: human readable name
    - category: e.g., 'top', 'bottom', 'shoes', etc.
    - image_path: optional path to the item's image file
    """
    id: str
    name: str
    category: str
    image_path: Optional[str] = None
    primary_color: str | None = None
    style: str | None = None

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "image_path": self.image_path,
        }
        if self.primary_color is not None:
            data["primary_color"] = self.primary_color
        if self.style is not None:
            data["style"] = self.style
        return data

    @staticmethod
    def from_dict(d: dict) -> "ClothingItem":
        return ClothingItem(
            id=d["id"],
            name=d["name"],
            category=d.get("category", ""),
            image_path=d.get("image_path"),
            primary_color=d.get("primary_color"),
            style=d.get("style"),
        )
