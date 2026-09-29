"""
Deterministic Dependency Resolver (§8).

Takes the required-services list from the Decision Engine and produces
an execution plan with wave ordering via topological sort over a static
dependency graph.

NO LLM in the loop — pure graph logic.
"""

from __future__ import annotations

from collections import defaultdict, deque

from app.models import ExecutionStep


# ── Static dependency graph (§8.1) ───────────────────────────────────────────
# Key = service, Value = list of services it depends on.
# POLLUTION_SERVICE depends on LAND_SERVICE because MPCB's Consent to Establish
# requires a verified Land Ownership Certificate.

SERVICE_DEPENDENCIES: dict[str, list[str]] = {
    "LAND_SERVICE": [],
    "ELECTRICITY_SERVICE": [],
    "POLLUTION_SERVICE": ["LAND_SERVICE"],
}

# Human-readable reasons for each dependency edge
DEPENDENCY_REASONS: dict[tuple[str, str], str] = {
    ("POLLUTION_SERVICE", "LAND_SERVICE"): (
        "MPCB Consent to Establish requires a verified Land Ownership "
        "Certificate as a submission prerequisite"
    ),
}

# Default reasons for services with no dependencies
NO_DEPENDENCY_REASONS: dict[str, str] = {
    "LAND_SERVICE": "No prerequisite; can be verified immediately",
    "ELECTRICITY_SERVICE": "Independent of Land and Pollution; can run in parallel",
    "POLLUTION_SERVICE": "No prerequisite dependencies apply for this project",
}


def resolve_execution_order(required_services: list[str]) -> list[ExecutionStep]:
    """
    Resolve the execution order for the given required services using
    topological sort over the static dependency graph.

    Steps (§8.2):
    1. Filter the dependency graph to only services actually required.
    2. Topologically sort into execution waves.
    3. Attach human-readable reason per dependency edge.

    Args:
        required_services: List of service names from the decision engine.

    Returns:
        List of ExecutionStep objects ordered by wave.
    """
    required_set = set(required_services)

    # Build filtered adjacency: only keep dependencies that are also required
    # If a dependency isn't required, it doesn't apply (§8.2 step 2)
    filtered_deps: dict[str, list[str]] = {}
    for service in required_services:
        raw_deps = SERVICE_DEPENDENCIES.get(service, [])
        # Only keep dependencies that are themselves in the required set
        filtered_deps[service] = [d for d in raw_deps if d in required_set]

    # Topological sort into waves using Kahn's algorithm
    # In-degree computation
    in_degree: dict[str, int] = {s: 0 for s in required_services}
    reverse_adj: dict[str, list[str]] = defaultdict(list)  # dependency -> dependents

    for service, deps in filtered_deps.items():
        in_degree[service] = len(deps)
        for dep in deps:
            reverse_adj[dep].append(service)

    # BFS-style wave assignment
    waves: list[list[str]] = []
    queue = deque([s for s in required_services if in_degree[s] == 0])

    while queue:
        # All services in the current queue have no unresolved dependencies → same wave
        current_wave = sorted(queue)  # Sort for determinism
        waves.append(current_wave)
        next_queue: deque[str] = deque()

        for service in current_wave:
            for dependent in reverse_adj.get(service, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_queue.append(dependent)

        queue = next_queue

    # Build ExecutionStep list
    execution_plan: list[ExecutionStep] = []
    for wave_num, wave_services in enumerate(waves, start=1):
        for service in wave_services:
            deps = filtered_deps.get(service, [])
            reason = _get_reason(service, deps)
            execution_plan.append(
                ExecutionStep(
                    wave=wave_num,
                    service=service,
                    depends_on=deps,
                    reason=reason,
                )
            )

    return execution_plan


def _get_reason(service: str, active_deps: list[str]) -> str:
    """
    Get a human-readable reason for why this service is in its wave.

    Uses the DEPENDENCY_REASONS lookup for edges that exist,
    falls back to NO_DEPENDENCY_REASONS for services with no active deps.
    """
    if not active_deps:
        return NO_DEPENDENCY_REASONS.get(
            service,
            "No prerequisite dependencies; can proceed immediately"
        )

    # Build reason from dependency edges
    reasons = []
    for dep in active_deps:
        edge_key = (service, dep)
        if edge_key in DEPENDENCY_REASONS:
            reasons.append(DEPENDENCY_REASONS[edge_key])
        else:
            reasons.append(f"Requires completed {dep} verification first")

    return "; ".join(reasons)
