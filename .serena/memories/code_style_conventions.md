# Code Style and Conventions

## Python Backend Style
- **Formatter**: Black (line length: 88 characters)
- **Import Sorting**: isort with Black compatibility
- **Linting**: flake8 for code quality
- **Type Checking**: mypy for static type analysis
- **Docstrings**: Required for all public functions and classes
- **Naming**: Snake_case for variables/functions, PascalCase for classes

## Backend Architecture Patterns
- **FastAPI**: Dependency injection pattern for services
- **Pydantic**: Models for request/response validation
- **Beanie ODM**: MongoDB document models with async/await
- **Service Layer**: Business logic separated from API endpoints
- **TDD**: Test-driven development with pytest

## Frontend Style (TypeScript/React)
- **ESLint**: Next.js configuration with TypeScript support
- **Naming**: camelCase for variables/functions, PascalCase for components
- **Components**: Functional components with hooks
- **State Management**: React state + SWR for data fetching
- **Styling**: Ant Design components with custom CSS modules

## File Organization
```
backend/
├── api/v1/endpoints/  # API route handlers
├── core/              # Configuration and core services
├── models/            # Pydantic/Beanie data models
├── services/          # Business logic
├── tasks/             # Celery tasks
└── tests/             # Unit and integration tests

frontend/
├── src/app/           # Next.js app directory
├── src/components/    # Reusable React components
└── src/types/         # TypeScript type definitions
```

## Database Conventions
- **Collections**: Snake_case naming (e.g., analysis_jobs)
- **Fields**: Snake_case for consistency with Python
- **IDs**: MongoDB ObjectId with string conversion
- **Timestamps**: UTC datetime with timezone awareness