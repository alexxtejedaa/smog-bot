# SMOG Bot — Docker Container (Skeleton)
# Builds a minimal Python 3.13 FastAPI container
# Not production-ready yet

FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
# TODO: Use gunicorn or uvicorn with proper configuration
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
