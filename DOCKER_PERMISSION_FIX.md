# Docker Permission Fix Documentation

## Problem
The PCAP Reporter application was experiencing permission issues when trying to write files to the uploads directory, resulting in the error:
```
Failed to submit analysis job: [Errno 13] Permission denied: '/app'
```

## Root Cause
The Docker container was creating an `app` user with a different UID than the host user, causing permission mismatches when mounting host directories into the container.

## Solution Implemented

### 1. Modified Dockerfile
Updated `/backend/Dockerfile` to accept build arguments for user and group IDs:

```dockerfile
# Create and use a non-root user with specific UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID app && \
    useradd -u $USER_ID -g $GROUP_ID --create-home --shell /bin/bash app
```

This change was applied to both the builder stage and production stage of the multi-stage build.

### 2. Updated docker-compose.yml
Modified all services (api, celery-worker, celery-beat, flower) to pass the host user/group IDs as build arguments:

```yaml
build:
  context: ./backend
  dockerfile: Dockerfile
  args:
    USER_ID: ${USER_ID:-1000}
    GROUP_ID: ${GROUP_ID:-1000}
```

### 3. Created Helper Scripts

#### fix-permissions.sh
- Creates uploads and logs directories if they don't exist
- Sets proper permissions (755)
- Sets ownership to current user
- Exports USER_ID and GROUP_ID environment variables

#### test-permissions.sh
- Tests write permissions in Docker containers
- Verifies the fix works correctly

## How to Apply the Fix

1. **Run the permission fix script:**
   ```bash
   ./fix-permissions.sh
   ```

2. **Export environment variables:**
   ```bash
   export USER_ID=$(id -u) GROUP_ID=$(id -g)
   ```

3. **Rebuild and restart containers:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Verification

After applying the fix, the Docker containers will:
- Run with the same UID/GID as the host user
- Have write access to the uploads and logs directories
- Eliminate permission denied errors when uploading files

## Files Modified
- `/backend/Dockerfile` - Added USER_ID and GROUP_ID build arguments
- `/docker-compose.yml` - Added build args for all backend services
- Created `fix-permissions.sh` - Helper script for setup
- Created `test-permissions.sh` - Verification script

## Environment Variables
- `USER_ID` - The user ID to use in Docker containers (defaults to 1000)
- `GROUP_ID` - The group ID to use in Docker containers (defaults to 1000)

These can be set automatically by running `./fix-permissions.sh` or manually:
```bash
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
```