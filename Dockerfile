# ── Stage 1: Build React frontend ─────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and data
COPY backend/ ./backend/
COPY data/ ./data/

# Copy built frontend
COPY --from=frontend-builder /frontend/build ./frontend/build

EXPOSE 8000

CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
