FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" python-multipart \
    pydantic pydantic-settings pypdf pdf2image asyncpg redis nats-py \
    "python-jose[cryptography]" bcrypt httpx python-dotenv anthropic Pillow requests

COPY . .

ENV PYTHONUNBUFFERED=1
# OCR_ENGINE=claude — jedyny dozwolony backend; nie zmieniać
ENV OCR_ENGINE=claude
ENV PRELOAD_MODELS=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
