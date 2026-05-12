# Bill Split Backend Dockerfile
# Optimized for development with Docker Compose

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies directly (pyproject.toml has [project] format incompatible with pip)
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary \
    alembic pydantic-settings python-multipart email-validator pyjwt "pwdlib[argon2,bcrypt]" argon2 bcrypt sqlmodel \
    python-dotenv "pydantic>=2.0" sentry-sdk httpx emails jinja2

# Copy application code
COPY alembic.ini ./
COPY app ./app

# Create uploads directory for QR codes and expense images
RUN mkdir -p /app/uploads/qr_codes /app/uploads/expense_images

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/utils/health-check/ || exit 1

# Default command - uses shell form so it can be overridden by compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
