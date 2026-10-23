"""Reusable screen layouts for the StyleMatch Tkinter interface."""

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from stylematch.images import ImageValidationError, create_thumbnail
from stylematch.models.clothing import (
    PRIMARY_COLORS,
    STYLES,
    ClothingItem,
)
from stylematch.models.outfit import Outfit
from stylematch.outfits.builder import OutfitBuilder
from stylematch.outfits.compatibility import CompatibilityResult
from stylematch.services.clothing_manager import CATEGORIES, ClothingManager
from stylematch.services.outfit_manager import OutfitManager
from stylematch.storage.json_store import StorageError
from stylematch.storage.wardrobe_persistence import PostCommitStorageError
from stylematch.ui.theme import BEIGE, BROWN, CREAM, MUTED_BROWN, WHITE


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


class EditClothingMetadataDialog(tk.Toplevel):
    """Edit optional color and style values without touching the item's image."""

    def __init__(
        self,
        parent: tk.Tk,
        manager: ClothingManager,
        item: ClothingItem,
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.item = item
        self.on_saved = on_saved
        self.title("Edit clothing details")
        self.transient(parent)
        self.resizable(False, False)
        self.columnconfigure(0, weight=1)

        form = ttk.Frame(self, padding=20)
        form.grid(row=0, column=0, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        ttk.Label(form, text=item.name, style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(form, text=item.category, style="Small.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 14)
        )
        ttk.Label(form, text="Primary color", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self.color_var = tk.StringVar(value=item.primary_color or "")
        self.color_select = ttk.Combobox(
            form,
            textvariable=self.color_var,
            values=("", *PRIMARY_COLORS),
            state="readonly",
        )
        self.color_select.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(form, text="Style", style="Body.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 4)
        )
        self.style_var = tk.StringVar(value=item.style or "")
        self.style_select = ttk.Combobox(
            form,
            textvariable=self.style_var,
            values=("", *STYLES),
            state="readonly",
        )
        self.style_select.grid(row=5, column=0, sticky="ew", pady=(0, 16))
        buttons = ttk.Frame(form)
        buttons.grid(row=6, column=0, sticky="e")
        ttk.Button(
            buttons,
            text="Cancel",
            style="Secondary.TButton",
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            buttons,
            text="Save",
            style="Primary.TButton",
            command=self._save,
        ).grid(row=0, column=1)
        self.grab_set()

    def _save(self) -> None:
        try:
            self.manager.update_metadata(
                self.item.id,
                self.color_var.get(),
                self.style_var.get(),
            )
        except (StorageError, ValueError) as error:
            messagebox.showerror(
                "Unable to update clothing",
                str(error),
                parent=self,
            )
            return
        self.on_saved()
        messagebox.showinfo(
            "Clothing updated",
            f"Details for {self.item.name} were saved.",
            parent=self,
        )
        self.destroy()


class WardrobeScreen(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        manager: ClothingManager,
        on_add_clothing: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.manager = manager
        self.on_add_clothing = on_add_clothing
        self._photo_images: list[ImageTk.PhotoImage] = []
        self._columns = 0
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
        self.gallery.canvas.bind("<Configure>", self._on_gallery_resize, add="+")
        self.empty_message: ttk.Label | None = None
        self.refresh()

    def _update_empty_state(self, _event: tk.Event) -> None:
        self.refresh()

    def _on_gallery_resize(self, _event: tk.Event) -> None:
        items = self._filtered_items()
        columns = self._column_count(len(items))
        if items and columns != self._columns:
            self.refresh()

    def _filtered_items(self) -> list[ClothingItem]:
        category = self.category_filter.get()
        return self.manager.list_items(None if category == "All" else category)

    def _column_count(self, item_count: int) -> int:
        available_width = max(1, self.gallery.canvas.winfo_width() - 40)
        return max(1, min(item_count or 1, available_width // 230))

    def refresh(self) -> None:
        """Redraw the current filter without retaining stale widgets or images."""
        content = self.gallery.content
        for column in range(self._columns):
            content.grid_columnconfigure(column, weight=0, uniform="")
        for child in content.winfo_children():
            child.destroy()
        self.empty_message = None
        self._photo_images.clear()

        items = self._filtered_items()
        if not items:
            category = self.category_filter.get()
            message = (
                "Your wardrobe is ready for its first piece."
                if category == "All" and not self.manager.list_items()
                else (
                    "No clothing items match this filter."
                    if category == "All"
                    else f"No {category.lower()} in your wardrobe yet."
                )
            )
            empty_state = ttk.Frame(content, style="Panel.TFrame", padding=(28, 34))
            empty_state.grid(row=0, column=0, sticky="nsew")
            empty_state.grid_columnconfigure(0, weight=1)
            ttk.Label(
                empty_state,
                text="A wardrobe made yours",
                style="EmptyTitle.TLabel",
            ).grid(row=0, column=0, pady=(0, 8))
            self.empty_message = ttk.Label(
                empty_state,
                text=message,
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
            self._columns = 0
            return

        columns = self._column_count(len(items))
        self._columns = columns
        for column in range(columns):
            content.grid_columnconfigure(column, weight=1, uniform="wardrobe")
        for index, item in enumerate(items):
            self._create_item_card(item, index // columns, index % columns)

    def _create_item_card(self, item: ClothingItem, row: int, column: int) -> None:
        card = ttk.Frame(
            self.gallery.content,
            style="SoftPanel.TFrame",
            padding=12,
        )
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure((0, 1), weight=1)
        image_box = ttk.Frame(card, style="SoftPanel.TFrame", width=170, height=170)
        image_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        image_box.grid_propagate(False)

        try:
            thumbnail = create_thumbnail(item.image_path or "", (150, 150))
            photo = ImageTk.PhotoImage(thumbnail, master=self.winfo_toplevel())
            self._photo_images.append(photo)
            image_label = ttk.Label(
                image_box,
                image=photo,
                background=BEIGE,
                anchor="center",
            )
        except ImageValidationError:
            image_label = ttk.Label(
                image_box,
                text="Image unavailable",
                style="Body.TLabel",
                background=BEIGE,
                anchor="center",
                width=23,
            )
        image_label.pack(fill="both", expand=True)
        ttk.Label(
            card,
            text=item.name,
            style="SectionTitle.TLabel",
            wraplength=210,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(card, text=item.category, style="Small.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(3, 2)
        )
        metadata_text = " · ".join(
            value
            for value in (
                f"Color: {item.primary_color}" if item.primary_color else "",
                f"Style: {item.style}" if item.style else "",
            )
            if value
        ) or "No color or style details"
        ttk.Label(
            card,
            text=metadata_text,
            style="Small.TLabel",
            wraplength=210,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Button(
            card,
            text="Edit",
            style="Secondary.TButton",
            command=lambda item_id=item.id: self._edit_item(item_id),
        ).grid(row=4, column=0, sticky="w")
        ttk.Button(
            card,
            text="Delete",
            style="Secondary.TButton",
            command=lambda item_id=item.id: self._delete_item(item_id),
        ).grid(row=4, column=1, sticky="e")

    def _edit_item(self, item_id: str) -> None:
        item = next(
            (item for item in self.manager.list_items() if item.id == item_id),
            None,
        )
        if item is None:
            messagebox.showerror(
                "Unable to edit clothing",
                "This clothing item is no longer in your wardrobe.",
                parent=self.winfo_toplevel(),
            )
            return
        self.edit_dialog = EditClothingMetadataDialog(
            self.winfo_toplevel(),
            self.manager,
            item,
            on_saved=self.refresh,
        )

    def _delete_item(self, item_id: str) -> None:
        if not messagebox.askyesno(
            "Delete clothing item",
            "Are you sure you want to delete this clothing item?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            deleted = self.manager.delete_item(item_id)
        except PostCommitStorageError as error:
            self.refresh()
            messagebox.showwarning(
                "Clothing deleted",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        except StorageError as error:
            messagebox.showerror(
                "Unable to delete clothing",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        if deleted:
            self.refresh()


class AddClothingScreen(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        parent_window: tk.Tk,
        manager: ClothingManager,
        on_item_added: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.parent_window = parent_window
        self.manager = manager
        self.on_item_added = on_item_added
        self.selected_image: str | None = None
        self.preview_image: ImageTk.PhotoImage | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        add_page_heading(
            self,
            "Add Clothing",
            "Add a piece to your digital wardrobe.",
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
        self.category_select = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=CATEGORIES,
            state="readonly",
        )
        self.category_select.grid(row=4, column=0, sticky="ew", pady=(0, 20))

        ttk.Label(form, text="Primary color (optional)", style="Body.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 6)
        )
        self.color_var = tk.StringVar()
        self.color_select = ttk.Combobox(
            form,
            textvariable=self.color_var,
            values=("", *PRIMARY_COLORS),
            state="readonly",
        )
        self.color_select.grid(row=6, column=0, sticky="ew", pady=(0, 14))

        ttk.Label(form, text="Style (optional)", style="Body.TLabel").grid(
            row=7, column=0, sticky="w", pady=(0, 6)
        )
        self.style_var = tk.StringVar()
        self.style_select = ttk.Combobox(
            form,
            textvariable=self.style_var,
            values=("", *STYLES),
            state="readonly",
        )
        self.style_select.grid(row=8, column=0, sticky="ew", pady=(0, 20))

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
            text="Your clothing and imported image are stored on this device.",
            style="Small.TLabel",
            wraplength=500,
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.add_button = ttk.Button(
            footer,
            text="Add Clothing",
            style="Primary.TButton",
            command=self._add_clothing,
        )
        self.add_button.grid(row=0, column=1, sticky="e")

    def _choose_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.parent_window,
            title="Choose a clothing image",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*"),
            ),
        )
        if not path:
            return

        try:
            image = create_thumbnail(path, (138, 138))
            preview = ImageTk.PhotoImage(image, master=self.parent_window)
        except (ImageValidationError, tk.TclError):
            self._clear_selected_image()
            messagebox.showwarning(
                "Unable to preview image",
                "This file is not a supported or readable PNG, JPEG, or WEBP image. Please choose another file.",
                parent=self.parent_window,
            )
            return

        self.selected_image = path
        self.preview_image = preview
        self.preview_label.configure(image=self.preview_image, text="")
        self.filename_label.configure(text=Path(path).name)

    def _clear_selected_image(self) -> None:
        self.selected_image = None
        self.preview_image = None
        self.preview_label.configure(image="", text="No image\nselected")
        self.filename_label.configure(text="No file selected")

    def _add_clothing(self) -> None:
        try:
            item = self.manager.add_item(
                self.name_var.get(),
                self.category_var.get(),
                self.selected_image,
                self.color_var.get(),
                self.style_var.get(),
            )
        except (ImageValidationError, StorageError, ValueError) as error:
            messagebox.showerror(
                "Unable to add clothing",
                str(error),
                parent=self.parent_window,
            )
            return

        self.on_item_added()
        messagebox.showinfo(
            "Clothing added",
            f"{item.name} was added to your wardrobe.",
            parent=self.parent_window,
        )
        self.name_var.set("")
        self.category_var.set("")
        self.color_var.set("")
        self.style_var.set("")
        self._clear_selected_image()


class OutfitBuilderScreen(ttk.Frame):
    CATEGORY_LABELS = {
        "Tops": "Top",
        "Bottoms": "Bottom",
        "Dresses": "Dress",
        "Shoes": "Shoes",
        "Outerwear": "Outerwear",
        "Jackets": "Jackets",
    }

    def __init__(
        self,
        parent: ttk.Frame,
        manager: ClothingManager,
        outfit_manager: OutfitManager,
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.manager = manager
        self.outfit_manager = outfit_manager
        self.builder: OutfitBuilder = outfit_manager.builder
        self.on_saved = on_saved
        self._category_items: dict[str, dict[str, ClothingItem]] = {}
        self._photo_images: list[ImageTk.PhotoImage] = []
        self._active_compatibility = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        add_page_heading(
            self,
            "Outfit Builder",
            "Create a look from pieces already in your wardrobe. Suggestions use category rules, not fashion-style or color analysis.",
        )

        workspace = ttk.Frame(self, style="Content.TFrame")
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1, uniform="outfit")
        workspace.grid_columnconfigure(1, weight=1, uniform="outfit")
        workspace.grid_rowconfigure(0, weight=1)

        selection_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=22)
        selection_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        selection_panel.grid_columnconfigure(0, weight=1)
        selection_panel.grid_rowconfigure(1, weight=1)
        ttk.Label(
            selection_panel,
            text="Build your look",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        self.selector_area = ScrollableArea(selection_panel)
        self.selector_area.grid(row=1, column=0, sticky="nsew")
        form = self.selector_area.content
        form.grid_columnconfigure(0, weight=1)
        ttk.Label(form, text="Outfit name", style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.outfit_name = tk.StringVar()
        ttk.Entry(form, textvariable=self.outfit_name).grid(
            row=1, column=0, sticky="ew", pady=(0, 16)
        )

        self.selector_vars: dict[str, tk.StringVar] = {}
        self.selectors: dict[str, ttk.Combobox] = {}
        self.selector_labels: dict[str, ttk.Label] = {}
        for index, category in enumerate(self.CATEGORY_LABELS):
            label = ttk.Label(
                form,
                text=self.CATEGORY_LABELS[category],
                style="Body.TLabel",
            )
            label.grid(
                row=2 + index * 2,
                column=0,
                sticky="w",
                pady=(0, 4),
            )
            self.selector_labels[category] = label
            variable = tk.StringVar()
            selector = ttk.Combobox(
                form,
                textvariable=variable,
                state="readonly",
            )
            selector.grid(
                row=3 + index * 2,
                column=0,
                sticky="ew",
                pady=(0, 7),
            )
            selector.bind(
                "<<ComboboxSelected>>",
                lambda _event: self._selection_changed(),
            )
            self.selector_vars[category] = variable
            self.selectors[category] = selector

        actions = ttk.Frame(selection_panel, style="Panel.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.suggest_button = ttk.Button(
            actions,
            text="Suggest Outfit",
            style="Secondary.TButton",
            command=self._suggest_outfit,
        )
        self.suggest_button.grid(row=0, column=0, sticky="w")
        self.try_another_button = ttk.Button(
            actions,
            text="Try Another",
            style="Secondary.TButton",
            command=self._try_another,
            state="disabled",
        )
        self.try_another_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        preview_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=22)
        preview_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        preview_panel.grid_columnconfigure(0, weight=1)
        preview_panel.grid_rowconfigure(1, weight=1)
        ttk.Label(
            preview_panel,
            text="Outfit preview",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))
        self.preview = ttk.Frame(preview_panel, style="SoftPanel.TFrame", padding=12)
        self.preview.grid(row=1, column=0, sticky="nsew")
        self.preview.grid_columnconfigure((0, 1), weight=1)
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(
            preview_panel,
            textvariable=self.status_var,
            style="Small.TLabel",
            wraplength=360,
        )
        self.status_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.compatibility_var = tk.StringVar()
        self.compatibility_label = ttk.Label(
            preview_panel,
            textvariable=self.compatibility_var,
            style="Small.TLabel",
            wraplength=360,
        )
        self.compatibility_label.grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.save_button = ttk.Button(
            preview_panel,
            text="Save Outfit",
            style="Primary.TButton",
            command=self._save_outfit,
        )
        self.save_button.grid(row=4, column=0, sticky="e", pady=(12, 0))
        self.refresh_from_wardrobe()

    @staticmethod
    def _display_labels(items: list[ClothingItem]) -> list[str]:
        """Create unique readable labels without exposing internal item IDs."""
        name_counts: dict[str, int] = {}
        for item in items:
            name_counts[item.name] = name_counts.get(item.name, 0) + 1

        original_names = set(name_counts)
        seen: set[str] = set()
        occurrences: dict[str, int] = {}
        labels = []
        for item in items:
            label = item.name
            if name_counts[item.name] > 1:
                occurrences[item.name] = occurrences.get(item.name, 0) + 1
                label = f"{item.name} ({occurrences[item.name]})"
            while label in seen or (label != item.name and label in original_names):
                label = f"{label} (wardrobe item)"
            seen.add(label)
            labels.append(label)
        return labels

    def refresh_from_wardrobe(self) -> None:
        """Refresh category options and remove choices no longer in the wardrobe."""
        self._active_compatibility = None
        for category, selector in self.selectors.items():
            current_item = self._category_items.get(category, {}).get(
                self.selector_vars[category].get()
            )
            current_id = current_item.id if current_item is not None else None
            items = self.manager.list_items(category)
            labels = self._display_labels(items)
            category_items = dict(zip(labels, items))
            self._category_items[category] = category_items
            selector.configure(values=("", *labels))
            selection = next(
                (
                    label
                    for label, item in category_items.items()
                    if item.id == current_id
                ),
                "",
            )
            self.selector_vars[category].set(selection)
        self._update_preview()

    def _selection_changed(self) -> None:
        self._active_compatibility = None
        self._update_preview()

    def _selected_items(self) -> list[ClothingItem]:
        return [
            self._category_items[category][choice]
            for category, variable in self.selector_vars.items()
            if (choice := variable.get()) in self._category_items[category]
        ]

    def _update_preview(self) -> None:
        for child in self.preview.winfo_children():
            child.destroy()
        self._photo_images.clear()
        items = self._selected_items()
        if not items:
            ttk.Label(
                self.preview,
                text="Choose wardrobe pieces to preview your look.",
                style="Body.TLabel",
                background=BEIGE,
                justify="center",
                wraplength=260,
            ).grid(row=0, column=0, columnspan=2, sticky="nsew", padx=12, pady=20)
        for index, item in enumerate(items):
            cell = ttk.Frame(self.preview, style="SoftPanel.TFrame", padding=6)
            cell.grid(row=index // 2, column=index % 2, sticky="nsew", padx=4, pady=4)
            try:
                thumbnail = create_thumbnail(item.image_path or "", (88, 88))
                photo = ImageTk.PhotoImage(thumbnail, master=self.winfo_toplevel())
                self._photo_images.append(photo)
                image_label = ttk.Label(
                    cell, image=photo, background=BEIGE, anchor="center"
                )
            except ImageValidationError:
                image_label = ttk.Label(
                    cell,
                    text="Image unavailable",
                    style="Small.TLabel",
                    background=BEIGE,
                    anchor="center",
                )
            image_label.pack(fill="both", expand=True)
            ttk.Label(
                cell,
                text=item.name,
                style="Small.TLabel",
                background=BEIGE,
                wraplength=110,
            ).pack(anchor="center", pady=(4, 0))
        try:
            OutfitBuilder.validate_items(items)
        except ValueError:
            self.status_var.set(
                "Choose Top + Bottom + Shoes, or Dress + Shoes. "
                "Outerwear or Jackets is optional; choose no more than one."
            )
        else:
            self.status_var.set("This is a complete outfit and is ready to save.")
        if self._active_compatibility is None:
            self.compatibility_var.set("")
        else:
            result = self._active_compatibility
            estimate = (
                f"Heuristic compatibility estimate: {result.score}/100. "
                f"{result.explanation}"
            )
            if self.builder.search_was_limited:
                estimate += (
                    f" Ranked within the first "
                    f"{self.builder.evaluated_candidate_count:,} combinations "
                    "evaluated; remaining combinations were not scored."
                )
            else:
                estimate += (
                    f" Ranked from {self.builder.evaluated_candidate_count:,} "
                    "valid combinations evaluated."
                )
            if (
                self.builder.evaluated_candidate_count
                > self.builder.MAX_RANKED_SUGGESTIONS
            ):
                estimate += (
                    f" Try Another offers the top "
                    f"{self.builder.MAX_RANKED_SUGGESTIONS} ranked choices."
                )
            self.compatibility_var.set(estimate)
        self._update_try_another_state()

    def _set_selection(
        self,
        items: list[ClothingItem],
        compatibility: CompatibilityResult | None = None,
    ) -> None:
        self._active_compatibility = compatibility
        selected = {item.category: item.id for item in items}
        for category, choices in self._category_items.items():
            choice = next(
                (
                    label
                    for label, item in choices.items()
                    if item.id == selected.get(category)
                ),
                "",
            )
            self.selector_vars[category].set(choice)
        self._update_preview()

    def _suggest_outfit(self) -> None:
        suggestion = self.builder.suggest_outfit()
        if suggestion is None:
            messagebox.showinfo(
                "No complete outfit available",
                "Add a Top, Bottom, and Shoes, or a Dress and Shoes, "
                "to your wardrobe before requesting a suggestion.",
                parent=self.winfo_toplevel(),
            )
            self._update_try_another_state()
            return
        self._set_selection(suggestion, self.builder.current_compatibility)

    def _try_another(self) -> None:
        suggestion = self.builder.try_another()
        if suggestion is None:
            messagebox.showinfo(
                "No other outfit available",
                "There is no different complete combination in your wardrobe yet.",
                parent=self.winfo_toplevel(),
            )
            self._update_try_another_state()
            return
        self._set_selection(suggestion, self.builder.current_compatibility)

    def _update_try_another_state(self) -> None:
        state = "normal" if self.builder.has_alternative() else "disabled"
        self.try_another_button.configure(state=state)

    def _save_outfit(self) -> None:
        selected_ids = [item.id for item in self._selected_items()]
        try:
            outfit = self.outfit_manager.save_outfit(
                self.outfit_name.get(), selected_ids
            )
        except (StorageError, ValueError) as error:
            messagebox.showerror(
                "Unable to save outfit",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        self.on_saved()
        messagebox.showinfo(
            "Outfit saved",
            f"{outfit.name} was saved to Saved Outfits.",
            parent=self.winfo_toplevel(),
        )
        self.outfit_name.set("")


class SavedOutfitsScreen(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        outfit_manager: OutfitManager,
    ) -> None:
        super().__init__(parent, style="Content.TFrame")
        self.outfit_manager = outfit_manager
        self._photo_images: list[ImageTk.PhotoImage] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        add_page_heading(
            self,
            "Saved Outfits",
            "Your saved looks, made from pieces in your wardrobe.",
        )

        self.gallery = ScrollableArea(self)
        self.gallery.grid(row=1, column=0, sticky="nsew")
        self.refresh()

    def refresh(self) -> None:
        content = self.gallery.content
        for child in content.winfo_children():
            child.destroy()
        self._photo_images.clear()
        outfits = self.outfit_manager.list_outfits()
        if not outfits:
            empty_state = ttk.Frame(
                content, style="Panel.TFrame", padding=(28, 34)
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
                text="There are no saved outfits yet. Create one in Outfit Builder.",
                style="Body.TLabel",
                wraplength=460,
                justify="center",
            ).grid(row=1, column=0)
            return
        for row, outfit in enumerate(outfits):
            self._create_outfit_card(outfit, row)

    def _create_outfit_card(self, outfit: Outfit, row: int) -> None:
        card = ttk.Frame(
            self.gallery.content, style="Panel.TFrame", padding=14
        )
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        header = ttk.Frame(card, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(
            header, text=outfit.name, style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Delete",
            style="Secondary.TButton",
            command=lambda outfit_id=outfit.id: self._delete_outfit(outfit_id),
        ).grid(row=0, column=1, sticky="e")
        preview = ttk.Frame(card, style="Panel.TFrame")
        preview.grid(row=1, column=0, sticky="w", pady=(10, 0))
        available, missing = self.outfit_manager.available_items(outfit)
        for column, item in enumerate(available):
            cell = ttk.Frame(preview, style="SoftPanel.TFrame", padding=6)
            cell.grid(row=0, column=column, padx=(0, 8), sticky="n")
            try:
                thumbnail = create_thumbnail(item.image_path or "", (82, 82))
                photo = ImageTk.PhotoImage(thumbnail, master=self.winfo_toplevel())
                self._photo_images.append(photo)
                image_label = ttk.Label(
                    cell, image=photo, background=BEIGE, anchor="center"
                )
            except ImageValidationError:
                image_label = ttk.Label(
                    cell,
                    text="Image unavailable",
                    style="Small.TLabel",
                    background=BEIGE,
                    anchor="center",
                )
            image_label.pack()
            ttk.Label(
                cell,
                text=f"{item.name}\n{item.category}",
                style="Small.TLabel",
                background=BEIGE,
                wraplength=100,
                justify="center",
            ).pack(pady=(4, 0))
        if missing:
            missing_text = ", ".join(missing)
            ttk.Label(
                card,
                text=f"Missing from wardrobe: {missing_text}",
                style="Small.TLabel",
                wraplength=480,
            ).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _delete_outfit(self, outfit_id: str) -> None:
        if not messagebox.askyesno(
            "Delete saved outfit",
            "Are you sure you want to delete this saved outfit?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            deleted = self.outfit_manager.delete_outfit(outfit_id)
        except StorageError as error:
            messagebox.showerror(
                "Unable to delete outfit",
                str(error),
                parent=self.winfo_toplevel(),
            )
            return
        if deleted:
            self.refresh()
