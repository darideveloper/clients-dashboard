# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app/

# Ensure start script is executable
RUN chmod +x /app/start.sh

# Required ARGs and ENVs for Build-Time operations
# These must be passed via Coolify's Build Environment Variables
ARG SECRET_KEY
ARG DB_ENGINE
ARG DB_NAME
ARG DB_USER
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT
ARG CORS_ALLOWED_ORIGINS
ARG CSRF_TRUSTED_ORIGINS

# AWS and Storage ARGs
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_STORAGE_BUCKET_NAME
ARG AWS_S3_REGION_NAME
ARG AWS_S3_ENDPOINT_URL
ARG AWS_S3_CUSTOM_DOMAIN
ARG STORAGE_AWS

# General Configuration ARGs
ARG ENV
ARG DEBUG
ARG ALLOWED_HOSTS

# Export them as ENVs so the 'RUN' commands below can see them
ENV SECRET_KEY=${SECRET_KEY} \
    DB_ENGINE=${DB_ENGINE} \
    DB_NAME=${DB_NAME} \
    DB_USER=${DB_USER} \
    DB_PASSWORD=${DB_PASSWORD} \
    DB_HOST=${DB_HOST} \
    DB_PORT=${DB_PORT} \
    CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS} \
    CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS}

ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
    AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
    AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME} \
    AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME} \
    AWS_S3_ENDPOINT_URL=${AWS_S3_ENDPOINT_URL} \
    AWS_S3_CUSTOM_DOMAIN=${AWS_S3_CUSTOM_DOMAIN} \
    STORAGE_AWS=${STORAGE_AWS}

ENV ENV=${ENV} \
    DEBUG=${DEBUG} \
    ALLOWED_HOSTS=${ALLOWED_HOSTS}

# Install system dependencies (e.g., for PostgreSQL support)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (for caching)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port that Django/Gunicorn will run on
EXPOSE 80

# Command to run the start script
CMD ["./start.sh"]
