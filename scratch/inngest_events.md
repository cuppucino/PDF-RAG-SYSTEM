# Inngest Events: Triggering & Handling: Interview Guide

This guide explains how events and handlers work together in Inngest, focusing on the event publication and consumption cycle.

---

## 1. What does "Triggered when the event is fired" mean?

Think of it like a **pub/sub (publish/subscribe)** messaging system or a radio broadcast:

1.  **The Broadcast (Publish/Fire)**: Somewhere in your application (e.g., when a user uploads a file on the frontend), you send a signal to Inngest called an **Event**. This signal has a name (like `"rag/ingest_pdf"`) and can contain some data (like the file URL).
2.  **The Radio Listener (Trigger/Subscribe)**: The `@inngest_client.create_function(...)` decorator tells Inngest: *"Listen for the radio station named `'rag/ingest_pdf'`."*
3.  **The Reaction (Handler)**: The moment Inngest hears that event name, it automatically calls the function defined directly underneath it (`rag_ingest_pdf`) and passes the event's data into it via `ctx`.

---

## 2. Example Scenario: Publishing and Handling a PDF Upload Event

Here is a simple scenario showing the two sides of the event loop: **firing** the event and **handling** the event.

### 1. The Code

```python
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
import inngest
import inngest.fast_api

app = FastAPI(title="Event Driven RAG")
app_logger = logging.getLogger("uvicorn.error")

# Setup Inngest
inngest_client = inngest.Inngest(
    app_id="pdf_processor",
    logging=app_logger,
    is_production=False
)

# SIDE A: Firing/Publishing the event from our API
@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf_endpoint(file_name: str) -> Dict[str, str]:
    """Receives a file upload and fires an event to process it in the background."""
    if not file_name.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF."
        )
        
    try:
        # We send ("fire") the event to Inngest.
        # This is asynchronous and returns immediately, so the client doesn't wait.
        await inngest_client.send(
            inngest.Event(
                name="rag/ingest_pdf",
                data={
                    "file_name": file_name,
                    "uploaded_by": "admin_user"
                }
            )
        )
        return {"message": "Upload accepted. Processing in the background."}
    except Exception as send_error:
        app_logger.error(f"Failed to fire event: {str(send_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue the processing task."
        )

# SIDE B: Handling/Receiving the event
@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def handle_pdf_ingestion(ctx: inngest.Context) -> Dict[str, Any]:
    """This function is triggered automatically when the 'rag/ingest_pdf' event is fired."""
    try:
        event_data = ctx.event.data
        file_name = event_data.get("file_name")
        
        # Real work happens here asynchronously
        app_logger.info(f"Background task: processing file {file_name}")
        return {"status": "processed", "file": file_name}
    except Exception as processing_error:
        app_logger.error(f"Background processing error: {str(processing_error)}")
        raise processing_error

# Serve the Inngest endpoints
inngest.fast_api.serve(app, inngest_client, [handle_pdf_ingestion])
```

### 2. Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

client = TestClient(app)

def test_upload_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that the API fires the event successfully and returns HTTP 202."""
    # Mock the client.send call so we don't need a running Inngest server during test
    async def mock_send(*args: Any, **kwargs: Any) -> None:
        pass
    monkeypatch.setattr(inngest_client, "send", mock_send)
    
    response = client.post("/upload?file_name=document.pdf")
    assert response.status_code == 202
    assert "Upload accepted" in response.json()["message"]

def test_upload_endpoint_bad_file() -> None:
    """Verifies that non-PDF files are rejected with a 400 status code."""
    response = client.post("/upload?file_name=document.txt")
    assert response.status_code == 400
    assert "File must be a PDF" in response.json()["detail"]
```
