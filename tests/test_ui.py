"""Focused tests for the Tkinter application shell and screen initialization."""

import tkinter as tk
from tkinter import TclError

import pytest
from PIL import Image

import stylematch.ui.main_window as main_window
from stylematch.ui.main_window import StyleMatchWindow
from stylematch.ui.screens import AddClothingScreen, WardrobeScreen


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
