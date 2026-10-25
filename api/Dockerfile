FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils curl wget unzip && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/ggml-org/llama.cpp/releases/download/b5600/llama-b5600-bin-ubuntu-x64.zip && \
    unzip -q llama-b5600-bin-ubuntu-x64.zip && \
    cp build/bin/llama-server /usr/local/bin/llama-server-real && \
    cp build/bin/*.so /usr/local/bin/ && \
    chmod +x /usr/local/bin/llama-server-real && \
    rm -rf build llama-b5600-bin-ubuntu-x64.zip && \
    printf '#!/bin/bash\nargs=()\nfor arg in "$@"; do\n  if [ "${prev}" = "-ngl" ]; then\n    args+=("0")\n  else\n    args+=("$arg")\n  fi\n  prev="$arg"\ndone\nexec /usr/local/bin/llama-server-real "${args[@]}"\n' > /usr/local/bin/llama-server && \
    chmod +x /usr/local/bin/llama-server

ENV LD_LIBRARY_PATH=/usr/local/bin:$LD_LIBRARY_PATH

COPY requirements.txt .
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir surya-ocr fastapi "uvicorn[standard]" python-multipart \
    pydantic pydantic-settings pypdf pdf2image asyncpg redis nats-py \
    "python-jose[cryptography]" bcrypt httpx python-dotenv

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PRELOAD_MODELS=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
