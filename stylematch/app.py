"""Application entrypoint for StyleMatch.

This module contains only the minimal bootstrap to start the Tkinter UI.
Business logic lives in other modules under stylematch.*
"""

from stylematch.ui.main_window import main
from stylematch.services.clothing_manager import ClothingManager
from stylematch.storage.wardrobe_persistence import WardrobePersistence


def run() -> None:
    """Run the StyleMatch application UI."""
    persistence = WardrobePersistence()
    manager = ClothingManager(persistence=persistence)
    main(manager=manager, startup_warning=persistence.startup_warning)


if __name__ == "__main__":
    run()
