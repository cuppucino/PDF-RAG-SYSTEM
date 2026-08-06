# Import tools needed for Gemini, reading PDFs, and splitting text
from google import genai
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

# Load settings and passwords from the .env file
load_dotenv()

# Initialize the gemini connection
client = genai.Client()
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072
# Gemini-embedding-001 uses 3072 dimensions by default

# Setup a text splitter: cuts text into chunks of 1000 letters, with 200 letters overlap
splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

# Function to read a PDF file and cut it into smaller paragraphs (chunks)
def load_and_chunk_pdf(path: str):
    # Read the PDF file
    docs = PDFReader().load_data(file=path)
    # Get the raw text from each page
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    # Cut every page's text into smaller paragraphs
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

# Function to convert a list of text paragraphs into list of vector numbers
def embed_texts(texts: list[str]) -> list[list[float]]:
    # Handle empty lists safely to prevent API errors
    if not texts:
        return []
    # Send paragraphs to Gemini API
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    # Extract and return the number vectors from Gemini's response
    return [item.values for item in response.embeddings]
