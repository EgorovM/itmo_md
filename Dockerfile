FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and README (needed for package metadata)
COPY pyproject.toml README.md ./

# Copy application code (needed for editable install)
COPY src/ ./src/

# Install dependencies (uv will install hatchling automatically)
RUN uv pip install --system --no-cache -e .

# Run the application
CMD ["python", "-m", "bankshield.collector"]
