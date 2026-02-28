"""Tests for ChromaDB policy-text retrieval.

Uses an in-memory/temporary ChromaDB collection with small test documents.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest
from sentence_transformers import SentenceTransformer

from claim_agent.core.retrieval import retrieve_policy_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_DOCS = [
    "Section 4: Collision coverage applies to direct physical damage to the insured vehicle.",
    "The standard deductible for collision claims is $500 per incident.",
    "Comprehensive coverage includes damage from natural disasters, theft, and vandalism.",
    "Section 7: Liability coverage protects against third-party bodily injury claims.",
    "Premium payments are due on the first of each month during the coverage period.",
]

_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_COLLECTION_NAME = "test_policy_chunks"


@pytest.fixture()
def chroma_dir(tmp_path: Path) -> str:
    """Create a small ChromaDB collection with sample docs and return the persist dir."""
    persist_dir = str(tmp_path / "chroma_test")
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name=_COLLECTION_NAME)

    model = SentenceTransformer(_EMBEDDING_MODEL)
    embeddings = model.encode(_SAMPLE_DOCS).tolist()

    collection.add(
        ids=[f"doc-{i}" for i in range(len(_SAMPLE_DOCS))],
        documents=_SAMPLE_DOCS,
        embeddings=embeddings,
    )
    return persist_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRetrieval:
    """Test suite for :func:`retrieve_policy_text`."""

    def test_returns_relevant_chunks(self, chroma_dir: str) -> None:
        """Collision-related queries should retrieve collision-related docs."""
        results = retrieve_policy_text(
            queries=["collision damage deductible"],
            chroma_persist_dir=chroma_dir,
            collection_name=_COLLECTION_NAME,
            embedding_model=_EMBEDDING_MODEL,
            n_results=3,
        )
        assert len(results) >= 1
        # At least one result should mention collision or deductible
        combined = " ".join(results).lower()
        assert "collision" in combined or "deductible" in combined

    def test_deduplicates_results(self, chroma_dir: str) -> None:
        """Multiple queries hitting the same doc should not produce duplicates."""
        results = retrieve_policy_text(
            queries=["collision coverage", "collision damage"],
            chroma_persist_dir=chroma_dir,
            collection_name=_COLLECTION_NAME,
            embedding_model=_EMBEDDING_MODEL,
            n_results=5,
        )
        assert len(results) == len(set(results))

    def test_missing_persist_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            retrieve_policy_text(
                queries=["test"],
                chroma_persist_dir=str(tmp_path / "nonexistent"),
                collection_name=_COLLECTION_NAME,
                embedding_model=_EMBEDDING_MODEL,
            )

    def test_missing_collection_raises(self, tmp_path: Path) -> None:
        # Create the directory but no collection
        persist_dir = str(tmp_path / "empty_chroma")
        Path(persist_dir).mkdir()
        chromadb.PersistentClient(path=persist_dir)  # init without any collection

        with pytest.raises(FileNotFoundError, match="not found"):
            retrieve_policy_text(
                queries=["test"],
                chroma_persist_dir=persist_dir,
                collection_name="nonexistent_collection",
                embedding_model=_EMBEDDING_MODEL,
            )

    def test_multiple_queries(self, chroma_dir: str) -> None:
        """Multiple diverse queries should return a union of relevant results."""
        results = retrieve_policy_text(
            queries=["liability bodily injury", "premium payment schedule"],
            chroma_persist_dir=chroma_dir,
            collection_name=_COLLECTION_NAME,
            embedding_model=_EMBEDDING_MODEL,
            n_results=2,
        )
        assert len(results) >= 2

    def test_n_results_capped_by_doc_count(self, chroma_dir: str) -> None:
        """Requesting more results than docs should not error."""
        results = retrieve_policy_text(
            queries=["insurance"],
            chroma_persist_dir=chroma_dir,
            collection_name=_COLLECTION_NAME,
            embedding_model=_EMBEDDING_MODEL,
            n_results=100,  # way more than the 5 sample docs
        )
        assert len(results) <= len(_SAMPLE_DOCS)
