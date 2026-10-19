# StyleMatch — Virtual Wardrobe & Outfit Planner (Starter)

This repository contains the initial skeleton for the StyleMatch desktop application, implemented in Python using Tkinter for UI, Pillow for image handling, and JSON for local persistence. This first step creates a simple modular architecture and a minimal runnable Tkinter window.

Goals for this step
- Propose a modular architecture
- Create initial folder structure and placeholder modules
- Provide a minimal runnable Tkinter application named `StyleMatch`

Architecture (modules)
1. User Interface (stylematch.ui)
   - Responsible for GUI only. Keeps business logic out of this layer.
2. Clothing & Image Management (stylematch.models)
   - Data models for clothing items and image helpers.
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
    - main_window.py        (Tkinter window, uses business modules)
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
- Business logic is intentionally minimal and separated from UI code.
- No external or paid APIs are used.

