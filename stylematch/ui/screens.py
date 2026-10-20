"""Reusable screen layouts for the StyleMatch Tkinter interface."""

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk, UnidentifiedImageError

from stylematch.ui.theme import BEIGE, BROWN, CREAM, MUTED_BROWN, WHITE

CATEGORIES = ("Tops", "Bottoms", "Dresses", "Shoes", "Outerwear")


def add_page_heading(parent: ttk.Frame, title: str, description: str) -> None:
    """Add the shared title and description at the top of a screen."""
    heading = ttk.Frame(parent, style="Content.TFrame")
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 20))
    ttk.Label(heading, text=title, style="PageTitle.TLabel").pack(anchor="w")
    ttk.Label(
        heading,
        text=description,
        style="PageDescription.TLabel",
        wraplength=780,
    ).pack(anchor="w", pady=(5, 0))


class ScrollableArea(ttk.Frame):
    """A small canvas-backed area for galleries that can grow beyond the viewport."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="Panel.TFrame")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            background=WHITE,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ttk.Frame(self.canvas, style="Panel.TFrame", padding=20)
        self.content.grid_columnconfigure(0, weight=1)
        self.window_id = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.canvas.bind("<Configure>", self._resize_content)
        self.content.bind("<Configure>", self._update_scroll_region)

    def _resize_content(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)
        requested_height = self.content.winfo_reqheight()
        height = max(event.height, requested_height)
        self.canvas.itemconfigure(self.window_id, height=height)
        self.canvas.configure(scrollregion=(0, 0, event.width, height))

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.after_idle(self._refresh_scroll_region)

    def _refresh_scroll_region(self) -> None:
        bounds = self.canvas.bbox("all")
        if bounds is not None:
            self.canvas.configure(scrollregion=bounds)


class WardrobeScreen(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        on_add_clothing: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.on_add_clothing = on_add_clothing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        add_page_heading(
            self,
            "My Wardrobe",
            "A thoughtful overview of the pieces you own and love.",
        )

        toolbar = ttk.Frame(self, style="Content.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        toolbar.grid_columnconfigure(1, weight=1)
        ttk.Label(
            toolbar,
            text="CATEGORY",
            style="PageDescription.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.category_filter = tk.StringVar(value="All")
        self.category_select = ttk.Combobox(
            toolbar,
            textvariable=self.category_filter,
            values=("All",) + CATEGORIES,
            state="readonly",
            width=18,
        )
        self.category_select.grid(row=0, column=1, sticky="w")
        self.category_select.bind("<<ComboboxSelected>>", self._update_empty_state)
        ttk.Button(
            toolbar,
            text="Add Clothing",
            style="Primary.TButton",
            command=self.on_add_clothing,
        ).grid(row=0, column=2, sticky="e")

        self.gallery = ScrollableArea(self)
        self.gallery.grid(row=2, column=0, sticky="nsew")
        self.gallery.content.grid_rowconfigure(0, weight=1)
        empty_state = ttk.Frame(
            self.gallery.content,
            style="Panel.TFrame",
            padding=(28, 34),
        )
        empty_state.grid(row=0, column=0, sticky="nsew")
        empty_state.grid_columnconfigure(0, weight=1)
        ttk.Label(
            empty_state,
            text="A wardrobe made yours",
            style="EmptyTitle.TLabel",
        ).grid(row=0, column=0, pady=(0, 8))
        self.empty_message = ttk.Label(
            empty_state,
            text="Your wardrobe is ready for its first piece.",
            style="Body.TLabel",
            wraplength=420,
            justify="center",
        )
        self.empty_message.grid(row=1, column=0, pady=(0, 20))
        ttk.Button(
            empty_state,
            text="Add your first item",
            style="Secondary.TButton",
            command=self.on_add_clothing,
        ).grid(row=2, column=0)

    def _update_empty_state(self, _event: tk.Event) -> None:
        category = self.category_filter.get()
        message = (
            "Your wardrobe is ready for its first piece."
            if category == "All"
            else f"No {category.lower()} in your wardrobe yet."
        )
        self.empty_message.configure(text=message)


class AddClothingScreen(ttk.Frame):
    def __init__(self, parent: ttk.Frame, parent_window: tk.Tk) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.parent_window = parent_window
        self.selected_image: str | None = None
        self.preview_image: ImageTk.PhotoImage | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        add_page_heading(
            self,
            "Add Clothing",
            "Add a piece to your digital wardrobe. Saving is not connected yet.",
        )

        panel = ttk.Frame(self, style="Panel.TFrame", padding=24)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.grid(row=0, column=0, sticky="new", padx=(0, 28))
        form.grid_columnconfigure(0, weight=1)
        ttk.Label(form, text="Clothing details", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 20)
        )

        ttk.Label(form, text="Clothing name", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var).grid(
            row=2, column=0, sticky="ew", pady=(0, 18)
        )

        ttk.Label(form, text="Category", style="Body.TLabel").grid(
            row=3, column=0, sticky="w", pady=(0, 6)
        )
        self.category_var = tk.StringVar()
        ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=CATEGORIES,
            state="readonly",
        ).grid(row=4, column=0, sticky="ew", pady=(0, 20))

        image_section = ttk.Frame(panel, style="Panel.TFrame", width=185)
        image_section.grid(row=0, column=1, sticky="n")
        image_section.grid_propagate(False)
        ttk.Label(
            image_section,
            text="Image preview",
            style="SectionTitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))
        self.preview_box = ttk.Frame(
            image_section,
            style="SoftPanel.TFrame",
            width=150,
            height=150,
        )
        self.preview_box.pack(anchor="w", pady=(0, 10))
        self.preview_box.pack_propagate(False)
        self.preview_label = ttk.Label(
            self.preview_box,
            text="No image\nselected",
            style="Body.TLabel",
            background=BEIGE,
            justify="center",
        )
        self.preview_label.pack(expand=True, fill="both")
        ttk.Button(
            image_section,
            text="Choose image",
            style="Secondary.TButton",
            command=self._choose_image,
        ).pack(anchor="w")
        self.filename_label = ttk.Label(
            image_section,
            text="No file selected",
            style="Small.TLabel",
            wraplength=175,
        )
        self.filename_label.pack(anchor="w", pady=(8, 0))

        ttk.Separator(panel).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(22, 16)
        )
        footer = ttk.Frame(panel, style="Panel.TFrame")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            text="This button is a placeholder; no clothing data will be saved.",
            style="Small.TLabel",
            wraplength=500,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Button(
            footer,
            text="Add Clothing",
            style="Primary.TButton",
            command=self._show_placeholder,
        ).grid(row=0, column=1, sticky="e")

    def _choose_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.parent_window,
            title="Choose a clothing image",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*"),
            ),
        )
        if not path:
            return

        try:
            with Image.open(path) as image:
                image.thumbnail((138, 138), Image.Resampling.LANCZOS)
                preview = ImageTk.PhotoImage(
                    image.convert("RGBA"),
                    master=self.parent_window,
                )
        except (
            UnidentifiedImageError,
            Image.DecompressionBombError,
            OSError,
            ValueError,
            tk.TclError,
        ):
            messagebox.showwarning(
                "Unable to preview image",
                "This file is not a supported or readable image. Please choose another file.",
                parent=self.parent_window,
            )
            return

        self.selected_image = path
        self.preview_image = preview
        self.preview_label.configure(image=self.preview_image, text="")
        self.filename_label.configure(text=Path(path).name)

    def _show_placeholder(self) -> None:
        messagebox.showinfo(
            "Not connected yet",
            "Clothing can be previewed here, but adding it to your wardrobe is not implemented yet.",
            parent=self.parent_window,
        )


class OutfitBuilderScreen(ttk.Frame):
    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        add_page_heading(
            self,
            "Outfit Builder",
            "Bring your pieces together and preview a look. Outfit creation is not connected yet.",
        )

        workspace = ttk.Frame(self, style="Content.TFrame")
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1, uniform="outfit")
        workspace.grid_columnconfigure(1, weight=1, uniform="outfit")
        workspace.grid_rowconfigure(0, weight=1)

        selection_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=22)
        selection_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        selection_panel.grid_columnconfigure(0, weight=1)
        ttk.Label(
            selection_panel,
            text="Build your look",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        ttk.Label(selection_panel, text="Outfit name", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        self.outfit_name = tk.StringVar()
        ttk.Entry(selection_panel, textvariable=self.outfit_name).grid(
            row=2, column=0, sticky="ew", pady=(0, 16)
        )

        for row, category in enumerate(
            ("Top", "Bottom", "Dress", "Shoes", "Outerwear"),
            start=3,
        ):
            ttk.Label(selection_panel, text=category, style="Body.TLabel").grid(
                row=row, column=0, sticky="w", pady=(0, 5)
            )
            ttk.Combobox(
                selection_panel,
                values=("No items available",),
                state="disabled",
            ).grid(row=row + 1, column=0, sticky="ew", pady=(0, 12))

        preview_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=22)
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        preview_panel.grid_columnconfigure(0, weight=1)
        preview_panel.grid_rowconfigure(1, weight=1)
        ttk.Label(
            preview_panel,
            text="Outfit preview",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))
        preview = ttk.Frame(preview_panel, style="SoftPanel.TFrame")
        preview.grid(row=1, column=0, sticky="nsew")
        preview.grid_columnconfigure(0, weight=1)
        preview.grid_rowconfigure(0, weight=1)
        ttk.Label(
            preview,
            text="Your outfit preview\nwill appear here",
            style="Body.TLabel",
            background=BEIGE,
            justify="center",
            wraplength=230,
        ).grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        ttk.Button(
            preview_panel,
            text="Save Outfit",
            style="Primary.TButton",
            command=self._show_placeholder,
        ).grid(row=2, column=0, sticky="e", pady=(16, 0))

    def _show_placeholder(self) -> None:
        messagebox.showinfo(
            "Not connected yet",
            "Saving outfits is not implemented yet; no outfit data was saved.",
            parent=self.winfo_toplevel(),
        )


class SavedOutfitsScreen(ttk.Frame):
    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        add_page_heading(
            self,
            "Saved Outfits",
            "Your saved combinations will have a home here.",
        )

        self.gallery = ScrollableArea(self)
        self.gallery.grid(row=1, column=0, sticky="nsew")
        self.gallery.content.grid_rowconfigure(0, weight=1)
        empty_state = ttk.Frame(
            self.gallery.content,
            style="Panel.TFrame",
            padding=(28, 34),
        )
        empty_state.grid(row=0, column=0, sticky="nsew")
        empty_state.grid_columnconfigure(0, weight=1)
        ttk.Label(
            empty_state,
            text="Looks will live here",
            style="EmptyTitle.TLabel",
        ).grid(row=0, column=0, pady=(0, 8))
        ttk.Label(
            empty_state,
            text="There are no saved outfits yet. Saving outfits will be available when the builder is connected.",
            style="Body.TLabel",
            wraplength=460,
            justify="center",
        ).grid(row=1, column=0)
