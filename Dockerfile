# Use the official Python 3.11 slim image for a smaller footprint
FROM python:3.11-slim

ARG LOTUS_BUILD_COMMIT_SHA=unknown
ARG LOTUS_BUILD_GIT_BRANCH=unknown
ARG LOTUS_BUILD_REPO_URL=https://github.com/sgajbi/lotus-advise
ARG LOTUS_BUILD_VERSION=0.1.0
ARG LOTUS_BUILD_TIMESTAMP=unknown
ARG LOTUS_CI_PIPELINE_ID=local
ARG LOTUS_IMAGE_DIGEST=unknown

LABEL org.opencontainers.image.title="lotus-advise" \
    org.opencontainers.image.description="Lotus Advise advisory workflow service" \
    org.opencontainers.image.source="${LOTUS_BUILD_REPO_URL}" \
    org.opencontainers.image.url="${LOTUS_BUILD_REPO_URL}" \
    org.opencontainers.image.revision="${LOTUS_BUILD_COMMIT_SHA}" \
    org.opencontainers.image.ref.name="${LOTUS_BUILD_GIT_BRANCH}" \
    org.opencontainers.image.version="${LOTUS_BUILD_VERSION}" \
    org.opencontainers.image.created="${LOTUS_BUILD_TIMESTAMP}" \
    org.opencontainers.image.vendor="Lotus" \
    com.lotus.ci.run-id="${LOTUS_CI_PIPELINE_ID}" \
    com.lotus.image.digest="${LOTUS_IMAGE_DIGEST}"

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOTUS_BUILD_COMMIT_SHA="${LOTUS_BUILD_COMMIT_SHA}" \
    LOTUS_BUILD_GIT_BRANCH="${LOTUS_BUILD_GIT_BRANCH}" \
    LOTUS_BUILD_REPO_URL="${LOTUS_BUILD_REPO_URL}" \
    LOTUS_BUILD_VERSION="${LOTUS_BUILD_VERSION}" \
    LOTUS_BUILD_TIMESTAMP="${LOTUS_BUILD_TIMESTAMP}" \
    LOTUS_CI_PIPELINE_ID="${LOTUS_CI_PIPELINE_ID}" \
    LOTUS_IMAGE_DIGEST="${LOTUS_IMAGE_DIGEST}"

# Create a non-root user for security compliance
RUN adduser --disabled-password --gecos '' lotus-advise

# Set the working directory
WORKDIR /app

# Copy only runtime requirements first to leverage Docker layer caching
COPY requirements-prod.txt .

# Install runtime dependencies only
RUN pip install -r requirements-prod.txt

# Copy the core application code
COPY src/ ./src/

# Change ownership of the application files to the non-root user
RUN chown -R lotus-advise:lotus-advise /app

# Switch to the non-root user
USER lotus-advise

# Expose the port uvicorn will listen on
EXPOSE 8000

# Container-level healthcheck using Python stdlib (no curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/version', timeout=3)"

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
