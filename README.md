# AutoPortfolio Builder

FastAPI application that turns profile data into portfolio-ready content with authentication, admin tools, and export-oriented workflows.

## Overview
AutoPortfolio Builder is a web application built to help users generate professional portfolio content from structured inputs such as GitHub and LinkedIn profile data. The project combines a FastAPI backend with a lightweight frontend and includes authentication flows, dashboard views, admin reporting, and content generation workflows.

It is especially useful as a portfolio/productivity project because it blends profile ingestion, content generation, user management, and export features in one system.

## Highlights
- Generate portfolio-ready content from developer profile inputs
- Authentication flow with protected dashboard routes
- Admin panel with activity and export visibility
- GitHub and LinkedIn input handling
- Clean frontend route separation using hash-based navigation
- CSV export support for admin workflows

## Tech Stack
### Backend
- FastAPI
- Pydantic
- Uvicorn
- HTTPX

### Frontend
- Vanilla JavaScript
- HTML / CSS
- Hash-based routing

### Supporting Features
- PDF generation via `fpdf2`
- Multipart form handling
- Pytest-based tests

## Repository Structure
```text
AutoPortfolio-Builder/
├── app/
│   ├── auth/
│   ├── dashboard/
│   ├── admin/
│   ├── services/
│   ├── static/
│   └── main.py
├── templates/
├── tests/
├── requirements.txt
└── render.yaml
```

## Core Workflows
### User Flow
- Register or log in
- Access dashboard and portfolio generator
- Submit GitHub / LinkedIn profile inputs
- Generate portfolio content

### Admin Flow
- Review usage and activity data
- View users and generated resume records
- Export users, resumes, and activity as CSV

### Validation and Guardrails
- Input validation for email, GitHub, and LinkedIn fields
- Route guards for authenticated and admin-only areas
- Protected backend admin dependencies

## Frontend Routes
- `#/` landing page
- `#/login` login view
- `#/signup` signup view
- `#/dashboard` authenticated dashboard
- `#/generator` portfolio generation flow
- `#/admin` admin-only panel

## Key Backend Endpoints
### Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/google`
- `GET /api/auth/github/start`

### Product Features
- `GET /api/dashboard`
- `POST /api/profile`
- `POST /api/generate`

### Admin
- `GET /api/admin/stats`
- `GET /api/admin/users`
- `GET /api/admin/resumes`
- `GET /api/admin/activity`
- `GET /api/admin/export/users.csv`
- `GET /api/admin/export/resumes.csv`
- `GET /api/admin/export/activity.csv`

## Local Development
### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
git clone https://github.com/bhedanikhilkumar-code/AutoPortfolio-Builder.git
cd AutoPortfolio-Builder
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:
```text
http://127.0.0.1:8000/
```

## Testing
```bash
pytest
```

## Deployment
This repository includes deployment-oriented files such as:
- `render.yaml`
- `Procfile`
- `runtime.txt`

These make it easier to adapt the project for hosted environments.

## Why This Project Matters
AutoPortfolio Builder shows practical product thinking: structured input validation, authenticated UX, admin tooling, export flows, and service-oriented backend design around a clear use case.

## License
Licensed under the MIT License. See `LICENSE` for details.
