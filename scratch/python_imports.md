# Python Modules & Import Conventions: Interview Guide

This guide explains how Python resolves module imports, why file naming conventions matter (such as hyphens vs underscores), and how to troubleshoot import crashes.

---

## 1. How Python Resolves Imports

When you write `import custom_types` or `from custom_types import ...`, Python looks through a list of directories in `sys.path`:
1.  **Current Directory**: The folder where the entrypoint script (e.g., `main.py`) is located.
2.  **Standard Library**: Python's built-in modules (e.g., `os`, `sys`, `json`).
3.  **Site-Packages**: Third-party libraries installed via package managers like `pip` or `uv` (e.g., `fastapi`, `qdrant-client`).

---

## 2. Why Hyphens `-` Break Imports

In Python, the hyphen `-` is a reserved mathematical operator (subtraction).
*   **Syntax Restriction**: You cannot write `import custom-types` because Python interprets it as `import custom minus types`, raising a `SyntaxError`.
*   **Resolution Mismatch**: Because of this restriction, if your file is named `custom-types.py` and you try to do `from custom_types import ...` (using an underscore), Python searches for `custom_types.py`. Since the file contains a hyphen, Python cannot find it and raises a `ModuleNotFoundError: No module named 'custom_types'`.
*   **Standard Rule**: Always use **snake_case** (underscores `_` instead of hyphens `-`) for all Python file names, variables, and function names.

---

## 3. Example Scenario: Dynamic Import & Module Loading

Here is a robust script demonstrating how Python checks if a module can be imported dynamically, with error handling and unit tests.

### Implementation

```python
import importlib
import logging
from typing import Dict, Any

app_logger = logging.getLogger("uvicorn.error")

def check_and_load_module(module_name: str) -> Dict[str, Any]:
    """Dynamically attempts to import a module and returns its status."""
    try:
        # Standardize naming: check for hyphens
        if "-" in module_name:
            raise ValueError(
                f"Invalid module name '{module_name}': "
                "Python modules cannot contain hyphens. Use underscores instead."
            )
            
        # Dynamically import the module
        imported_module = importlib.import_module(module_name)
        
        return {
            "status": "success",
            "module_name": module_name,
            "version": getattr(imported_module, "__version__", "unknown")
        }
    except ModuleNotFoundError as error:
        app_logger.error(f"Module '{module_name}' was not found: {str(error)}")
        raise ModuleNotFoundError(f"Failed to find: {module_name}") from error
    except ValueError as validation_error:
        app_logger.error(str(validation_error))
        raise validation_error
    except Exception as unexpected_error:
        app_logger.error(f"Unexpected error loading module: {str(unexpected_error)}")
        raise unexpected_error
```

### Unit Tests

```python
import pytest

def test_check_and_load_module_success() -> None:
    """Verifies that standard library modules (like os) import successfully."""
    result = check_and_load_module("os")
    assert result["status"] == "success"
    assert result["module_name"] == "os"

def test_check_and_load_module_hyphen_failure() -> None:
    """Verifies that passing a module name with a hyphen raises a ValueError."""
    with pytest.raises(ValueError) as error_info:
        check_and_load_module("invalid-hyphen-module")
    assert "cannot contain hyphens" in str(error_info.value)

def test_check_and_load_module_missing_failure() -> None:
    """Verifies that requesting a non-existent module raises ModuleNotFoundError."""
    with pytest.raises(ModuleNotFoundError):
        check_and_load_module("non_existent_module_xyz")
```
