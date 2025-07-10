#!/bin/bash

echo "Applying Docker Permission Fix for PCAP Reporter..."
echo ""

# Set environment variables
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

echo "Environment variables set:"
echo "USER_ID=$USER_ID"
echo "GROUP_ID=$GROUP_ID"
echo ""

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down

echo ""
echo "Building containers with correct user permissions..."
echo "This may take a few minutes..."

# Rebuild with the new user configuration
docker-compose build

echo ""
echo "Starting containers..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 15

echo ""
echo "Checking container status:"
docker-compose ps

echo ""
echo "=== Permission Fix Applied Successfully! ==="
echo ""
echo "The containers now run with USER_ID=$USER_ID and GROUP_ID=$GROUP_ID"
echo "This should resolve the '[Errno 13] Permission denied: /app' error"
echo ""
echo "You can verify the fix is working by:"
echo "1. Accessing the application"
echo "2. Trying to upload a file"
echo "3. Checking that no permission errors occur"