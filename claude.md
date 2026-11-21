my\_claude\_md = """

\# CLAUDE.md



\## Project Overview

SmartStudy AI is a personalised AI learning companion for Singapore Primary 2 to Primary 4 students. Parents upload their children's Mathematics and English worksheets, and the application uses AI to generate simple concept explanations, personalised practice exercises, and learning performance analysis. Students use the application to practise and improve their understanding, while parents monitor their progress and identify areas that need more attention.



\## Stack

\- Frontend: Next.js

\- Backend: Python, FastAPI

\- Database: PostgreSQL

\- AI/LLM: OpenAI API

\- Document Processing: PyMuPDF





\## Commands

\# FRONTEND



\# Navigate to frontend directory

cd frontend



\# Install dependencies

npm install



\# Start development server

npm run dev



\# Run lint checks

npm run lint



\# Build for production

npm run build



\# Start production server

npm run start



\# BACKEND



\# Navigate to backend directory

cd backend



\# Install dependencies

uv sync



\# Start FastAPI development server

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000



\# Run automated tests

uv run pytest



\# Run tests with verbose output

uv run pytest -v



\# Run tests with coverage (requires pytest-cov)

uv run pytest --cov=app



\# Check Python syntax

uv run python -m compileall app



\# DATABASE



\# Run database migrations (if Alembic is configured)

uv run alembic upgrade head



\# Generate a new migration

uv run alembic revision --autogenerate -m "describe\_change"



\# GIT



\# Check working changes

git status



\# Stage and commit changes

git add .

git commit -m "describe changes"



\# Push changes to GitHub

git push origin main



\# Deployment is handled by the configured GitHub Actions

\# and hosting provider workflows.



\## Architecture

/frontend

•  /app — Next.js App Router pages, layouts and application routes.

/dashboard — Parent dashboard and learning summaries.

/students — Student profiles and management.

/worksheets — Worksheet upload and processing status.

/learning — Concept explanations and practice exercises.

/progress — Student performance and learning analytics.

/lib - Frontend utilities, API client, authentication helpers and shared functions.

/components - Reusable UI components such as navigation, forms, upload controls, exercise cards and dashboards.



/backend

/app — FastAPI application package.

/api — REST API routes and endpoint definitions.

/core — Configuration, environment variables, security and authentication.

/models — Database models and ORM definitions.

/schemas — Pydantic request and response schemas.

/services — Business logic and application services.

worksheet\_service.py — Worksheet upload and processing.

document\_service.py — PDF extraction and OCR.

ai\_service.py — OpenAI API integration.

exercise\_service.py — Practice exercise generation and grading.

analytics\_service.py — Learning performance analysis.

main.py — FastAPI application entry point.

/tests — Backend unit tests, API tests and integration tests.



\## Key Constraints

\- No hardcoded secrets: Never hardcode OpenAI API keys, database credentials, passwords or other secrets. Use environment variables and secure secrets management. Never expose backend secrets in frontend code.

\- Input validation: All API endpoints must validate incoming data using Pydantic schemas. Validate uploaded worksheet file types, file sizes and content before processing.

\- Async/await: Use async/await for asynchronous FastAPI operations, database access and external API calls. Avoid blocking operations in asynchronous request handlers.

\- AI content accuracy: AI-generated explanations and practice exercises must be grounded in uploaded worksheet content. Validate structured AI responses before saving or displaying them. Never assume AI-generated educational answers are automatically correct.

\- Child safety and privacy: Design the application for Primary 2 to Primary 4 students. Use age-appropriate language and interfaces. Minimise collection of children's personal information, enforce parent-level access controls and protect uploaded worksheets and student records.

\- MVP scope: Only implement Singapore Primary 2 to Primary 4 Mathematics and English functionality. Do not introduce unrequested features such as live tutoring, social networking, school portals or native mobile applications without approval.





\## Coding Conventions

\- Python: Follow PEP 8 conventions. Use descriptive function and variable names, type hints and clear docstrings.

\- TypeScript: Use TypeScript with strict typing. Avoid any unless absolutely necessary. Define reusable interfaces and types for API requests and responses.

\- API design: Use RESTful endpoint conventions, appropriate HTTP status codes and consistent JSON response formats. Keep API routes separate from business logic by using service modules.

\- Component design: Build reusable React components. Keep UI components separate from API communication and business logic. Use responsive layouts suitable for desktop, tablet and mobile devices.

\- Error handling: Handle errors explicitly. Return meaningful API error responses, log technical details securely and display simple, user-friendly messages in the frontend.

\- Testing: Write automated tests for new backend functionality and important frontend workflows. Mock external OpenAI API calls in automated tests where appropriate.

\- Database: Use migrations for schema changes. Maintain proper foreign keys, relationships and indexes. Never delete or modify existing database structures without checking their dependencies.

\- Documentation: Update README.md and spec.md when introducing significant architectural changes, new dependencies or changes to application behaviour.



