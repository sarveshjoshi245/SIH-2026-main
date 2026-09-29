# TASK: RAG-Based Conversational Intake & Deterministic Service-Decision Engine (v2)

## 1. Context — what you are building, and what you are NOT

This is **one module** inside a larger SIH team project (Industrial Project Setup use case: a company establishing a chemical manufacturing plant in Pune needs verification from three departments — Land/Revenue, Electricity, and Pollution/Environment).

Your teammates are separately building:
- The three mock departmental APIs + databases (Land, Electricity, Pollution)
- The interoperability/API gateway layer (auth, consent enforcement, schema mapping, circuit breakers, audit logging, and actually executing the calls to each mock service)
- The frontend chat UI and dashboards

**You are building only:** the conversational intake system that talks to the user, retrieves relevant domain knowledge, builds a structured project profile, deterministically decides which of the three departmental services are required, **and works out the order those services must be verified in** (some departments depend on prerequisite data from others) — then hands that decision off to the interoperability layer through a clean API contract.

You do **not** call the departmental APIs yourself, and you do not build the UI, the mock services, the admin dashboard, or the auth/consent/audit layer.

---

## 2. Non-negotiable architectural rule

**The LLM must never directly decide or output an API call, and must never be the final decision-maker on which services are required or in what order.** Its job stops at producing a structured, validated project profile. A separate deterministic engine (plain rules + a static dependency graph — not a model call) reads that profile and outputs both the required-service list *and* the execution order. This keeps the decision explainable, testable, and reproducible — a judge can ask "why does Pollution come after Land?" and you point to a rule, not a guess.

So the module is **three connected pieces you own end-to-end**:

1. **RAG-assisted conversational interview → structured profile** (uses the LLM + retrieval)
2. **Deterministic decision engine → required services list** (plain code, no LLM in the loop)
3. **Deterministic dependency resolver → execution order** (plain code, static dependency graph — see §8)

Only pieces 2 and 3's combined output is what gets sent downstream to your teammates' interoperability layer.

---

## 3. What your module must do, end-to-end

1. Greet the user, explain it will determine which department verifications their project needs.
2. Ask a structured, MCQ-first interview — dynamically, skipping irrelevant questions.
3. Use RAG retrieval to (a) decide which follow-up questions are relevant for this project type/industry, and (b) generate a one-line explanation of *why* a question is being asked.
4. Build and validate a structured JSON **Project Profile**.
5. Run the profile through the deterministic **Decision Engine** to get the required-service list.
6. Run the required-service list through the deterministic **Dependency Resolver** to get the execution order (§8).
7. Return the profile, the required services, and the execution plan — each with a short human-readable reason — via your module's API.
8. Handle its own failures gracefully (see §9) — downstream department-API failures are not your concern.

---

## 4. Example interview (MCQ-first, dynamic)

```
User:
"I want to establish a chemical manufacturing plant in Pune."

Chatbot:
Q1. What type of project are you establishing?
  [ Manufacturing ]  [ Warehouse ]  [ IT/Office ]  [ Other ]

Q2. Where is the proposed project located?
  [ Pune ]  [ Mumbai ]  [ Nashik ]  [ Other ]

Q3. Do you already own the proposed land?
  [ Yes ]  [ No ]  [ Under acquisition ]

Q4. What is the approximate land requirement?
  [ <1 hectare ]  [ 1–5 hectares ]  [ 5–10 hectares ]  [ >10 hectares ]

Q5. What is your expected electricity requirement?
  [ <100 kW ]  [ 100–500 kW ]  [ 500 kW–1 MW ]  [ >1 MW ]

Q6. Will the project generate industrial emissions, wastewater, or hazardous waste?
  [ Yes ]  [ No ]  [ Not sure ]
```

Rules:
- Prefer multiple-choice; use free text only for values that can't be enumerated (name, exact numeric values).
- If an earlier answer makes a later question moot, **skip it** — don't ask it, mark it `"not_applicable"` in the profile.
- Every question should be traceable to a reason retrieved from the knowledge base. This traceability is what makes the RAG usage genuine rather than decorative.

---

## 5. Project Profile schema (your module's primary output)

```json
{
  "project_type": "MANUFACTURING",
  "industry_type": "CHEMICAL",
  "location": {
    "district": "Pune",
    "state": "Maharashtra"
  },
  "land": {
    "required": true,
    "owned": true,
    "area_hectare": 7.5
  },
  "electricity": {
    "required": true,
    "required_load_kw": 750
  },
  "environment": {
    "industrial_emissions": true,
    "hazardous_waste": true
  }
}
```

Validate before passing to the decision engine: required fields present, numeric fields non-negative, enums restricted to known values. Re-prompt the user on invalid/ambiguous answers rather than writing bad data into the profile.

---

## 6. RAG knowledge base — already generated, do not regenerate

The knowledge base has already been created (via a separate one-off prompt to another LLM), in this format per document:

```
FILE: knowledge/<folder>/<short_filename>.md
TITLE: <document title>
TRIGGER: <the profile condition this doc justifies>
CONTENT: <120-250 word body>
```

Load and index these files as-is — **do not write new logic to generate knowledge base content**, only logic to parse, chunk, and embed the existing files. Folders in place: `land/`, `electricity/`, `pollution/`, `industrial_project_types/`, `faq/`.

**Gap to check before you build the dependency resolver (§8):** the existing knowledge base was generated before the cross-department dependency requirement existed, so it may not contain documents explaining *why* one department depends on another (e.g., why Pollution needs Land data first). If there's no `knowledge/dependencies/` content covering this, either (a) generate 1–2 short additional documents in that format covering the known dependency in §8, or (b) hardcode the justification string directly in the dependency graph — either is acceptable, since the dependency graph itself must be deterministic code either way (§2), and RAG is only used here to produce the human-readable "why" text, not the decision itself.

**Use RAG for:** deciding which questions to ask/skip, and generating the "why we're asking this" / "why this service was selected" / "why this order" explanations shown to the user.

**Do NOT use RAG for:** the final service-selection decision or the execution order — those are the deterministic engine's job (§2, §8).

---

## 7. Deterministic Decision Engine (which services are required)

```
IF land.required == true
  → LAND_SERVICE

IF electricity.required == true OR electricity.required_load_kw > 0
  → ELECTRICITY_SERVICE

IF environment.industrial_emissions == true OR environment.hazardous_waste == true
  → POLLUTION_SERVICE
```

This stage's output feeds directly into the Dependency Resolver in §8 — it does not go to the interoperability layer on its own anymore (see §10 for the combined output contract).

---

## 8. NEW: Cross-Department Dependency Graph & Execution Order

Some departmental verifications require another department's *already-verified* data as an input, not just independent parallel checks. Your teammate's research confirms a concrete real-world example: Maharashtra Pollution Control Board's Consent to Establish requires a Land Ownership Certificate as a submission document, and the Maharashtra Land Records department separately exposes API services to authorized institutions ("Mahabhumi API Services"). This is real grounding for the pattern — but don't claim in the demo that this exact automatic cross-department exchange already happens in production today. Frame it as: *"our platform is the proposed mechanism that resolves this dependency where authorized APIs and policy permit it."*

### 8.1 Static dependency graph

Define this as a plain lookup table, not something derived at runtime:

```python
SERVICE_DEPENDENCIES = {
    "LAND_SERVICE": [],
    "ELECTRICITY_SERVICE": [],
    "POLLUTION_SERVICE": ["LAND_SERVICE"],
}
```

`POLLUTION_SERVICE` depends on `LAND_SERVICE` because MPCB's Consent-to-Establish process requires a verified Land Ownership Certificate before that application can be meaningfully progressed.

### 8.2 What the resolver does

1. Take the `required_services` list from §7.
2. Filter the dependency graph down to only the services actually required for this profile (a dependency on a service that isn't required for this project doesn't apply).
3. Topologically sort the filtered graph into **execution waves** — services with no unresolved dependency in the same wave (parallel), dependents in a later wave.
4. Attach a human-readable reason per dependency edge (from the knowledge base where available, per §6; otherwise a plain templated string).

### 8.3 Output contract

```json
{
  "required_services": ["LAND_SERVICE", "ELECTRICITY_SERVICE", "POLLUTION_SERVICE"],
  "reasoning": {
    "LAND_SERVICE": "Project requires land area of 7.5 hectares",
    "ELECTRICITY_SERVICE": "Project requires 750 kW power connection",
    "POLLUTION_SERVICE": "Project generates industrial emissions and hazardous waste"
  },
  "execution_plan": [
    {
      "wave": 1,
      "service": "LAND_SERVICE",
      "depends_on": [],
      "reason": "No prerequisite; can be verified immediately"
    },
    {
      "wave": 1,
      "service": "ELECTRICITY_SERVICE",
      "depends_on": [],
      "reason": "Independent of Land and Pollution; can run in parallel"
    },
    {
      "wave": 2,
      "service": "POLLUTION_SERVICE",
      "depends_on": ["LAND_SERVICE"],
      "reason": "MPCB Consent to Establish requires a verified Land Ownership Certificate as a submission prerequisite"
    }
  ]
}
```

### 8.4 Important scope boundary

This module produces the **static plan** — which services, in what order, and why — based on the project profile alone. It does **not** track live execution state (e.g., "Land mutation came back PENDING, so block Pollution"). That's runtime orchestration against real/mock API responses, which belongs to your teammates' interoperability/workflow layer. Your `depends_on` field is exactly what they need to implement that blocking behavior correctly — you're handing them the dependency graph, they're the ones who watch it execute and hold up dependents on a pending/failed prerequisite. Make sure they know `execution_plan` is what to consume for that.

---

## 9. Your module's own error handling

(Separate from downstream department-API failures, which your teammates' layer handles — not you.)

- If the LLM call for question generation fails or times out, fall back to a static predefined question list for that project type. Don't block the interview.
- If RAG retrieval returns nothing relevant, fall back to a default question set and log the miss — don't let the interview stall.
- Validate every user answer before writing it to the profile; re-ask on invalid input rather than crashing or silently guessing.
- If a required service has no entry in `SERVICE_DEPENDENCIES`, default it to no dependencies (empty list) rather than erroring — log it as a config gap to fix, don't crash the interview over it.

---

## 10. Interface contract with the rest of the team

Expose your module as a small FastAPI service with, at minimum:

- `POST /interview/message` — takes `{session_id, user_response}`, returns `{next_question | profile_complete, profile_so_far}`
- `GET /interview/{session_id}/decision` — once the profile is complete, returns the combined §8.3 output (`required_services`, `reasoning`, `execution_plan`)

**Agree this exact JSON shape with your teammates before building internals** — it's the seam between your module and theirs, and the most common source of last-minute integration pain. Flag `execution_plan` specifically since it's new — they need to actually consume `depends_on` in their workflow orchestration for it to matter.

---

## 11. Tech stack (scoped to this module only)

- Python + FastAPI — expose the two endpoints above
- LangChain or LlamaIndex + FAISS for retrieval
- Configurable LLM provider abstraction (don't hardcode one vendor)
- Plain Python for the decision engine and dependency resolver — no framework needed; a topological sort over a small static graph is a ~20-line function, no library required
- Pytest — unit-test the decision engine and the dependency resolver separately, against fixed inputs; this is the easiest part to *prove* correct to a judge, so actually write these tests

---

## 12. Explicitly NOT in scope for this module

Mock departmental APIs/DBs, the interoperability/API gateway (auth, consent enforcement, circuit breaker, retries), **live dependency-state tracking during execution** (pending/blocked/resolved based on actual API responses — you only produce the static plan, see §8.4), schema mapping between department responses and the canonical model, admin dashboard, frontend chat UI, audit logging of department calls, RabbitMQ/Redis/Docker orchestration for the whole platform. These belong to your teammates; your module only needs to produce the outputs in §5 and §8.3, served via the API in §10.

---

## 13. Success criteria for this module specifically

Given the demo profile (chemical manufacturing, Pune, land owned 7.5 ha, 750 kW, industrial emissions + hazardous waste = true), your module must:

- Ask only relevant questions — skip irrelevant ones when tested against a second profile
- Produce a valid, complete Project Profile JSON
- Deterministically output `required_services = [LAND_SERVICE, ELECTRICITY_SERVICE, POLLUTION_SERVICE]` with a one-line reason for each
- Deterministically output an `execution_plan` where `LAND_SERVICE` and `ELECTRICITY_SERVICE` are wave 1 (parallel) and `POLLUTION_SERVICE` is wave 2, depending on `LAND_SERVICE`, with a correct reason string
- Produce the **identical decision and plan every time** given the identical profile — run it twice live if a judge asks
- Degrade gracefully if the LLM/retrieval call fails mid-interview

---

## 14. Build order

1. **Decision engine + dependency resolver first**, with unit tests against 3–4 hand-written profiles, including one that checks the wave ordering is correct. Build the part that must never be flaky before the part with an LLM in the loop.
2. Wire in the already-generated knowledge base (parse, chunk, embed) — no content generation needed, per §6.
3. RAG retrieval tested standalone against that knowledge base.
4. MCQ interview flow producing a profile, using retrieval to pick/skip questions.
5. FastAPI wrapper exposing the two endpoints, returning the combined §8.3 output.
6. Integration test against a stubbed interoperability layer (a fake endpoint that just logs what it receives) so you can demo your piece independently before wiring to teammates' real services.
