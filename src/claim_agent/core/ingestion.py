"""PDF ingestion — extract, chunk, embed, and store in ChromaDB.

Can be run standalone via ``python -m claim_agent.core.ingestion`` (used by
``make ingest``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
from loguru import logger
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_policy_pdf(
    pdf_path: str,
    chroma_persist_dir: str,
    collection_name: str,
    embedding_model: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> None:
    """Extract text from *pdf_path*, chunk it, embed, and persist to ChromaDB.

    The operation is **idempotent**: if the collection already contains
    documents it will be skipped unless the PDF content has changed.

    Parameters
    ----------
    pdf_path:
        Path to the insurance policy PDF file.
    chroma_persist_dir:
        Directory where ChromaDB persists its data.
    collection_name:
        Name of the ChromaDB collection.
    embedding_model:
        HuggingFace model identifier for ``sentence-transformers``.
    chunk_size:
        Maximum number of characters per chunk.
    chunk_overlap:
        Number of overlapping characters between consecutive chunks.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        logger.error("Policy PDF not found: {path}", path=pdf_path)
        raise FileNotFoundError(f"Policy PDF not found: {pdf_path}")

    # ── Connect to (or create) the ChromaDB persistent client ───────────
    persist_dir = Path(chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(name=collection_name)

    # ── Idempotency check ───────────────────────────────────────────────
    existing_count = collection.count()
    if existing_count > 0:
        logger.info(
            "Collection '{name}' already contains {n} documents — skipping ingestion",
            name=collection_name,
            n=existing_count,
        )
        return

    # ── Extract text from PDF ───────────────────────────────────────────
    logger.info("Extracting text from {path}", path=pdf_path)
    raw_text = _extract_pdf_text(pdf_file)
    if not raw_text.strip():
        logger.warning("PDF appears to contain no extractable text")
        return

    # ── Chunk the text ──────────────────────────────────────────────────
    chunks = _chunk_text(raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    logger.info(
        "Created {n} chunks (size={sz}, overlap={ov})",
        n=len(chunks),
        sz=chunk_size,
        ov=chunk_overlap,
    )

    # ── Embed chunks ────────────────────────────────────────────────────
    logger.info("Loading embedding model: {model}", model=embedding_model)
    model = SentenceTransformer(embedding_model)
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    # ── Store in ChromaDB ───────────────────────────────────────────────
    ids = [_chunk_id(i, chunk) for i, chunk in enumerate(chunks)]
    metadatas = [{"source": str(pdf_file.name), "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info(
        "Ingested {n} chunks into ChromaDB collection '{col}' at {dir}",
        n=len(chunks),
        col=collection_name,
        dir=chroma_persist_dir,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_path: Path) -> str:
    """Read all pages from a PDF and return concatenated text."""
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
            logger.debug("Page {i}: extracted {n} chars", i=i + 1, n=len(text))
    return "\n\n".join(pages)


def _chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split *text* into overlapping chunks of roughly *chunk_size* characters.

    Attempts to break on paragraph boundaries (double newlines) first, then
    falls back to sentence-level or hard character splits.
    """
    # Normalise whitespace within paragraphs but keep paragraph breaks
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph would exceed the chunk size, flush
        candidate = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
        if len(candidate) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            # Start new chunk with overlap from the tail of the previous chunk
            overlap_text = current_chunk[-chunk_overlap:] if chunk_overlap else ""
            current_chunk = f"{overlap_text} {para}".strip() if overlap_text else para
        else:
            current_chunk = candidate

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Handle any chunks that are still too long (single giant paragraphs)
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # Hard-split long chunks
            for start in range(0, len(chunk), chunk_size - chunk_overlap):
                end = min(start + chunk_size, len(chunk))
                final_chunks.append(chunk[start:end])
                if end == len(chunk):
                    break

    return final_chunks


def _chunk_id(index: int, text: str) -> str:
    """Deterministic chunk ID based on index + content hash."""
    content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"chunk-{index:04d}-{content_hash}"


# ---------------------------------------------------------------------------
# CLI entry point (``python -m claim_agent.core.ingestion``)
# ---------------------------------------------------------------------------


def _cli() -> None:
    """Standalone ingestion script — reads Hydra config and ingests the PDF."""
    import hydra
    from omegaconf import DictConfig

    @hydra.main(version_base=None, config_path="../../../conf", config_name="config")
    def _main(cfg: DictConfig) -> None:
        from claim_agent.logging.setup import setup_logging

        setup_logging(cfg.logging)
        ingest_policy_pdf(
            pdf_path=cfg.data.policy_pdf,
            chroma_persist_dir=cfg.data.chroma_persist_dir,
            collection_name=cfg.vectordb.collection_name,
            embedding_model=cfg.vectordb.embedding_model,
            chunk_size=cfg.vectordb.chunk_size,
            chunk_overlap=cfg.vectordb.chunk_overlap,
        )

    _main()


if __name__ == "__main__":
    _cli()
