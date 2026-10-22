"""JSON persistence and managed image storage for the clothing wardrobe."""

from pathlib import Path, PurePosixPath
import os
import shutil
from uuid import uuid4

from PIL import Image

from stylematch.images import validate_image
from stylematch.models.clothing import CATEGORIES, ClothingItem
from stylematch.storage.data_paths import get_app_data_dir
from stylematch.storage.json_store import JSONStore, StorageError

_FORMAT_EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}


class PostCommitStorageError(StorageError):
    """Raised when a saved operation completed but post-save cleanup failed."""


class WardrobePersistence:
    """Load and save wardrobe records and manage imported image copies."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else get_app_data_dir()
        self.image_dir = self.data_dir / "images"
        self.store = JSONStore(self.data_dir / "wardrobe.json")
        self.writes_enabled = True
        self.startup_warning: str | None = None
        try:
            self.image_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.writes_enabled = False
            self.startup_warning = (
                f"StyleMatch could not create managed image storage at "
                f"'{self.image_dir}': {error}. Persistence writes are disabled "
                "for this session."
            )
        else:
            try:
                self._managed_image_root()
            except StorageError as error:
                self.writes_enabled = False
                self.startup_warning = (
                    f"{error} Persistence writes are disabled for this session."
                )

    def load_items(self) -> list[ClothingItem]:
        """Load and validate all records, preserving recoverable bad files."""
        try:
            document = self.store.load()
        except StorageError as error:
            self._recover_unreadable_data(error)
            return []

        if document is None and not self.store.path.exists():
            return []

        try:
            return self._decode_document(document)
        except (KeyError, StorageError, TypeError, ValueError) as error:
            self._recover_unreadable_data(error)
            return []

    def save_items(self, items: list[ClothingItem]) -> None:
        """Save a complete wardrobe snapshot using portable image references."""
        if not self.writes_enabled:
            raise StorageError(
                self.startup_warning
                or "Wardrobe persistence is disabled because its data is unsafe."
            )

        records = []
        seen_ids: set[str] = set()
        for item in items:
            if item.id in seen_ids:
                raise StorageError(f"Duplicate clothing item ID '{item.id}'.")
            seen_ids.add(item.id)
            records.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "image_path": self._relative_image_reference(item.image_path),
                }
            )

        self.store.save({"version": 1, "clothing": records})

    def import_image(self, source: str | Path) -> str:
        """Validate and copy a source image into managed storage."""
        source_path = Path(source).expanduser()
        validate_image(source_path)
        try:
            with Image.open(source_path) as image:
                image_format = image.format
        except (OSError, ValueError) as error:
            raise StorageError(
                f"Unable to inspect the selected image '{source_path}': {error}"
            ) from error

        extension = _FORMAT_EXTENSIONS.get(image_format or "")
        if extension is None:
            raise StorageError("The selected image format is not supported.")

        try:
            self.image_dir.mkdir(parents=True, exist_ok=True)
            image_root = self._managed_image_root()
            for _ in range(10):
                destination = image_root / f"{uuid4().hex}{extension}"
                try:
                    with source_path.open("rb") as source_file:
                        with destination.open("xb") as destination_file:
                            shutil.copyfileobj(source_file, destination_file)
                    return str(destination.resolve())
                except FileExistsError:
                    continue
                except OSError as error:
                    cleanup_error: OSError | None = None
                    try:
                        destination.unlink(missing_ok=True)
                    except OSError as remove_error:
                        cleanup_error = remove_error
                    cleanup_message = (
                        f" The incomplete copy could not be removed: "
                        f"{cleanup_error}"
                        if cleanup_error is not None
                        else ""
                    )
                    raise StorageError(
                        f"Unable to import image '{source_path}': {error}."
                        f"{cleanup_message}"
                    ) from error
        except OSError as error:
            raise StorageError(
                f"Unable to create managed image storage at "
                f"'{self.image_dir}': {error}"
            ) from error
        raise StorageError("Unable to generate a unique managed image filename.")

    def remove_managed_image(self, image_path: str | Path | None) -> None:
        """Delete an image only when its resolved path is inside managed storage."""
        if image_path is None:
            return
        managed_path = self._resolve_managed_path(image_path)
        if managed_path is None:
            return
        try:
            managed_path.unlink(missing_ok=True)
        except OSError as error:
            raise StorageError(
                f"Unable to remove managed image '{managed_path}': {error}"
            ) from error

    def _decode_document(self, document: object) -> list[ClothingItem]:
        if not isinstance(document, dict):
            raise ValueError("The wardrobe JSON root must be an object.")
        version = document.get("version")
        if type(version) is not int or version != 1:
            raise ValueError(f"Unsupported wardrobe data version: {version!r}.")
        records = document.get("clothing")
        if not isinstance(records, list):
            raise ValueError("The wardrobe 'clothing' field must be a list.")

        items: list[ClothingItem] = []
        seen_ids: set[str] = set()
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"Clothing record {index + 1} must be an object.")
            item_id = record.get("id")
            name = record.get("name")
            category = record.get("category")
            image_reference = record.get("image_path")
            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError(f"Clothing record {index + 1} has an invalid ID.")
            if item_id in seen_ids:
                raise ValueError(f"Duplicate clothing item ID '{item_id}'.")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Clothing record '{item_id}' has an invalid name.")
            if not isinstance(category, str) or category not in CATEGORIES:
                raise ValueError(
                    f"Clothing record '{item_id}' has an invalid category."
                )
            if image_reference is not None and not isinstance(image_reference, str):
                raise ValueError(
                    f"Clothing record '{item_id}' has an invalid image reference."
                )
            seen_ids.add(item_id)
            resolved_image = (
                self.resolve_image_reference(image_reference)
                if image_reference is not None
                else None
            )
            items.append(
                ClothingItem(
                    id=item_id,
                    name=name,
                    category=category,
                    image_path=resolved_image,
                )
            )
        return items

    def resolve_image_reference(self, reference: str) -> str:
        """Resolve a portable JSON reference while preventing path traversal."""
        if "\\" in reference or ":" in reference:
            raise ValueError("Image references must use portable relative paths.")
        relative = PurePosixPath(reference)
        if (
            relative.is_absolute()
            or len(relative.parts) != 2
            or relative.parts[0] != "images"
            or any(part in (".", "..") for part in relative.parts)
        ):
            raise ValueError(f"Unsafe managed image reference '{reference}'.")
        try:
            image_root = self._managed_image_root()
            unresolved = image_root / relative.parts[1]
            if unresolved.is_symlink():
                raise ValueError(
                    f"Managed image reference '{reference}' is a symbolic link."
                )
            resolved = unresolved.resolve()
        except (OSError, RuntimeError) as error:
            raise ValueError(
                f"Image reference '{reference}' cannot be safely resolved."
            ) from error
        try:
            resolved.relative_to(image_root)
        except ValueError as error:
            raise ValueError(
                f"Image reference '{reference}' escapes managed storage."
            ) from error
        return str(resolved)

    def _relative_image_reference(self, image_path: str | None) -> str | None:
        if image_path is None:
            return None
        managed_path = self._resolve_managed_path(image_path)
        if managed_path is None:
            raise StorageError(
                "A persistent clothing item must reference an image in managed storage."
            )
        if managed_path.parent != self._managed_image_root():
            raise StorageError(
                "Managed clothing images must be stored directly in the images directory."
            )
        try:
            relative = managed_path.relative_to(self.data_dir.resolve())
        except ValueError as error:
            raise StorageError(
                f"Image path '{image_path}' is outside application data storage."
            ) from error
        return PurePosixPath(*relative.parts).as_posix()

    def _resolve_managed_path(self, image_path: str | Path) -> Path | None:
        try:
            image_root = self._managed_image_root()
            unresolved = Path(image_path).expanduser()
            if unresolved.is_symlink():
                raise StorageError(
                    f"Managed image '{image_path}' is a symbolic link."
                )
            path = unresolved.resolve()
        except (OSError, RuntimeError) as error:
            raise StorageError(
                f"Image path '{image_path}' cannot be safely resolved: {error}"
            ) from error
        try:
            path.relative_to(image_root)
        except ValueError:
            return None
        return path

    def _managed_image_root(self) -> Path:
        try:
            if self.image_dir.is_symlink():
                raise StorageError(
                    f"Managed image directory '{self.image_dir}' cannot be a "
                    "symbolic link."
                )
            image_root = self.image_dir.resolve()
            image_root.relative_to(self.data_dir.resolve())
        except ValueError as error:
            raise StorageError(
                f"Managed image directory '{self.image_dir}' resolves outside "
                "the application data directory."
            ) from error
        except (OSError, RuntimeError) as error:
            raise StorageError(
                f"Managed image directory '{self.image_dir}' cannot be safely "
                f"resolved: {error}"
            ) from error
        return image_root

    def _recover_unreadable_data(self, error: Exception) -> None:
        path = self.store.path
        try:
            if not path.exists():
                self.writes_enabled = False
                self.startup_warning = (
                    f"StyleMatch could not safely read its wardrobe data: {error}. "
                    "Persistence is disabled for this session to protect existing data."
                )
                return
            backup_path = path.with_name(
                f"{path.name}.corrupt-{uuid4().hex}.bak"
            )
            os.replace(path, backup_path)
        except OSError as backup_error:
            self.writes_enabled = False
            self.startup_warning = (
                f"StyleMatch could not safely load or preserve its wardrobe data: "
                f"{error}. The original file has not been overwritten, and "
                f"persistence is disabled for this session. Backup error: "
                f"{backup_error}"
            )
            return

        warning = (
            f"StyleMatch could not load its wardrobe data: {error}. "
            f"The original file was preserved as '{backup_path.name}'. "
            "The application will start with an empty wardrobe."
        )
        if not self.writes_enabled:
            warning += " Persistence writes remain disabled for this session."
        self.startup_warning = warning
