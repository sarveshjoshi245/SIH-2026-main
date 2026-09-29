# RAG Intake & Deterministic Decision Engine

**Module** within the SIH project for Industrial Project Setup. Handles conversational intake, RAG-assisted question selection, deterministic service decision, and dependency-based execution ordering.

## Architecture

```
User ──► Interview Engine (LLM + RAG) ──► Project Profile (JSON)
                                              │
                                              ▼
                                    Decision Engine (deterministic rules)
                                              │
                                              ▼
                                    Dependency Resolver (static graph + topo sort)
                                              │
                                              ▼
                                    Execution Plan ──► Interoperability Layer
```

**Key constraint:** The LLM never decides which services are required. It only builds the profile. The decision engine and dependency resolver are pure deterministic code — testable, reproducible, explainable.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your LLM API key

# 3. Run
python -m uvicorn app.main:app --reload --port 8000

# 4. Test
pytest tests/ -v
```

## API Endpoints

### `POST /interview/message`

Start or continue an interview session.

```json
// Request
{"session_id": "user-123", "user_response": "MANUFACTURING"}

// Response
{
  "session_id": "user-123",
  "state": "IN_PROGRESS",
  "next_question": {
    "question_id": "industry_type",
    "question_text": "What industry does your manufacturing project belong to?",
    "question_type": "mcq",
    "options": [{"label": "Chemical", "value": "CHEMICAL"}, ...],
    "why": "Industry type determines which environmental checks apply."
  },
  "profile_so_far": {"project_type": "MANUFACTURING"},
  "profile_complete": false
}
```

### `GET /interview/{session_id}/decision`

Get the decision result after interview completion.

```json
{
  "required_services": ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"],
  "reasoning": {
    "LAND_SERVICE": "Project requires land area of 7.5 hectares",
    "ELECTRICITY_SERVICE": "Project requires 750 kW power connection",
    "POLLUTION_SERVICE": "Project generates industrial emissions and hazardous waste"
  },
  "execution_plan": [
    {"wave": 1, "service": "LAND_SERVICE", "depends_on": [], "reason": "No prerequisite; can be verified immediately"},
    {"wave": 1, "service": "ELECTRICITY_SERVICE", "depends_on": [], "reason": "Independent of Land and Pollution; can run in parallel"},
    {"wave": 2, "service": "POLLUTION_SERVICE", "depends_on": ["LAND_SERVICE"], "reason": "MPCB Consent to Establish requires a verified Land Ownership Certificate as a submission prerequisite"}
  ]
}
```

## Project Structure

```
rag-service/
├── app/
│   ├── main.py                    # FastAPI app + endpoints
│   ├── config.py                  # Environment-based configuration
│   ├── models.py                  # Pydantic schemas
│   ├── decision_engine.py         # §7 deterministic rules
│   ├── dependency_resolver.py     # §8 static graph + topological sort
│   ├── rag/
│   │   ├── knowledge_loader.py    # Parse knowledge base .md files
│   │   ├── vector_store.py        # FAISS index build/save/load/search
│   │   └── retriever.py           # High-level retrieval interface
│   └── interview/
│       ├── questions.py           # Static question bank + skip logic
│       ├── session.py             # In-memory session management
│       └── engine.py              # Interview flow orchestrator
├── knowledge/                     # Pre-generated knowledge base
│   ├── land/
│   ├── electricity/
│   ├── pollution/
│   ├── industrial_project_types/
│   ├── faq/
│   └── dependencies/
├── tests/
│   ├── test_decision_engine.py
│   ├── test_dependency_resolver.py
│   └── test_integration.py
├── requirements.txt
├── .env.example
└── README.md
```

## Testing

```bash
# Unit tests (no LLM/RAG required)
pytest tests/test_decision_engine.py tests/test_dependency_resolver.py -v

# Full integration tests (no LLM/RAG required)
pytest tests/test_integration.py -v

# All tests
pytest tests/ -v
```
