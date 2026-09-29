"""
Interview Engine — orchestrates the conversational intake flow.

Connects RAG retrieval, question selection, profile building,
and decision engine into the end-to-end interview experience.
Handles graceful degradation when LLM/RAG fails (§9).
"""

from __future__ import annotations

import logging
from typing import Optional

from app.models import (
    ProjectProfile, ProjectType, IndustryType, LandOwnership,
    InterviewQuestion, QuestionOption, InterviewState,
    DecisionResult, ExecutionStep,
)
from app.interview.questions import (
    QuestionDef, QUESTION_BANK, get_next_question,
    should_skip_question, get_question_by_id, get_fallback_question_ids,
)
from app.interview.session import InterviewSession, get_session_store
from app.decision_engine import decide_required_services
from app.dependency_resolver import resolve_execution_order

logger = logging.getLogger(__name__)

# Attempt to import RAG retriever — may not be available if deps aren't installed
_retriever = None

def _get_retriever():
    """Lazy-load the retriever singleton."""
    global _retriever
    if _retriever is None:
        try:
            from app.rag.retriever import get_retriever
            _retriever = get_retriever()
        except Exception as e:
            logger.warning(f"Could not load RAG retriever: {e}")
    return _retriever


GREETING_MESSAGE = (
    "Welcome! I'll help determine which department verifications your "
    "industrial project needs. I'll ask you a few questions about your project, "
    "and then recommend the required services and their verification order.\n\n"
    "Let's get started!"
)


def process_message(
    session_id: str,
    user_response: Optional[str] = None,
) -> dict:
    """
    Process a user message in the interview flow.

    This is the main entry point called by the FastAPI endpoint.

    Args:
        session_id: Unique session identifier.
        user_response: The user's answer (None on first call to start the interview).

    Returns:
        Dict with: session_id, state, next_question (or None), profile_so_far,
        message, profile_complete.
    """
    store = get_session_store()
    session, is_new = store.get_or_create(session_id)

    if session.is_complete:
        return _build_response(
            session,
            message="Interview already complete. Use GET /interview/{session_id}/decision to see results.",
        )

    # First call — greet and ask first question
    if is_new or user_response is None:
        session.add_message("assistant", GREETING_MESSAGE)
        next_q = _get_next_question_for_session(session)
        return _build_response(session, next_question=next_q, message=GREETING_MESSAGE)

    # Process the user's answer
    session.add_message("user", user_response)

    # Find which question this is answering (the last one we asked)
    current_q = _find_current_question(session)
    if current_q is None:
        # Edge case: no pending question, try to get the next one
        next_q = _get_next_question_for_session(session)
        if next_q is None:
            return _finalize_interview(session)
        return _build_response(session, next_question=next_q)

    # Validate and apply the answer
    valid, error_msg = _validate_and_apply_answer(session, current_q, user_response)
    if not valid:
        # Re-ask with error message (§9: re-prompt on invalid input)
        next_q = _question_def_to_interview_question(current_q, session)
        return _build_response(
            session,
            next_question=next_q,
            message=f"Invalid answer: {error_msg}. Please try again.",
        )

    session.mark_question_answered(current_q.question_id)

    # Mark skippable questions
    _mark_newly_skippable(session)

    # Check if profile is complete
    if session.profile.is_complete():
        return _finalize_interview(session)

    # Get next question
    next_q = _get_next_question_for_session(session)
    if next_q is None:
        # All questions asked/skipped but profile may still be incomplete
        if session.profile.is_complete():
            return _finalize_interview(session)
        else:
            # Force-complete with what we have
            logger.warning(
                f"Session {session_id}: all questions exhausted but profile incomplete. "
                f"Missing: {session.profile.get_missing_fields()}"
            )
            return _finalize_interview(session)

    return _build_response(session, next_question=next_q)


def get_decision(session_id: str) -> dict | None:
    """
    Get the decision result for a completed session.

    Returns None if session doesn't exist or isn't complete.
    """
    store = get_session_store()
    session = store.get(session_id)

    if session is None:
        return None

    if not session.is_complete or session.decision_result is None:
        return None

    return session.decision_result.model_dump()


# ── Internal helpers ─────────────────────────────────────────────────────────

def _get_next_question_for_session(session: InterviewSession) -> InterviewQuestion | None:
    """Get the next question, with RAG-enhanced 'why' text."""
    question_def = get_next_question(session.profile, session.answered_question_ids)
    if question_def is None:
        return None
    return _question_def_to_interview_question(question_def, session)


def _question_def_to_interview_question(
    q: QuestionDef,
    session: InterviewSession,
) -> InterviewQuestion:
    """Convert a QuestionDef to an InterviewQuestion with optional RAG 'why' text."""
    why_text = q.default_why

    # Try RAG retrieval for better 'why' text
    retriever = _get_retriever()
    if retriever and retriever.is_initialized:
        try:
            project_ctx = _get_project_context_string(session.profile)
            results = retriever.retrieve_question_context(q.profile_field, project_ctx)
            if results:
                # Use the most relevant doc's content as the 'why'
                why_text = _extract_why_from_rag(results[0], q.profile_field)
        except Exception as e:
            logger.warning(f"RAG retrieval failed for question {q.question_id}: {e}")
            session.error_count += 1
            # Fall back to default_why (§9)

    options = None
    if q.options:
        options = [QuestionOption(label=o["label"], value=o["value"]) for o in q.options]

    return InterviewQuestion(
        question_id=q.question_id,
        question_text=q.question_text,
        question_type=q.question_type,
        options=options,
        why=why_text,
    )


def _find_current_question(session: InterviewSession) -> QuestionDef | None:
    """Find the question that the user is currently answering."""
    # Walk the question bank to find the first unanswered, non-skipped question
    # This should be the one we last presented
    for q in QUESTION_BANK:
        if q.question_id in session.answered_question_ids:
            continue
        if q.question_id in session.skipped_question_ids:
            continue
        if should_skip_question(q, session.profile):
            continue
        return q
    return None


def _validate_and_apply_answer(
    session: InterviewSession,
    question: QuestionDef,
    answer: str,
) -> tuple[bool, str]:
    """
    Validate a user's answer and apply it to the profile.

    Returns (is_valid, error_message).
    """
    answer = answer.strip()

    if not answer:
        return False, "Answer cannot be empty"

    # Check if the answer matches one of the MCQ options (if applicable)
    if question.options:
        valid_values = [o["value"] for o in question.options]
        valid_labels = [o["label"].lower() for o in question.options]

        # Accept either the value or the label (case-insensitive)
        matched_value = None
        if answer in valid_values:
            matched_value = answer
        elif answer.lower() in valid_labels:
            idx = valid_labels.index(answer.lower())
            matched_value = valid_values[idx]
        else:
            # Try matching by option number (1-based)
            try:
                idx = int(answer) - 1
                if 0 <= idx < len(valid_values):
                    matched_value = valid_values[idx]
            except ValueError:
                pass

        if matched_value is None:
            option_list = ", ".join(f"'{o['label']}'" for o in question.options)
            return False, f"Please choose one of: {option_list}"

        answer = matched_value

    # Apply to profile
    try:
        _set_profile_field(session.profile, question.profile_field, answer)
        return True, ""
    except Exception as e:
        return False, str(e)


def _set_profile_field(profile: ProjectProfile, field_path: str, value: str) -> None:
    """Set a profile field from a dot-notation path and string value."""

    if field_path == "project_type":
        profile.project_type = ProjectType(value)

    elif field_path == "industry_type":
        profile.industry_type = IndustryType(value)

    elif field_path == "location.district":
        profile.location.district = value

    elif field_path == "land.required":
        profile.land.required = _parse_bool(value)

    elif field_path == "land.ownership_status":
        profile.land.ownership_status = LandOwnership(value)
        profile.land.owned = (value == "Yes")

    elif field_path == "land.area_hectare":
        profile.land.area_hectare = float(value)

    elif field_path == "electricity.required":
        profile.electricity.required = _parse_bool(value)

    elif field_path == "electricity.required_load_kw":
        profile.electricity.required_load_kw = float(value)

    elif field_path == "environment.industrial_emissions":
        profile.environment.industrial_emissions = _parse_bool_or_unsure(value)

    elif field_path == "environment.hazardous_waste":
        profile.environment.hazardous_waste = _parse_bool_or_unsure(value)

    else:
        raise ValueError(f"Unknown profile field: {field_path}")


def _parse_bool(value: str) -> bool:
    """Parse a boolean value from string."""
    return value.lower() in ("true", "yes", "1")


def _parse_bool_or_unsure(value: str) -> bool:
    """Parse a boolean, treating 'not_sure' as True (conservative approach)."""
    if value.lower() in ("not_sure", "not sure", "unsure"):
        return True  # Conservative: if not sure, assume yes for safety
    return _parse_bool(value)


def _mark_newly_skippable(session: InterviewSession) -> None:
    """After an answer, check if any upcoming questions should now be skipped."""
    for q in QUESTION_BANK:
        if q.question_id in session.answered_question_ids:
            continue
        if q.question_id in session.skipped_question_ids:
            continue
        if should_skip_question(q, session.profile):
            session.mark_question_skipped(q.question_id)
            logger.debug(f"Auto-skipped question: {q.question_id}")


def _finalize_interview(session: InterviewSession) -> dict:
    """
    Finalize the interview: run decision engine + dependency resolver.

    Produces the combined §8.3 output.
    """
    profile = session.profile

    # Run deterministic decision engine (§7)
    required_services, reasoning = decide_required_services(profile)

    # Run deterministic dependency resolver (§8)
    execution_plan = resolve_execution_order(required_services)

    # Build the combined result
    decision = DecisionResult(
        required_services=required_services,
        reasoning=reasoning,
        execution_plan=execution_plan,
    )

    session.mark_complete(decision)

    response = _build_response(
        session,
        message="Interview complete! Your project profile has been analyzed. "
                "The required department verifications and their execution order "
                "have been determined.",
    )
    response["profile_complete"] = True
    response["decision"] = decision.model_dump()
    return response


def _build_response(
    session: InterviewSession,
    next_question: InterviewQuestion | None = None,
    message: str | None = None,
) -> dict:
    """Build the standard response dict for the API."""
    profile_dict = session.profile.model_dump(exclude_none=True)

    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "next_question": next_question.model_dump() if next_question else None,
        "profile_so_far": profile_dict,
        "message": message,
        "profile_complete": session.is_complete,
    }


def _get_project_context_string(profile: ProjectProfile) -> str:
    """Build a short context string from the current profile state."""
    parts = []
    if profile.project_type:
        parts.append(profile.project_type.value)
    if profile.industry_type:
        parts.append(profile.industry_type.value)
    if profile.location.district:
        parts.append(f"in {profile.location.district}")
    return " ".join(parts) if parts else "industrial project"


def _extract_why_from_rag(result: dict, field_name: str) -> str:
    """Extract a concise 'why' explanation from a RAG result."""
    text = result.get("text", "")
    # Take the first sentence or first 150 chars
    sentences = text.split(". ")
    if sentences:
        why = sentences[0].strip()
        if len(why) > 150:
            why = why[:147] + "..."
        return why
    return text[:150] if text else ""
