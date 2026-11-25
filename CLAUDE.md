# Working on the HEE evidence map

Read this before editing anything under `docs/`. AGENTS.md says the same for other AI tools.

**Anything pushed to `main` goes live** at <https://3ieimpact.pages.dev/hee/>. Several people
(and their AI agents) push to this repo, so the main risk is undoing someone else's recent
design work without noticing.

**Working on the Wellcome priority themes page?** Read README "Read first: Wellcome priority themes
page" before anything else. It lists the visual and wording changes already made (17 studies added
on review and marked ◆, rewritten Technical details), which must not be redone or reverted.
Build the page with `scripts/build_wellcome_analysis_gbd_v6.py`, and never edit the exported HTML
by hand.

## Do not overwrite recent design features

1. **Pull first.** Run `git pull` before you start editing, and again before you push.
2. **Edit `docs/app.js` and `docs/index.html` in place, with small targeted edits.** Never
   rewrite or regenerate either file wholesale, and never paste in a copy from another
   folder, branch, chat, or an earlier version.
3. **Protected features** are listed in `FEATURES` in `scripts/check_site_features.py`
   (for example: each Overview card links to the right place: Studies → cumulative
   publication trend, the others → their Thematic analysis page via `TILE_THEME`; theme
   pages repeat their Overview cards; DOI links in study lists; CSV download progress bar;
   the Explorer HALY filter opens on "All"). Keep them working unless the user explicitly
   asks to change one.
4. **Run `python scripts/check_site_features.py`** after editing `docs/`. It must print OK.
   If it fails, restore what you removed (see `git log -p docs/app.js`); do not edit the
   check to make it pass unless the user asked for that feature to be removed or changed.
5. **When you add a design feature** colleagues should not lose, add an entry to `FEATURES`
   and a line to README "Latest updates" in the same commit.
6. **Bump `BUILD`** in `docs/app.js` and the matching `app.js?v=` in `docs/index.html` on every
   change to the site, including data-only changes (the check verifies they match).
7. **Never force-push `main`**, and never use `git push --no-verify` unless the user asks.
8. When a merge conflict touches `docs/app.js` or `docs/index.html`, keep both sides' features;
   do not resolve it by taking one whole side.

## Never commit secrets

The repo, the fork and the site are public, and git history keeps everything ever pushed.

- Read API keys (OpenRouter etc.) from environment variables, e.g.
  `os.environ["OPENROUTER_API_KEY"]`; never write a key, token or password into a script,
  notebook, log, output file or commit message. Local `.env` / `.Renviron` files are gitignored.
- Run `python scripts/check_secrets.py` before committing new scripts or outputs; it must print OK.
  (The pre-push hook runs it on every push to every remote.)
- If a real key is ever found in a commit, tell the user to revoke it with the provider first;
  deleting it from the repo afterwards does not make it safe.

## Other house rules

- Don't top-level-access `db` in `docs/app.js`; test startup in headless Chrome.
- Save substantial script changes as a new versioned copy (`*_v2.py`) rather than editing in place.
- Wording: the base includes reviews, so say "studies" or "economic evidence", not
  "economic evaluations"; keep site denominators the same as the manuscript.
