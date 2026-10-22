# StyleMatch — Virtual Wardrobe & Outfit Planner (Starter)

StyleMatch is a small Python desktop application for a virtual wardrobe and outfit planner. Its interface uses Tkinter and ttk, with Pillow used to preview selected clothing images. The UI is separated from the clothing model, outfit builder, and JSON storage modules.

Current functionality
- Provide a resizable Tkinter application with wardrobe, clothing-entry, outfit-builder, and saved-outfit screens.
- Add clothing items with a name, category, and local PNG, JPEG, or WEBP image.
- Preview images and display proportion-preserving thumbnails in a scrollable, filterable wardrobe gallery.
- Persist clothing metadata locally as versioned JSON and restore the wardrobe when the application restarts.
- Delete wardrobe items after confirmation; the application removes only its own managed image copy, never the original image.
- Keep outfit creation and saving as placeholders.

Local data storage
- StyleMatch stores `wardrobe.json` and imported image copies in a per-user application data directory, not in the source package:
  - Windows: `%LOCALAPPDATA%\StyleMatch` (falls back to `%USERPROFILE%\AppData\Local\StyleMatch` when `LOCALAPPDATA` is unavailable).
  - macOS: `~/Library/Application Support/StyleMatch`.
  - Linux: `$XDG_DATA_HOME/StyleMatch`, or `~/.local/share/StyleMatch` when `XDG_DATA_HOME` is unset or not an absolute path.
- The JSON file stores clothing IDs, names, categories, and portable relative references to images in its `images/` subdirectory.
- Selected images are validated and copied into that managed `images/` directory. The original files are not modified or deleted.
- If a managed image is missing or unreadable, its clothing record remains in the wardrobe and the gallery displays “Image unavailable.”
- If wardrobe JSON is malformed or invalid, StyleMatch preserves it under a unique `.bak` filename and displays a warning before starting with an empty wardrobe. If it cannot preserve the file safely, persistence writes are disabled for that session.

Architecture (modules)
1. User Interface (stylematch.ui)
   - `main_window.py` provides the shared window and navigation.
   - `screens.py` defines the four screen layouts and reusable gallery area.
   - Clothing actions call the shared clothing management service.
2. Clothing & Image Management
   - `models/clothing.py` defines clothing item data.
   - `services/clothing_manager.py` validates and manages in-memory clothing items.
   - `images.py` validates supported image files and creates thumbnails.
3. Outfit Builder (stylematch.outfits)
   - Business logic for building outfit combinations.
4. Local JSON Data Storage (stylematch.storage)
   - Atomically read/write versioned wardrobe JSON and manage imported image copies.

Folder structure created
- stylematch/               (package)
  - __init__.py
  - app.py                  (application entrypoint)
  - ui/
    - __init__.py
    - main_window.py        (Tkinter window and screen navigation)
    - screens.py            (screen layouts and UI components)
  - models/
    - __init__.py
    - clothing.py          (ClothingItem dataclass placeholder)
  - outfits/
    - __init__.py
    - builder.py           (OutfitBuilder placeholder)
  - storage/
    - __init__.py
    - json_store.py        (atomic JSON file storage)
    - data_paths.py        (cross-platform user data directory)
    - wardrobe_persistence.py (wardrobe JSON and managed images)
- tests/
  - test_placeholder.py    (basic pytest placeholder)
- pyproject.toml
- README.md
- .gitignore

Run the application (Windows exact commands)
1. Create and activate a virtual environment (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   (If using cmd.exe: .\.venv\Scripts\activate.bat)

2. Upgrade pip and install dependencies:
   python -m pip install --upgrade pip
   pip install Pillow

3. Run the app:
   python -m stylematch.app

Run tests (after installing pytest):
   pip install pytest
   pytest -q

Notes
- Normal application launches persist clothing items and restore them on restart.
- Outfit creation and saving remain placeholders.
- Business logic remains separate from UI code.
- No external or paid APIs are used.
