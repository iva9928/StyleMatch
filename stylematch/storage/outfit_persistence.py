"""Versioned JSON persistence for saved outfits."""

import os
from pathlib import Path
from uuid import uuid4

from stylematch.models.outfit import Outfit
from stylematch.storage.json_store import JSONStore, StorageError


class OutfitPersistence:
    """Load and atomically save outfit references separately from the wardrobe."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.store = JSONStore(self.data_dir / "outfits.json")
        self.writes_enabled = True
        self.startup_warning: str | None = None

    def load_outfits(self) -> list[Outfit]:
        try:
            document = self.store.load()
            if document is None:
                if self.store.path.exists():
                    raise ValueError("The outfits JSON root must be an object.")
                return []
            if not isinstance(document, dict):
                raise ValueError("The outfits JSON root must be an object.")
            if type(document.get("version")) is not int or document["version"] != 1:
                raise ValueError(
                    f"Unsupported outfits data version: {document.get('version')!r}."
                )
            records = document.get("outfits")
            if not isinstance(records, list):
                raise ValueError("The outfits 'outfits' field must be a list.")
            outfits: list[Outfit] = []
            seen_ids: set[str] = set()
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    raise ValueError(f"Outfit record {index + 1} must be an object.")
                outfit = Outfit.from_dict(record)
                if outfit.id in seen_ids:
                    raise ValueError(f"Duplicate outfit ID '{outfit.id}'.")
                seen_ids.add(outfit.id)
                outfits.append(outfit)
            return outfits
        except (StorageError, KeyError, TypeError, ValueError) as error:
            self._preserve_unreadable_data(error)
            return []

    def save_outfits(self, outfits: list[Outfit]) -> None:
        if not self.writes_enabled:
            raise StorageError(
                self.startup_warning
                or "Outfit persistence is disabled because its data is unsafe."
            )
        records: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        for outfit in outfits:
            if outfit.id in seen_ids:
                raise StorageError(f"Duplicate outfit ID '{outfit.id}'.")
            seen_ids.add(outfit.id)
            records.append(outfit.to_dict())
        self.store.save({"version": 1, "outfits": records})

    def _preserve_unreadable_data(self, error: Exception) -> None:
        path = self.store.path
        try:
            if not path.exists():
                self.writes_enabled = False
                self.startup_warning = (
                    f"StyleMatch could not safely read outfit data: {error}. "
                    "Outfit persistence is disabled for this session."
                )
                return
            backup_path = path.with_name(
                f"{path.name}.corrupt-{uuid4().hex}.bak"
            )
            os.replace(path, backup_path)
        except OSError as backup_error:
            self.writes_enabled = False
            self.startup_warning = (
                f"StyleMatch could not safely load or preserve outfit data: "
                f"{error}. The original file has not been overwritten, and "
                f"outfit persistence is disabled for this session. "
                f"Backup error: {backup_error}"
            )
            return
        self.writes_enabled = False
        self.startup_warning = (
            f"StyleMatch could not load outfit data: {error}. The original "
            f"file was preserved as '{backup_path.name}'. Outfit persistence "
            "is disabled for this session."
        )
