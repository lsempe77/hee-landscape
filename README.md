# hee-landscape

Hybrid GitHub Pages site for the HEE (health economic evaluation) evidence map: a
static landing page at the site root (`docs/index.html` — headline stats, teaser
figures, launch button) plus the full Shinylive (WebR) interactive app under
`docs/app/`. The source Shiny app lives in the private HSF repository at
`projects/hee/analysis/shiny`. To rebuild: (1) run `R/09-build-shiny-data.R` from
`projects/hee/analysis` (refreshes `app_data.rds`, converts `figures/*.png` into
slimmed `shiny/www/*.webp`); (2) `shinylive::export("shiny", "<destdir>")`;
(3) assemble `docs/` — landing `index.html` at root, export under `docs/app/`,
teaser WebPs in `docs/figures/`, keep `docs/.nojekyll` — then commit and push to
`main`.
