# Diagnosing Dollars: browser version

This isolated version executes Python in each learner's browser. It has no Python server, login, database, or central score store. Keep the complete static directory together and serve it over HTTP(S); opening index.html as a local file is unsupported.

The source branch is `rollout/stlite-browser-navigation`; the separate static publishing branch is `stlite-browser`. The live Community Cloud entrypoint, dependencies, theme and server settings remain unchanged on main. Do not merge the migration into main as part of this rollout.

## Build and test

From this repository root in the saved Accounting Teaching Apps environment:

```bash
/workspace/.cloud-setup/venvs/main/bin/python -m unittest discover -s tests -v
/workspace/.cloud-setup/venvs/main/bin/python -m browser.build
/workspace/.cloud-setup/venvs/main/bin/python -m browser.test_browser
```

The optional cached build flags are `--runtime-archive /tmp/assigned-runtime-cache/runtime.tgz --asset-cache /tmp/assigned-runtime-cache`. All inputs are hash-checked even when cached. Playwright and `/usr/bin/chromium` are local development tools only. Build output is `browser/dist`; fresh evidence is `browser/test-results`. Reviewed evidence is retained in `browser/validation`.

The build reuses Dock to Dollar source commit `8a0f25a2bff6f9f1eacbc8ab132ababc94974c87`: stlite 1.8.1, its patched Streamlit 1.57.0, Pyodide 0.29.3 and locally packaged, hash-verified wheels/assets. Server Streamlit 1.60.0 is never installed into stlite. The declaration extraction fails if it cannot uniquely locate the original initialization driver. Root packages are placed ahead of the browser entrypoint directory to prevent module-name collisions. A dedicated worker per browser page isolates sessions.

## Progress and review

The compact boxed Back/Forward arrows have native accessible labels, visible keyboard focus and 44px touch targets. Back only changes the viewed page. A private state copy renders earlier work as static text, with no answer controls, submit actions, hint/reveal actions or reset controls. Forward visits reached pages and stops at the actual current page. Existing activity controls earn new pages.

The seven-stage case retains its original submission and scoring rules: completed submissions unlock the next stage even when some answers are wrong. Numeric and choice drafts are also stored in a bounded, validated `draft` URL parameter. The written rationale stays within the current session and is never included in the URL; after submission the original three rubric flags remain refresh-safe.

Browser fields outside forms transmit draft changes on change while retaining explicit submission. Widget values are retained before rendering on each rerun, without relying on newer Streamlit persist_state APIs. Canonical URL snapshots retain the original validation and scoring rules; the separate `view` parameter is clamped to reached pages. Refresh and bookmarks reconstruct progress and review position. URL progress remains a learner-controlled recovery mechanism, not an authenticated grade record.

## GitHub Pages activation

GitHub reported `has_pages: false` before rollout. The available connected tools cannot configure Pages. In this repository: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: stlite-browser → Folder: / (root) → Save**. Verify the subsequent Pages build/deployment before sharing its URL. The static branch contains `.nojekyll` and preserves subdirectory asset paths. Do not replace an existing Pages site if one appears meanwhile.

The cloud proxy restriction on cybercrs.github.io remains respected. Hosted browser testing is not claimed. Local walkthroughs establish functionality, not classroom capacity; no concurrency claim is made for 40–45 or 80–135 students. Initial visits download about 57 MB of runtime files; local transfer timings are not public-site performance estimates.
