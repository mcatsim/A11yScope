FROM python:3.12-slim

WORKDIR /app

# System deps for lxml and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy source + project metadata
COPY pyproject.toml .
COPY src/ src/

# Install with web extras
RUN pip install --no-cache-dir ".[web]"

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

VOLUME ["/app/output"]
EXPOSE 8080

CMD ["uvicorn", "canvas_a11y.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
