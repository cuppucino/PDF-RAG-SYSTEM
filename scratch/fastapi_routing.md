# FastAPI Routing, 404 Handling & Inngest Registration: Interview Guide

This guide covers how FastAPI handles routing, why `404 Not Found` errors occur, and how third-party middleware/frameworks like Inngest register endpoints.

---

## 1. FastAPI Routing & 404 Errors

When a client makes an HTTP request to Uvicorn, FastAPI resolves the path (e.g., `/`) by matching it against registered route patterns in order of definition.

*   **Root Route 404**: In the original code, the client requested `GET /` and received `404 Not Found` because there was no path decorator matching `@app.get("/")`.
*   **Default Behavior**: Unlike some frameworks that provide default index pages, FastAPI immediately returns a clean JSON response: `{"detail": "Not Found"}` with a `404` status code.
*   **Path Resolution**: Path matching is exact (unless path parameters are used). Standard routes are registered using decorator methods on the `FastAPI` instance (e.g., `@app.get()`, `@app.post()`, `@app.put()`).

---

## 2. Inngest Mounting & Serving Architecture

Inngest operates as a separate service or developer server that triggers your API endpoints when events happen. To do this, it needs to communicate with your FastAPI app over HTTP.

*   **Mounting Endpoint**: When you run `inngest.fast_api.serve(app, inngest_client, [...])`, the Inngest SDK dynamically mounts a sub-app or route on your FastAPI app. By default, it is mounted at `/api/inngest`.
*   **Function Discovery**: The third argument to `serve` is a list of functions (`[rag_ingest_pdf]`). Inngest registers these functions under its schema. When the Inngest Dev Server sends a `POST` request to `/api/inngest` (or runs a schema sync check via `GET /api/inngest`), it checks this list to discover which events your worker can handle. Passing an empty list `[]` means your background tasks are invisible to the Inngest platform.

---

## 3. Python Set vs. Dictionary Return Types

In the original code:
```python
async def rag_ingest_pdf(ctx: inngest.Context):
    return {"hello World!"}
```
*   **Set vs. Dict**: `{"hello World!"}` is a Python **`set`** (an unordered collection of unique elements). A dictionary requires key-value pairs (e.g., `{"message": "hello World!"}`).
*   **Serialization Error**: FastAPI automatically serializes return values into JSON using `jsonable_encoder`. Since standard JSON does not support sets, returning a set can lead to serialization issues or it gets formatted as a plain list, which doesn't conform to the expected key-value mapping of typical APIs.

---

## 4. Example Scenario: Registering multiple tasks & testing `/`

Here is a multi-route FastAPI app demonstrating a root check endpoint, a status endpoint, and two registered Inngest functions.

### Implementation

```python
import logging
from typing import Dict
from fastapi import FastAPI
import inngest
import inngest.fast_api

# Setup application and logger
app = FastAPI(title="Multi-task RAG Engine")
app_logger = logging.getLogger("uvicorn.error")

# Setup Inngest Client
inngest_client = inngest.Inngest(
    app_id="multi_rag_app",
    logging=app_logger,
    is_production=False
)

# Function 1: Ingest PDF
@inngest_client.create_function(
    fn_id="rag-ingest-pdf",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def handle_pdf_ingestion(ctx: inngest.Context) -> Dict[str, str]:
    return {"status": "PDF ingested successfully"}

# Function 2: Generate Embeddings
@inngest_client.create_function(
    fn_id="rag-generate-embeddings",
    trigger=inngest.TriggerEvent(event="rag/generate_embeddings")
)
async def handle_embedding_generation(ctx: inngest.Context) -> Dict[str, str]:
    return {"status": "Embeddings generated successfully"}

# Root Route
@app.get("/")
async def read_root() -> Dict[str, str]:
    return {"status": "API is healthy"}

# Serve the Inngest routes and register both functions
inngest.fast_api.serve(
    app,
    inngest_client,
    [handle_pdf_ingestion, handle_embedding_generation]
)
```

### Unit Tests

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_root() -> None:
    """Verifies that the root route returns a 200 OK and a healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "API is healthy"}

def test_inngest_route_registered() -> None:
    """Verifies that the inngest serving route is mounted and accessible."""
    response = client.get("/api/inngest")
    # A GET request to the Inngest endpoint returns details of registered functions
    assert response.status_code == 200
    data = response.json()
    # Check that both functions are returned in the configuration
    registered_ids = [fn["id"] for fn in data.get("functions", [])]
    assert "rag-ingest-pdf" in registered_ids
    assert "rag-generate-embeddings" in registered_ids
```
