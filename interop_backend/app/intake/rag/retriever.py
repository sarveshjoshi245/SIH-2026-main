"""
RAG Retriever — high-level interface for knowledge base retrieval.

Wraps the VectorStore and KnowledgeLoader to provide:
- One-call initialization (load → embed → index)
- Query interface used by the interview engine
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.intake.rag.knowledge_loader import load_knowledge_base, KnowledgeDocument
from app.intake.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """
    RAG retriever for the knowledge base.

    Used by the interview engine to:
    - Decide which questions to ask/skip based on project context
    - Generate "why we're asking this" explanations
    - Provide "why this service was selected" / "why this order" text
    """

    def __init__(self):
        self.store = VectorStore()
        self.documents: list[KnowledgeDocument] = []
        self._initialized = False

    def initialize(
        self,
        knowledge_dir: str | Path,
        index_dir: str | Path,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        force_rebuild: bool = False,
    ) -> None:
        """
        Initialize the retriever: load knowledge, build or load FAISS index.

        Args:
            knowledge_dir: Path to the knowledge/ directory.
            index_dir: Path to save/load the FAISS index.
            embedding_model: Sentence-transformers model name.
            force_rebuild: If True, rebuild even if saved index exists.
        """
        # Load knowledge documents
        self.documents = load_knowledge_base(knowledge_dir)

        if not self.documents:
            logger.warning("No knowledge documents loaded — retriever will return empty results")
            self._initialized = True
            return

        # Try to load existing index
        if not force_rebuild and self.store.load(index_dir):
            # Verify the loaded index matches current documents
            if self.store.index.ntotal == len(self.documents):
                logger.info("Loaded existing FAISS index — document count matches")
                self._initialized = True
                return
            else:
                logger.info(
                    f"Index mismatch ({self.store.index.ntotal} vs {len(self.documents)} docs) "
                    f"— rebuilding"
                )

        # Build new index
        texts = [doc.full_text for doc in self.documents]
        metadatas = [doc.metadata for doc in self.documents]

        self.store.build_index(texts, metadatas, embedding_model)
        self.store.save(index_dir)

        self._initialized = True
        logger.info("Retriever initialized successfully")

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Retrieve the most relevant knowledge documents for a query.

        Args:
            query: Natural language query (e.g., project description, question context).
            top_k: Number of results to return.

        Returns:
            List of dicts with: text, title, trigger, folder, source_file, score.
        """
        if not self._initialized:
            logger.warning("Retriever not initialized — returning empty results")
            return []

        return self.store.search(query, top_k=top_k)

    def retrieve_for_profile_context(self, project_type: str, industry_type: str = "") -> list[dict]:
        """
        Retrieve knowledge relevant to a specific project type/industry.

        Used at interview start to determine which question areas are relevant.
        """
        query = f"{project_type} {industry_type} project service requirements verification"
        return self.retrieve(query, top_k=5)

    def retrieve_question_context(self, field_name: str, project_context: str) -> list[dict]:
        """
        Retrieve knowledge to explain why a specific question is being asked.

        Args:
            field_name: The profile field the question populates (e.g., "land.area_hectare").
            project_context: Brief description of the project so far.
        """
        query = f"{field_name} {project_context} verification requirement"
        return self.retrieve(query, top_k=2)

    def retrieve_service_reason(self, service_name: str) -> list[dict]:
        """
        Retrieve knowledge explaining why a particular service is required.

        Used for generating the reasoning text in the decision output.
        """
        service_map = {
            "LAND_SERVICE": "land ownership verification requirement",
            "ELECTRICITY_SERVICE": "electricity connection verification requirement",
            "POLLUTION_SERVICE": "pollution environment consent verification requirement",
        }
        query = service_map.get(service_name, f"{service_name} verification")
        return self.retrieve(query, top_k=2)

    def retrieve_dependency_reason(self, service: str, depends_on: str) -> str:
        """
        Retrieve a human-readable reason for a dependency edge.

        Falls back to a template string if no relevant doc found.
        """
        query = f"{service} depends on {depends_on} prerequisite requirement"
        results = self.retrieve(query, top_k=1)

        if results and results[0]["folder"] == "dependencies":
            # Found a dedicated dependency doc
            return results[0]["text"][:200]  # Trim to reasonable length

        # Fallback template
        return f"{service} requires completed {depends_on} verification as a prerequisite"

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def document_count(self) -> int:
        return len(self.documents)


# Module-level singleton for use across the app
_retriever_instance: Retriever | None = None


def get_retriever() -> Retriever:
    """Get the module-level retriever singleton."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    return _retriever_instance

