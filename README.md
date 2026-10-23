# StyleMatch — Virtual Wardrobe & Outfit Planner

StyleMatch is a small Python desktop application for a virtual wardrobe and outfit planner. Its interface uses Tkinter and ttk, with Pillow used to preview selected clothing images. The UI is separated from clothing and outfit models, business logic, and JSON storage.

Current functionality
- Provide a resizable Tkinter application with wardrobe, clothing-entry, outfit-builder, and saved-outfit screens.
- Add clothing items with a name, category, and local PNG, JPEG, or WEBP image.
- Organize clothing into Tops, Bottoms, Dresses, Shoes, Outerwear, and Jackets.
- Optionally record a garment's primary color and style, and edit those details later without replacing its image.
- Preview images and display proportion-preserving thumbnails in a scrollable, filterable wardrobe gallery.
- Persist clothing metadata locally as versioned JSON and restore the wardrobe when the application restarts.
- Delete wardrobe items after confirmation; the application removes only its own managed image copy, never the original image.
- Create outfits manually from existing wardrobe items or request a color- and style-aware rule-based suggestion.
- Save named outfits and browse or delete them from the Saved Outfits screen.

Local data storage
- StyleMatch stores `wardrobe.json`, `outfits.json`, and imported image copies in a per-user application data directory, not in the source package:
  - Windows: `%LOCALAPPDATA%\StyleMatch` (falls back to `%USERPROFILE%\AppData\Local\StyleMatch` when `LOCALAPPDATA` is unavailable).
  - macOS: `~/Library/Application Support/StyleMatch`.
  - Linux: `$XDG_DATA_HOME/StyleMatch`, or `~/.local/share/StyleMatch` when `XDG_DATA_HOME` is unset or not an absolute path.
- The JSON file stores clothing IDs, names, categories, and portable relative references to images in its `images/` subdirectory.
- Optional `primary_color` and `style` values are stored on wardrobe records. Existing records without these values load with them unset; the wardrobe schema remains version 1.
- Selected images are validated and copied into that managed `images/` directory. The original files are not modified or deleted.
- If a managed image is missing or unreadable, its clothing record remains in the wardrobe and the gallery displays “Image unavailable.”
- If wardrobe JSON is malformed or invalid, StyleMatch preserves it under a unique `.bak` filename and displays a warning before starting with an empty wardrobe. If it cannot preserve the file safely, persistence writes are disabled for that session.
- Saved outfits use a separate versioned `outfits.json` file and store only outfit IDs, names, and references to existing clothing IDs. They do not copy clothing records or image files. Missing or malformed outfit data is preserved safely and does not alter `wardrobe.json`.
- If a referenced clothing item is deleted, its saved outfit remains visible with a notice identifying the missing wardrobe item.

Outfit planning
- Build valid looks from Top + Bottom + Shoes or Dress + Shoes. Optionally add either one Outerwear item or one Jacket, but not both.
- Add clothing with optional primary-color metadata (Black, White, Gray, Navy, Beige, Brown, Red, Blue, Green, Yellow, Pink, or Purple) and style metadata (Casual, Formal, Business, Sporty, Outdoor, or Streetwear). These are user-entered labels, not image recognition.
- Edit a garment's color and style from its My Wardrobe card. Editing preserves its ID, category, name, image path, managed image, and any saved outfit references.
- Suggest Outfit validates category rules first, then ranks valid combinations using explicit color and style compatibility rules. Neutral colors are treated as versatile, and missing metadata is neutral rather than a mismatch. Try Another advances through distinct highly ranked suggestions.
- The heuristic averages known pairwise color comparisons (60% of the score) and style comparisons (40%). Matching colors/styles and a small list of compatible pairs score positively; Black, White, Gray, Navy, Beige, and Brown are treated as neutrals. Red/Green and Yellow/Purple receive an explicit color-contrast penalty; Formal/Sporty, Formal/Outdoor, and Business/Streetwear receive explicit style-contrast penalties. Unlisted pairings receive a neutral contribution, and missing metadata contributes no penalty.
- The displayed compatibility score is a heuristic estimate based only on user-entered metadata, not an objective fashion judgment. The rules are intentionally small and do not account for garment cut, material, occasion, fit, season, or personal taste.
- To keep work bounded, at most 5,000 deterministic candidate combinations are evaluated and only the top 20 are retained for Try Another. If a wardrobe exceeds that limit, the UI says that remaining combinations were not scored; the recommendation is not claimed to be globally best.

Architecture (modules)
1. User Interface (stylematch.ui)
   - `main_window.py` provides the shared window and navigation.
   - `screens.py` defines the four screen layouts and reusable gallery area.
   - Clothing actions call the shared clothing management service.
2. Clothing & Image Management
   - `models/clothing.py` defines clothing item data.
   - `services/clothing_manager.py` validates and manages in-memory clothing items.
   - `images.py` validates supported image files and creates thumbnails.
3. Outfit Builder (stylematch.outfits, stylematch.services.outfit_manager)
   - Validates manual combinations, suggests complete category combinations, and manages saved outfit references.
4. Local JSON Data Storage (stylematch.storage)
   - Atomically read/write separate versioned wardrobe and outfit JSON files and manage imported clothing image copies.

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
    - clothing.py          (ClothingItem dataclass)
    - outfit.py            (saved outfit ID and clothing references)
  - outfits/
    - __init__.py
    - builder.py           (outfit validation and rule-based suggestions)
  - services/
    - clothing_manager.py  (wardrobe business operations)
    - outfit_manager.py    (saved outfit business operations)
  - storage/
    - __init__.py
    - json_store.py        (atomic JSON file storage)
    - data_paths.py        (cross-platform user data directory)
    - wardrobe_persistence.py (wardrobe JSON and managed images)
    - outfit_persistence.py (versioned saved outfit JSON)
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
- Normal application launches restore both clothing items and saved outfits on restart.
- Outfit suggestions use local deterministic rules only; they do not use AI, image recognition, or external services.
- Business logic remains separate from UI code.
- No external or paid APIs are used.
