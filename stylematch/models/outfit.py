"""Saved outfit data model containing references to wardrobe item IDs."""

from dataclasses import dataclass


@dataclass
class Outfit:
    """A named combination of existing clothing item IDs."""

    id: str
    name: str
    clothing_item_ids: list[str]

    def __post_init__(self) -> None:
        self.name = self.name.strip() if isinstance(self.name, str) else ""
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("An outfit must have a valid ID.")
        self.id = self.id.strip()
        if not self.name:
            raise ValueError("Enter an outfit name.")
        if (
            not isinstance(self.clothing_item_ids, list)
            or not self.clothing_item_ids
        ):
            raise ValueError("An outfit must reference clothing items.")
        if any(
            not isinstance(item_id, str) or not item_id.strip()
            for item_id in self.clothing_item_ids
        ):
            raise ValueError("Outfit clothing references must be valid IDs.")
        if len(self.clothing_item_ids) != len(set(self.clothing_item_ids)):
            raise ValueError("An outfit cannot reference the same item twice.")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "clothing_item_ids": list(self.clothing_item_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "Outfit":
        item_ids = data.get("clothing_item_ids")
        outfit_id = data.get("id")
        name = data.get("name")
        if not isinstance(item_ids, list):
            raise ValueError("Outfit clothing references must be a list.")
        if not isinstance(outfit_id, str):
            raise ValueError("An outfit must have a valid ID.")
        if not isinstance(name, str):
            raise ValueError("Enter an outfit name.")
        if any(not isinstance(item_id, str) for item_id in item_ids):
            raise ValueError("Outfit clothing references must be valid IDs.")
        return Outfit(
            id=outfit_id,
            name=name,
            clothing_item_ids=item_ids,
        )
