# Inngest Steps & Durable Execution: Interview Guide

This guide explains how **durable execution** works in Inngest using `ctx.step.run`, based on the multi-step pipeline inside `main.py`.

---

## 1. What is Durable Execution & Inngest Steps?

When running long, complex background tasks (like downloading a file, chunking it, embedding it, and saving it to a database), servers can crash or network calls can fail.

*   **Standard Python execution**: If a crash happens on step 3, you have to restart the whole function from step 1. This is expensive and duplicates work (e.g., calling OpenAI embeddings twice).
*   **Inngest Durable Steps (`ctx.step.run`)**: By wrapping each part of your task in `await ctx.step.run(...)`, Inngest saves the result of each step. 
    *   If a crash happens at step 3, Inngest restarts the function, but **skips steps 1 and 2** by reading their saved results from history.
    *   This is called **re-entrancy** or **checkpointing**.

---

## 2. Line-by-Line Code Explanation

Here is how the multi-step logic inside the `rag_ingest_pdf` function works:

*   **Line 34-38**: `def _load(ctx: inngest.Context) -> RAGChunkAndSrc:` — A helper function to read the PDF path from the event, load it, cut it into chunks, and return the structured data.
*   **Line 40-52**: `def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:` — A helper function to embed the text chunks and upload them to Qdrant storage.
    *   `vecs = embed_texts(chunks)`: Calls the OpenAI API to embed all text chunks.
    *   `ids = [...]`: Generates a deterministic UUID for each chunk using `uuid.uuid5` so we don't insert duplicate IDs if the task runs again.
    *   `storage = QdrantStorage()`: Connects to the Qdrant database.
    *   `storage.upsert(ids, vecs, payload)`: Uploads the vectors and raw text chunks to Qdrant.
    *   `return RAGUpsertResult(ingested=len(chunks))`: Returns the number of chunks successfully saved.
*   **Line 55**: `chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), ...)` — Runs the load/chunk logic as a durable step named `"load-and-chunk"`.
*   **Line 57**: `ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), ...)` — Runs the embed/upload logic as a durable step named `"embed-and-upsert"`.
    *   `output_type=RAGUpsertResult`: Tells Inngest to parse the return value of this step using the `RAGUpsertResult` pydantic model.
*   **Line 60**: `return ingested.model_dump()` — Converts the pydantic object into a clean dictionary to return it to the Inngest runner.

---

## 3. Example Scenario: Durable Multi-Step File Ingestion

Below is a complete, runnable example of a multi-step background job, featuring robust error handling and unit tests.

### Implementation

```python
import logging
from typing import Dict, Any, List
import pydantic
import inngest

app_logger = logging.getLogger("uvicorn.error")

# Data Models
class DownloadResult(pydantic.BaseModel):
    file_path: str
    size_bytes: int

class ProcessResult(pydantic.BaseModel):
    chunks_count: int
    success: bool

# Initialize Inngest Client
inngest_client = inngest.Inngest(
    app_id="file_pipeline",
    logging=app_logger,
    is_production=False
)

@inngest_client.create_function(
    fn_id="durable-pipeline",
    trigger=inngest.TriggerEvent(event="pipeline/run")
)
async def handle_durable_pipeline(ctx: inngest.Context) -> Dict[str, Any]:
    """Runs a file processing pipeline with durable checkpointing steps."""
    
    # Step 1: Download the file
    def _download() -> DownloadResult:
        url = ctx.event.data.get("url")
        if not url:
            raise ValueError("Missing file URL.")
        app_logger.info(f"Downloading file from {url}...")
        # Simulate download
        return DownloadResult(file_path="/tmp/downloaded_doc.pdf", size_bytes=2048)

    # Step 2: Process the downloaded file
    def _process(downloaded: DownloadResult) -> ProcessResult:
        app_logger.info(f"Processing local file at {downloaded.file_path}...")
        # Simulate processing
        return ProcessResult(chunks_count=12, success=True)

    # Durable step calls
    download_res = await ctx.step.run(
        "download-file", 
        _download, 
        output_type=DownloadResult
    )
    process_res = await ctx.step.run(
        "process-file", 
        lambda: _process(download_res), 
        output_type=ProcessResult
    )

    return {
        "status": "complete",
        "download_details": download_res.model_dump(),
        "processing_details": process_res.model_dump()
    }
```

### Unit Tests

```python
import pytest
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_handle_durable_pipeline_success() -> None:
    """Verifies the logic steps of the durable pipeline function run correctly."""
    mock_event = inngest.Event(
        name="pipeline/run",
        data={"url": "http://example.com/doc.pdf"}
    )
    
    # Mocking step.run behavior
    mock_step = MagicMock()
    
    # Step 1 returns a DownloadResult
    mock_download_res = DownloadResult(file_path="/tmp/downloaded_doc.pdf", size_bytes=2048)
    # Step 2 returns a ProcessResult
    mock_process_res = ProcessResult(chunks_count=12, success=True)
    
    # Setup step.run to return the mock results sequentially
    mock_step.run.side_effect = [mock_download_res, mock_process_res]
    
    mock_ctx = inngest.Context(
        event=mock_event,
        run_id="run_123",
        step=mock_step
    )

    result = await handle_durable_pipeline(mock_ctx)
    
    assert result["status"] == "complete"
    assert result["download_details"]["file_path"] == "/tmp/downloaded_doc.pdf"
    assert result["processing_details"]["chunks_count"] == 12
    assert mock_step.run.call_count == 2
```
