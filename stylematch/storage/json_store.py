"""Small, atomic JSON file storage helpers."""

import json
import os
from pathlib import Path
import tempfile
from typing import Any


class StorageError(Exception):
    """Raised when local application data cannot be safely read or written."""


class InvalidJSONError(StorageError):
    """Raised when a JSON file exists but cannot be decoded."""


class JSONStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> Any | None:
        """Return decoded JSON, or None if the file does not exist."""
        try:
            with self.path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as error:
            raise InvalidJSONError(
                f"JSON data in '{self.path}' is malformed: {error}"
            ) from error
        except UnicodeDecodeError as error:
            raise InvalidJSONError(
                f"JSON data in '{self.path}' is not valid UTF-8: {error}"
            ) from error
        except OSError as error:
            raise StorageError(
                f"Unable to read '{self.path}': {error}"
            ) from error

    def save(self, obj: Any) -> None:
        """Atomically replace the JSON file, preserving the old file on failure."""
        temporary_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                json.dump(obj, file, indent=2, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        except (OSError, RecursionError, TypeError, ValueError) as error:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    raise StorageError(
                        f"Unable to save '{self.path}': {error}. "
                        f"Temporary file '{temporary_path}' could not be "
                        f"removed: {cleanup_error}"
                    ) from error
            raise StorageError(
                f"Unable to save '{self.path}': {error}"
            ) from error
