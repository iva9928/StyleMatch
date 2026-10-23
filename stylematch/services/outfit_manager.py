"""Business operations for saving and managing outfits."""

from uuid import uuid4

from stylematch.models.clothing import ClothingItem
from stylematch.models.outfit import Outfit
from stylematch.outfits.builder import OutfitBuilder
from stylematch.services.clothing_manager import ClothingManager
from stylematch.storage.outfit_persistence import OutfitPersistence


class OutfitManager:
    """Manage saved outfit references against one shared clothing wardrobe."""

    def __init__(
        self,
        clothing_manager: ClothingManager,
        persistence: OutfitPersistence | None = None,
    ) -> None:
        self.clothing_manager = clothing_manager
        self.persistence = persistence
        self._outfits = (
            persistence.load_outfits() if persistence is not None else []
        )
        self.builder = OutfitBuilder(clothing_manager)

    def list_outfits(self) -> list[Outfit]:
        return list(self._outfits)

    def save_outfit(self, name: str, clothing_item_ids: list[str]) -> Outfit:
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name:
            raise ValueError("Enter an outfit name.")
        items = self.builder.resolve_items(clothing_item_ids)
        outfit = Outfit(
            id=str(uuid4()),
            name=normalized_name,
            clothing_item_ids=[item.id for item in items],
        )
        updated = [*self._outfits, outfit]
        if self.persistence is not None:
            self.persistence.save_outfits(updated)
        self._outfits = updated
        return outfit

    def delete_outfit(self, outfit_id: str) -> bool:
        if not any(outfit.id == outfit_id for outfit in self._outfits):
            return False
        updated = [
            outfit for outfit in self._outfits if outfit.id != outfit_id
        ]
        if self.persistence is not None:
            self.persistence.save_outfits(updated)
        self._outfits = updated
        return True

    def available_items(self, outfit: Outfit) -> tuple[list[ClothingItem], list[str]]:
        wardrobe = {
            item.id: item for item in self.clothing_manager.list_items()
        }
        available = [
            wardrobe[item_id]
            for item_id in outfit.clothing_item_ids
            if item_id in wardrobe
        ]
        missing = [
            item_id
            for item_id in outfit.clothing_item_ids
            if item_id not in wardrobe
        ]
        return available, missing
