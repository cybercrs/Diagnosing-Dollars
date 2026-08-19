# Diagnosing Dollars

**Diagnosing Dollars** is an introductory financial-health learning activity. Students diagnose the fictional Gem City Outfitters by classifying balance-sheet accounts, calculating liquidity and solvency measures, comparing results, and making a lender recommendation.

The first draft contains one complete case and requires no login, database, or student-identifying information.

## Learning flow

1. Classify randomized accounts in a classified balance sheet.
2. Order current assets by liquidity and resolve context-dependent classifications.
3. Calculate working capital, current ratio, debt-to-assets ratio, and debt-to-equity ratio.
4. Make intracompany, industry-average, and intercompany comparisons.
5. Review a completed patient chart and diagnose liquidity and solvency using the whole set of evidence.

The evidence question awards partial credit, and the written rationale uses a visible three-point rubric: recommendation, liquidity evidence, and solvency evidence.

## Run locally

Use Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Run the automated checks with:

```bash
python -m unittest discover -s tests -v
python -m py_compile streamlit_app.py diagnosing_dollars/*.py
```

## Deploy with GitHub and Streamlit Community Cloud

1. Create a GitHub repository and push this project from the repository root.
2. In Streamlit Community Cloud, select the repository and branch.
3. Set the app entrypoint to `streamlit_app.py`.
4. Select Python 3.12 in the advanced deployment settings.
5. Deploy. No secrets are required for this draft.

The pinned `requirements.txt` and root-level entrypoint are ready for Community Cloud. Each push to the connected GitHub branch will update the deployed app.

## Project structure

```text
streamlit_app.py              # Interface and stage flow
diagnosing_dollars/
  case_data.py                # Case narrative, questions, and benchmarks
  engine.py                   # Calculations and scoring
tests/
  test_engine.py              # Calculation and scoring tests
.streamlit/config.toml        # App theme and server settings
.github/workflows/tests.yml   # GitHub Actions checks
requirements.txt              # Pinned deployment dependency
```

## Visual identity

The interface uses a red, navy, and white palette inspired by the University of Dayton's published red-and-blue identity. It does not bundle or reproduce an official University logo.
