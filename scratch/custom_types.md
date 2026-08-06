# Custom Data Types & Pydantic: Interview Guide

This guide explains how to define structured data types in Python using **Pydantic**, based on the structures in `custom-types.py`.

---

## 1. What is Pydantic?

**Pydantic** is a data validation and serialization library for Python.
*   **Structured Contracts**: It lets you define what your data should look like (a "schema" or "contract") using standard Python classes.
*   **Auto Validation**: If you pass invalid data (e.g., passing an integer when a list of strings is expected), Pydantic raises an error immediately.
*   **JSON Serialization**: It makes it easy to convert Python objects to JSON strings (serialization) and vice-versa (deserialization).

---

## 2. Line-by-Line Code Explanation

Here is the line-by-line breakdown of `custom-types.py`:

*   **Line 1**: `import pydantic` — Imports Pydantic to access `BaseModel`.
*   **Line 4**: `class RAGChunkAndSrc(pydantic.BaseModel):` — Defines a model representing the result of document processing. It inherits from `BaseModel`, which gives it parsing and validation features.
    *   `chunks: list[str]`: An attribute that must be a list of text strings.
    *   `source_id: str = None`: An attribute that must be a string, defaulting to `None` if not provided.
*   **Line 8**: `class RAGUpsertResult(pydantic.BaseModel):` — Defines a model representing database status after ingestion.
    *   `ingested: int`: The count of chunks written to the vector database.
*   **Line 11**: `class RAGSearchResult(pydantic.BaseModel):` — Defines a model representing the result of querying the vector database.
    *   `contexts: list[str]`: The raw text chunks that are relevant.
    *   `sources: list[str]`: The files those chunks came from.
*   **Line 15**: `class RAQQueryResult(pydantic.BaseModel):` — Defines a model representing the output of the final RAG query. *(Note: The class name has a typo, `RAQ` instead of `RAG`, which likely stands for Retrieval-Augmented Query)*.
    *   `answer: str`: The written response from the LLM.
    *   `sources: list[str]`: The files that were referenced.
    *   `num_contexts: int`: The count of paragraphs used.

---

## 3. Example Scenario: RAG Pipeline Data Flow

Here is a mock RAG pipeline showing how these types enforce data structures across function boundaries, complete with unit tests.

### Implementation

```python
import logging
from typing import List, Dict, Any
import pydantic

app_logger = logging.getLogger("uvicorn.error")

# 1. Input data structure
class RAGChunkAndSrc(pydantic.BaseModel):
    chunks: List[str]
    source_id: str = None

# 2. Vector search output data structure
class RAGSearchResult(pydantic.BaseModel):
    contexts: List[str]
    sources: List[str]

# 3. Final answer data structure
class RAGQueryResult(pydantic.BaseModel):
    answer: str
    sources: List[str]
    num_contexts: int

def mock_search_database(query: str) -> RAGSearchResult:
    """Simulates searching a database and returning matching chunks."""
    try:
        # Mock database response
        return RAGSearchResult(
            contexts=["FastAPI is built on Starlette.", "Pydantic does validation."],
            sources=["fastapi.pdf", "pydantic.pdf"]
        )
    except Exception as error:
        app_logger.error(f"Search failed: {str(error)}")
        raise error

def mock_generate_answer(search_result: RAGSearchResult) -> RAGQueryResult:
    """Simulates an LLM generating an answer based on search results."""
    try:
        # Construct response model
        return RAGQueryResult(
            answer="FastAPI handles routing while Pydantic handles validation.",
            sources=search_result.sources,
            num_contexts=len(search_result.contexts)
        )
    except Exception as error:
        app_logger.error(f"Answer generation failed: {str(error)}")
        raise error
```

### Unit Tests

```python
import pytest

def test_rag_chunk_and_src_validation() -> None:
    """Verifies that Pydantic enforces type constraints on RAGChunkAndSrc."""
    # Correct structure works
    valid_data = RAGChunkAndSrc(chunks=["hello", "world"], source_id="doc_1")
    assert valid_data.chunks == ["hello", "world"]
    assert valid_data.source_id == "doc_1"

    # Mismatched structure throws an exception
    with pytest.raises(pydantic.ValidationError):
        # chunks must be a list, not a single string
        RAGChunkAndSrc(chunks="not a list", source_id="doc_1")

def test_pipeline_data_flow() -> None:
    """Verifies data flows correctly between our structured functions."""
    search_res = mock_search_database("How does FastAPI validate?")
    assert isinstance(search_res, RAGSearchResult)
    assert len(search_res.contexts) == 2
    
    query_res = mock_generate_answer(search_res)
    assert isinstance(query_res, RAGQueryResult)
    assert query_res.num_contexts == 2
    assert "fastapi.pdf" in query_res.sources
```
