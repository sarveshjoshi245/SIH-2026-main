"""
FastAPI application for the RAG Intake & Decision Engine module.

Exposes two endpoints per §10:
- POST /interview/message — conversational interview step
- GET  /interview/{session_id}/decision — get decision result for completed interview
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.intake.models import InterviewMessageRequest, InterviewMessageResponse, DecisionResult
from app.intake.interview.engine import process_message, get_decision
from app.intake.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize RAG index on startup."""
    logger.info("Starting RAG Intake & Decision Engine...")
    settings = get_settings()

    # Initialize RAG retriever (optional — works without it via fallback)
    try:
        from app.intake.rag.retriever import get_retriever
        retriever = get_retriever()
        retriever.initialize(
            knowledge_dir=settings.knowledge_base_path,
            index_dir=settings.faiss_index_path,
            embedding_model=settings.embedding_model,
        )
        logger.info(
            f"RAG retriever initialized: {retriever.document_count} documents indexed"
        )
    except Exception as e:
        logger.warning(
            f"RAG retriever initialization failed: {e}. "
            f"Interview will use fallback question logic (§9)."
        )

    yield

    logger.info("Shutting down RAG Intake & Decision Engine.")


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Intake & Decision Engine",
    description=(
        "Conversational intake system for industrial project setup. "
        "Conducts a structured interview, builds a project profile, "
        "and deterministically decides which departmental verifications "
        "are required and in what order."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the frontend to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints (§10) ─────────────────────────────────────────────────────────

@app.post("/interview/message")
async def interview_message(request: InterviewMessageRequest) -> dict:
    """
    POST /interview/message

    Takes {session_id, user_response} and returns the next question
    or profile completion status.

    - On first call (user_response=None): starts the interview, returns greeting + first question.
    - On subsequent calls: validates answer, updates profile, returns next question.
    - When all questions answered: finalizes profile, runs decision engine, returns results.

    Response shape:
    {
        "session_id": "...",
        "state": "IN_PROGRESS" | "COMPLETE",
        "next_question": {...} | null,
        "profile_so_far": {...},
        "message": "..." | null,
        "profile_complete": false | true,
        "decision": {...} | null   // Only present when profile_complete=true
    }
    """
    try:
        result = process_message(
            session_id=request.session_id,
            user_response=request.user_response,
        )
        return result
    except Exception as e:
        logger.error(f"Error processing message for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing interview message: {str(e)}",
        )


@app.get("/interview/{session_id}/decision")
async def interview_decision(session_id: str) -> dict:
    """
    GET /interview/{session_id}/decision

    Returns the combined §8.3 output once the interview is complete:
    {
        "required_services": ["LAND_SERVICE", ...],
        "reasoning": {"LAND_SERVICE": "...", ...},
        "execution_plan": [
            {"wave": 1, "service": "LAND_SERVICE", "depends_on": [], "reason": "..."},
            ...
        ]
    }

    Returns 404 if the session doesn't exist.
    Returns 400 if the interview is not yet complete.
    """
    from app.intake.interview.session import get_session_store

    store = get_session_store()
    session = store.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not session.is_complete:
        raise HTTPException(
            status_code=400,
            detail="Interview is not yet complete. Continue sending responses to POST /interview/message",
        )

    decision = get_decision(session_id)
    if decision is None:
        raise HTTPException(status_code=500, detail="Decision result not available")

    return decision


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    retriever_status = "not_initialized"
    try:
        from app.intake.rag.retriever import get_retriever
        retriever = get_retriever()
        if retriever.is_initialized:
            retriever_status = f"ok ({retriever.document_count} docs)"
    except Exception:
        retriever_status = "unavailable"

    return {
        "status": "healthy",
        "service": "rag-intake-decision-engine",
        "version": "1.0.0",
        "retriever": retriever_status,
    }


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )

