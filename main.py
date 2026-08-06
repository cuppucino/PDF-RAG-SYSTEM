import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
# NOTE: this inngest version's "ai" package only re-exports openai/anthropic
# in its __init__.py, so we must import the gemini submodule directly
from inngest.experimental.ai import gemini
from dotenv import load_dotenv
import uuid
import os
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc


# load the environment variables inside of this .env file
load_dotenv()

# Create clients
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,

    #define the types of diiferent variables in this dynamic typed programming language
    serializer=inngest.PydanticSerializer()
)

# This function is triggered when the 'rag/ingest_pdf' event is fired.
@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    # Step 1: Open the PDF file and cut it into small text paragraphs (chunks)
    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        # Get the file path from the event data that triggered this function
        pdf_path = ctx.event.data["pdf_path"]
        # Use the file path as the source name if no source_id was given
        source_id = ctx.event.data.get("source_id", pdf_path)
        # Read the PDF and split it into chunks
        chunks = load_and_chunk_pdf(pdf_path)
        # Package the chunks + source name into one structured object
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    # Step 2: Convert paragraphs to vectors and save them to Qdrant database
    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        # Convert text paragraphs to vectors
        vecs = embed_texts(chunks)
        # Create a unique ID for each paragraph based on source_id and index
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        # Prepare the text payload to store with the vector
        payload = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]

        # Connect to the Qdrant storage drawer and upload the data
        storage = QdrantStorage()
        storage.upsert(ids, vecs, payload)

        # Return how many chunks were uploaded
        return RAGUpsertResult(ingested=len(chunks))

    # Run the PDF load and chunk step durably
    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    # Run the embedding and database upload step durably (uses RAGUpsertResult validator)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)

    # Convert the pydantic model to a standard dictionary to return it to Inngest
    return ingested.model_dump()


# This function is triggered when the 'rag/query_pdf_ai' event is fired.
# NOTE: it must live at the TOP LEVEL of the file (not inside another function),
# and the decorator needs the '@' symbol, otherwise it never gets registered.
@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf(ctx: inngest.Context):
    # Search step: find the paragraphs in Qdrant that are most similar to the question
    def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        # Turn the question into a vector (same embedding model as ingestion!)
        query_vec = embed_texts([question])[0]
        # Connect to the Qdrant database
        store = QdrantStorage()
        # Ask Qdrant for the top_k most similar paragraphs
        found = store.search(query_vec, top_k)
        # vector_db.search returns the key "context" (singular), so we map it
        # into our RAGSearchResult model which calls it "contexts" (plural)
        return RAGSearchResult(contexts=found["context"], sources=found["sources"])

    # Read the question from the event data that triggered this function
    question = ctx.event.data["question"]
    # How many paragraphs to fetch (default 5 if not provided)
    top_k = int(ctx.event.data.get("top_k", 5))

    # Run the search step durably (checkpointed by Inngest)
    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    # Join all found paragraphs into one bullet-point list of text
    content_block = "\n\n".join(f"- {c}" for c in found.contexts)
    # Build the final prompt: context first, then the question
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{content_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )

    # The adapter tells Inngest which AI provider to call and with which key
    adapter = gemini.Adapter(
        auth_key=os.getenv("GEMINI_API_KEY"),
        model="gemini-3.5-flash",
    )

    # Ask the AI model to generate an answer (this is also a durable step).
    # IMPORTANT: the body must follow GEMINI's request format, not OpenAI's:
    #   - OpenAI uses "messages" -> Gemini uses "contents" with "parts"
    #   - OpenAI uses "max_tokens"/"temperature" at the top level
    #     -> Gemini puts them inside "generationConfig"
    #   - OpenAI's "system" role -> Gemini's separate "systemInstruction" field
    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            # Rules the AI must always follow (like OpenAI's "system" message)
            "systemInstruction": {
                "parts": [{"text": "You answer questions using only the provided context."}]
            },
            # The conversation itself: one user message containing our prompt
            "contents": [
                {"role": "user", "parts": [{"text": user_content}]}
            ],
            # Settings that control the generation behaviour
            "generationConfig": {
                # Maximum length of the answer (in tokens)
                "maxOutputTokens": 1024,
                # Low temperature = more focused, less "creative" answers
                "temperature": 0.2,
            },
        },
    )

    # Gemini's response format: candidates[0].content.parts[0].text
    # (OpenAI would be choices[0].message.content — different providers, different shapes)
    answer = res["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Package the final result using our pydantic model, then convert to a dict
    return RAGQueryResult(
        answer=answer,
        sources=found.sources,
        num_contexts=len(found.contexts),
    ).model_dump()


app = FastAPI()

@app.get("/")
async def root():
    # Default root endpoint to verify the server is running
    return {"message": "api is running doohhhhh <3"}

# Register BOTH functions here — if a function is missing from this list,
# the Inngest dev server will never see it
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf])
