# Lambda Functions in Python: Interview Guide

This guide explains what **lambda** (anonymous) functions are in Python, how they differ from standard `def` functions, and when to use them.

---

## 1. What is a Lambda Function?

A **lambda** function in Python is a small, anonymous (unnamed) function that is defined in a single line of code.
*   **Syntax**: `lambda arguments: expression`
*   **One-liner**: They can only contain a single expression or calculation. They cannot contain complex loops, multiple statements, or variable assignments inside the body.
*   **Implicit Return**: You don't write the word `return`. The result of the expression is returned automatically.

---

## 2. Standard `def` vs. `lambda`

### Standard Function
```python
def double_number(number: int) -> int:
    return number * 2
```

### Lambda Equivalent
```python
double_number = lambda number: number * 2
```

Both do the exact same thing, but the lambda function is written inline without a formal name declaration.

---

## 3. Common Use Cases

Lambda functions are typically used when you need a simple function for a short period of time, usually as an argument to other functions (higher-order functions), such as:
1.  **Sorting Lists**: Customizing sort criteria (e.g., sorting dictionaries by a specific key).
2.  **Filtering Lists**: Using `filter()` to select items matching a condition.
3.  **Transforming Lists**: Using `map()` to apply a calculation to all elements.

---

## 4. Example Scenario: Sorting & Filtering PDF Pages

Imagine you have a list of dictionary payloads representing PDF pages, and you want to sort them by page number and filter out pages with short text.

### Implementation

```python
import logging
from typing import List, Dict, Any

app_logger = logging.getLogger("uvicorn.error")

def get_sorted_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorts pages by page_number using a lambda function as the sorting key."""
    try:
        # The lambda extracts the 'page_number' from each dictionary to use as the sorting key
        sorted_pages = sorted(pages, key=lambda x: x.get("page_number", 0))
        return sorted_pages
    except Exception as error:
        app_logger.error(f"Failed to sort pages: {str(error)}")
        raise error

def get_long_pages(pages: List[Dict[str, Any]], minimum_length: int = 10) -> List[Dict[str, Any]]:
    """Filters pages to keep only those with character length >= minimum_length."""
    try:
        # The filter function uses the lambda to return True/False for each page
        filtered_iterator = filter(lambda x: len(x.get("text", "")) >= minimum_length, pages)
        return list(filtered_iterator)
    except Exception as error:
        app_logger.error(f"Failed to filter pages: {str(error)}")
        raise error
```

### Unit Tests

```python
import pytest

def test_get_sorted_pages() -> None:
    """Verifies that pages are correctly sorted chronologically."""
    raw_pages = [
        {"page_number": 3, "text": "Page three content"},
        {"page_number": 1, "text": "Page one content"},
        {"page_number": 2, "text": "Page two content"}
    ]
    
    sorted_res = get_sorted_pages(raw_pages)
    
    assert sorted_res[0]["page_number"] == 1
    assert sorted_res[1]["page_number"] == 2
    assert sorted_res[2]["page_number"] == 3

def test_get_long_pages() -> None:
    """Verifies that pages shorter than the minimum limit are filtered out."""
    raw_pages = [
        {"page_number": 1, "text": "Short"},             # Length 5 (filtered out)
        {"page_number": 2, "text": "This is long text"}  # Length 17 (kept)
    ]
    
    filtered_res = get_long_pages(raw_pages, minimum_length=10)
    
    assert len(filtered_res) == 1
    assert filtered_res[0]["page_number"] == 2
```
