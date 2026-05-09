FROM python:3.12-slim

WORKDIR /app

# Install Python deps (cached unless requirements change).
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the ONNX MiniLM model into the image cache so the container
# doesn't need internet egress on first chat (avoids TLS-handshake timeouts).
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()(['warmup'])"

# Backend code.
COPY backend/ .

# Bake demo data sources into the image. The path mirrors the dev layout:
# services/data_proxy.py resolves DATA_DIR as /app/../database/data_sources.
COPY database/data_sources /database/data_sources

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
