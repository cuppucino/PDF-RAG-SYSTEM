# JSON Formatting & Schema Validation: Interview Guide

This guide explains standard **JSON (JavaScript Object Notation)** formatting rules, common syntax errors, and how to structure JSON payloads to match backend schemas.

---

## 1. Core JSON Formatting Rules

JSON is a standard text-based format for representing structured data. It has strict syntax rules that differ from Python dictionaries:

1.  **Double Quotes Only**: Keys and string values **must** be enclosed in double quotes (`"key": "value"`). Single quotes (`'`) or unquoted text will cause syntax crashes.
2.  **Object Structure**: Curly braces `{}` represent objects (directories of key-value pairs). Every item inside `{}` must follow the `"key": value` format.
3.  **No Trailing Commas**: The last element in an object or array must not have a trailing comma.

---

## 2. Analyzing the Error

In your screenshot:
```json
{
  "data": {/Users/admin/Downloads/Voldi_Customer_Journey.pdf}
}
```
*   **The Syntax Error**: The text `{/Users/admin/Downloads/...}` uses curly braces, which tells the parser: *"I am starting a new sub-object."* However, `/Users/admin/...` is unquoted and is not a key-value pair.
*   **The Schema Error**: The code in `main.py` looks for a specific key called `"pdf_path"` inside the event data:
    ```python
    pdf_path = ctx.event.data["pdf_path"]
    ```
    If you don't provide the key `"pdf_path"`, the code will crash with a `KeyError` at runtime.

---

## 3. The Correct Payload Format

To trigger your background task successfully, format the JSON payload like this:

```json
{
  "data": {
    "pdf_path": "/Users/admin/Downloads/Voldi_Customer_Journey.pdf"
  }
}
```

---

## 4. Example Scenario: Parsing and Validating JSON Payload

Below is a Python function demonstrating how to safely parse JSON strings and check for valid schemas, complete with unit tests.

### Implementation

```python
import json
import logging
from typing import Dict, Any

app_logger = logging.getLogger("uvicorn.error")

def validate_ingestion_payload(json_str: str) -> Dict[str, Any]:
    """Parses a JSON string and verifies it matches the RAG input schema."""
    try:
        # Step 1: Parse the JSON string
        payload = json.loads(json_str)
        
        # Step 2: Validate structure
        if "data" not in payload:
            raise ValueError("Missing root key 'data'.")
            
        data_object = payload["data"]
        if not isinstance(data_object, dict):
            raise ValueError("'data' must be a JSON object.")
            
        if "pdf_path" not in data_object:
            raise ValueError("Missing required key 'pdf_path' inside 'data'.")
            
        return data_object
    except json.JSONDecodeError as decode_error:
        app_logger.error(f"Invalid JSON format: {str(decode_error)}")
        # Raise standard value error with coordinate details
        raise ValueError(f"Malformed JSON syntax: {str(decode_error)}") from decode_error
    except ValueError as validation_error:
        app_logger.error(f"Schema validation error: {str(validation_error)}")
        raise validation_error
```

### Unit Tests

```python
import pytest

def test_validate_ingestion_payload_success() -> None:
    """Verifies that a correctly formatted JSON payload parses successfully."""
    valid_json = '{"data": {"pdf_path": "/path/to/doc.pdf"}}'
    result = validate_ingestion_payload(valid_json)
    assert result["pdf_path"] == "/path/to/doc.pdf"

def test_validate_ingestion_payload_syntax_error() -> None:
    """Verifies that malformed JSON strings throw a malformed syntax error."""
    # Missing quotes around the path
    invalid_json = '{"data": {/path/to/doc.pdf}}'
    with pytest.raises(ValueError) as error_info:
        validate_ingestion_payload(invalid_json)
    assert "Malformed JSON syntax" in str(error_info.value)

def test_validate_ingestion_payload_missing_keys() -> None:
    """Verifies that missing required keys raise a schema validation error."""
    invalid_json = '{"data": {"wrong_key": "/path/to/doc.pdf"}}'
    with pytest.raises(ValueError) as error_info:
        validate_ingestion_payload(invalid_json)
    assert "Missing required key 'pdf_path'" in str(error_info.value)
```
