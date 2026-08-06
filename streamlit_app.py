# Path gives us a clean way to work with file/folder paths
from pathlib import Path
# time is used for small pauses and for the polling timeout clock
import time

# The Streamlit library — every "st.something" call renders a widget in the browser
import streamlit as st
import inngest
# Loads our .env file so environment variables are available
from dotenv import load_dotenv
import os
# requests lets us make plain HTTP calls (used to poll the Inngest API)
import requests

# Read the .env file into environment variables
load_dotenv()

# Configure the browser tab: title, icon, and page width
st.set_page_config(page_title="RAG Ingest PDF", page_icon="📄", layout="centered")


# @st.cache_resource = build this object ONCE and reuse it.
# Important because Streamlit re-runs this whole script on EVERY user
# interaction — without caching we'd create a new client on every click.
@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    # Same app_id as main.py so events go to the same Inngest app
    return inngest.Inngest(app_id="rag_app", is_production=False)


# Save the browser-uploaded PDF onto local disk so the backend can read it
def save_uploaded_pdf(file) -> Path:
    # Make sure an "uploads" folder exists (create it if missing)
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    # Build the full path: uploads/<original filename>
    file_path = uploads_dir / file.name
    # Get the raw bytes of the uploaded file and write them to disk
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path


# Fire the "rag/ingest_pdf" event — this wakes up rag_ingest_pdf() in main.py.
# Note: the frontend never calls the backend directly, it only sends events.
# We use send_sync() (not async send + asyncio.run) because Streamlit re-runs
# this script constantly: asyncio.run() destroys its event loop when done, but
# our CACHED client would keep connections tied to that dead loop — causing
# "RuntimeError: Event loop is closed" on the next interaction.
def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    client.send_sync(
        inngest.Event(
            name="rag/ingest_pdf",
            # This data dict becomes ctx.event.data on the backend side
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


# ---------- UI section 1: PDF upload ----------

# Big heading on the page
st.title("Upload a PDF to Ingest")
# File picker widget — returns None until the user actually uploads something
uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)

# Streamlit has no "on upload" event — instead the script re-runs after the
# upload, and this if-check acts as our upload handler
if uploaded is not None:
    # Show a spinner while the work inside this block runs
    with st.spinner("Uploading and triggering ingestion..."):
        # Save the file locally so the backend worker can open it
        path = save_uploaded_pdf(uploaded)
        # Kick off the event (plain function call now — no asyncio needed)
        send_rag_ingest_event(path)
        # Small pause for user feedback continuity
        time.sleep(0.3)
    # Green success box + a small grey caption
    st.success(f"Triggered ingestion for: {path.name}")
    st.caption("You can upload another PDF if you like.")

# Horizontal divider line between the two sections
st.divider()

# ---------- UI section 2: Ask a question ----------

st.title("Ask a question about your PDFs")


# Fire the "rag/query_pdf_ai" event — this wakes up rag_query_pdf() in main.py.
# send_sync() returns the IDs of the events it created; we keep the first
# one so we can look up the run that this event triggered.
def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = client.send_sync(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    # result is a list of event IDs (one per event sent) — grab the first
    return result[0]


# The base URL of the local Inngest dev server's REST API
def _inngest_api_base() -> str:
    # Local dev server default; configurable via env
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


# Ask the Inngest API: "which function runs did this event trigger?"
def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    # Raise an error if the HTTP request failed (e.g. dev server not running)
    resp.raise_for_status()
    data = resp.json()
    # The list of runs lives under the "data" key ([] if none yet)
    return data.get("data", [])


# Poll (repeatedly check) the run status until it finishes, then return its
# output. Needed because the backend works in the background — the answer
# isn't ready immediately, so we check every 0.5s until it is.
def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    # Remember when we started so we can time out
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            # Finished successfully -> return the function's return value
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            # Finished but failed -> stop waiting and raise an error
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        # Give up if we've been waiting longer than the timeout
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        # Sleep briefly before checking again (avoids hammering the API)
        time.sleep(poll_interval_s)


# st.form groups widgets so the script only re-runs when Submit is pressed,
# not on every keystroke in the text box
with st.form("rag_query_form"):
    # Text box for the question
    question = st.text_input("Your question")
    # Number picker for how many paragraphs to retrieve from Qdrant
    top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
    # The submit button — True only on the re-run where it was clicked
    submitted = st.form_submit_button("Ask")

    # Only proceed if the button was clicked AND the question isn't blank
    if submitted and question.strip():
        with st.spinner("Sending event and generating answer..."):
            # Fire-and-forget event to Inngest for observability/workflow
            event_id = send_rag_query_event(question.strip(), int(top_k))
            # Poll the local Inngest API for the run's output
            output = wait_for_run_output(event_id)
            # output is the dict rag_query_pdf() returned (RAGQueryResult)
            answer = output.get("answer", "")
            sources = output.get("sources", [])

        # Display the answer and, if present, the list of source files
        st.subheader("Answer")
        st.write(answer or "(No answer)")
        if sources:
            st.caption("Sources")
            for s in sources:
                st.write(f"- {s}")
