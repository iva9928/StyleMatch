# StyleMatch – AI-Assisted Development Log

**Project:** StyleMatch – Virtual Wardrobe & Outfit Planner  
**Date:** October 19, 2026  
**Development Phase:** Day 1 – Project Setup & Architecture

**AI Tools:** GitHub Copilot Free, ChatGPT

---

## Prompt 1 – Initial Project Setup & Architecture

**AI Tool:** GitHub Copilot Free  
**Purpose:** Create the initial project structure and architecture.

### Prompt

```text
I am developing a university AI-Assisted Development exam project called StyleMatch – Virtual Wardrobe & Outfit Planner.

Technology stack:
- Python 3.12+
- Tkinter and ttk
- Pillow for image processing
- JSON for local storage
- pytest for testing
- pyproject.toml for dependencies

Required features:
1. Upload and categorize clothing images.
2. Display clothes in a wardrobe gallery.
3. Filter and delete clothing items.
4. Build and save outfit combinations.
5. Persist data between application restarts.

Organize the application into four technological modules:
1. User Interface
2. Clothing & Image Management
3. Outfit Builder
4. Local JSON Data Storage

FOR THIS FIRST STEP ONLY:
- Inspect the existing StyleMatch folder and preserve existing files.
- Propose a simple modular architecture.
- Create the project folder structure.
- Create a valid pyproject.toml with Pillow and pytest as a development dependency.
- Create README.md and .gitignore.
- Create app/__init__.py and app/main.py.
- Implement a minimal runnable Tkinter window displaying "StyleMatch" and "Your Personal Digital Wardrobe".
- Explain every created file.
- Provide exact Windows commands to set up a virtual environment, install dependencies, and run the application.

Important:
Do not implement the full application yet.
Keep the architecture simple.
Do not use paid APIs.
Do not modify files outside the StyleMatch folder.
Do not claim tests have passed without running them.
```

### AI-Generated Result

GitHub Copilot generated the initial project architecture, including the following modules:

- `stylematch/ui/` – Graphical User Interface
- `stylematch/models/` – Clothing data models
- `stylematch/outfits/` – Outfit Builder
- `stylematch/storage/` – Local JSON storage

It also created the project configuration files, README documentation, and an initial Tkinter application window.

### Validation

The application was launched using:

`python -m stylematch.app`

**Result:** Successful. The application displayed a window titled "StyleMatch" with the message "Welcome to StyleMatch (UI placeholder)".

---

## Prompt 2 – Fix Dependency Configuration

**AI Tool:** GitHub Copilot Free  
**Purpose:** Debug the invalid dependency configuration in `pyproject.toml`.

### Prompt

```text
I encountered an error while installing the StyleMatch project dependencies using:

python -m pip install -e ".[dev]"

Error:
configuration error: project.dependencies must be array

The current pyproject.toml appears to define dependencies incorrectly.

Please:
1. Inspect the existing pyproject.toml file.
2. Fix the dependency declaration using valid PEP 621 syntax.
3. Specify Pillow as a runtime dependency.
4. Specify pytest as an optional development dependency under [project.optional-dependencies] with a dev group.
5. Verify that the build system and setuptools package discovery are configured correctly for the existing stylematch package.
6. Preserve the existing project structure and source files.
7. Do not create requirements.txt.
8. Do not add unnecessary dependencies.

After making the correction, explain what caused the error and show the corrected dependency configuration.

Do not claim installation succeeds unless the command is actually executed successfully.
```

### Problem Encountered

The first attempt to install dependencies failed because the generated `pyproject.toml` used an invalid format:

`configuration error: project.dependencies must be array`

### AI-Assisted Solution

GitHub Copilot was asked to correct the dependency configuration according to PEP 621.

After the correction, the installation command was executed again:

`python -m pip install -e ".[dev]"`

**Result:** Successful installation of StyleMatch 0.1.0.

---

## Development Environment

- **Operating System:** Windows 10
- **Python:** 3.12.10
- **IDE:** Visual Studio Code
- **AI Coding Assistant:** GitHub Copilot Free
- **Image Processing:** Pillow 13.0.0
- **Testing Framework:** pytest 9.1.1
- **Dependency Management:** pyproject.toml and Python virtual environment

---

## Initial Testing

**Test command:**

`python -m pytest -v`

**Actual result:**

```text
tests/test_placeholder.py::test_placeholder PASSED [100%]

1 passed in 0.04s
```

The initial placeholder test passed successfully.

The graphical interface was also launched manually and displayed the initial StyleMatch window.

**Note:** The initial test validates the basic test setup. Clothing management, outfit creation, and data persistence have not yet been fully implemented or tested.

---

## Challenges and Lessons Learned

The main challenge on Day 1 was an invalid AI-generated dependency configuration.

This demonstrated that AI-generated code and configuration files must be reviewed and tested rather than accepted without validation.

By using GitHub Copilot for debugging and manually repeating the installation command, the issue was resolved.

---

## Day 1 Summary

**Completed:**
- Initial system architecture
- Modular project structure
- Python virtual environment
- Dependency installation
- Initial Tkinter application
- Initial automated test
- Correction of the dependency configuration error

**Next Phase:** Day 2 – User Interface Development.