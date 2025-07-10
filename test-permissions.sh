#!/bin/bash

echo "Testing Docker permission fix..."

# Set environment variables
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

echo "Using USER_ID=$USER_ID, GROUP_ID=$GROUP_ID"

# Build only the API container to test permissions
echo "Building API container with correct user permissions..."
docker-compose build api

# Start just the dependencies first
echo "Starting MongoDB and Redis..."
docker-compose up -d mongodb redis

# Wait a bit for services to start
echo "Waiting for services to be ready..."
sleep 10

# Test if the API container can write to the uploads directory
echo "Testing write permissions in container..."
docker-compose run --rm api /bin/bash -c "
    echo 'Testing write access to /app/uploads'
    touch /app/uploads/test-file.txt && 
    echo 'SUCCESS: Can write to uploads directory' || 
    echo 'FAILED: Cannot write to uploads directory'
    
    echo 'Testing write access to /app/logs'
    touch /app/logs/test-log.txt && 
    echo 'SUCCESS: Can write to logs directory' || 
    echo 'FAILED: Cannot write to logs directory'
    
    echo 'Current user in container:'
    id
    
    echo 'Permissions of mounted directories:'
    ls -la /app/uploads /app/logs
"

echo "Checking files created on host:"
ls -la uploads/ logs/

echo "Cleaning up test files..."
rm -f uploads/test-file.txt logs/test-log.txt

echo "Test completed."