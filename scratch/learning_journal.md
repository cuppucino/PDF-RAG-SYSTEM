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

---

## [[Phase 5: Data Loader Setup]]

### What I Did
I created `data_loader.py` to handle parsing local PDF files, splitting the text into manageable semantic chunks, and generating vector embeddings using the OpenAI API.

### What I Used
*   **[[data_loader]]**: Contains functions for document reading and embedding generation.
*   **`llama-index-readers-file`**: Used `PDFReader` to read PDF files page-by-page.
*   **`llama-index-core`**: Used `SentenceSplitter` to divide text with semantic overlap.
*   **OpenAI SDK (`openai`)**: Connected to the `text-embedding-3-large` model.
*   **What I Learned**:
    *   **Embedding Model Naming**: Fixed a typo where the model name was written as `text-embeeding-3-large` instead of `text-embedding-3-large`.
    *   **Chunking & Overlap**: Splitting text prevents hitting LLM context limits and increases retrieval precision. The overlap keeps sentences coherent between chunks.

---

## [[Phase 6: Custom Types & Pydantic]]

### What I Did
I commented and documented `custom-types.py` which defines structured Pydantic schemas for the data pipelines (chunk output, ingestion status, search matches, and AI answers).

### What I Used
*   **[[custom_types]]**: Establishes type models to ensure data integrity.
*   **Pydantic (`pydantic`)**: Validates input shapes and supports JSON serialization.
*   **What I Learned**:
    *   **Data Validation**: Models guarantee variables match their expected types (e.g. lists or integers) before they are passed between parts of the system.
    *   **Naming Details**: Noticed a minor typo where `RAQQueryResult` has a `Q` (representing Query) instead of a `G` (representing Generation).

---

## [[Phase 7: Lambda Functions]]

### What I Did
I studied Python **lambda functions** (anonymous functions) and documented their usage patterns, syntax rules, and sorting/filtering use cases.

### What I Used
*   **[[lambda_expressions]]**: Details syntax, standard `def` comparison, and code scenarios.
*   **What I Learned**:
    *   **Anonymous Nature**: Lambda functions do not require names and are defined inline.
    *   **Limitations**: They can only have one expression and cannot include multi-line code blocks like standard `def` declarations.
    *   **Practical Use**: Highly useful for passing quick inline transformation logic to methods like `sorted()` or `filter()`.

---

## [[Phase 8: Durable Steps & Inngest Steps]]

### What I Did
I updated and debugged `main.py` where a multi-step background ingestion process extracts, chunks, embeds, and uploads PDF texts to a Qdrant database using Inngest steps.

### What I Used
*   **[[inngest_steps]]**: Details checkpointing, durable executions, and re-entrancy.
*   **What I Learned**:
    *   **Syntax & Imports**: Resolved a syntax typo (`ffrom` instead of `from`) and class name mismatches.
    *   **Durable Step Execution (`ctx.step.run`)**: Splitting code into steps guarantees Inngest checkpointing. If the server crashes, it doesn't need to re-run preceding steps (saving OpenAI credits).
    *   **Step Outputs**: Matched the correct step output structures (`RAGChunkAndSrc` and `RAGUpsertResult`) and called the actual database storage `upsert` logic.

---

## [[Phase 9: Python Module Import Rules]]

### What I Did
I solved a startup crash in Uvicorn caused by a module import mismatch. The file defining Pydantic schemas was named `custom-types.py` (with a hyphen), preventing Python from importing it. I renamed it to `custom_types.py` (with an underscore).

### What I Used
*   **[[python_imports]]**: Details sys.path loading patterns and naming convention restrictions.
*   **What I Learned**:
    *   **Hyphen Restriction**: Hyphens are subtraction symbols in Python, meaning files with hyphens in their names cannot be imported using standard syntax.
    *   **Naming Consistency**: Python modules must use snake_case (`custom_types.py`) to align import statements (`import custom_types`) with actual filenames on disk.

---

## [[Phase 10: JSON Formatting & Schema Validation]]

### What I Did
I studied and troubleshooted a JSON formatting error in the Inngest Dev Server dashboard. The manual trigger payload used incorrect curly braces and lacked standard key names, violating JSON syntax rules and backend expectations.

### What I Used
*   **[[json_basics]]**: Details JSON syntax constraints, object structures, and payload formats.
    *   **Schema Alignment**: Custom payloads must align with backend dictionaries (e.g. providing `"pdf_path"` so `ctx.event.data["pdf_path"]` evaluates successfully).

---

## [[Phase 11: API Limits & Quotas]]

### What I Did
I studied and analyzed an `openai.RateLimitError` (HTTP 429) that halted our embedding steps. The API response explicitly identified this as an `insufficient_quota` error.

### What I Used
*   **[[rate_limits]]**: Details API rate limits vs account billing quotas, along with recovery strategies like exponential backoff and local model fallbacks.
*   **What I Learned**:
    *   **Billing Limit vs. Speed Limit**: While both return HTTP 429, speed limits can be fixed by waiting and retrying, whereas quota limits require funding the account balance.
    *   **Resiliency**: Catching specific exception codes prevents waste of network retries during billing outages.

---

## [[Phase 12: AI Answer Generation (Gemini + step.ai.infer)]]

### What I Did
I built the second Inngest function `rag_query_pdf`, which completes the RAG loop: embed the question → search Qdrant for similar paragraphs → stuff them into a prompt → ask Gemini to generate the answer. The tutorial used OpenAI for this step, but I swapped in Google's Gemini using Inngest's provider adapters.

### What I Used
*   **[[gemini_adapter]]**: Details the adapter concept, `step.ai.infer`, and the OpenAI-vs-Gemini request format differences.
*   **`ai.gemini.Adapter`**: Inngest's built-in Gemini connector (`auth_key` + `model`).
*   **`ctx.step.ai.infer`**: Makes the LLM call a durable, checkpointed step executed by the Inngest server itself.
*   **What I Learned**:
    *   **Provider Dialects**: The adapter only swaps the URL/auth — the request body must be written in the provider's own format. Gemini uses `contents`/`parts`/`generationConfig`, not OpenAI's `messages`/`max_tokens`, and answers come back under `candidates`, not `choices`.
    *   **Code After `return` Never Runs**: My query function was accidentally nested inside the ingest function *after* its `return` — silently dead code. Inngest functions must be defined at module level, with the `@` decorator, AND passed to the `serve(...)` list.
    *   **Exact Dictionary Keys**: `search()` returned `"context"` but I read `"contexts"` → `KeyError`. Same lesson as `"max-tokens"` (typo) vs `"maxOutputTokens"` — JSON/dict keys are never auto-corrected.
    *   **Mixed Providers Are Fine**: OpenAI still does the embeddings, Gemini writes the answers — so `.env` needs both keys. The only hard rule: the question must be embedded with the *same* model as the documents.
    *   **Library APIs Get Removed, Not Just Deprecated**: `qdrant-client` 1.16+ deleted the old `client.search()` method — the tutorial's code raised `AttributeError`. The replacement is `client.query_points(collection_name=..., query=..., limit=...)`, which renames `query_vector` to `query` and wraps the matches in a response object (access them via `.points`). Lesson: when a tutorial is older than your installed library, check the library's changelog/migration guide instead of assuming the code is wrong.
    *   **`__init__.py` Controls What a Package Exposes** (builds on [[python_imports]]): `ai.gemini` crashed with `AttributeError` even though `gemini.py` physically exists in the package folder — because this inngest version's `__init__.py` only imports `openai` and `anthropic`. A file being *in* the folder isn't enough; Python only attaches submodules that get imported. Fix: import the submodule directly with `from inngest.experimental.ai import gemini`.

---

## [[Phase 13: Streamlit Frontend]]

### What I Did
I added `streamlit_app.py` as the user interface: upload a PDF (fires the `rag/ingest_pdf` event) and ask questions (fires `rag/query_pdf_ai`, then polls the Inngest API for the run's output to display the answer and sources).

### What I Used
*   **[[streamlit_frontend]]**: Explains how a Python file can be a "frontend" at all.
*   **Streamlit (`streamlit`)**: Pre-built React widgets driven from Python; run with `uv run streamlit run streamlit_app.py`.
*   **What I Learned**:
    *   **Frontends Are Always HTML/CSS/JS**: Streamlit doesn't avoid them — its engineers pre-wrote a React app, and my Python calls just tell it which widgets to render over a WebSocket.
    *   **The Re-Run Model**: Every interaction re-runs the whole script top-to-bottom; widgets return values instead of firing callbacks (`if uploaded is not None:` replaces an "on upload" event handler). `@st.cache_resource` keeps expensive objects alive across re-runs.
    *   **Event-Driven Architecture**: The frontend never imports the backend — it communicates purely by sending Inngest events and polling run outputs. UI and workers stay decoupled.
    *   **"Event Loop is Closed" (asyncio vs caching)**: `asyncio.run()` creates a fresh event loop and *destroys it* when done. My `@st.cache_resource`-cached Inngest client kept async HTTP connections tied to that destroyed loop, so the *second* interaction crashed with `RuntimeError: Event loop is closed`. Fix: use the client's synchronous `send_sync()` method — no event loops at all. Lesson: don't mix short-lived `asyncio.run()` calls with long-lived cached async objects; in a synchronous framework like Streamlit, prefer the sync API.
