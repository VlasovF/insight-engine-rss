FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    uv sync --no-cache

# Copy application code
COPY backend/app/ ./app

# Set PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]