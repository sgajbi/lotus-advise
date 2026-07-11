# Build runtime dependencies outside the final image so installer tooling does
# not become part of the release vulnerability surface.
FROM python:3.11-slim AS dependency-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements-prod.txt .

RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements-prod.txt

# Use the official Python 3.11 slim image for a smaller footprint.
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
    PATH="/opt/venv/bin:${PATH}" \
    LOTUS_BUILD_COMMIT_SHA="${LOTUS_BUILD_COMMIT_SHA}" \
    LOTUS_BUILD_GIT_BRANCH="${LOTUS_BUILD_GIT_BRANCH}" \
    LOTUS_BUILD_REPO_URL="${LOTUS_BUILD_REPO_URL}" \
    LOTUS_BUILD_VERSION="${LOTUS_BUILD_VERSION}" \
    LOTUS_BUILD_TIMESTAMP="${LOTUS_BUILD_TIMESTAMP}" \
    LOTUS_CI_PIPELINE_ID="${LOTUS_CI_PIPELINE_ID}" \
    LOTUS_IMAGE_DIGEST="${LOTUS_IMAGE_DIGEST}"

# Apply available base-image security updates, then create a non-root user.
RUN apt-get update \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' lotus-advise

# Set the working directory
WORKDIR /app

# Copy runtime dependencies from the builder and remove installer packages that
# are not needed by the running service.
COPY --from=dependency-builder /opt/venv /opt/venv
RUN rm -rf \
    /usr/local/lib/python3.11/site-packages/pip \
    /usr/local/lib/python3.11/site-packages/pip-*.dist-info \
    /usr/local/lib/python3.11/site-packages/setuptools \
    /usr/local/lib/python3.11/site-packages/setuptools-*.dist-info \
    /usr/local/lib/python3.11/site-packages/wheel \
    /usr/local/lib/python3.11/site-packages/wheel-*.dist-info \
    /opt/venv/bin/pip \
    /opt/venv/bin/pip3 \
    /opt/venv/bin/pip3.11 \
    /opt/venv/lib/python3.11/site-packages/pip \
    /opt/venv/lib/python3.11/site-packages/pip-*.dist-info \
    /opt/venv/lib/python3.11/site-packages/setuptools \
    /opt/venv/lib/python3.11/site-packages/setuptools-*.dist-info \
    /opt/venv/lib/python3.11/site-packages/wheel \
    /opt/venv/lib/python3.11/site-packages/wheel-*.dist-info

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
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
