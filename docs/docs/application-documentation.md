# MCP-PCAP Reporter: Application Documentation

This document provides comprehensive documentation for the MCP-PCAP Reporter application, covering its architecture, setup, API, and usage. It will be updated as each implementation phase is completed.

---

## Table of Contents

1. [Current Status](#current-status)
2. [Frontend Architecture](#frontend-architecture)
3. [Development Environment](#development-environment)
4. [Known Issues](#known-issues)

---

## Current Status

### Completed Phases

✅ **Phase 0: Project Setup & Foundation**
- Complete Docker-based development environment
- All services properly configured (nginx, backend-api, backend-worker, frontend, mongodb, redis)
- Comprehensive project structure and documentation

✅ **Phase 3: Frontend Foundation & UI Setup**
- Complete Next.js application with Ant Design integration
- Responsive landing page with feature highlights
- Full-featured upload page with drag-and-drop functionality
- Dynamic report display page with data visualization
- Theme provider with dark/light mode toggle
- Comprehensive error handling and user feedback

🔄 **Phase 4: End-to-End Integration (Partially Complete)**
- Frontend successfully connects to backend API endpoints
- Upload functionality implemented with progress tracking
- Report page with real-time status polling
- **BLOCKED**: Backend API permission issue preventing file uploads

### In Progress

- Resolving backend infrastructure issues
- Backend API permission configuration

---

## Frontend Architecture

### Technology Stack

- **Framework**: Next.js 14.0.4 with TypeScript
- **UI Library**: Ant Design 5.12.8
- **Styling**: CSS Modules with Tailwind-like utilities
- **Data Fetching**: SWR 2.2.4 for API calls
- **HTTP Client**: Axios 1.6.2
- **Icons**: Ant Design Icons
- **Visualization**: Recharts 2.8.0 (for future chart implementation)
- **Diagrams**: Mermaid 10.6.1 (for network diagrams)

### Application Structure

```
frontend/src/app/
├── components/
│   ├── ThemeProvider.tsx    # Theme context provider
│   └── ThemeToggle.tsx      # Dark/light mode toggle
├── lib/
│   └── api.ts              # API service and utilities
├── page.tsx                # Landing page
├── layout.tsx              # Root layout with theme provider
├── globals.css             # Global styles
├── upload/
│   └── page.tsx            # File upload page
└── reports/
    ├── page.tsx            # Reports listing page
    └── [id]/
        └── page.tsx        # Individual report view
```

### Key Features Implemented

#### 1. Landing Page (`/`)
- Hero section with compelling value proposition
- Feature highlights with icons and descriptions
- Call-to-action buttons for navigation
- Responsive design for all device sizes
- Theme toggle integration

#### 2. Upload Page (`/upload`)
- Drag-and-drop file upload interface
- File type validation (PCAP, CAP, PCAPNG)
- Upload progress tracking
- Success/error state handling
- Automatic redirection to report page on success
- Comprehensive error messaging

#### 3. Report Page (`/reports/[id]`)
- Dynamic route handling for job IDs
- Real-time status polling with SWR
- Loading states and progress indicators
- Structured data display with Ant Design tables
- Error handling for failed analyses

#### 4. Theme System
- Light/dark mode toggle
- Persistent theme preference
- Ant Design ConfigProvider integration
- Consistent theming across all components

### API Integration

#### Service Layer (`lib/api.ts`)
- Centralized API configuration
- Error handling utilities
- File upload with progress tracking
- Report fetching with status polling
- Type-safe response interfaces

#### Key API Endpoints
- `POST /api/analyze` - File upload and analysis job submission
- `GET /api/report/{job_id}` - Report status and data retrieval
- `GET /api/health` - Service health check

### User Experience Features

- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Progressive Enhancement**: Graceful degradation for older browsers
- **Loading States**: Clear feedback during async operations
- **Error Handling**: User-friendly error messages and recovery options
- **Accessibility**: Proper ARIA labels and keyboard navigation
- **Performance**: Optimized bundle size and lazy loading

---

## Development Environment

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pcap-reporter
   ```

2. **Start the development environment**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Workflow

- Frontend development server runs on port 3000 with hot reload
- Backend API runs on port 8000 with auto-reload
- All changes are automatically reflected in the Docker environment
- MongoDB and Redis are available for backend services

---

## Known Issues

### Current Blockers

1. **Backend API Permission Error**
   - **Issue**: 500 Internal Server Error when uploading files
   - **Error**: "Failed to submit analysis job: [Errno 13] Permission denied: '/app'"
   - **Impact**: Prevents end-to-end file upload functionality
   - **Status**: Open - requires Docker container permission configuration

### Resolved Issues

1. **Text Overlapping on Upload Page**
   - **Issue**: UI elements overlapping causing poor UX
   - **Solution**: Restructured hero section and improved layout spacing
   - **Status**: Resolved in commits 773ac71, 55d6e5a, cd86774, 2ec9d20

---

*This documentation will be updated as development progresses and new features are implemented.* 