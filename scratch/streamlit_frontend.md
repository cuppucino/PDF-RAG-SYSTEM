# Streamlit: A Frontend Written in Python

This note answers my own question: "Isn't frontend supposed to be HTML/CSS/JavaScript? How is `streamlit_app.py` a frontend?"

---

## 1. Every frontend IS HTML/CSS/JS — the question is who writes it

The browser only speaks three languages:

*   **HTML** — structure (what's on the page)
*   **CSS** — appearance (colors, spacing, layout)
*   **JavaScript** — behavior (what happens on click)

That is non-negotiable. Frameworks and tools differ only in **who produces that code**:

| Approach | Who writes the HTML/CSS/JS |
|---|---|
| Hand-built | You, by hand |
| React / Vue | You write JS components, the framework renders them |
| **Streamlit** | **Streamlit's engineers already wrote it — you just call Python functions** |

## 2. How Streamlit works under the hood

Streamlit ships a **pre-built React app** (yes, JavaScript!) containing polished, ready-made widgets. When I run `streamlit run streamlit_app.py`:

1.  A Python web server runs my script **top to bottom**.
2.  Calls like `st.title(...)` / `st.file_uploader(...)` don't draw anything themselves — they send *messages* over a WebSocket: "render an uploader widget here."
3.  The React app in the browser receives the messages and renders the real HTML/CSS/JS.

One Python line = a whole widget. `st.file_uploader("Choose a PDF", type=["pdf"])` replaces an `<input type="file">`, drag-and-drop CSS, and file-reading + upload JavaScript.

## 3. The re-run model (Streamlit's weirdest idea)

There are **no event handlers** (no `onClick`). Instead, *every* user interaction re-runs the whole script from the top, and widget functions return their current values:

```python
uploaded = st.file_uploader(...)   # returns None until the user uploads
if uploaded is not None:           # this replaces an "on upload" callback
    ...
```

Consequences:

*   State does not survive re-runs by default — that's why `@st.cache_resource` wraps `get_inngest_client()`, so the client is built once and reused instead of being recreated on every click.
*   Code reads like a plain script, which is why it feels so simple.

## 4. How our frontend talks to the backend

`streamlit_app.py` doesn't call Qdrant or Gemini itself. It:

1.  Saves the uploaded PDF to `uploads/`, then **fires an Inngest event** (`rag/ingest_pdf` or `rag/query_pdf_ai`) — the same events our `main.py` worker functions listen for.
2.  For questions, it **polls** the Inngest dev server's REST API (`/v1/events/{id}/runs`) every 0.5s until the run status is "Completed", then reads the run's `output` (our `RAGQueryResult` dict) and displays `answer` + `sources`.

So the architecture is: **Streamlit (UI) → Inngest event → FastAPI worker (main.py) → Qdrant + Gemini → run output → polled back by Streamlit.** The frontend and backend never call each other directly — they communicate through events and run results.

## 5. Bug diary: `RuntimeError: Event loop is closed`

The app crashed on the **second** interaction (first one always worked). Cause — a bad interaction between three things:

1.  `asyncio.run(coro)` creates a temporary event loop, runs the coroutine, then **closes the loop forever**.
2.  The Inngest client internally keeps an **async HTTP connection pool**, and async connections are bound to the loop they were created on.
3.  `@st.cache_resource` keeps that client (and its pool) **alive across re-runs** — including its now-dead connections.

So: interaction #1 works and kills its loop → interaction #2 creates a new loop, but the cached pool tries to touch connections from the dead loop → crash.

**Fix**: the inngest client offers `send_sync()`, a plain synchronous method. Streamlit is a synchronous world (top-to-bottom script), so using the sync API removes event loops from the picture entirely. General rule: *never mix short-lived `asyncio.run()` with long-lived cached async objects.*

## 6. When to use Streamlit vs a "real" JS frontend (interview answer)

*   **Streamlit**: prototypes, demos, internal tools, data/ML apps. Full UI in ~100 lines of Python, no frontend skills needed.
*   **React/Vue/etc.**: customer-facing products needing custom design, instant interactivity, complex state. Full control, much more work.
*   Rule of thumb: *Streamlit to prove it works, a JS framework to ship it to customers.*
