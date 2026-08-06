# Gemini Adapter & LLM Inference with Inngest (`step.ai.infer`)

This note covers how the final "answer generation" step of the RAG pipeline works: taking the paragraphs we found in Qdrant and asking an AI model (Gemini) to write an answer from them.

---

## 1. What is an Adapter?

An **adapter** is a small translator object that tells Inngest *which* AI provider to call, *where* its API lives, and *how* to authenticate. Inngest ships adapters for several providers (`openai`, `gemini`, `anthropic`, `deepseek`, `grok`), and they all share the same interface:

```python
adapter = ai.gemini.Adapter(
    auth_key=os.getenv("GEMINI_API_KEY"),   # your API key from .env
    model="gemini-2.5-flash",               # which model to use
)
```

Swapping providers = swapping the adapter. The tutorial used `ai.openai.Adapter` with `OPENAI_API_KEY`; I use `ai.gemini.Adapter` with `GEMINI_API_KEY`. **But the adapter only changes the URL and auth — it does NOT translate the request body.** That part is on you (see below).

---

## 2. Why `step.ai.infer` instead of calling Gemini directly?

`ctx.step.ai.infer(...)` makes the AI call a **durable step**:

*   The request is actually made **by the Inngest server**, not my Python code — my function "offloads" the call and can pause (no compute wasted while waiting).
*   The response gets **checkpointed** like any other step: if a later step crashes, the (paid!) AI call is not repeated on retry.
*   The request/response appear in the Dev Server UI, so I can inspect exactly what was sent and received.

---

## 3. OpenAI format vs Gemini format (the big gotcha)

Every provider speaks its own JSON dialect. My first attempt sent an OpenAI-style body to Gemini — that fails, because Gemini's `generateContent` API expects a totally different shape:

| Concept | OpenAI | Gemini |
|---|---|---|
| Conversation | `"messages": [{"role", "content"}]` | `"contents": [{"role", "parts": [{"text"}]}]` |
| System prompt | a message with `"role": "system"` | separate top-level `"systemInstruction"` field |
| Max answer length | `"max_tokens"` (top level) | `"maxOutputTokens"` inside `"generationConfig"` |
| Temperature | `"temperature"` (top level) | `"temperature"` inside `"generationConfig"` |
| Answer in response | `res["choices"][0]["message"]["content"]` | `res["candidates"][0]["content"]["parts"][0]["text"]` |

The working Gemini body:

```python
body={
    "systemInstruction": {"parts": [{"text": "You answer questions using only the provided context."}]},
    "contents": [{"role": "user", "parts": [{"text": user_content}]}],
    "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
}
```

Bonus catch: I had written `"max-tokens"` with a hyphen — that key doesn't exist in *any* provider's API. JSON keys are exact strings; a typo'd key is silently ignored or rejected, never auto-corrected.

---

## 4. Bugs I fixed in this phase (great interview stories)

1.  **Dead code after `return`**: my second Inngest function was defined *inside* the first one, *after* its `return` statement. Python never executes anything after `return`, so the function silently never existed. Lesson: registration code must run at **module level** (top of the file, no indentation).
2.  **Missing `@` on the decorator**: `inngest_client.create_function(...)` without `@` is just a function call whose result is thrown away. The `@` is what wires the decorator to the function below it.
3.  **Forgot the serve list**: every function must be passed to `inngest.fast_api.serve(app, client, [fn1, fn2])`. Missing = invisible to the dev server (same lesson as Phase 3!).
4.  **Key name mismatch**: `vector_db.search()` returns `{"context": ...}` (singular) but I read `found["contexts"]` (plural) → instant `KeyError`. Dictionaries don't guess; keys must match exactly.

---

## 5. RAG prompt pattern ("stuffing")

The prompt we send is the classic RAG shape — retrieved paragraphs pasted above the question, with an instruction to only use that context:

```
Use the following context to answer the question.

Context:
- <paragraph 1>
- <paragraph 2>

Question: <the user's question>
Answer concisely using the context above.
```

This is called **context stuffing**: the model doesn't "know" our PDF — we hand it the relevant snippets at question time. That is the whole point of RAG: **R**etrieve (Qdrant search) → **A**ugment (build this prompt) → **G**enerate (Gemini writes the answer).

---

## 6. One thing to watch out for

My embeddings (`text-embedding-3-large`, 3072 dims) still come from **OpenAI**, while answer generation now comes from **Gemini**. That's perfectly fine — retrieval and generation are independent — but it means the app needs BOTH keys in `.env`: `OPENAI_API_KEY` (embeddings) and `GEMINI_API_KEY` (answers). The question must be embedded with the **same model** used at ingestion, or the vectors live in different "spaces" and search returns garbage.
