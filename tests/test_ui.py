"""Focused tests for the Tkinter application shell and screen initialization."""

import tkinter as tk
from tkinter import TclError

import pytest
from PIL import Image

import stylematch.ui.main_window as main_window
from stylematch.ui.main_window import StyleMatchWindow
from stylematch.ui.screens import (
    AddClothingScreen,
    OutfitBuilderScreen,
    WardrobeScreen,
)


@pytest.fixture
def tk_root():
    """Create one Tk root, skipping UI tests when no display is available."""
    try:
        root = tk.Tk()
    except TclError as error:
        pytest.skip(f"Tk is unavailable in this environment: {error}")

    try:
        yield root
    finally:
        try:
            root.destroy()
        except TclError:
            pass


@pytest.fixture
def app(tk_root):
    return StyleMatchWindow(tk_root)


def test_main_window_can_be_created(app, tk_root):
    assert app.root is tk_root
    assert tk_root.title() == "StyleMatch"
    assert tk_root.minsize() == (850, 600)


def test_all_screens_are_initialized(app):
    assert set(app.screens) == {
        "My Wardrobe",
        "Add Clothing",
        "Outfit Builder",
        "Saved Outfits",
    }
    assert app.current_screen_name == "My Wardrobe"
    assert isinstance(app.screens["My Wardrobe"], WardrobeScreen)
    assert isinstance(app.screens["Add Clothing"], AddClothingScreen)


@pytest.mark.parametrize(
    "screen_name",
    ("My Wardrobe", "Add Clothing", "Outfit Builder", "Saved Outfits"),
)
def test_navigation_switches_to_requested_screen(app, screen_name):
    app.nav_buttons[screen_name].invoke()

    assert app.current_screen_name == screen_name
    assert app.nav_buttons[screen_name].cget("style") == "NavActive.TButton"
    assert all(
        button.cget("style")
        == ("NavActive.TButton" if name == screen_name else "Nav.TButton")
        for name, button in app.nav_buttons.items()
    )


def test_screens_fit_when_window_is_resized_to_minimum(app, tk_root):
    tk_root.geometry("850x600")
    tk_root.update_idletasks()

    assert tk_root.winfo_width() == 850
    assert tk_root.winfo_height() == 600
    assert app.content.winfo_width() > 0
    assert all(
        screen.winfo_width() == app.content.winfo_width()
        and screen.winfo_height() == app.content.winfo_height()
        for screen in app.screens.values()
    )


def test_screen_navigation_does_not_create_another_root(tk_root, monkeypatch):
    root_constructor = tk.Tk
    created_roots = []

    def track_root_creation(*args, **kwargs):
        created_roots.append(True)
        return root_constructor(*args, **kwargs)

    monkeypatch.setattr(main_window.tk, "Tk", track_root_creation)
    app = StyleMatchWindow(tk_root)
    for screen_name in app.screens:
        app.show_screen(screen_name)

    assert created_roots == []
    assert app.root is tk_root


def test_wardrobe_category_filter_is_initialized(app):
    wardrobe = app.screens["My Wardrobe"]

    assert isinstance(wardrobe, WardrobeScreen)
    assert wardrobe.category_filter.get() == "All"
    assert tuple(wardrobe.category_select.cget("values")) == (
        "All",
        "Tops",
        "Bottoms",
        "Dresses",
        "Shoes",
        "Outerwear",
        "Jackets",
    )
    assert str(wardrobe.category_select.cget("state")) == "readonly"


def test_category_selection_updates_wardrobe_empty_state(app, tk_root):
    wardrobe = app.screens["My Wardrobe"]
    wardrobe.category_select.set("Tops")
    wardrobe.category_select.event_generate("<<ComboboxSelected>>")
    tk_root.update_idletasks()

    assert wardrobe.empty_message.cget("text") == "No tops in your wardrobe yet."


def test_invalid_image_selection_displays_warning_and_keeps_image_unselected(
    app,
    monkeypatch,
    tmp_path,
):
    add_clothing = app.screens["Add Clothing"]
    invalid_image = tmp_path / "not-an-image.png"
    invalid_image.write_text("not an image", encoding="utf-8")
    warnings = []

    monkeypatch.setattr(
        "stylematch.ui.screens.filedialog.askopenfilename",
        lambda **_kwargs: str(invalid_image),
    )
    monkeypatch.setattr(
        "stylematch.ui.screens.messagebox.showwarning",
        lambda *args, **_kwargs: warnings.append(args),
    )

    add_clothing._choose_image()

    assert add_clothing.selected_image is None
    assert add_clothing.filename_label.cget("text") == "No file selected"
    assert len(warnings) == 1


def test_image_preview_preserves_aspect_ratio(app, monkeypatch, tmp_path):
    add_clothing = app.screens["Add Clothing"]
    image_path = tmp_path / "portrait.png"
    Image.new("RGB", (80, 160), color="beige").save(image_path)

    monkeypatch.setattr(
        "stylematch.ui.screens.filedialog.askopenfilename",
        lambda **_kwargs: str(image_path),
    )

    add_clothing._choose_image()

    assert add_clothing.selected_image == str(image_path)
    assert add_clothing.filename_label.cget("text") == image_path.name
    assert add_clothing.preview_image.width() == 69
    assert add_clothing.preview_image.height() == 138


def test_add_button_adds_item_and_renders_complete_wardrobe_card(
    app,
    tk_root,
    monkeypatch,
    tmp_path,
):
    add_clothing = app.screens["Add Clothing"]
    wardrobe = app.screens["My Wardrobe"]
    image_path = tmp_path / "pink-shirt.jpg"
    Image.new("RGB", (80, 160), color="pink").save(image_path)
    confirmations = []
    monkeypatch.setattr(
        "stylematch.ui.screens.messagebox.showinfo",
        lambda *args, **_kwargs: confirmations.append(args),
    )

    add_clothing.name_var.set(" pink T-shirt ")
    add_clothing.category_var.set("Tops")
    add_clothing.color_var.set("Pink")
    add_clothing.style_var.set("Casual")
    add_clothing.selected_image = str(image_path)
    add_clothing.add_button.invoke()
    tk_root.update_idletasks()

    items = app.clothing_manager.list_items()
    assert len(items) == 1
    assert items[0].name == "pink T-shirt"
    assert items[0].category == "Tops"
    assert items[0].primary_color == "Pink"
    assert items[0].style == "Casual"
    assert confirmations and confirmations[0][0] == "Clothing added"
    assert add_clothing.name_var.get() == ""
    assert add_clothing.category_var.get() == ""
    assert add_clothing.color_var.get() == ""
    assert add_clothing.style_var.get() == ""
    assert add_clothing.selected_image is None

    cards = wardrobe.gallery.content.winfo_children()
    assert len(cards) == 1
    card = cards[0]
    assert any(
        child.winfo_class() == "TButton" and child.cget("text") == "Delete"
        for child in card.winfo_children()
    )
    assert any(
        child.winfo_class() == "TLabel" and child.cget("text") == "pink T-shirt"
        for child in card.winfo_children()
    )
    assert any(
        child.winfo_class() == "TLabel" and child.cget("text") == "Tops"
        for child in card.winfo_children()
    )
    image_box = card.winfo_children()[0]
    image_label = image_box.winfo_children()[0]
    assert image_label.cget("image")
    assert len(wardrobe._photo_images) == 1


def test_add_clothing_screen_does_not_show_obsolete_placeholder(app):
    add_clothing = app.screens["Add Clothing"]
    labels = []

    def collect_labels(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == "TLabel":
                labels.append(child.cget("text"))
            collect_labels(child)

    collect_labels(add_clothing)

    assert "This button is a placeholder; no clothing data will be saved." not in labels


def test_wardrobe_filters_added_items_and_shows_category_empty_state(
    app,
    tk_root,
    tmp_path,
):
    wardrobe = app.screens["My Wardrobe"]
    image_path = tmp_path / "top.png"
    Image.new("RGB", (80, 80), color="pink").save(image_path)
    app.clothing_manager.add_item("Pink top", "Tops", image_path)
    app.clothing_manager.add_item("Blue shoes", "Shoes", image_path)

    wardrobe.category_select.set("Tops")
    wardrobe.category_select.event_generate("<<ComboboxSelected>>")
    tk_root.update_idletasks()

    assert len(wardrobe.gallery.content.winfo_children()) == 1
    assert wardrobe.gallery.content.winfo_children()[0].winfo_children()[1].cget(
        "text"
    ) == "Pink top"

    wardrobe.category_select.set("Dresses")
    wardrobe.category_select.event_generate("<<ComboboxSelected>>")
    tk_root.update_idletasks()

    assert wardrobe.empty_message.cget("text") == "No dresses in your wardrobe yet."


def test_jackets_filter_and_outfit_selectors_are_category_specific(
    app,
    tk_root,
    tmp_path,
):
    image_path = tmp_path / "items.png"
    Image.new("RGB", (80, 80), color="plum").save(image_path)
    top = app.clothing_manager.add_item("White shirt", "Tops", image_path)
    second_top = app.clothing_manager.add_item("Blue shirt", "Tops", image_path)
    bottom = app.clothing_manager.add_item("Black jeans", "Bottoms", image_path)
    dress = app.clothing_manager.add_item("Summer dress", "Dresses", image_path)
    shoes = app.clothing_manager.add_item("Brown shoes", "Shoes", image_path)
    outerwear = app.clothing_manager.add_item("Raincoat", "Outerwear", image_path)
    jacket = app.clothing_manager.add_item("Denim jacket", "Jackets", image_path)
    wardrobe = app.screens["My Wardrobe"]
    builder = app.screens["Outfit Builder"]

    assert isinstance(builder, OutfitBuilderScreen)
    builder.refresh_from_wardrobe()
    assert tuple(builder.selectors["Tops"].cget("values")) == (
        "",
        "White shirt",
        "Blue shirt",
    )
    assert tuple(builder.selectors["Bottoms"].cget("values")) == (
        "",
        "Black jeans",
    )
    assert tuple(builder.selectors["Dresses"].cget("values")) == (
        "",
        "Summer dress",
    )
    assert tuple(builder.selectors["Shoes"].cget("values")) == ("", "Brown shoes")
    assert tuple(builder.selectors["Outerwear"].cget("values")) == (
        "",
        "Raincoat",
    )
    assert tuple(builder.selectors["Jackets"].cget("values")) == (
        "",
        "Denim jacket",
    )
    assert "Brown shoes" not in builder.selectors["Tops"].cget("values")
    assert "Brown shoes" not in builder.selectors["Outerwear"].cget("values")

    builder.selectors["Tops"].set("White shirt")
    builder.selectors["Tops"].event_generate("<<ComboboxSelected>>")
    tk_root.update_idletasks()
    assert builder._selected_items() == [top]
    assert second_top.id != top.id
    assert any(
        child.winfo_class() == "TLabel" and child.cget("text") == top.name
        for cell in builder.preview.winfo_children()
        for child in cell.winfo_children()
    )

    wardrobe.category_select.set("Jackets")
    wardrobe.category_select.event_generate("<<ComboboxSelected>>")
    tk_root.update_idletasks()
    assert len(wardrobe.gallery.content.winfo_children()) == 1
    assert wardrobe.gallery.content.winfo_children()[0].winfo_children()[1].cget(
        "text"
    ) == jacket.name
    assert shoes.category == "Shoes"
    assert bottom.category == "Bottoms"
    assert dress.category == "Dresses"
    assert outerwear.category == "Outerwear"


def test_add_clothing_category_dropdown_contains_all_six_categories(app):
    add_clothing = app.screens["Add Clothing"]

    assert tuple(add_clothing.category_select.cget("values")) == (
        "Tops",
        "Bottoms",
        "Dresses",
        "Shoes",
        "Outerwear",
        "Jackets",
    )
    assert tuple(add_clothing.color_select.cget("values")) == (
        "",
        "Black",
        "White",
        "Gray",
        "Navy",
        "Beige",
        "Brown",
        "Red",
        "Blue",
        "Green",
        "Yellow",
        "Pink",
        "Purple",
    )
    assert tuple(add_clothing.style_select.cget("values")) == (
        "",
        "Casual",
        "Formal",
        "Business",
        "Sporty",
        "Outdoor",
        "Streetwear",
    )


def test_edit_wardrobe_item_updates_metadata_without_changing_identity(
    app,
    tk_root,
    monkeypatch,
    tmp_path,
):
    image_path = tmp_path / "existing.png"
    Image.new("RGB", (80, 120), color="navy").save(image_path)
    item = app.clothing_manager.add_item(
        "Everyday jacket",
        "Jackets",
        image_path,
    )
    wardrobe = app.screens["My Wardrobe"]
    confirmations = []
    monkeypatch.setattr(
        "stylematch.ui.screens.messagebox.showinfo",
        lambda *args, **_kwargs: confirmations.append(args),
    )

    wardrobe._edit_item(item.id)
    dialog = wardrobe.edit_dialog
    dialog.color_var.set("Navy")
    dialog.style_var.set("Casual")
    dialog._save()
    tk_root.update_idletasks()

    updated = app.clothing_manager.list_items()[0]
    assert updated.id == item.id
    assert updated.name == item.name
    assert updated.category == item.category
    assert updated.image_path == item.image_path
    assert updated.primary_color == "Navy"
    assert updated.style == "Casual"
    assert confirmations
    assert image_path.is_file()


def test_suggest_outfit_preserves_manual_selection_when_no_candidate_exists(
    app,
    tk_root,
    monkeypatch,
    tmp_path,
):
    image_path = tmp_path / "single-top.png"
    Image.new("RGB", (80, 120), color="plum").save(image_path)
    item = app.clothing_manager.add_item("Manual top", "Tops", image_path)
    builder = app.screens["Outfit Builder"]
    builder.refresh_from_wardrobe()
    builder.selector_vars["Tops"].set("Manual top")
    builder._selection_changed()
    messages = []
    monkeypatch.setattr(
        "stylematch.ui.screens.messagebox.showinfo",
        lambda *args, **_kwargs: messages.append(args),
    )

    builder._suggest_outfit()
    tk_root.update_idletasks()

    assert builder._selected_items() == [item]
    assert builder.selector_vars["Tops"].get() == "Manual top"
    assert messages


def test_suggestion_displays_heuristic_explanation(app, tmp_path):
    image_path = tmp_path / "complete.png"
    Image.new("RGB", (80, 120), color="navy").save(image_path)
    app.clothing_manager.add_item(
        "Navy shirt",
        "Tops",
        image_path,
        primary_color="Navy",
        style="Casual",
    )
    app.clothing_manager.add_item(
        "Beige trousers",
        "Bottoms",
        image_path,
        primary_color="Beige",
        style="Casual",
    )
    app.clothing_manager.add_item(
        "Navy shoes",
        "Shoes",
        image_path,
        primary_color="Navy",
        style="Casual",
    )
    builder = app.screens["Outfit Builder"]
    builder.refresh_from_wardrobe()

    builder._suggest_outfit()

    assert "Heuristic compatibility estimate:" in builder.compatibility_var.get()
    assert "Colors:" in builder.compatibility_var.get()
    assert "Styles:" in builder.compatibility_var.get()



def test_outfit_selector_layout_is_accessible_at_minimum_window_size(app, tk_root):
    builder = app.screens["Outfit Builder"]
    tk_root.geometry("850x600")
    tk_root.update_idletasks()

    assert set(builder.selectors) == {
        "Tops",
        "Bottoms",
        "Dresses",
        "Shoes",
        "Outerwear",
        "Jackets",
    }
    assert builder.selector_area.canvas.winfo_height() > 0
    assert builder.selector_area.canvas.cget("scrollregion")
    for category, selector in builder.selectors.items():
        assert selector.winfo_manager() == "grid"
        assert str(selector.cget("state")) == "readonly"
        assert selector.master is builder.selector_area.content
        assert builder.selector_labels[category].master is selector.master
        assert int(builder.selector_labels[category].grid_info()["row"]) < int(
            selector.grid_info()["row"]
        )
    form_rows = [
        int(child.grid_info()["row"])
        for child in builder.selector_area.content.winfo_children()
    ]
    assert len(form_rows) == len(set(form_rows))


def test_duplicate_clothing_names_are_distinguished_without_ids(app, tmp_path):
    image_path = tmp_path / "duplicate.png"
    Image.new("RGB", (80, 80), color="plum").save(image_path)
    first = app.clothing_manager.add_item("Black jacket", "Jackets", image_path)
    second = app.clothing_manager.add_item("Black jacket", "Jackets", image_path)
    builder = app.screens["Outfit Builder"]
    builder.refresh_from_wardrobe()
    labels = tuple(builder.selectors["Jackets"].cget("values"))

    assert labels == ("", "Black jacket (1)", "Black jacket (2)")
    assert first.id not in labels[1]
    assert second.id not in labels[2]
    builder.selectors["Jackets"].set(labels[2])
    assert builder._selected_items() == [second]


@pytest.mark.parametrize(("confirm", "expected_count"), [(True, 0), (False, 1)])
def test_wardrobe_delete_confirmation_updates_only_when_confirmed(
    app,
    monkeypatch,
    tmp_path,
    confirm,
    expected_count,
):
    wardrobe = app.screens["My Wardrobe"]
    image_path = tmp_path / "item.png"
    Image.new("RGB", (80, 80), color="pink").save(image_path)
    item = app.clothing_manager.add_item("Pink top", "Tops", image_path)
    wardrobe.refresh()
    prompts = []
    monkeypatch.setattr(
        "stylematch.ui.screens.messagebox.askyesno",
        lambda *args, **_kwargs: prompts.append(args) or confirm,
    )

    wardrobe._delete_item(item.id)

    assert len(prompts) == 1
    assert len(app.clothing_manager.list_items()) == expected_count
    if confirm:
        assert wardrobe.empty_message is not None
    else:
        assert len(wardrobe.gallery.content.winfo_children()) == 1


def test_wardrobe_renders_multiple_compact_cards(app, tk_root, tmp_path):
    wardrobe = app.screens["My Wardrobe"]
    image_path = tmp_path / "item.png"
    Image.new("RGB", (160, 100), color="pink").save(image_path)
    for index in range(5):
        app.clothing_manager.add_item(f"Item {index}", "Tops", image_path)

    tk_root.update()

    cards = wardrobe.gallery.content.winfo_children()
    assert len(cards) == 5
    assert wardrobe._columns > 1
    assert len(wardrobe._photo_images) == 5
    assert all(
        card.winfo_children()[0].winfo_children()[0].cget("image")
        for card in cards
    )
    assert {
        child.cget("text")
        for card in cards
        for child in card.winfo_children()
        if child.winfo_class() == "TLabel"
        and child.cget("text").startswith("Item ")
    } == {f"Item {index}" for index in range(5)}


def test_missing_image_in_wardrobe_uses_fallback_without_crashing(
    app,
    tk_root,
    tmp_path,
):
    image_path = tmp_path / "item.png"
    Image.new("RGB", (80, 80), color="pink").save(image_path)
    item = app.clothing_manager.add_item("Pink top", "Tops", image_path)
    image_path.unlink()
    wardrobe = app.screens["My Wardrobe"]

    wardrobe.refresh()
    tk_root.update_idletasks()

    image_box = wardrobe.gallery.content.winfo_children()[0].winfo_children()[0]
    assert image_box.winfo_children()[0].cget("text") == "Image unavailable"
    assert app.clothing_manager.list_items() == [item]
