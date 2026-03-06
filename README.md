# AutoPortfolio Builder

AutoPortfolio Builder is a FastAPI + vanilla JS app that generates portfolio content from GitHub/LinkedIn profile data, with authenticated dashboard and admin workflows.

## Route Map (Frontend)
- `#/` landing page only: hero, features, how-it-works, footer
- `#/login` login page (email/password + social auth buttons)
- `#/signup` signup page (email/password + social auth buttons)
- `#/dashboard` authenticated user dashboard
- `#/generator` authenticated portfolio generator
- `#/admin` authenticated admin-only panel

The app is served from `/`, and uses hash routing for clean static frontend route separation.

## Auth and Guard Flow
- Unauthenticated users are redirected from `#/dashboard`, `#/generator`, and `#/admin` to `#/login`.
- `Logout` is shown only when logged in.
- Dashboard nav entry is hidden when logged out.
- Social login buttons are rendered only in login/signup views.
- Admin route and admin navigation are shown only when `user.is_admin == true`.
- Admin CSV actions are blocked in non-admin UI state and still protected server-side by admin dependencies.

## Key API Endpoints
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/google`
- `GET /api/auth/github/start`
- `GET /api/dashboard`
- `POST /api/profile`
- `POST /api/generate`
- `GET /api/admin/stats`
- `GET /api/admin/users`
- `GET /api/admin/resumes`
- `GET /api/admin/activity`
- `GET /api/admin/export/users.csv`
- `GET /api/admin/export/resumes.csv`
- `GET /api/admin/export/activity.csv`

## Frontend Modules
- `app/static/js/state.js`
- `app/static/js/utils.js`
- `app/static/js/api.js`
- `app/static/js/router.js`
- `app/static/js/auth.js`
- `app/static/js/generator.js`
- `app/static/js/dashboard.js`
- `app/static/js/admin.js`
- `app/static/js/main.js`

## Local Run
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Start server:
```bash
uvicorn app.main:app --reload
```
3. Open `http://127.0.0.1:8000/`.

## Test
Run:
```bash
pytest
```

## Notes
- Backend admin endpoints are protected using `require_admin` dependency checks.
- Generator validates email, GitHub input (username/profile URL), and LinkedIn input (username/profile URL).
- Buttons use loading/disabled states and show clear success/error messaging across auth, generator, dashboard, and admin actions.
