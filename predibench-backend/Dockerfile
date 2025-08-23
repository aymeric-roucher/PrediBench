FROM python:3.13-slim

WORKDIR /app

# Install git and uv for faster Python package management
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/

# Copy and install dependencies
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application code
COPY main.py ./

# Create user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
RUN mkdir -p /home/appuser/.cache/uv && chown -R appuser:appuser /home/appuser/.cache
USER appuser

# Expose port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]