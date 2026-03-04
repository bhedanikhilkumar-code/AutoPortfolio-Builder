# FUTURE_ROADMAP.md

## Phase 4 (Next)
- [ ] PDF export (`/api/export/pdf`) with clean printable template
- [ ] Professional multi-template PDF resume engine (modern / classic / ATS)
- [ ] Deterministic per-user PDF style selection (same user => stable style; Try Another => alternate style)
- [ ] Variant-aware PDF output matching selected draft variation (1/2/3)
- [ ] Strong typography + spacing system for recruiter-friendly print quality
- [ ] Save edited portfolio draft as JSON and reload later
- [ ] Improve export naming/versioning

## Phase 5
- [ ] Custom layout editor (section reorder)
- [ ] Additional themes (developer, minimal-dark, creative)
- [ ] Better project curation rules (quality score)

## Phase 6
- [ ] Auth (optional) + user workspace
- [ ] Multiple portfolios per user
- [ ] Shareable public links

## Testing Upgrades
- [ ] End-to-end tests (Playwright)
- [ ] API contract tests for export responses
- [ ] CI matrix (Python 3.11 + 3.12)

## DevOps Improvements
- [ ] Render deploy status badge in README
- [ ] Production logging + error monitoring
- [ ] Health/readiness split endpoints
