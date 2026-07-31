# Inngest Function Invocation: Interview Guide

This guide explains what invoking a function means in Inngest, focusing on trigger methods, direct console invocation (`inngest/function.invoked`), and programmatic inter-function invocation (`step.invoke()`).

---

## 1. What is Function Invocation in Inngest?

In Inngest, **invoking a function** means starting a execution run of that function. There are three primary ways a function is invoked:

1.  **Event-Driven Trigger (Standard)**:
    *   The function runs automatically in response to a published event (e.g., `"rag/ingest_pdf"`).
2.  **Direct Dev Server Invocation (Manual testing)**:
    *   From the Inngest Dev Server UI, clicking **"Send test event"** or **"Run function"** triggers a direct run.
    *   Under the hood, Inngest fires a special built-in event called `inngest/function.invoked` to run the targeted function. This is what you see in your screenshot!
3.  **Programmatic Step Invocation (Parent-Child workflows)**:
    *   One function calls another function as a durable step: `await ctx.step.invoke(...)`.
    *   Inngest schedules the sub-function to run, tracks its state, waits for the result, and returns it to the parent function. If the child function fails, only the child is retried.

---

## 2. Programmatic Step Invocation (`step.invoke`)

Programmatic invocation is crucial for breaking down complex workflows. For example, instead of running everything inside `rag_ingest_pdf`, you might invoke a sub-function to extract text, and another to generate embeddings.

### Why use `ctx.step.invoke()` instead of calling a Python function directly?
*   **Timeouts**: Background tasks have execution limits. Inngest runs sub-functions independently, resetting timeout clocks.
*   **State Caching**: If the parent function crashes at step 4, Inngest resumes execution without re-running steps 1-3. The result of the invoked sub-function is cached.
*   **Language Polyglot**: A Python FastAPI backend can invoke a function running on a Node.js TypeScript backend.

---

## 3. Example Scenario: Parent-Child Ingestion Pipeline

Here is an example where a parent ingestion function programmatically invokes a child indexing function using `step.invoke()`.

### Implementation Code

```python
import logging
from typing import Dict, Any
from fastapi import FastAPI
import inngest
import inngest.fast_api

app = FastAPI(title="Orchestrated RAG Pipeline")
app_logger = logging.getLogger("uvicorn.error")

inngest_client = inngest.Inngest(
    app_id="orchestrator_app",
    logging=app_logger,
    is_production=False,
)

# Child Function: Performs the database indexing
@inngest_client.create_function(
    fn_id="rag-index-embeddings",
    trigger=inngest.TriggerEvent(event="rag/index_embeddings")
)
async def handle_indexing(ctx: inngest.Context) -> Dict[str, Any]:
    try:
        payload = ctx.event.data
        embeddings = payload.get("embeddings")
        document_id = payload.get("document_id")
        
        if not embeddings or not document_id:
            raise ValueError("Invalid payload: missing embeddings or document_id.")
            
        app_logger.info(f"Indexing embeddings for document: {document_id}")
        # Imagine writing embeddings to Pinecone / ChromaDB here
        return {"status": "indexed", "document_id": document_id}
    except Exception as error:
        app_logger.error(f"Indexing error: {str(error)}")
        raise error

# Parent Function: Coordinates ingestion
@inngest_client.create_function(
    fn_id="rag-pipeline-coordinator",
    trigger=inngest.TriggerEvent(event="rag/run_pipeline")
)
async def handle_pipeline_orchestration(ctx: inngest.Context) -> Dict[str, Any]:
    try:
        event_payload = ctx.event.data
        document_id = event_payload.get("document_id")
        
        if not document_id:
            raise ValueError("Missing document_id in pipeline trigger.")
            
        # Step 1: Simulate generating embeddings locally in the parent
        app_logger.info("Step 1: Generating embeddings locally...")
        simulated_embeddings = [0.1, 0.2, 0.3, 0.4]
        
        # Step 2: Invoke the child function programmatically to handle indexing
        # This keeps the functions decoupled and modular
        indexing_result = await ctx.step.invoke(
            "invoke-indexing-step",
            function_id="rag-index-embeddings",  # Targets the registered fn_id
            data={
                "document_id": document_id,
                "embeddings": simulated_embeddings
            }
        )
        
        return {
            "status": "pipeline_complete",
            "document_id": document_id,
            "child_step_output": indexing_result
        }
    except Exception as error:
        app_logger.error(f"Pipeline execution failed: {str(error)}")
        raise error

# Serve the functions
inngest.fast_api.serve(
    app,
    inngest_client,
    [handle_indexing, handle_pipeline_orchestration]
)
```

### Unit Tests

```python
import pytest
import inngest

@pytest.mark.asyncio
async def test_handle_indexing_success() -> None:
    """Verifies indexing logic compiles and returns correct dictionary keys."""
    mock_event = inngest.Event(
        name="rag/index_embeddings",
        data={"document_id": "doc_abc", "embeddings": [0.1, 0.2]}
    )
    mock_ctx = inngest.Context(
        event=mock_event,
        run_id="run_123",
        step=inngest.Step(run_id="run_123", client=inngest_client, logger=app_logger)
    )
    
    result = await handle_indexing(mock_ctx)
    assert result["status"] == "indexed"
    assert result["document_id"] == "doc_abc"

@pytest.mark.asyncio
async def test_handle_indexing_invalid() -> None:
    """Verifies that indexing fails if payload parameters are missing."""
    mock_event = inngest.Event(name="rag/index_embeddings", data={})
    mock_ctx = inngest.Context(
        event=mock_event,
        run_id="run_123",
        step=inngest.Step(run_id="run_123", client=inngest_client, logger=app_logger)
    )
    
    with pytest.raises(ValueError) as error_info:
        await handle_indexing(mock_ctx)
    assert "Invalid payload" in str(error_info.value)
```
