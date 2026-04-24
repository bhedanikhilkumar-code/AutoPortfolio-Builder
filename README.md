# AutoPortfolio Builder

<p align="left">
  <a href="https://github.com/bhedanikhilkumar-code/AutoPortfolio-Builder"><img src="https://img.shields.io/badge/Repo-GitHub-111827?style=for-the-badge&logo=github&logoColor=white" alt="Repo" /></a>
  <a href="https://autoportfolio-builder.onrender.com"><img src="https://img.shields.io/badge/Live%20Demo-Render-0A66C2?style=for-the-badge&logo=render&logoColor=white" alt="Live Demo" /></a>
  <img src="https://img.shields.io/badge/Backend-FastAPI-111827?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
</p>

FastAPI portfolio generator that turns profile inputs into portfolio-ready content with authentication, admin tools, and export workflows.

## What This Project Solves
Creating portfolio content manually can be repetitive, inconsistent, and time-consuming.

AutoPortfolio Builder is designed to reduce that friction by taking structured inputs such as GitHub and LinkedIn data, processing them through a web workflow, and generating portfolio-oriented output in a more streamlined way.

## Demo
- **Live app:** https://autoportfolio-builder.onrender.com

## Key Capabilities
- Accept GitHub and LinkedIn-oriented profile inputs
- Generate portfolio-ready content from structured user data
- Provide authentication and protected user flows
- Include admin views for usage tracking and exports
- Support CSV exports for users, resumes, and activity data
- Add validation and guardrails around core input flows

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

## Workflow Overview
### User Flow
- Register or log in
- Access dashboard and portfolio generator
- Submit GitHub / LinkedIn profile inputs
- Generate portfolio content

### Admin Flow
- Review usage and activity data
- View users and generated resume records
- Export users, resumes, and activity as CSV

### Validation & Guardrails
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

## Getting Started
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

## Why This Project Stands Out
AutoPortfolio Builder shows practical product thinking around a clear use case: transforming structured profile data into usable portfolio content while supporting authentication, admin tooling, validation, and exports.

## Deployment
This repository includes deployment-oriented files such as:
- `render.yaml`
- `Procfile`
- `runtime.txt`

## License
Licensed under the MIT License. See `LICENSE` for details.
