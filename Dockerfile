FROM python:3.12-slim

WORKDIR /app

# System deps for lxml and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy source + project metadata
COPY pyproject.toml .
COPY src/ src/

# Install with web + auth extras
RUN pip install --no-cache-dir ".[web,auth,ai]"

# Non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser

VOLUME ["/app/output", "/app/data"]
EXPOSE 8080

CMD ["uvicorn", "a11yscope.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
