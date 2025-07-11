# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpcap-dev \
    libpcap0.8-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user with specific UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID app && \
    useradd -u $USER_ID -g $GROUP_ID --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip

# Switch to app user and install packages
USER app
RUN pip install --no-cache-dir --user -r requirements.txt

# Switch back to root for remaining setup
USER root

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/home/app/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpcap0.8 \
    tshark \
    && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user with specific UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID app && \
    useradd -u $USER_ID -g $GROUP_ID --create-home --shell /bin/bash app

# Copy Python dependencies from builder stage
COPY --from=builder /home/app/.local /home/app/.local

# Set work directory
WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 