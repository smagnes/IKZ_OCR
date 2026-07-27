FROM ikz-gl.ib2.eu:5050/medyk/reg:surya-test

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart \
    pydantic pydantic-settings pypdf pdf2image asyncpg redis nats-py \
    python-jose[cryptography] bcrypt httpx python-dotenv

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PRELOAD_MODELS=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT []
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
