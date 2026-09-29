# Samanvay — single-service Docker image (all 5 services, 1 public port).
# Render/Railway: deploy this repo as ONE Web Service, Docker runtime.
FROM node:20-bookworm-slim

# Python for the 2 FastAPI services
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Node deps (portal + land + pollution)
RUN cd server && npm install --omit=dev && cd ../land_api && npm install --omit=dev && cd ../pollution_api && npm install --omit=dev

# Python deps (interop + electricity) into a shared venv
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r interop_backend/requirements.txt -r electricity_department_api/requirements.txt

ENV SINGLE_SERVICE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

# Render injects $PORT at runtime; start-single.js respects it.
EXPOSE 10000
CMD ["node", "start-single.js"]
