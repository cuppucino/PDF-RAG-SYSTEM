# Vector Database & OOP Basics: Interview Guide

This guide explains Object-Oriented Programming (OOP) concepts in Python (such as `class`, `self`, and `__init__`) and breaks down how Qdrant works line by line, including the concept of "upserting."

---

## 1. Python OOP Concepts (Classes & Instances)

To understand `vector_db.py`, we first need to understand Classes:
*   **`class QdrantStorage:`**: A class is like a blueprint or a recipe. It defines variables (data) and functions (actions) that belong to a specific object.
*   **`def __init__(self, ...):`**: This is the **Constructor** (or initializer). It is the setup function that runs automatically the exact moment you create a new instance of the class (e.g., `db = QdrantStorage()`).
*   **`self`**: In Python, `self` represents the specific object created from the blueprint.
    *   If you write `self.client = ...`, you are saying: *"Attach the `client` variable to this specific instance so other functions inside the class can access it."*
    *   Think of it like saying: *"My client is..."* instead of just a temporary local variable.

---

## 2. Line-by-Line Code Explanation

Here is the line-by-line breakdown of `vector_db.py`:

*   **Line 1**: `from qdrant_client import QdrantClient` — Imports the library to talk to Qdrant (the database).
*   **Line 2**: `from qdrant_client.models import ...` — Imports helpers: `VectorParams` (settings for vectors), `Distance` (how to calculate similarity), and `PointStruct` (the package of data to store).
*   **Line 5**: `class QdrantStorage:` — Starts the blueprint.
*   **Line 6**: `def __init__(self, url="...", collection="docs", dim=3072):` — The setup function.
    *   `url`: Where the database is running (defaults to localhost).
    *   `collection`: The name of the table or folder inside the database (defaults to `"docs"`).
    *   `dim`: The size of the vector embedding list (e.g., OpenAI's standard is `3072`).
*   **Line 7**: `self.client = QdrantClient(...)` — Starts the database connector client.
*   **Line 8**: `self.collection = collection` — Saves the collection name to `self` so other functions can use it.
*   **Line 9-13**: Checks if the collection directory already exists. If not, tells Qdrant to create it using **Cosine Distance** (a method to measure how similar two vectors are).
*   **Line 15**: `def upsert(self, ids, vectors, payloads):` — The update/insert function.
*   **Line 16**: `points = [PointStruct(...) for i in range(len(ids))]` — Converts lists of IDs, vector numbers, and payloads into structured points that Qdrant expects.
*   **Line 17**: `self.client.upsert(self.collection, points=points)` — Sends the points to Qdrant.
*   **Line 20**: `def search(self, query_vector, top_k=5):` — Queries the database using a vector representing the user's search text, asking for the `top_k` (usually 5) most similar items.
*   **Line 28-29**: Initializes empty collections: a list for matching texts (`context`) and a unique set for references (`sources`).
*   **Line 31-38**: Loops through search results, extracts the text and source filepath, and saves them.
*   **Line 39**: Returns the results as a dictionary: `{"context": [...], "sources": [...]}`.

---

## 3. What is an Upsert?

**Upsert** is a combination of **Update** and **Insert**:
*   If a record with the given ID **does not exist**, the database **inserts** a new record.
*   If a record with the given ID **already exists**, the database **updates** it with the new data.
*   This prevents duplicate entries in your database when you re-upload or re-process files.

---

## 4. Example Scenario: Storing & Searching Sentences

Below is a complete, runnable example using `QdrantStorage` to store and query text, complete with robust error handling and unit tests.

### Implementation

```python
import logging
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# Setup logs
app_logger = logging.getLogger("uvicorn.error")

class QdrantStorage:
    def __init__(self, url: str = "http://localhost:6333", collection: str = "docs", dim: int = 3) -> None:
        """Initializes the Qdrant database connection."""
        try:
            self.client = QdrantClient(url=url, timeout=30)
            self.collection = collection
            # Automatically create the collection if missing
            if not self.client.collection_exists(self.collection):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
                )
        except Exception as error:
            app_logger.error(f"Failed to connect to Qdrant: {str(error)}")
            raise error

    def upsert(self, ids: List[int], vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        """Inserts or updates points in the database."""
        try:
            if not (len(ids) == len(vectors) == len(payloads)):
                raise ValueError("Input lists must all have the same length.")
                
            points = [
                PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) 
                for i in range(len(ids))
            ]
            self.client.upsert(self.collection, points=points)
        except Exception as error:
            app_logger.error(f"Upsert failed: {str(error)}")
            raise error

    def search(self, query_vector: List[float], top_k: int = 5) -> Dict[str, Any]:
        """Searches the database for similar vectors."""
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                with_payload=True,
                limit=top_k
            )
            
            context = []
            sources = set()
            
            for r in results:
                payload = getattr(r, "payload", None) or {}
                text = payload.get("text", "")
                source = payload.get("source", "")
                
                if text:
                    context.append(text)
                if source:
                    sources.add(source)
                    
            return {"context": context, "sources": list(sources)}
        except Exception as error:
            app_logger.error(f"Search failed: {str(error)}")
            raise error
```

### Unit Tests

```python
import pytest
from qdrant_client import QdrantClient

# Define a test collection name
TEST_COLLECTION = "test_docs"

@pytest.fixture
def storage_instance() -> QdrantStorage:
    """Fixture to provide a clean test storage instance connected to local Qdrant."""
    # Connecting to local Qdrant memory/dev server instance
    storage = QdrantStorage(url="http://localhost:6333", collection=TEST_COLLECTION, dim=3)
    yield storage
    # Cleanup after tests
    try:
        storage.client.delete_collection(TEST_COLLECTION)
    except Exception:
        pass

def test_qdrant_storage_upsert_and_search(storage_instance: QdrantStorage) -> None:
    """Verifies that items can be upserted and retrieved by vector search."""
    ids = [1, 2]
    vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0]
    ]
    payloads = [
        {"text": "Apple pie recipe", "source": "cooking.pdf"},
        {"text": "Rocket science tutorial", "source": "physics.pdf"}
    ]
    
    # Run upsert
    storage_instance.upsert(ids, vectors, payloads)
    
    # Search for something very close to "Apple pie" (first vector)
    search_result = storage_instance.search(query_vector=[0.9, 0.1, 0.0], top_k=1)
    
    assert len(search_result["context"]) == 1
    assert search_result["context"][0] == "Apple pie recipe"
    assert search_result["sources"] == ["cooking.pdf"]

def test_qdrant_storage_invalid_input(storage_instance: QdrantStorage) -> None:
    """Verifies that mismatching inputs raise a ValueError."""
    with pytest.raises(ValueError):
        storage_instance.upsert(
            ids=[1],
            vectors=[[1.0, 0.0, 0.0]],
            payloads=[]  # Length mismatch
        )
```
