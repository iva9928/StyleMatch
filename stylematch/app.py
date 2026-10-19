"""Application entrypoint for StyleMatch.

This module contains only the minimal bootstrap to start the Tkinter UI.
Business logic lives in other modules under stylematch.*
"""

from stylematch.ui.main_window import main


def run() -> None:
    """Run the StyleMatch application UI."""
    main()


if __name__ == "__main__":
    run()
