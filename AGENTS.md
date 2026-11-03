# Instructions for AI coding agents

The rules for this repo are in [CLAUDE.md](CLAUDE.md); they apply to every agent (Kilo, Codex,
Cursor, Copilot, Claude, ...). Read it before editing anything under `docs/`.

Short version: pushing to `main` deploys the live site. Pull first; make small in-place edits to
`docs/app.js` and `docs/index.html` (never rewrite them or paste in an older copy); run
`python scripts/check_site_features.py` and make sure it prints OK; never force-push.
