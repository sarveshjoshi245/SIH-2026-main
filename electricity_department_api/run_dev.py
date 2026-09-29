"""Start the Electricity Department API on the host/port assigned in the repo-root ports.json.

Use this (or start-all.js at the repo root) instead of typing a --port by hand,
so this service can never end up on another service's port.
"""
import json
from pathlib import Path

import uvicorn

PORTS = json.loads((Path(__file__).resolve().parent.parent / "ports.json").read_text(encoding="utf-8"))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=PORTS["host"], port=PORTS["services"]["electricity"]["port"])
