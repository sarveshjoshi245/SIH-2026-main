"""
Knowledge Base Loader.

Parses the existing .md knowledge files (§6), extracts metadata (TITLE, TRIGGER, CONTENT),
and prepares them for embedding and indexing.
"""

from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """A single parsed knowledge base document."""
    title: str
    trigger: str
    content: str
    source_file: str
    folder: str  # e.g. "land", "electricity", "pollution", "dependencies"

    @property
    def full_text(self) -> str:
        """Combined text for embedding — includes title and content."""
        return f"{self.title}\n{self.content}"

    @property
    def metadata(self) -> dict:
        """Metadata dict for storage alongside the vector."""
        return {
            "title": self.title,
            "trigger": self.trigger,
            "source_file": self.source_file,
            "folder": self.folder,
        }


def parse_knowledge_file(file_path: str | Path) -> KnowledgeDocument | None:
    """
    Parse a single knowledge .md file.

    Expected format:
    ---
    TITLE: <title>
    TRIGGER: <trigger condition>
    CONTENT:
    <body text>
    ---

    Returns None if the file can't be parsed.
    """
    file_path = Path(file_path)

    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not read {file_path}: {e}")
        return None

    # Extract frontmatter between --- markers
    # The format uses --- as delimiters with TITLE:, TRIGGER:, CONTENT: fields
    title_match = re.search(r"TITLE:\s*(.+)", raw)
    trigger_match = re.search(r"TRIGGER:\s*(.+)", raw)
    content_match = re.search(r"CONTENT:\s*\n?([\s\S]*?)(?:\n---|\Z)", raw)

    if not title_match or not trigger_match or not content_match:
        logger.warning(f"Could not parse knowledge file {file_path} — missing fields")
        return None

    title = title_match.group(1).strip()
    trigger = trigger_match.group(1).strip()
    content = content_match.group(1).strip()

    # Determine folder from path
    folder = file_path.parent.name

    return KnowledgeDocument(
        title=title,
        trigger=trigger,
        content=content,
        source_file=str(file_path),
        folder=folder,
    )


def load_knowledge_base(knowledge_dir: str | Path) -> list[KnowledgeDocument]:
    """
    Load all knowledge documents from the knowledge directory.

    Scans all subdirectories for .md files and parses them.

    Args:
        knowledge_dir: Path to the knowledge/ directory.

    Returns:
        List of parsed KnowledgeDocument objects.
    """
    knowledge_dir = Path(knowledge_dir)
    documents: list[KnowledgeDocument] = []

    if not knowledge_dir.exists():
        logger.error(f"Knowledge directory not found: {knowledge_dir}")
        return documents

    # Recursively find all .md files
    for md_file in sorted(knowledge_dir.rglob("*.md")):
        doc = parse_knowledge_file(md_file)
        if doc is not None:
            documents.append(doc)
            logger.info(f"Loaded: [{doc.folder}] {doc.title}")
        else:
            logger.warning(f"Skipped unparseable file: {md_file}")

    logger.info(f"Loaded {len(documents)} knowledge documents from {knowledge_dir}")
    return documents
