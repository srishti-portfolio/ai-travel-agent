# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first - this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the application code
COPY app/ ./app/

# Cloud Run injects $PORT at runtime; default to 8080 for local
ENV PORT=8080
EXPOSE 8080

# Use shell form so $PORT is expanded; exec so uvicorn is PID 1
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}