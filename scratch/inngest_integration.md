# Inngest & FastAPI Integration: Interview Guide

This guide explains event-driven background jobs using **Inngest** integrated with **FastAPI**, based on the code in `main.py`.

---

## 1. What is Inngest?

**Inngest** is an event-driven backend platform that enables developers to run durable, step-by-step background functions without managing queues, workers, or state persistence.
- **Event-Driven**: Functions are triggered automatically when specific events (e.g., `"rag/ingest-pdf"`) are sent (published) to the system.
- **Serverless Queueing**: Instead of polling a database or managing a Redis-backed queue like Celery or BullMQ, Inngest receives events and invokes your application endpoints asynchronously.
- **FastAPI Integration**: The backend application hosts a special API route (via `inngest.fast_api.serve`) that the Inngest server or cloud communicates with to trigger functions.

---

## 2. Line-by-Line Code Explanation

Here is the line-by-line breakdown of the structure in `main.py`:

*   **Line 1**: `import logging` — Imports Python's built-in logging module to write runtime logs.
*   **Line 2**: `from fastapi import FastAPI` — Imports the `FastAPI` class to create the web server.
*   **Line 3**: `import inngest.fast_api` — Imports the FastAPI adapter module from Inngest to mount its serving endpoint.
*   **Line 4**: `from dotenv import load_dotenv` — Imports the helper function to load key-value configurations from a `.env` file into system environment variables.
*   **Lines 5-7**: `import uuid`, `import os`, `import datetime` — Import basic utilities for unique IDs, environment variables, and timestamps.
*   **Line 11**: `load_dotenv()` — Invokes the helper to read variables (like API keys) from the `.env` file.
*   **Line 14-19**: `inngest_client = inngest.Inngest(...)` — Initializes the core client config.
    *   `app_id="rag_app"`: Sets the unique identifier for this application.
    *   `logging=logging.getLogger("uvicorn")`: Pipes logs into the Uvicorn web server's logging pipeline.
    *   `is_production=False`: Configures it to run locally (usually communicating with the Inngest Dev Server).
    *   `serializer=inngest.PydanticSerializer()`: Tells Inngest to serialize and parse event payloads using Pydantic models automatically.
*   **Line 21-24**: `@inngest_client.create_function(...)` — A decorator that registers a background function.
    *   `fn_id="RAG: Ingest PDF"`: A unique name for the background task.
    *   `trigger=inngest.TriggerEvent(event="rag/ingest-pdf")`: Configures the task to automatically run whenever an event named `"rag/ingest-pdf"` is fired.
*   **Line 25**: `async def rag_ingest_pdf(ctx: inngest.Context):` — The definition of the asynchronous handler that executes when the trigger event fires.
*   **Line 26**: `app = FastAPI ()` — Creates the main FastAPI web server instance.
*   **Line 28**: `inngest.fast_api.serve(app, inngest_client, functions:[])` — Registers the serving endpoints on the FastAPI app so the Inngest Dev Server can communicate with your background workers.

---

## 3. Key Issues Identified in `main.py`

There are three bugs preventing the file from compiling or running successfully:

1.  **Missing Core Import**: `inngest` itself is used on line 14 (`inngest.Inngest`) and line 23, but only `inngest.fast_api` was imported. `import inngest` must be added.
2.  **Indentation / Function Body Syntax Error**: 
    ```python
    async def rag_ingest_pdf(ctx: inngest.Context):
    app = FastAPI ()
    ```
    Python requires an indented body block for the function definition. Since `app` is defined at the root level immediately after, Python raises an `IndentationError`.
3.  **Invalid Serving Syntax**: 
    ```python
    inngest.fast_api.serve(app, inngest_client, functions:[])
    ```
    `functions:[]` is invalid syntax for keyword arguments in Python. It must use an equals sign (`functions=[]`).

---

## 4. Example Scenario: Processing & Indexing PDFs

Here is a syntactically correct, robust implementation with error handling and corresponding unit tests.

### Implementation

```python
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import fastapi
import inngest
import inngest.fast_api

# Load configs
load_dotenv()

# Initialize the main FastAPI application
app = fastapi.FastAPI(title="PDF-RAG Ingestion Engine")

# Setup logger
app_logger = logging.getLogger("uvicorn.error")

# Configure the Inngest client
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logging=app_logger,
    is_production=False,
)

@inngest_client.create_function(
    fn_id="rag-ingest-pdf",
    trigger=inngest.TriggerEvent(event="rag/ingest-pdf"),
)
async def handle_rag_ingest_pdf(ctx: inngest.Context) -> Dict[str, Any]:
    """Background job handler that executes when the 'rag/ingest-pdf' event fires."""
    try:
        event_payload = ctx.event.data
        file_path = event_payload.get("file_path")
        document_id = event_payload.get("document_id")

        if not file_path or not document_id:
            raise ValueError("Missing file_path or document_id in event payload.")

        # Simulate durable background work (e.g., parsing, embedding, storing in vector db)
        app_logger.info(f"Ingesting PDF doc: {document_id} from path: {file_path}")
        
        return {
            "status": "success",
            "document_id": document_id,
            "processed_file": file_path,
        }
    except Exception as error:
        app_logger.error(f"Ingestion failed: {str(error)}")
        # Allow Inngest to handle retries by propagating the exception
        raise error

# Serve Inngest integration endpoint on FastAPI (adds a POST /api/inngest route)
inngest.fast_api.serve(
    app,
    inngest_client,
    functions=[handle_rag_ingest_pdf],
)
```

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

# Create client for checking endpoints
test_client = TestClient(app)

def test_inngest_serve_endpoint_exists() -> None:
    """Verifies that the Inngest integration route responds to GET requests for sync checking."""
    response = test_client.get("/api/inngest")
    # Inngest serves an options check or returns a 405/400 for bad sync,
    # but the path should be registered.
    assert response.status_code in [200, 400, 405]

@pytest.mark.asyncio
async def test_handle_rag_ingest_pdf_success() -> None:
    """Tests the logic of the event handler with mock context payloads."""
    # Build a mock event context
    mock_event = inngest.Event(
        name="rag/ingest-pdf",
        data={"file_path": "/data/sample.pdf", "document_id": "doc_123"},
    )
    mock_ctx = inngest.Context(
        event=mock_event,
        run_id="run_abc",
        step=inngest.Step(
            run_id="run_abc",
            client=inngest_client,
            logger=app_logger,
        ),
    )

    result = await handle_rag_ingest_pdf(mock_ctx)
    
    assert result["status"] == "success"
    assert result["document_id"] == "doc_123"
    assert result["processed_file"] == "/data/sample.pdf"

@pytest.mark.asyncio
async def test_handle_rag_ingest_pdf_validation_failure() -> None:
    """Tests that missing event parameters trigger value errors in the handler."""
    mock_event = inngest.Event(
        name="rag/ingest-pdf",
        data={},  # Empty payload
    )
    mock_ctx = inngest.Context(
        event=mock_event,
        run_id="run_abc",
        step=inngest.Step(
            run_id="run_abc",
            client=inngest_client,
            logger=app_logger,
        ),
    )

    with pytest.raises(ValueError) as error_info:
        await handle_rag_ingest_pdf(mock_ctx)
    
    assert "Missing file_path or document_id" in str(error_info.value)
```
