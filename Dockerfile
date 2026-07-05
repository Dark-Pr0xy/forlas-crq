# syntax=docker/dockerfile:1.7

# ----- Frontend builder -------------------------------------------------------
FROM node:22-alpine AS frontend-build
WORKDIR /app
ENV VITE_BASE_PATH=/app/
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


# ----- Runtime ----------------------------------------------------------------
FROM python:3.13-slim AS runtime

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FORLAS_HOST=0.0.0.0 \
    FORLAS_PORT=8765 \
    FORLAS_DATA_DIR=/data

WORKDIR /srv

# Install the backend
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
RUN pip install .

# Bake the built frontend in alongside the backend so a single process serves both
COPY --from=frontend-build /app/dist ./static

# Mount the frontend bundle at /app/* via FastAPI StaticFiles (added in app/main.py
# when the directory exists). See the note in main.py.
VOLUME ["/data"]
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8765/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
