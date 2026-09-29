"""
Interview Session State Management.

In-memory session store tracking conversation state, partial profile,
question history, and interview status per session_id.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field as dc_field

from app.intake.models import ProjectProfile, InterviewState, DecisionResult

logger = logging.getLogger(__name__)


@dataclass
class InterviewSession:
    """State for a single interview session."""
    session_id: str
    profile: ProjectProfile = dc_field(default_factory=ProjectProfile)
    state: InterviewState = InterviewState.IN_PROGRESS
    answered_question_ids: set[str] = dc_field(default_factory=set)
    skipped_question_ids: set[str] = dc_field(default_factory=set)
    conversation_history: list[dict] = dc_field(default_factory=list)
    decision_result: DecisionResult | None = None
    created_at: float = dc_field(default_factory=time.time)
    updated_at: float = dc_field(default_factory=time.time)
    error_count: int = 0  # Track LLM/RAG failures for fallback logic

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self.updated_at = time.time()

    def mark_question_answered(self, question_id: str) -> None:
        """Mark a question as answered."""
        self.answered_question_ids.add(question_id)
        self.updated_at = time.time()

    def mark_question_skipped(self, question_id: str) -> None:
        """Mark a question as skipped (not applicable)."""
        self.skipped_question_ids.add(question_id)
        self.updated_at = time.time()

    def mark_complete(self, decision: DecisionResult) -> None:
        """Mark the interview as complete with decision results."""
        self.state = InterviewState.COMPLETE
        self.decision_result = decision
        self.updated_at = time.time()

    @property
    def is_complete(self) -> bool:
        return self.state == InterviewState.COMPLETE


class SessionStore:
    """
    In-memory session store.

    For a hackathon demo, in-memory is fine. Production would use Redis or similar.
    """

    def __init__(self):
        self._sessions: dict[str, InterviewSession] = {}

    def get_or_create(self, session_id: str) -> tuple[InterviewSession, bool]:
        """
        Get an existing session or create a new one.

        Returns (session, is_new).
        """
        if session_id in self._sessions:
            return self._sessions[session_id], False

        session = InterviewSession(session_id=session_id)
        self._sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        return session, True

    def get(self, session_id: str) -> InterviewSession | None:
        """Get an existing session, or None."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    @property
    def active_count(self) -> int:
        return len(self._sessions)


# Module-level singleton
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the module-level session store singleton."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store

