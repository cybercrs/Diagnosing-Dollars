# Diagnosing Dollars — native browser app

The final student-facing app uses HTML/CSS/JavaScript with no Python, Streamlit, Pyodide, WebAssembly, runtime package, external asset request, npm runtime dependency, central storage or new service. Source lives in `native/` on `native/html-js`; publication adds only `/js/` to the existing `stlite-browser` branch. Main, the original Python application, the stlite source/root and Pages settings remain unchanged.

## Original case and scoring

The original seven stages, fifteen account classifications, liquidity order/context checks, four financial ratios, comparison table and vocabulary, diagnoses, evidence deductions, written-rationale rubric, completed patient chart and all debrief performance labels remain. Original teaching screens and case data are exported during development. There are no Receivables-specific curriculum changes.

An independent native engine recalculates all 39 points. Ratio tolerances include the original relative/absolute isclose rules. Currency and decimal display round the exact IEEE-754 value with Python-compatible ties-to-even behavior, including half-cent edge cases. Evidence selections retain partial credit and deductions. The reflection rubric uses the original normalized substring criteria. Required answers and the 20-character rationale gate remain. Once submitted, a section is locked, and its ordinary Continue action advances even after wrong answers; no score-perfect gate or new attempt system is introduced.

## Saved work and review

Original compressed version-1 `progress` tokens and bounded typed `draft` tokens remain compatible. Original account and liquidity display orders are retained exactly. To use an old bookmark, preserve its query parameters and change only the path to `/Diagnosing-Dollars/js/`. Native progress tokens are accepted by the unchanged Python validator. Query values and fragments are retained.

The native-only optional `numbers` parameter retains bounded formatted/incomplete numeric text (for example `120.0` or `1e`). Valid numerical values also remain in the original typed draft format; older apps ignore the extra native parameter. Unsupported arbitrary text is excluded. The written rationale remains **session-only**: Back/Forward within the current tab preserves it, while refresh clears its raw text. Submitted three-bit rubric outcomes survive refresh as before. No rationale text, name, identity or free-text response is written to URL storage, localStorage, sessionStorage or a server.

Compact boxed Back/Forward controls have native accessible names, visible keyboard focus and 44px targets. Back renders completed-stage feedback without editing, checks, new submissions, hint/reveal actions, scoring or reset. The Quick Reference disclosure is unavailable during review. Forward stops at the actual earned current stage. The engine enforces the same restrictions independently of the UI. Reset starts a new independently randomized case; old copied links remain their own saved work. Independent tabs/contexts share no storage.

Native comparison tables retain the original complete data, sorting, keyboard-accessible expansion and CSV download. Mobile tables scroll horizontally within a labelled region. The CSV filename and metadata contain no provisional app branding.

## Build and verification

```bash
/workspace/.cloud-setup/venvs/main/bin/python native/export.py
node --test native/tests/*.test.mjs
/workspace/.cloud-setup/venvs/main/bin/python -m unittest discover -s tests -v
/workspace/.cloud-setup/venvs/main/bin/python native/build.py
/workspace/.cloud-setup/venvs/main/bin/python native/tests/browser.py
/workspace/.cloud-setup/venvs/main/bin/python native/tests/rationale.py
```

The build copies seven native assets and a hash manifest only. `--site-output PATH` writes only `PATH/js/`. Python and Node are development tools; neither is downloaded by learners. Current ES-module browsers with Web Crypto, BigInt, structured cloning and Compression Streams are required. Serve over HTTP(S); `file://` is unsupported. Chromium is tested; other browsers and physical devices remain unmeasured.

See `VALIDATION.md` and `review/` for screenshots, browser outcomes, original/Python parity and source-protection evidence. Publishing verifies every old non-js static blob is identical and checks the exact source/static refs and Pages deployment. The known hosted proxy restriction is respected, with no alternate route. Local startup measurements are not school-network speed or classroom-capacity promises.
