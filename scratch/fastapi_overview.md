# FastAPI: Overview & Interview Guide

FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.

---

## Core Technical Concepts

1. **High Performance**: Underpinned by **Starlette** (for web routing/events) and **Pydantic** (for data serialization and validation). It matches NodeJS and Go speeds using Python's asynchronous ecosystem (`async`/`await`).
2. **Asynchronous by Design**: Built on top of ASGI (Asynchronous Server Gateway Interface), enabling concurrent request handling via an event loop without blocking the main execution thread.
3. **Automatic Documentation**: Generates interactive OpenAPI (Swagger UI) and ReDoc documentation out-of-the-box using the metadata from type hints and Pydantic schemas.
4. **Data Validation & Serialization**: Uses Pydantic to enforce type safety, automatically validate request payloads, and serialize Python objects to JSON.

---

## Example Scenario: PDF Metadata Extractor (for PDF-RAG)

Imagine a scenario in a PDF-RAG system where a frontend client needs to upload a PDF file and extract its basic metadata (e.g., number of pages, title, author) to catalog it in a database.

### 1. Implementation Code

Below is a robust FastAPI application implementing this endpoint, with built-in error handling and strict type checking.

```python
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="PDF Metadata Extractor API",
    description="Extracts metadata from PDF files for RAG ingestion.",
    version="1.0.0",
)

class MetadataResponse(BaseModel):
    """Pydantic model representing the structured JSON output."""
    file_name: str = Field(..., description="The name of the uploaded PDF file.")
    file_size_bytes: int = Field(..., description="Size of the file in bytes.")
    mime_type: str = Field("application/pdf", description="Expected MIME type of the file.")
    simulated_pages: int = Field(..., ge=1, description="Simulated count of PDF pages.")

def extract_pdf_details(file_content: bytes, file_name: str) -> Dict[str, Any]:
    """Helper logic to process the raw PDF bytes and extract metadata.
    
    Uses snake_case for all parameters and variables in compliance with project style.
    """
    try:
        # Robust check to ensure the file looks like a PDF signature
        if not file_content.startswith(b"%PDF"):
            raise ValueError("Invalid PDF header signature.")
            
        file_size = len(file_content)
        # Mocking page calculation (in a real app, use PyPDF2 or pdfplumber)
        simulated_pages = max(1, file_size // 100000)
        
        return {
            "file_name": file_name,
            "file_size_bytes": file_size,
            "mime_type": "application/pdf",
            "simulated_pages": simulated_pages,
        }
    except Exception as error:
        # Centralized internal handling and error propagation
        raise ValueError(f"Failed to parse PDF binary data: {str(error)}")

@app.post(
    "/extract-metadata",
    response_model=MetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a PDF and extract metadata",
)
async def upload_pdf_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Asynchronous endpoint that receives a PDF and returns extracted metadata."""
    # Ensure it's a PDF based on content-type header
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are allowed.",
        )
        
    try:
        file_bytes = await file.read()
        extracted_info = extract_pdf_details(
            file_content=file_bytes, 
            file_name=file.filename or "unknown.pdf"
        )
        return extracted_info
    except ValueError as validation_error:
        # Catch value/parsing errors and return a clean HTTP 422 Unprocessable Entity
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(validation_error),
        )
    except Exception as unexpected_error:
        # Fallback error handling for security and resilience
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {str(unexpected_error)}",
        )
```

### 2. Unit Tests

Here are the accompanying unit tests to verify both successful and error flows using FastAPI's `TestClient`.

```python
import io
from fastapi.testclient import TestClient

# Initialize the TestClient with the app instance
client = TestClient(app)

def test_extract_metadata_success() -> None:
    """Verifies that a valid PDF upload yields correct metadata and a 200 OK status."""
    # Mock valid PDF bytes starting with '%PDF' signature
    pdf_content = b"%PDF-1.4 mock content here..."
    file_payload = {
        "file": ("sample.pdf", io.BytesIO(pdf_content), "application/pdf")
    }
    
    response = client.post("/extract-metadata", files=file_payload)
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["file_name"] == "sample.pdf"
    assert json_data["file_size_bytes"] > 0
    assert json_data["mime_type"] == "application/pdf"
    assert json_data["simulated_pages"] >= 1

def test_extract_metadata_invalid_mime() -> None:
    """Verifies that uploading a non-PDF mime type raises a 400 Bad Request."""
    text_content = b"Some plain text content."
    file_payload = {
        "file": ("notes.txt", io.BytesIO(text_content), "text/plain")
    }
    
    response = client.post("/extract-metadata", files=file_payload)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid file format. Only PDF files are allowed."

def test_extract_metadata_corrupt_pdf() -> None:
    """Verifies that uploading a file with application/pdf mime type but invalid bytes raises 422."""
    corrupt_bytes = b"NOT_A_PDF_HEADER"
    file_payload = {
        "file": ("corrupt.pdf", io.BytesIO(corrupt_bytes), "application/pdf")
    }
    
    response = client.post("/extract-metadata", files=file_payload)
    
    assert response.status_code == 422
    assert "Invalid PDF header signature" in response.json()["detail"]
```
