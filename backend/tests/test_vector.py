"""Tests for ChromaDB vector operations."""

import tempfile

import chromadb
import pytest
from chromadb.config import Settings

from app.vector import get_chroma_client


class TestChromaDB:
    """Test ChromaDB operations."""

    @pytest.fixture
    def temp_chroma_dir(self):
        """Create temporary directory for ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_get_chroma_client_loads_existing_collection(self, temp_chroma_dir):
        """Test that get_chroma_client loads existing collection."""
        # Create collection using direct client
        client = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection1 = client.create_collection(name="test_collection")
        collection1.add(
            ids=["id1"],
            embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"test": "data"}],
        )

        # Load existing collection using get_chroma_client
        collection2 = get_chroma_client(
            collection_name="test_collection",
            persist_directory=temp_chroma_dir,
        )

        assert collection2.count() == 1
        assert collection2.name == "test_collection"

    def test_get_chroma_client_reset(self, temp_chroma_dir):
        """Test reset parameter deletes collection."""
        # Create collection using direct client
        client = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection1 = client.create_collection(name="test_collection")
        collection1.add(
            ids=["id1"],
            embeddings=[[0.1, 0.2, 0.3]],
        )

        # Reset collection
        collection2 = get_chroma_client(
            collection_name="test_collection",
            persist_directory=temp_chroma_dir,
            reset=True,
        )

        assert collection2.count() == 0

    def test_add_vectors(self, temp_chroma_dir):
        """Test adding vectors to collection."""
        client = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection = client.create_collection(name="test_collection")

        collection.add(
            ids=["id1", "id2"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            metadatas=[{"label": "A"}, {"label": "B"}],
            documents=["doc1", "doc2"],
        )

        assert collection.count() == 2

    def test_query_vectors(self, temp_chroma_dir):
        """Test querying vectors."""
        client = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection = client.create_collection(name="test_collection")

        collection.add(
            ids=["id1", "id2", "id3"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
            documents=["doc1", "doc2", "doc3"],
        )

        results = collection.query(
            query_embeddings=[[0.15, 0.25, 0.35]],
            n_results=2,
            include=["distances", "documents"],
        )

        assert len(results["ids"][0]) == 2
        assert results["ids"][0][0] == "id1"
        assert results["distances"][0][0] < results["distances"][0][1]

    def test_chroma_persistence_between_clients(self, temp_chroma_dir):
        """Test that data persists between different client instances."""
        # First client
        client1 = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection1 = client1.create_collection(name="test_collection")
        collection1.add(
            ids=["id1"],
            embeddings=[[0.1, 0.2, 0.3]],
            documents=["test doc"],
        )

        # Second client (should load from disk)
        collection2 = get_chroma_client(
            collection_name="test_collection",
            persist_directory=temp_chroma_dir,
        )

        assert collection2.count() == 1
        results = collection2.query(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=1,
        )
        assert results["ids"][0][0] == "id1"

    def test_chroma_collection_operations(self, temp_chroma_dir):
        """Test full collection operations with direct client."""
        client = chromadb.PersistentClient(
            path=temp_chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection = client.create_collection(name="test_collection")

        collection.add(
            ids=["id1", "id2"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            documents=["doc1", "doc2"],
        )
        assert collection.count() == 2

        results = collection.query(
            query_embeddings=[[0.15, 0.25, 0.35]],
            n_results=1,
        )
        assert results["ids"][0][0] == "id1"

        collection.delete(ids=["id1"])
        assert collection.count() == 1

        collection.update(
            ids=["id2"],
            embeddings=[[0.7, 0.8, 0.9]],
        )
        results = collection.query(
            query_embeddings=[[0.7, 0.8, 0.9]],
            n_results=1,
        )
        assert results["ids"][0][0] == "id2"
