# My Learning Journal: PDF-RAG System

This is my personal learning diary as I build a Retrieval-Augmented Generation (RAG) system for PDFs from scratch. I am documenting each phase, what I ran, and what I learned.

---

## [[Phase 1: Project Setup & Dependencies]]

### What I Did
I started by setting up the project workspace. I wanted to initialize a new Python project, but I encountered a command-not-found error for `uv`.

### What I Used
*   **[[uv]]**: A super-fast Python package manager written in Rust. I installed it using:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
*   **Project Initialization**: I ran `uv init` to generate a standard boilerplate structure:
    *   `pyproject.toml` (configuration)
    *   `.python-version` (pinned to Python 3.11)
    *   `src/pdf_rag_system/` (for modular source code)

---

## [[Phase 2: Web Server API Setup]]

### What I Did
I set up the backbone web server that will receive requests (like document uploads and queries).

### What I Used
*   **[[FastAPI]]**: A modern, high-performance web framework for Python. I added it with `uv add fastapi`.
*   **[[Uvicorn]]**: An ASGI web server to run our FastAPI application.
*   **Running the Server**: I started it up using:
    ```bash
    uv run uvicorn main:app --reload
    ```
*   **What I Learned**: 
    *   Always define a root route (`/`) or you will get a `404 Not Found` error when visiting the default URL.
    *   Make sure to return dictionaries (key-value pairs) instead of Python sets (e.g., return `{"message": "hello"}` instead of `{"hello"}`) so FastAPI can properly convert it into JSON.
    *   See [[fastapi_overview]] and [[fastapi_routing]] for full details on this phase.

---

## [[Phase 3: Background Jobs & Event Queue]]

### What I Did
Because parsing PDFs and generating embeddings can take a long time, doing it directly in the web request would cause timeout errors and freeze the application. I needed a way to trigger jobs in the background.

### What I Used
*   **[[Inngest]]**: An event-driven queue runner. I added it to the project, connected it to FastAPI, and created my first background task `rag_ingest_pdf`.
*   **Inngest Dev Server**: I started the local developer UI dashboard using:
    ```bash
    npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
    ```
*   **What I Learned**:
    *   **[[inngest_events]]**: Events are like signals. We broadcast (fire) a signal, and the worker function catches (triggers on) it.
    *   **[[inngest_invocation]]**: We can manually trigger runs inside the Dev Server UI using the `inngest/function.invoked` event to test things out.
    *   **Function List**: Don't forget to pass the functions into `inngest.fast_api.serve(..., [rag_ingest_pdf])` or the dev server won't know they exist!
    *   See [[inngest_integration]] for the integration details.

---

## [[Phase 4: Vector Database Setup]]

### What I Did
I successfully created `vector_db.py` to store and retrieve high-dimensional vectors representing PDF text segments. I resolved a list iteration bug in the sources accumulator.

### What I Used
*   **[[Qdrant]]**: A specialized Vector Database.
*   **`qdrant-client`**: The Python SDK to connect to it.
*   **What I Learned**:
    *   **OOP Basics**: How Python classes use `self` to reference their own variables and how `__init__` acts as a setup function.
    *   **[[vector_database]]**: The details of setting up collections, distances (Cosine), and doing "upserts".
    *   **Upsert**: The database automatically checks if an item exists by ID. If yes, it updates it. If no, it inserts it.

