"""Main Tkinter window and navigation for StyleMatch."""

import tkinter as tk
from tkinter import messagebox, ttk

from stylematch.services.clothing_manager import ClothingManager
from stylematch.services.outfit_manager import OutfitManager
from stylematch.storage.outfit_persistence import OutfitPersistence
from stylematch.ui.screens import (
    AddClothingScreen,
    OutfitBuilderScreen,
    SavedOutfitsScreen,
    WardrobeScreen,
)
from stylematch.ui.theme import BEIGE, BROWN, CREAM, MUTED_BROWN, WHITE

WINDOW_TITLE = "StyleMatch"
WINDOW_SIZE = "1100x750"
WINDOW_MIN_SIZE = (850, 600)


class StyleMatchWindow:
    """Build the shared application shell and switch between its screens."""

    def __init__(
        self,
        root: tk.Tk,
        manager: ClothingManager | None = None,
        outfit_manager: OutfitManager | None = None,
    ) -> None:
        self.root = root
        self.clothing_manager = (
            manager if manager is not None else ClothingManager()
        )
        self.outfit_manager = (
            outfit_manager
            if outfit_manager is not None
            else OutfitManager(self.clothing_manager)
        )
        self.current_screen_name: str | None = None
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)
        self._configure_styles()
        self._build_layout()
        self._build_screens()
        self.show_screen("My Wardrobe")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10), foreground=BROWN)
        style.configure("App.TFrame", background=CREAM)
        style.configure("Header.TFrame", background=WHITE)
        style.configure("Sidebar.TFrame", background=CREAM)
        style.configure("Content.TFrame", background=CREAM)
        style.configure("Panel.TFrame", background=WHITE)
        style.configure("SoftPanel.TFrame", background=BEIGE)
        style.configure(
            "AppTitle.TLabel",
            background=WHITE,
            foreground=BROWN,
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=WHITE,
            foreground=MUTED_BROWN,
            font=("Segoe UI", 10),
        )
        style.configure(
            "PageTitle.TLabel",
            background=CREAM,
            foreground=BROWN,
            font=("Segoe UI", 19, "bold"),
        )
        style.configure(
            "PageDescription.TLabel",
            background=CREAM,
            foreground=MUTED_BROWN,
            font=("Segoe UI", 10),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=WHITE,
            foreground=BROWN,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "EmptyTitle.TLabel",
            background=WHITE,
            foreground=BROWN,
            font=("Segoe UI", 15, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background=WHITE,
            foreground=MUTED_BROWN,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Small.TLabel",
            background=WHITE,
            foreground=MUTED_BROWN,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Nav.TButton",
            background=CREAM,
            foreground=BROWN,
            anchor="w",
            padding=(14, 11),
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.map(
            "Nav.TButton",
            background=[("active", BEIGE)],
            foreground=[("active", BROWN)],
        )
        style.configure(
            "NavActive.TButton",
            background=BROWN,
            foreground=WHITE,
            anchor="w",
            padding=(14, 11),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "NavActive.TButton",
            background=[("active", BROWN)],
            foreground=[("active", WHITE)],
        )
        style.configure(
            "Primary.TButton",
            background=BROWN,
            foreground=WHITE,
            padding=(16, 9),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", MUTED_BROWN), ("disabled", BEIGE)],
            foreground=[("disabled", MUTED_BROWN)],
        )
        style.configure(
            "Secondary.TButton",
            background=BEIGE,
            foreground=BROWN,
            padding=(14, 8),
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#DCCEBF")])
        style.configure(
            "TEntry",
            fieldbackground=WHITE,
            foreground=BROWN,
            padding=8,
        )
        style.configure(
            "TCombobox",
            fieldbackground=WHITE,
            foreground=BROWN,
            padding=6,
        )

    def _build_layout(self) -> None:
        self.root.configure(background=CREAM)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(28, 18))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_group = ttk.Frame(header, style="Header.TFrame")
        title_group.grid(row=0, column=0, sticky="w")
        ttk.Label(title_group, text=WINDOW_TITLE, style="AppTitle.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            title_group,
            text="Your Personal Digital Wardrobe",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(1, 0))

        body = ttk.Frame(self.root, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=0, minsize=205)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(body, style="Sidebar.TFrame", padding=(16, 22))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        ttk.Label(
            self.sidebar,
            text="YOUR SPACE",
            style="Subtitle.TLabel",
            background=CREAM,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(2, 13))

        self.nav_buttons: dict[str, ttk.Button] = {}
        for row, screen_name in enumerate(
            ("My Wardrobe", "Add Clothing", "Outfit Builder", "Saved Outfits"),
            start=1,
        ):
            button = ttk.Button(
                self.sidebar,
                text=screen_name,
                style="Nav.TButton",
                command=lambda name=screen_name: self.show_screen(name),
            )
            button.grid(row=row, column=0, sticky="ew", pady=3)
            self.nav_buttons[screen_name] = button

        self.content = ttk.Frame(body, style="Content.TFrame", padding=(28, 26))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_screens(self) -> None:
        wardrobe = WardrobeScreen(
            self.content,
            manager=self.clothing_manager,
            on_add_clothing=lambda: self.show_screen("Add Clothing"),
        )
        saved_outfits = SavedOutfitsScreen(
            self.content,
            outfit_manager=self.outfit_manager,
        )
        self.screens: dict[str, ttk.Frame] = {
            "My Wardrobe": wardrobe,
            "Add Clothing": AddClothingScreen(
                self.content,
                parent_window=self.root,
                manager=self.clothing_manager,
                on_item_added=wardrobe.refresh,
            ),
            "Outfit Builder": OutfitBuilderScreen(
                self.content,
                manager=self.clothing_manager,
                outfit_manager=self.outfit_manager,
                on_saved=saved_outfits.refresh,
            ),
            "Saved Outfits": saved_outfits,
        }
        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")

    def show_screen(self, screen_name: str) -> None:
        """Raise a screen in the shared content area and highlight its navigation."""
        screen = self.screens[screen_name]
        if isinstance(screen, OutfitBuilderScreen):
            screen.refresh_from_wardrobe()
        elif isinstance(screen, SavedOutfitsScreen):
            screen.refresh()
        screen.tkraise()
        self.current_screen_name = screen_name
        for name, button in self.nav_buttons.items():
            button.configure(
                style="NavActive.TButton" if name == screen_name else "Nav.TButton"
            )


def main(
    manager: ClothingManager | None = None,
    startup_warning: str | None = None,
) -> None:
    root = tk.Tk()
    clothing_manager = manager if manager is not None else ClothingManager()
    outfit_persistence = (
        OutfitPersistence(clothing_manager.persistence.data_dir)
        if clothing_manager.persistence is not None
        else None
    )
    outfit_manager = OutfitManager(
        clothing_manager=clothing_manager,
        persistence=outfit_persistence,
    )
    StyleMatchWindow(
        root,
        manager=clothing_manager,
        outfit_manager=outfit_manager,
    )
    warnings = [
        warning
        for warning in (
            startup_warning,
            outfit_persistence.startup_warning
            if outfit_persistence is not None
            else None,
        )
        if warning
    ]
    if warnings:
        root.after_idle(
            lambda: messagebox.showwarning(
                "Local data warning",
                "\n\n".join(warnings),
                parent=root,
            )
        )
    root.mainloop()


if __name__ == "__main__":
    main()
