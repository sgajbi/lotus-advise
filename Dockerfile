# Use the official Python 3.11 slim image for a smaller footprint
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user for security compliance
RUN adduser --disabled-password --gecos '' dpm-user

# Set the working directory
WORKDIR /app

# Copy only the requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies without keeping the pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the core application code
COPY src/ ./src/

# Change ownership of the application files to the non-root user
RUN chown -R dpm-user:dpm-user /app

# Switch to the non-root user
USER dpm-user

# Expose the port uvicorn will listen on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
