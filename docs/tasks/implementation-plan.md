# MCP-PCAP Reporter: Implementation Plan

This document outlines the phased implementation plan for the MCP PCAP Reporter project. It follows Test-Driven Development (TDD) principles and details each step required to build, test, and deploy the application. All tasks will be marked with a checkbox, which will be checked upon completion.

## Table of Contents
* [Phase 0: Project Setup & Foundation](#phase-0-project-setup--foundation)
* [Phase 1: Backend Core & API Development](#phase-1-backend-core--api-development)
* [Phase 2: PCAP Analysis Engine Implementation](#phase-2-pcap-analysis-engine-implementation)
* [Phase 3: Frontend Foundation & UI Setup](#phase-3-frontend-foundation--ui-setup)
* [Phase 4: End-to-End Integration](#phase-4-end-to-end-integration)
* [Phase 5: Reporting & Visualization](#phase-5-reporting--visualization)
* [Phase 6: Finalization, Documentation & Deployment Prep](#phase-6-finalization-documentation--deployment-prep)

---

## Phase 0: Project Setup & Foundation ✅

**Goal:** Establish the complete development environment, including version control, directory structure, and the Docker-based infrastructure.

- [x] **Step 0.1: Initialize Project Structure**
    - [x] Create main project directories (`backend`, `frontend`, `docs`).
    - [x] Initialize Git repository.
    - [x] Create a comprehensive `.gitignore` file (including `.env`, `node_modules`, `__pycache__`, etc.).
- [x] **Step 0.2: Dockerize the Environment**
    - [x] Create `docker-compose.yml` defining all services: `nginx`, `backend-api`, `backend-worker`, `frontend`, `mongodb`, `redis`.
    - [x] Create `Dockerfile` for the `backend` service (FastAPI + Celery).
    - [x] Create `Dockerfile` for the `frontend` service (Next.js).
    - [x] Create Nginx configuration (`nginx.conf`) to act as a reverse proxy.
- [x] **Step 0.3: Initial Service Scaffolding**
    - [x] `backend`: Create basic FastAPI app with a `/api/health` endpoint.
    - [x] `backend`: Set up Celery instance and define a simple test task.
    - [x] `backend`: Set up database models (Report, AnalysisJob, User)
    - [x] `backend`: Create API endpoints structure (health, analysis, reports)
    - [x] `backend`: Create PCAP analyzer service with hybrid tshark/Scapy engine
    - [x] `backend`: Create Celery tasks for PCAP analysis
    - [x] `backend`: Create MCP server implementation
    - [x] `frontend`: Initialize a new Next.js application.
- [x] **Step 0.4: Verify Environment**
    - [x] Created comprehensive README.md with setup instructions
    - [x] Created basic test script (backend/test_basic.py) for verification
    - [x] All services properly configured with health checks
- [x] **Phase 0 Documentation:**
    - [x] Created comprehensive README.md with development environment setup
    - [x] Created application documentation structure in docs/

---

## Phase 1: Backend Core & API Development

**Goal:** Build the core asynchronous backend API, including job submission and status retrieval endpoints, adhering to TDD.

- [ ] **Step 1.1: Setup Backend Testing Framework**
    - [ ] Add `pytest` and `httpx` to the backend dependencies.
    - [ ] Configure `pytest` to work with the FastAPI application and the Docker environment.
- [ ] **Step 1.2: Implement Health Check Endpoint**
    - [ ] (TDD) Write a test for the `/api/health` endpoint.
    - [ ] Implement the endpoint to return a success status, confirming DB and Redis connectivity.
- [ ] **Step 1.3: Implement Analysis Job Submission Endpoint**
    - [ ] (TDD) Write tests for the `start_pcap_analysis` MCP tool endpoint (`/api/analyze`).
        - Test valid PCAP file upload.
        - Test that it correctly enqueues a Celery task.
        - Test that it returns a valid `job_id`.
        - Test invalid inputs (e.g., wrong file type).
    - [ ] Implement the endpoint logic using FastAPI's `UploadFile`.
    - [ ] The endpoint should save the uploaded file to a shared volume and pass the file path to the Celery task.
- [ ] **Step 1.4: Implement Job Status/Result Endpoint**
    - [ ] (TDD) Write tests for the `get_analysis_report` MCP tool endpoint (`/api/report/{job_id}`).
        - Test retrieving status for a "PENDING" job.
        - Test retrieving status for a "COMPLETED" job.
        - Test retrieving status for a "FAILED" job.
        - Test retrieving JSON results for a completed job.
        - Test for a non-existent `job_id`.
    - [ ] Implement the endpoint logic, which queries the Celery backend (Redis) for task state and retrieves final results from MongoDB.
- [ ] **Phase 1 Documentation:**
    - [ ] Create/update `docs/docs/application-documentation.md` with an "API Endpoints" section, detailing the new endpoints with request/response examples.

---

## Phase 2: PCAP Analysis Engine Implementation

**Goal:** Implement the core PCAP analysis logic within a Celery worker, driven by tests using sample PCAP files.

- [ ] **Step 2.1: Setup Analysis Test Fixtures**
    - [ ] Create a `tests/fixtures` directory for sample `.pcap` files with known characteristics (e.g., one with clear DNS issues, one with TCP retransmissions).
- [ ] **Step 2.2: Implement High-Speed Triage (`tshark`)**
    - [ ] (TDD) Write tests that run `pyshark` on a fixture PCAP and assert that basic stats ("Top N" talkers, conversations, protocols) are correctly extracted.
    - [ ] Implement the `tshark`-based analysis logic in a Celery task.
- [ ] **Step 2.3: Implement Deep Packet Inspection (`Scapy`)**
    - [ ] (TDD) Write tests that run `Scapy` on a targeted stream from a fixture PCAP and assert that specific issues (e.g., high handshake latency, TCP Zero Window) are detected.
    - [ ] Implement the `Scapy`-based analysis logic in the Celery task.
- [ ] **Step 2.4: Data Persistence**
    - [ ] (TDD) Write tests to ensure the analysis result (a structured JSON object) is correctly saved to MongoDB upon task completion.
    - [ ] Implement the logic to connect to MongoDB from the Celery worker and save the results.
- [ ] **Phase 2 Documentation:**
    - [ ] Create/update `docs/docs/application-documentation.md` with an "Analysis Engine" section, describing the hybrid approach and the structure of the resulting JSON data.

---

## Phase 3: Frontend Foundation & UI Setup ✅

**Goal:** Build the basic structure and layout of the web interface.

- [x] **Step 3.1: Integrate UI Framework**
    - [x] Install and configure Ant Design in the Next.js application.
    - [x] Install a data fetching library like `SWR` or `React Query`.
- [x] **Step 3.2: Create Core Layout**
    - [x] Create a main application layout component with a header, content area, and footer.
    - [x] Create theme provider and toggle functionality.
- [x] **Step 3.3: Build the Upload Page**
    - [x] Create a new page for uploading PCAP files.
    - [x] Use the Ant Design `Upload` component.
    - [x] Implement file upload logic with progress tracking.
    - [x] Add comprehensive error handling and user feedback.
- [x] **Step 3.4: Build the Report Display Page**
    - [x] Create a dynamic page that takes a `job_id` from the URL (`/reports/[job_id]`).
    - [x] Add placeholder components for the report sections (Summary, "Top N" tables, Diagram).
- [x] **Step 3.5: Landing Page Implementation**
    - [x] Create responsive landing page with feature highlights.
    - [x] Implement hero section with call-to-action.
    - [x] Add navigation between pages.
- [x] **Phase 3 Documentation:**
    - [x] Create/update `docs/docs/application-documentation.md` with a "Frontend Architecture" section.

---

## Phase 4: End-to-End Integration

**Goal:** Connect the frontend and backend to create a functional user flow from upload to report view.

- [x] **Step 4.1: Implement File Upload Logic**
    - [x] Connect the Upload Page's component to the `/api/analyze` backend endpoint.
    - [x] On successful upload, automatically redirect the user to the report page (`/reports/{job_id}`).
    - [x] Add comprehensive error handling and user feedback.
    - [x] **RESOLVED**: Fixed Docker permission issue with host user ID mapping (see problems.md)
- [x] **Step 4.2: Implement Report Data Fetching**
    - [x] On the report page, use the data fetching library to poll the `/api/report/{job_id}` endpoint.
    - [x] Display a loading/processing indicator while the job status is "PENDING".
    - [x] Once the job is "COMPLETED", fetch the final JSON data and store it in the component's state.
- [x] **Step 4.3: Display Basic Report Data**
    - [x] Populate the UI with the fetched analysis results.
    - [x] Use Ant Design `Table` components to display the "Top N" statistics.
    - [x] Display the executive summary and other simple data points.
- [x] **Phase 4 Documentation:**
    - [x] Update the "Development Environment" and "API Endpoints" sections with any integration-specific notes.

---

## Phase 5: Reporting & Visualization

**Goal:** Implement the advanced visualization components for the report.

- [ ] **Step 5.1: Generate Diagram Data**
    - [ ] In the backend Celery task, add logic to generate a text-based definition for the Logical Communication Diagram (e.g., in Mermaid.js syntax).
    - [ ] Add this definition to the JSON result stored in MongoDB.
- [ ] **Step 5.2: Render the Diagram**
    - [ ] In the frontend report page, add a component that takes the diagram definition.
    - [ ] Use `Mermaid.js` or a similar library to render the diagram visually.
- [ ] **Step 5.3: Implement PDF Export**
    - [ ] Add a new backend endpoint `/api/export/pdf` that takes a `job_id`.
    - [ ] (TDD) Write tests for the PDF export functionality.
    - [ ] Implement the logic to fetch the report data, render it into an HTML template, and convert it to a professional-looking PDF using a library like WeasyPrint.
    - [ ] Add a "Download PDF" button to the frontend report page.
- [ ] **Phase 5 Documentation:**
    - [ ] Create/update `docs/docs/application-documentation.md` with a "Report Generation" section.

---

## Phase 6: Finalization, Documentation & Deployment Prep

**Goal:** Polish the application, complete all documentation, and prepare for production deployment.

- [ ] **Step 6.1: Styling and UI Polish**
    - [ ] Review the entire application for UI/UX consistency and professional appearance.
    - [ ] Add comprehensive error handling and user feedback messages.
- [ ] **Step 6.2: Finalize Documentation**
    - [ ] Review and complete all sections of `docs/docs/application-documentation.md`.
    - [ ] Create a `README.md` at the project root with instructions for production deployment.
- [ ] **Step 6.3: Production Docker Builds**
    - [ ] Optimize Dockerfiles for production (e.g., multi-stage builds, non-root users).
- [ ] **Step 6.4: Final Review**
    - [ ] Conduct a full, end-to-end test of the application.
- [ ] **Phase 6 Documentation:**
    - [ ] Mark the main application documentation as complete and version it (v1.0). 