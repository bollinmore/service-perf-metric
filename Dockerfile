# syntax=docker/dockerfile:1

FROM python:3.11-alpine AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build wheels once (kept out of final image)
RUN apk add --no-cache build-base openblas-dev
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

# Stage app sources (no data)
COPY spm.py ./spm.py
COPY src ./src
COPY static ./static
COPY templates ./templates


FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime libs only (pandas needs openblas, libstdc++)
RUN apk add --no-cache libstdc++ openblas

# Install from prebuilt wheels to avoid build deps
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-compile /wheels/*

# Copy application code
COPY --from=builder /app/spm.py ./spm.py
COPY --from=builder /app/src ./src
COPY --from=builder /app/static ./static
COPY --from=builder /app/templates ./templates

# Expose Flask/Gunicorn port
EXPOSE 6231

# Default: generate reports (if needed) and start web UI
CMD ["python", "spm.py", "serve", "--host", "0.0.0.0", "--port", "6231"]

