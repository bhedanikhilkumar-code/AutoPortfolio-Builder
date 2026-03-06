# AutoPortfolio Builder

AutoPortfolio Builder is a FastAPI application that turns a public GitHub profile into a generated portfolio draft. It fetches profile and repository metadata from the GitHub REST API, derives portfolio sections, and renders the result in a minimal single-page UI.

## Phase 3 Features
- `GET /api/health` for health checks
- `POST /api/profile` to fetch GitHub profile and non-fork repositories
- Optional `GITHUB_TOKEN` support for authenticated GitHub API requests, with unauthenticated fallback
- Accepts GitHub username or full profile URL input (for example `https://github.com/username`)
- Consistent JSON error responses in the format `{ "error": { "code": "...", "message": "..." } }`
- `POST /api/generate` to build portfolio sections with selectable themes
- Optional AI content enrichment for About/Skills/Projects using `AI_API_KEY` (deterministic fallback when key is missing)
- `POST /api/export/html` to download the current portfolio as a standalone HTML file
- `POST /api/export/zip` to download a ZIP package containing `index.html` and `portfolio.json`
- Single-page frontend at `/` to generate, edit, save, preview, and export the portfolio in `modern` or `minimal` mode
- Expanded pytest API coverage including export flows and edge cases
- GitHub Actions CI workflow

## Tech Stack
- Backend: FastAPI
- Frontend: vanilla HTML, CSS, and JavaScript served by FastAPI
- Data source: GitHub REST API
- Optional AI provider: OpenAI-compatible Chat Completions API
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

3. Optionally copy `.env.example` and configure secrets.

4. Optionally set a GitHub token to reduce rate-limit issues:

```bash
export GITHUB_TOKEN=your_github_token
```

On Windows PowerShell:

```powershell
$env:GITHUB_TOKEN="your_github_token"
```

5. Optional AI configuration:

```bash
export AI_API_KEY=your_ai_api_key
export AI_BASE_URL=https://api.openai.com/v1
export AI_MODEL=gpt-4o-mini
```

On Windows PowerShell:

```powershell
$env:AI_API_KEY="your_ai_api_key"
$env:AI_BASE_URL="https://api.openai.com/v1"
$env:AI_MODEL="gpt-4o-mini"
```

If `AI_API_KEY` is missing, the generator still works using deterministic GitHub-based copy.

6. Start the development server:

```bash
uvicorn app.main:app --reload
```

7. Open `http://127.0.0.1:8000`.

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

Export the current portfolio as HTML:

```bash
curl -X POST http://127.0.0.1:8000/api/export/html \
  -H "Content-Type: application/json" \
  -d "{\"portfolio\":{...},\"filename\":\"my-portfolio\"}" \
  -o my-portfolio.html
```

Export the current portfolio as a ZIP package:

```bash
curl -X POST http://127.0.0.1:8000/api/export/zip \
  -H "Content-Type: application/json" \
  -d "{\"portfolio\":{...},\"filename\":\"my-portfolio\"}" \
  -o my-portfolio.zip
```

## Phase 3 UI Flow
1. Enter a GitHub username and choose a theme.
2. Generate the portfolio draft.
3. Update the draft fields in the editor:
   Hero, About, Skills, Contact, and project names/descriptions.
4. Click `Save Edits` to copy the draft into the preview/export state.
5. Export the saved version as HTML or ZIP.

PDF export is not implemented in this phase. HTML and ZIP are complete and supported.

## Future Enhancements (Planned)
- PDF export endpoint and one-click download from UI
- Persistent save/load for edited portfolio drafts
- Custom section ordering and drag-drop editor
- More portfolio themes and dark/light presets
- Social/contact block customization (X, LinkedIn, portfolio links)
- End-to-end browser test suite (Playwright)
- Optional auth + user workspace for multiple saved portfolios

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
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Deployment checklist:
1. Use Python 3.12 or later in a clean environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Ensure your platform injects `PORT` (Render does this automatically).
4. Ensure outbound access to `api.github.com`, since profile generation depends on the GitHub API.
5. If AI enrichment is enabled, ensure outbound access to your `AI_BASE_URL`.
6. This repo includes `render.yaml`, `Procfile`, and `runtime.txt` for smoother Render deployment.

## Notes
- If `GITHUB_TOKEN` is set, the backend sends authenticated GitHub API requests with `Authorization: Bearer ...`.
- If `GITHUB_TOKEN` is not set, the app still works with public GitHub API access and lower rate limits.
- If `AI_API_KEY` is set, `/api/generate` enriches About/Skills/Projects with AI-generated copy.
- If `AI_API_KEY` is not set (or AI request fails), deterministic GitHub-derived content is returned.
- The frontend shows styled error banners for validation errors, missing users, and upstream GitHub API failures.
- The frontend keeps a draft edit state separate from the saved/exported portfolio state.
- The existing `LICENSE` file is preserved unchanged.
