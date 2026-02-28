"""Policy text retrieval via ChromaDB semantic similarity search."""

from __future__ import annotations

from pathlib import Path

import chromadb
from loguru import logger
from sentence_transformers import SentenceTransformer


def retrieve_policy_text(
    queries: list[str],
    chroma_persist_dir: str,
    collection_name: str,
    embedding_model: str,
    n_results: int = 5,
) -> list[str]:
    """Embed *queries* and retrieve the most relevant policy text chunks.

    Parameters
    ----------
    queries:
        Search queries generated from the claim (typically 3–5).
    chroma_persist_dir:
        Directory where ChromaDB data is persisted.
    collection_name:
        Name of the ChromaDB collection to query.
    embedding_model:
        HuggingFace model identifier for ``sentence-transformers``.
    n_results:
        Maximum number of results to return **per query**.

    Returns
    -------
    list[str]
        Deduplicated list of the most relevant policy text chunks.
    """
    persist_dir = Path(chroma_persist_dir)
    if not persist_dir.exists():
        msg = (
            f"ChromaDB persist directory not found: {chroma_persist_dir}. Run 'make ingest' first."
        )
        logger.error(msg)
        raise FileNotFoundError(msg)

    client = chromadb.PersistentClient(path=str(persist_dir))

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        msg = (
            f"Collection '{collection_name}' not found in ChromaDB. "
            "Run 'make ingest' first to populate the vector store."
        )
        logger.error(msg)
        raise FileNotFoundError(msg)

    doc_count = collection.count()
    if doc_count == 0:
        logger.warning(
            "Collection '{name}' is empty — no policy text available", name=collection_name
        )
        return []

    logger.info(
        "Querying collection '{name}' ({n} docs) with {q} queries",
        name=collection_name,
        n=doc_count,
        q=len(queries),
    )

    # ── Embed queries ───────────────────────────────────────────────────
    model = SentenceTransformer(embedding_model)
    query_embeddings = model.encode(queries).tolist()

    # ── Retrieve from ChromaDB ──────────────────────────────────────────
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=min(n_results, doc_count),
        include=["documents", "distances"],
    )

    # ── Deduplicate and collect chunks ──────────────────────────────────
    seen: set[str] = set()
    chunks: list[str] = []

    documents_lists: list[list[str]] = results.get("documents", [])  # type: ignore[assignment]
    distances_lists: list[list[float]] = results.get("distances", [])  # type: ignore[assignment]

    for query_idx, (docs, dists) in enumerate(zip(documents_lists, distances_lists)):
        for doc, dist in zip(docs, dists):
            if doc not in seen:
                seen.add(doc)
                chunks.append(doc)
                logger.debug(
                    "Query {qi} | distance={dist:.4f} | chunk preview: {preview}",
                    qi=query_idx,
                    dist=dist,
                    preview=doc[:120].replace("\n", " "),
                )

    logger.info(
        "Retrieved {n} unique policy chunks from {q} queries",
        n=len(chunks),
        q=len(queries),
    )
    return chunks
