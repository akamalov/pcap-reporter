# Problem & Solution Log

This document tracks technical problems encountered during development and the solutions or workarounds implemented.

---

## Problem 1: Text Overlapping Issues on Upload Page

**Date:** 2025-07-10  
**Phase:** Phase 3 - Frontend Foundation & UI Setup  
**Severity:** Medium  

### Description
Text elements were overlapping on the upload page, particularly in the hero section and headers, causing poor user experience and readability issues.

### Root Cause
Inconsistent CSS spacing and layout configurations causing elements to overlap, especially on different screen sizes.

### Solution
- Completely restructured the hero section layout
- Fixed text overlapping issues in hero section and headers
- Improved upload page layout with proper spacing and positioning
- Fine-tuned ThemeToggle positioning with -7px margin adjustment

### Status
**RESOLVED** - Fixed in commits 773ac71, 55d6e5a, cd86774, and 2ec9d20

---

## Problem 2: Backend API Upload Error - Permission Denied

**Date:** 2025-07-10  
**Phase:** Phase 4 - End-to-End Integration  
**Severity:** High  

### Description
When attempting to upload PCAP files through the frontend, the backend API returns a 500 Internal Server Error with the message: "Failed to submit analysis job: [Errno 13] Permission denied: '/app'"

### Root Cause
Docker container user ID mismatch - the container runs as user `app` (UID 1000) but the host directories had incompatible ownership, preventing write access to the upload directories.

### Impact
- Frontend upload functionality is implemented and working correctly
- Backend API endpoint exists but fails due to permission issues
- End-to-end file upload flow was blocked

### Solution Implemented
1. **Modified Docker Configuration**:
   - Updated `backend/Dockerfile` to accept `USER_ID` and `GROUP_ID` build arguments
   - Modified `docker-compose.yml` to pass host user/group IDs to container builds
   - Ensures container user matches host user for seamless file access

2. **Created Helper Scripts**:
   - `fix-permissions.sh` - Sets up directories and permissions
   - `verify-fix.sh` - Verifies configuration is correct
   - `apply-permission-fix.sh` - Applies complete fix with container rebuild
   - `test-permissions.sh` - Tests container write permissions

3. **Documentation**:
   - Created `DOCKER_PERMISSION_FIX.md` with complete solution documentation

### Files Modified
- `backend/Dockerfile` - Added user ID configuration for permission mapping
- `docker-compose.yml` - Added build arguments for all backend services
- Created comprehensive documentation and helper scripts

### Status
**RESOLVED** - Permission fix implemented, ready for backend deployment testing

--- 

## Problem 3: Pytest Collection Error with Pydantic Settings

**Date:** 2025-07-11
**Phase:** Phase 2 - Backend Development & Integration
**Severity:** Critical

### Description
The `pytest` suite consistently fails during the test collection phase with the error: `pydantic_settings.sources.SettingsError: error parsing value for field "ALLOWED_HOSTS" from source "DotEnvSettingsSource"`. This error blocks all backend tests from running.

### Root Cause Analysis
The error is triggered when `pytest` imports any test file that directly or indirectly imports the application's configuration module (`core.config`). The Pydantic `Settings` class is instantiated at the module level, which occurs before any `pytest` fixtures or patches can be applied. This leads to Pydantic attempting to parse environment variables (like `ALLOWED_HOSTS`) from a non-existent or malformed `.env` source in the test environment, causing a `JSONDecodeError`.

### Solutions Attempted
- **Validator Modifications**: Added logic to the Pydantic `Settings` validators to handle `None` or empty string values.
- **CLI Environment Variables**: Passed settings directly via the command line (`ALLOWED_HOSTS='[]' pytest ...`).
- **Configuration Refactoring**: Removed the global `settings` object and refactored all dependent modules to use a cached `get_settings()` function.
- **Pytest Fixture Patching**: Implemented a session-scoped `autouse` fixture in `conftest.py` to patch `core.config.get_settings` and return a test-safe `Settings` instance.

None of these attempts have resolved the error, suggesting a fundamental conflict between the application's startup configuration logic and the `pytest` test collection lifecycle.

### Solutions Implemented
- **Matplotlib/Seaborn Error Handling**: Added comprehensive error handling in `services/report_generator.py` to gracefully handle missing or unavailable matplotlib styles during test collection
- **Lazy Initialization Pattern**: Replaced module-level instantiation of `AutomatedReportGenerator` with a lazy initialization function `get_report_generator()` to prevent import-time issues
- **Import Chain Fixes**: Updated `api/v1/endpoints/export.py` to use the new lazy initialization pattern instead of importing the module-level instance

### Files Modified
- `backend/services/report_generator.py` - Added error handling for matplotlib configuration and implemented lazy initialization
- `backend/api/v1/endpoints/export.py` - Updated to use `get_report_generator()` function instead of direct import

### Status
**RESOLVED** - All 294 tests now collect successfully without any collection errors. The pytest collection phase completes without blocking errors, and backend testing is fully functional.

--- 