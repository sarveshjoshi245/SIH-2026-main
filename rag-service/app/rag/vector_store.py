"""
FAISS Vector Store for the knowledge base.

Builds, saves, and loads a FAISS index from the parsed knowledge documents.
Uses sentence-transformers for local embedding (no API key needed).
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports — these are heavy, only load when needed
_embedder = None
_faiss = None


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


def _get_embedder(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {model_name}")
        _embedder = SentenceTransformer(model_name)
    return _embedder


class VectorStore:
    """
    FAISS-based vector store for knowledge document retrieval.

    Stores document embeddings and metadata. Supports save/load to disk.
    """

    def __init__(self):
        self.index = None
        self.documents: list[dict] = []  # Parallel array: metadata + content for each vector
        self.dimension: int = 0

    def build_index(
        self,
        texts: list[str],
        metadatas: list[dict],
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        """
        Build a FAISS index from texts and their metadata.

        Args:
            texts: List of text strings to embed.
            metadatas: Parallel list of metadata dicts.
            embedding_model: Name of the sentence-transformers model.
        """
        faiss = _get_faiss()
        embedder = _get_embedder(embedding_model)

        logger.info(f"Embedding {len(texts)} documents...")
        embeddings = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        embeddings = embeddings.astype(np.float32)

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)

        # Store metadata + original text for retrieval
        self.documents = [
            {**meta, "text": text}
            for meta, text in zip(metadatas, texts)
        ]

        logger.info(
            f"Built FAISS index: {self.index.ntotal} vectors, "
            f"dimension={self.dimension}"
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Search the index for the most similar documents.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of dicts with keys: text, title, trigger, folder, source_file, score.
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Search called on empty index")
            return []

        embedder = _get_embedder()
        query_vec = embedder.encode([query], convert_to_numpy=True).astype(np.float32)

        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx].copy()
            doc["score"] = float(dist)
            results.append(doc)

        return results

    def save(self, directory: str | Path) -> None:
        """Save index and metadata to disk."""
        faiss = _get_faiss()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        if self.index is not None:
            faiss.write_index(self.index, str(directory / "index.faiss"))

        with open(directory / "documents.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

        with open(directory / "config.json", "w", encoding="utf-8") as f:
            json.dump({"dimension": self.dimension}, f)

        logger.info(f"Saved FAISS index to {directory}")

    def load(self, directory: str | Path) -> bool:
        """
        Load index and metadata from disk.

        Returns True if loaded successfully, False otherwise.
        """
        faiss = _get_faiss()
        directory = Path(directory)

        index_path = directory / "index.faiss"
        docs_path = directory / "documents.json"
        config_path = directory / "config.json"

        if not all(p.exists() for p in [index_path, docs_path, config_path]):
            logger.info(f"No saved index found at {directory}")
            return False

        try:
            self.index = faiss.read_index(str(index_path))

            with open(docs_path, "r", encoding="utf-8") as f:
                self.documents = json.load(f)

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.dimension = config["dimension"]

            logger.info(
                f"Loaded FAISS index from {directory}: "
                f"{self.index.ntotal} vectors, dimension={self.dimension}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load index from {directory}: {e}")
            return False
