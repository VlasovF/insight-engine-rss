"""ChromaDB client wrapper."""

import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from structlog import get_logger

logger = get_logger(__name__)


def get_chroma_client(
    collection_name: str = "events",
    persist_directory: Optional[str] = None,
    reset: bool = False,
) -> Collection:
    """
    Get or create a ChromaDB collection.

    Args:
        collection_name: Name of the collection.
        persist_directory: Directory for persistent storage.
        reset: If True, delete existing collection.

    Returns:
        ChromaDB collection instance.

    """
    if persist_directory is None:
        persist_directory = os.getenv("CHROMA_PATH", "./chroma_data")

    # Ensure directory exists
    path = Path(persist_directory)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    # Initialize client
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )

    # Reset collection if requested
    if reset:
        try:
            client.delete_collection(collection_name)
            logger.info("collection_deleted", collection=collection_name)
        except ValueError:
            pass

    # Check if collection exists using list_collections()
    collections = client.list_collections()
    collection_names = [c.name for c in collections]

    if collection_name in collection_names:
        collection = client.get_collection(collection_name)
        logger.info(
            "collection_loaded", collection=collection_name, count=collection.count()
        )
    else:
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("collection_created", collection=collection_name)

    return collection


def reset_collection(collection_name: str = "events") -> int:
    """
    Reset collection and return count of deleted items.

    Args:
        collection_name: Name of the collection to reset.

    Returns:
        Number of items deleted.

    """
    persist_directory = os.getenv("CHROMA_PATH", "./chroma_data")
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )

    # Check if collection exists using list_collections()
    collections = client.list_collections()
    collection_names = [c.name for c in collections]

    if collection_name not in collection_names:
        logger.info("collection_not_found", collection=collection_name)
        return 0

    collection = client.get_collection(collection_name)
    count = collection.count()

    client.delete_collection(collection_name)
    logger.info("collection_reset", collection=collection_name, deleted_count=count)

    return count
