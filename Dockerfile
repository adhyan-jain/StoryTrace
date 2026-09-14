FROM python:3.12-slim AS backend

WORKDIR /app

# PyMuPDF (fitz) and clickhouse-connect's transport need a C toolchain to
# build wheels on some platforms; keep the image slim but not broken.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

# UID/GID default to 1000 (the common single-user-host default) and are
# overridable at build time -- this container mounts the host's gcloud ADC
# credentials file read-only for Vertex AI auth (see docker-compose.yml),
# and that file is 0600 on the host, so the container user must share the
# host user's UID to read it; a mismatched auto-assigned system UID (plain
# `useradd -r`) cannot.
ARG BACKEND_UID=1000
ARG BACKEND_GID=1000
RUN groupadd -g "${BACKEND_GID}" backend \
    && useradd -u "${BACKEND_UID}" -g backend backend \
    && chown -R backend:backend /app
USER backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
