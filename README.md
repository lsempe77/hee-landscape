# HEE evidence map — interactive

Public static site for the health economic evaluation evidence map: pure HTML/JS
(no server, no WebR), served from `docs/` via GitHub Pages at
<https://sempe.dev/hee-landscape/>.

The full build/test/publish runbook, decision log and known gotchas live in
**`WEBAPP.md`** in the HSF analysis repo (`projects/hee/analysis/WEBAPP.md`);
the site source is `projects/hee/analysis/webapp/site/`. JS data semantics:
`webapp/DATA_CONTRACT.md` in the same repo.

Rebuild & republish (from `projects/hee/analysis`):
`R/09-build-shiny-data.R` → `R/10-build-webapp-data.R` →
`node webapp/test/run-tests.mjs` (all assertions must pass) → copy
`webapp/site/*` into `docs/` (keep `docs/.nojekyll`) → commit → push `main`.

Runtime deps are pinned jsdelivr CDNs: plotly.js-dist-min 2.35.2 (full
bundle), tom-select 2.3.1, noUiSlider 15.8.1, Google Fonts (Newsreader +
Inter). No build step, no bundler.
