import os
import chromadb
from chromadb.config import Settings
from Jarvis.config import ALLOWED_ROOT

# Store vector DB inside the sandbox
DB_PATH = os.path.join(ALLOWED_ROOT, "vector_memory")

client = chromadb.Client(
    Settings(
        persist_directory=DB_PATH,
        anonymized_telemetry=False
    )
)

collection = client.get_or_create_collection(name="jarvis_memory")


def store_memory(text: str, metadata: dict):
    """
    Store a piece of text as long-term memory.
    """
    memory_id = str(hash(text))

    collection.add(
        documents=[text],
        metadatas=[metadata],
        ids=[memory_id]
    )
    # No persist() needed in new ChromaDB


def query_memory(query: str, limit: int = 3):
    """
    Retrieve semantically similar memories.
    """
    return collection.query(
        query_texts=[query],
        n_results=limit
    )

