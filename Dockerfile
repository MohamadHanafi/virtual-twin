FROM python:3.11-slim

ARG INSTALL_RAG=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=gemini

WORKDIR /app

COPY requirements.txt requirements-rag.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_RAG" = "true" ]; then \
        pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.10.0 \
        && pip install --no-cache-dir -r requirements-rag.txt; \
    fi

COPY . .

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 0"]
