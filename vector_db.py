# Import Qdrant database tools
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# Create a class/blueprint to handle Qdrant database storage
class QdrantStorage:
    # Setup connection to Qdrant and make sure a drawer (collection) exists
    def __init__(self, url="http://localhost:6333", collection="docs", dim=3072):
        # Connect to the Qdrant database server
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        
        # Create a new collection if it does not already exist
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    # Insert or update data points in the database
    def upsert(self, ids, vectors, payloads):
        # Package the data (IDs, number vectors, and texts) into Qdrant "Points"
        points = [PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i]) for i in range(len(ids))]
        # Upload the structured points to the database collection
        self.client.upsert(self.collection, points=points)

    # Search for similar paragraphs using a query vector list
    def search(self, query_vector, top_k: int =5):
        # Ask Qdrant to find the top matching items.
        # NOTE: the old client.search() was removed in qdrant-client 1.16+,
        # query_points() is the new way. It also renames the argument
        # "query_vector" -> "query", and wraps the matches in a response
        # object, so we grab the ".points" list off it.
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k
        ).points

        context = []
        sources = set()

        # Loop through search matches and extract the text and file sources
        for r in results:
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")

            if text:
               context.append(text)
               sources.add(source)

        # Return a dictionary containing the matching texts and their file paths
        return {"context": context, "sources": list(sources)}
        

    