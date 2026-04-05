# Base image: python:3.10-slim
FROM python:3.10-slim

# Set strict environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install curl required for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user running with mapping UID 1000 
# (REQUIRED constraint by Hugging Face Spaces for Docker environments)
RUN useradd -m -u 1000 appuser

# Switch to the non-root execution context
USER appuser

# Define Application Workspace
WORKDIR /app

# Strategically copy requirements.txt first for efficient layer caching
COPY --chown=appuser:appuser requirements.txt .

# Install pinned dependencies globally to user directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Load the remaining local context files (including main.py, src, inference.py)
COPY --chown=appuser:appuser . .

# Expose Space communication endpoint
EXPOSE 7860

# Add pinging HEALTHCHECK hitting HTTP dashboard root every 30 seconds
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:7860/ || exit 1

# Execute core ASGI application server via Uvicorn single threaded worker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
