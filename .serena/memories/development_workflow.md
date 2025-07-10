# Development Workflow

## Task Completion Checklist

### Before Making Changes
1. Review implementation plan phase status
2. Read relevant memories for context
3. Check current git status and recent commits
4. Identify dependencies and impact scope

### During Development
1. Follow TDD approach where applicable
2. Run tests frequently during development
3. Use appropriate code formatting and linting
4. Document any architectural decisions

### After Task Completion
1. **Code Quality Check**:
   ```bash
   cd backend
   black .
   isort .
   flake8
   mypy .
   ```

2. **Run Tests**:
   ```bash
   pytest tests/unit/
   pytest tests/integration/
   ```

3. **Frontend Quality Check**:
   ```bash
   cd frontend
   npm run lint
   npm run type-check
   npm run build  # ensure it builds
   ```

4. **Integration Testing**:
   ```bash
   # Start all services
   docker-compose up -d
   
   # Test API endpoints
   curl http://localhost:8000/health
   
   # Test frontend
   curl http://localhost:3000
   ```

5. **Documentation Updates**:
   - Update implementation plan progress
   - Document any new problems in docs/tasks/problems.md
   - Update README.md if new setup steps are needed

## Git Workflow
- Feature branches for new development
- Descriptive commit messages
- Regular commits with logical chunks
- Testing before commits

## Current Priorities
1. Fix backend permission issue (Docker/file system)
2. Complete Phase 1 backend API development
3. Integrate Phase 2 PCAP analysis engine
4. Complete end-to-end upload workflow