"""Cross-platform locations for mutable StyleMatch application data."""

import os
import platform
from pathlib import Path


def get_app_data_dir() -> Path:
    """Return the per-user StyleMatch data directory without creating it."""
    operating_system = platform.system()
    if operating_system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        candidate = Path(local_app_data) if local_app_data else None
        base = (
            candidate
            if candidate is not None and candidate.is_absolute()
            else Path.home() / "AppData" / "Local"
        )
    elif operating_system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        candidate = Path(xdg_data_home) if xdg_data_home else None
        base = (
            candidate
            if candidate is not None and candidate.is_absolute()
            else Path.home() / ".local" / "share"
        )
    return base / "StyleMatch"
