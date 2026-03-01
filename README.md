# AutoPortfolio Builder

AutoPortfolio Builder is a FastAPI application that turns a public GitHub profile into a generated portfolio draft. It fetches profile and repository metadata from the GitHub REST API, derives portfolio sections, and renders the result in a minimal single-page UI.

## Phase 2 Features
- `GET /api/health` for health checks
- `POST /api/profile` to fetch GitHub profile and non-fork repositories
- Optional `GITHUB_TOKEN` support for authenticated GitHub API requests, with unauthenticated fallback
- Consistent JSON error responses in the format `{ "error": { "code": "...", "message": "..." } }`
- `POST /api/generate` to build portfolio sections with selectable themes
- Single-page frontend at `/` to generate and preview the portfolio in `modern` or `minimal` mode
- Pytest API coverage
- GitHub Actions CI workflow

## Tech Stack
- Backend: FastAPI
- Frontend: vanilla HTML, CSS, and JavaScript served by FastAPI
- Data source: GitHub REST API
- Testing: pytest

## Project Structure
- `app/main.py`: FastAPI app and routes
- `app/schemas.py`: request and response models
- `app/services/github.py`: GitHub API integration
- `app/services/portfolio.py`: portfolio generation logic
- `app/static/index.html`: frontend UI
- `tests/test_api.py`: API test suite
- `.github/workflows/ci.yml`: CI pipeline

## Local Run
1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optionally set a GitHub token to reduce rate-limit issues:

```bash
export GITHUB_TOKEN=your_github_token
```

On Windows PowerShell:

```powershell
$env:GITHUB_TOKEN="your_github_token"
```

4. Start the development server:

```bash
uvicorn app.main:app --reload
```

5. Open `http://127.0.0.1:8000`.

## API Usage

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Fetch a GitHub profile:

```bash
curl -X POST http://127.0.0.1:8000/api/profile \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"octocat\"}"
```

Generate a portfolio:

```bash
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d @profile-response.json
```

Generate a portfolio with a specific theme:

```bash
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"profile\":{...},\"repos\":[...],\"theme\":\"minimal\"}"
```

## Test

Run the test suite:

```bash
pytest
```

The CI workflow runs the same test command on pushes to `main` and on pull requests.

## Deploy

This app can be deployed to any platform that supports ASGI applications.

Recommended production start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Deployment checklist:
1. Use Python 3.12 or later in a clean environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Expose port `8000` or map your platform port to the Uvicorn process.
4. Ensure outbound access to `api.github.com`, since profile generation depends on the GitHub API.

## Notes
- If `GITHUB_TOKEN` is set, the backend sends authenticated GitHub API requests with `Authorization: Bearer ...`.
- If `GITHUB_TOKEN` is not set, the app still works with public GitHub API access and lower rate limits.
- The frontend shows styled error banners for validation errors, missing users, and upstream GitHub API failures.
- The existing `LICENSE` file is preserved unchanged.
