# StyleMatch — Virtual Wardrobe & Outfit Planner (Starter)

StyleMatch is a small Python desktop application for a virtual wardrobe and outfit planner. Its interface uses Tkinter and ttk, with Pillow used to preview selected clothing images. The UI is separated from the clothing model, outfit builder, and JSON storage modules.

Current functionality
- Provide a resizable Tkinter application with wardrobe, clothing-entry, outfit-builder, and saved-outfit screens.
- Add clothing items with a name, category, and local PNG, JPEG, or WEBP image.
- Preview images and display proportion-preserving thumbnails in a scrollable, filterable wardrobe gallery.
- Delete wardrobe items after confirmation; original image files are not changed.
- Keep wardrobe items in memory for the current session only. JSON persistence and outfit creation/saving are not implemented yet.

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
   - Read/write JSON persistence for wardrobe and outfits.

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
    - json_store.py        (JSONStore placeholder)
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
- Clothing items are held in memory and are cleared when the application closes.
- Outfit creation and saving remain placeholders.
- Business logic remains separate from UI code.
- No external or paid APIs are used.
