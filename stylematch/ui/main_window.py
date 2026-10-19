"""Minimal Tkinter main window for StyleMatch.

This file contains only UI wiring and imports the business-layer modules but does not implement logic yet.
"""
import tkinter as tk
from tkinter import ttk

WINDOW_TITLE = "StyleMatch"
WINDOW_MIN_SIZE = (600, 400)


def main() -> None:
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.minsize(*WINDOW_MIN_SIZE)

    # Simple header frame
    header = ttk.Frame(root, padding=10)
    header.pack(fill="x")

    title_label = ttk.Label(header, text=WINDOW_TITLE, font=("Segoe UI", 16, "bold"))
    title_label.pack(side="left")

    # Content placeholder
    content = ttk.Frame(root, padding=10)
    content.pack(fill="both", expand=True)

    placeholder = ttk.Label(content, text="Welcome to StyleMatch (UI placeholder)")
    placeholder.pack(pady=20)

    # Status bar
    status = ttk.Label(root, text="Ready", relief="sunken", anchor="w")
    status.pack(fill="x", side="bottom")

    root.mainloop()


if __name__ == "__main__":
    main()
