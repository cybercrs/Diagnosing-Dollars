from __future__ import annotations

import html
import random
from typing import Iterable

import streamlit as st

from diagnosing_dollars.case_data import (
    ACCOUNTS,
    ANALYSIS_QUESTIONS,
    BENCHMARKS,
    CATEGORIES,
    COMPANY_DESCRIPTION,
    COMPANY_NAME,
    COMPARISON_OPTIONS,
    COMPARISON_QUESTIONS,
    CONTEXT_QUESTIONS,
    CORRECT_EVIDENCE,
    CURRENT_FINANCIALS,
    DIAGNOSIS_QUESTIONS,
    EVIDENCE_OPTIONS,
    LIQUIDITY_ORDER,
    PRIOR_FINANCIALS,
)
from diagnosing_dollars.engine import (
    calculate_ratios,
    format_currency,
    score_classifications,
    score_evidence,
    score_multiple_choice,
    score_order,
    score_ratio_entry,
    score_reflection,
)


st.set_page_config(
    page_title="Diagnosing Dollars",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


UD_RED = "#D50032"
UD_BLUE = "#002554"
UD_PALE_BLUE = "#EAF1F8"

STAGES = (
    "Patient Intake",
    "Classify the Evidence",
    "Check Liquidity",
    "Ratio Lab",
    "Comparisons",
    "Make the Diagnosis",
    "Case Debrief",
)

MAX_SCORES = {
    "classification": len(ACCOUNTS),
    "liquidity": 1 + len(CONTEXT_QUESTIONS),
    "ratios": 4,
    "analysis": len(ANALYSIS_QUESTIONS) + len(COMPARISON_QUESTIONS),
    "diagnosis": len(DIAGNOSIS_QUESTIONS) + 4 + 3,
}


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --ud-red: {UD_RED};
            --ud-blue: {UD_BLUE};
            --ud-pale-blue: {UD_PALE_BLUE};
            --ink: #10233f;
            --muted: #53657d;
            --paper: #ffffff;
            --line: #d9e1ea;
        }}

        .stApp {{
            background:
                radial-gradient(circle at 100% 0%, rgba(213, 0, 50, 0.07), transparent 28rem),
                linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
            color: var(--ink);
        }}

        .block-container {{
            max-width: 1120px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }}

        h1, h2, h3 {{ color: var(--ud-blue); letter-spacing: -0.025em; }}
        h1 {{ font-weight: 850 !important; }}

        .brand-shell {{
            background: linear-gradient(120deg, var(--ud-blue) 0%, #063d78 100%);
            border-radius: 24px;
            color: white;
            overflow: hidden;
            padding: 1.6rem 1.8rem;
            position: relative;
            box-shadow: 0 18px 46px rgba(0, 37, 84, 0.18);
            margin-bottom: 1.25rem;
        }}

        .brand-shell::after {{
            background: var(--ud-red);
            content: "";
            height: 8px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .brand-kicker {{
            color: #b9d3ee;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }}

        .brand-title {{
            color: white;
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 900;
            letter-spacing: -0.045em;
            line-height: 0.98;
            margin: 0;
        }}

        .brand-subtitle {{
            color: #dce8f4;
            font-size: 1.02rem;
            margin: 0.7rem 0 0;
            max-width: 48rem;
        }}

        .clinical-card {{
            background: rgba(255, 255, 255, 0.93);
            border: 1px solid var(--line);
            border-left: 5px solid var(--ud-red);
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 37, 84, 0.07);
            margin: 0.75rem 0 1.25rem;
            padding: 1rem 1.15rem;
        }}

        .clinical-label {{
            color: var(--ud-red);
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        .clinical-title {{ color: var(--ud-blue); font-size: 1.15rem; font-weight: 850; margin: 0.22rem 0; }}
        .clinical-copy {{ color: var(--muted); margin: 0; }}

        .stage-line {{
            color: var(--ud-blue);
            display: flex;
            font-size: 0.83rem;
            font-weight: 800;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }}

        .formula-chip {{
            background: var(--ud-pale-blue);
            border: 1px solid #c9d9e9;
            border-radius: 12px;
            color: var(--ud-blue);
            font-weight: 750;
            margin: 0.35rem 0;
            padding: 0.65rem 0.8rem;
        }}

        .feedback-row {{
            border-bottom: 1px solid #e7ecf2;
            padding: 0.7rem 0;
        }}

        .feedback-row:last-child {{ border-bottom: 0; }}
        .feedback-good {{ color: #176b45; font-weight: 800; }}
        .feedback-fix {{ color: #a33232; font-weight: 800; }}

        .vital-grid {{
            display: grid;
            gap: 0.75rem;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            margin: 0.75rem 0 1.25rem;
        }}

        .vital-box {{
            background: white;
            border: 1px solid var(--line);
            border-radius: 14px;
            box-shadow: 0 6px 18px rgba(0, 37, 84, 0.05);
            min-width: 0;
            padding: 0.8rem 0.9rem;
        }}

        .vital-label {{
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 750;
            line-height: 1.2;
            min-height: 1.8em;
        }}

        .vital-value {{
            color: var(--ink);
            font-size: clamp(1.05rem, 1.65vw, 1.45rem);
            font-variant-numeric: tabular-nums;
            font-weight: 750;
            line-height: 1.25;
            white-space: nowrap;
        }}

        .chart-table {{
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.88rem;
            margin-bottom: 1rem;
            overflow: hidden;
            width: 100%;
        }}

        .chart-table th {{
            background: var(--ud-blue);
            color: white;
            padding: 0.65rem 0.75rem;
            text-align: left;
        }}

        .chart-table td {{
            background: white;
            border-bottom: 1px solid var(--line);
            padding: 0.55rem 0.75rem;
            vertical-align: top;
        }}

        .chart-table td:last-child {{
            font-variant-numeric: tabular-nums;
            text-align: right;
            white-space: nowrap;
        }}

        .chart-section td {{
            background: var(--ud-pale-blue);
            color: var(--ud-blue);
            font-weight: 850;
        }}

        .chart-total td {{ font-weight: 850; }}

        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid var(--line);
            border-radius: 14px;
            box-shadow: 0 6px 18px rgba(0, 37, 84, 0.05);
            padding: 0.8rem 1rem;
        }}

        div[data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem;
        }}

        .stButton > button, .stFormSubmitButton > button {{
            border-radius: 999px;
            font-weight: 800;
            min-height: 2.8rem;
        }}

        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
            background: var(--ud-red);
            border-color: var(--ud-red);
        }}

        div[data-testid="stProgress"] > div > div > div {{ background-color: var(--ud-red); }}

        @media (min-width: 769px) {{
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapsedControl"] {{
                display: none !important;
            }}
        }}

        @media (max-width: 640px) {{
            .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }}
            .brand-shell {{ border-radius: 18px; padding: 1.35rem 1.15rem; }}
            .clinical-card {{ padding: 0.9rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "stage": 0,
        "results": {},
        "stage_reviewed": {},
        "reflection": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    session_random = random.SystemRandom()
    if "account_order" not in st.session_state:
        account_order = list(range(len(ACCOUNTS)))
        session_random.shuffle(account_order)
        st.session_state.account_order = account_order
    if "liquidity_option_order" not in st.session_state:
        liquidity_option_order = list(LIQUIDITY_ORDER)
        session_random.shuffle(liquidity_option_order)
        st.session_state.liquidity_option_order = liquidity_option_order


def scroll_to_top_on_stage_change() -> None:
    """Start each new learning stage at its heading without disrupting form reruns."""
    stage = st.session_state.stage
    if st.session_state.get("_top_stage") == stage:
        return

    st.iframe(
        f"""
        <script>
        const stage = {stage};
        const scrollMain = () => {{
            const main = window.parent.document.querySelector('section[data-testid="stMain"]');
            if (main) main.scrollTo({{ top: 0, left: 0, behavior: 'instant' }});
        }};
        scrollMain();
        window.setTimeout(scrollMain, 80);
        </script>
        """,
        height=1,
        width=1,
        tab_index=-1,
    )
    st.session_state._top_stage = stage


def reset_case() -> None:
    for key in list(st.session_state):
        del st.session_state[key]
    st.rerun()


def render_header() -> None:
    st.markdown(
        """
        <div class="brand-shell">
            <div class="brand-kicker">Financial Health Lab</div>
            <div class="brand-title">Diagnosing Dollars</div>
            <p class="brand-subtitle">Read the balance sheet. Check the vital signs. Make a diagnosis supported by evidence.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress() -> None:
    stage = st.session_state.stage
    st.markdown(
        f'<div class="stage-line"><span>{html.escape(STAGES[stage])}</span><span>{stage + 1} of {len(STAGES)}</span></div>',
        unsafe_allow_html=True,
    )
    st.progress(stage / (len(STAGES) - 1))


def clinical_card(label: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="clinical-card">
            <div class="clinical-label">{html.escape(label)}</div>
            <div class="clinical-title">{html.escape(title)}</div>
            <p class="clinical-copy">{html.escape(copy)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.title("Patient Chart")
        st.caption(COMPANY_NAME)
        st.progress(st.session_state.stage / (len(STAGES) - 1))

        with st.expander("Quick Reference"):
            st.markdown(
                """
                **Liquidity** is the ability to pay obligations due within the next year or operating cycle.

                **Solvency** is the ability to pay interest and repay debt at maturity.
                """
            )
            st.markdown('<div class="formula-chip">Working capital = Current assets − Current liabilities</div>', unsafe_allow_html=True)
            st.markdown('<div class="formula-chip">Current ratio = Current assets ÷ Current liabilities</div>', unsafe_allow_html=True)
            st.markdown('<div class="formula-chip">Debt to assets = Total liabilities ÷ Total assets</div>', unsafe_allow_html=True)
            st.markdown('<div class="formula-chip">Debt to equity = Total liabilities ÷ Total equity</div>', unsafe_allow_html=True)

        if st.button("Restart Case", width="stretch"):
            reset_case()


def advance() -> None:
    st.session_state.stage = min(st.session_state.stage + 1, len(STAGES) - 1)
    st.rerun()


def stage_result_banner(score: int, maximum: int) -> None:
    if score == maximum:
        st.success(f"Vital signs recorded: {score} of {maximum} correct.")
    elif score >= maximum * 0.7:
        st.info(f"Good clinical progress: {score} of {maximum} correct. Review the notes below.")
    else:
        st.warning(f"This section needs another look: {score} of {maximum} correct. Review the notes below before continuing.")


def feedback_list(items: Iterable[dict[str, object]], show_name: bool = False) -> None:
    for item in items:
        marker = "✓" if item["is_correct"] else "↺"
        css = "feedback-good" if item["is_correct"] else "feedback-fix"
        name = f"<strong>{html.escape(str(item.get('name', '')))}</strong><br>" if show_name else ""
        chosen = html.escape(str(item.get("chosen", "")))
        correct = html.escape(str(item.get("correct", "")))
        answer_line = "Correct" if item["is_correct"] else f"Your answer: {chosen or 'No answer'} · Correct: {correct}"
        why = html.escape(str(item.get("why", "")))
        st.markdown(
            f'<div class="feedback-row">{name}<span class="{css}">{marker} {answer_line}</span><br><small>{why}</small></div>',
            unsafe_allow_html=True,
        )


def render_intake() -> None:
    st.header("Patient Intake")
    clinical_card("New patient", COMPANY_NAME, COMPANY_DESCRIPTION)

    st.subheader("Your Assignment")
    st.write(
        "You are the financial health team. Organize the balance-sheet evidence, calculate the patient's vital signs, compare the results, and advise the lender."
    )
    st.markdown(
        """
        - **Classify** accounts using the standard balance-sheet sections.
        - **Calculate** liquidity and solvency measures.
        - **Compare** the company with its past, its peers, and a competitor.
        - **Diagnose** the company's condition without relying on one number alone.
        """
    )
    st.info("The goal is sound reasoning, not speed. You may use the Quick Reference in the sidebar.")

    if st.button("Open the Case", type="primary", width="stretch"):
        advance()


def render_classification() -> None:
    st.header("Classify the Evidence")
    st.write("Place each account in its classified balance-sheet section. Dollar amounts are in actual dollars.")

    result = st.session_state.results.get("classification")
    if result is None:
        with st.form("classification_form"):
            answers: dict[str, str] = {}
            for index in st.session_state.account_order:
                account = ACCOUNTS[index]
                description, choice = st.columns([1.35, 1])
                amount = format_currency(float(account["amount"]))
                with description:
                    st.markdown(f"**{account['name']}**  \n{amount}")
                with choice:
                    answers[str(account["name"])] = st.selectbox(
                        f"Classification for {account['name']}",
                        ("Select a section",) + CATEGORIES,
                        key=f"class_{index}",
                        label_visibility="collapsed",
                    )
            submitted = st.form_submit_button("Submit Classifications", type="primary", width="stretch")

        if submitted:
            if "Select a section" in answers.values():
                st.error("Classify every account before submitting the patient chart.")
            else:
                score, feedback = score_classifications(answers, ACCOUNTS)
                st.session_state.results["classification"] = {
                    "score": score,
                    "max": MAX_SCORES["classification"],
                    "feedback": feedback,
                }
                st.rerun()
        return

    stage_result_banner(result["score"], result["max"])
    with st.expander("Review every classification", expanded=True):
        feedback_list(result["feedback"], show_name=True)
    if st.button("Continue to Liquidity", type="primary", width="stretch"):
        advance()


def render_liquidity() -> None:
    st.header("Check Classification Judgment")
    st.write("Current assets are listed in order of liquidity. Classification can also depend on how an item is used or when it matures.")

    result = st.session_state.results.get("liquidity")
    if result is None:
        with st.form("liquidity_form"):
            order = st.multiselect(
                "Select all four current assets from most liquid to least liquid",
                st.session_state.liquidity_option_order,
                help="Your selections will appear in the order you choose them.",
            )
            st.divider()
            answers = {}
            for question in CONTEXT_QUESTIONS:
                answers[str(question["id"])] = st.selectbox(
                    str(question["prompt"]),
                    ("Select an answer",) + tuple(question["options"]),
                    key=f"context_{question['id']}",
                )
            submitted = st.form_submit_button("Submit Judgment Checks", type="primary", width="stretch")

        if submitted:
            if len(order) != len(LIQUIDITY_ORDER) or "Select an answer" in answers.values():
                st.error("Complete the liquidity order and all three judgment checks.")
            else:
                order_correct = score_order(order, LIQUIDITY_ORDER)
                context_score, feedback = score_multiple_choice(answers, CONTEXT_QUESTIONS)
                st.session_state.results["liquidity"] = {
                    "score": context_score + int(order_correct),
                    "max": MAX_SCORES["liquidity"],
                    "order_correct": order_correct,
                    "submitted_order": order,
                    "feedback": feedback,
                }
                st.rerun()
        return

    stage_result_banner(result["score"], result["max"])
    st.markdown(
        "**Correct liquidity order:** " + " → ".join(LIQUIDITY_ORDER)
    )
    with st.expander("Review the judgment checks", expanded=True):
        feedback_list(result["feedback"])
    if st.button("Continue to Ratio Lab", type="primary", width="stretch"):
        advance()


def render_financial_tiles() -> None:
    tiles = (
        ("Current Assets", "$580,000"),
        ("Current Liabilities", "$320,000"),
        ("Total Liabilities", "$720,000"),
        ("Total Assets", "$1,320,000"),
        ("Total Equity", "$600,000"),
    )
    tile_html = "".join(
        f'<div class="vital-box"><div class="vital-label">{html.escape(label)}</div>'
        f'<div class="vital-value">{html.escape(value)}</div></div>'
        for label, value in tiles
    )
    st.markdown(f'<div class="vital-grid">{tile_html}</div>', unsafe_allow_html=True)


def render_ratio_answer_feedback(result: dict[str, object], expected: object) -> None:
    entries = result["entries"]
    checks = result["checks"]
    items = (
        (
            "working_capital",
            "Working capital",
            format_currency(float(entries["working_capital"])),
            format_currency(expected.working_capital),
        ),
        (
            "current_ratio",
            "Current ratio",
            f"{float(entries['current_ratio']):.2f}:1",
            f"{expected.current_ratio:.2f}:1",
        ),
        (
            "debt_to_assets",
            "Debt-to-assets ratio",
            f"{float(entries['debt_to_assets']):.1f}%",
            f"{expected.debt_to_assets:.1f}%",
        ),
        (
            "debt_to_equity",
            "Debt-to-equity ratio",
            f"{float(entries['debt_to_equity']):.1f}%",
            f"{expected.debt_to_equity:.1f}%",
        ),
    )

    for key, label, submitted, correct in items:
        is_correct = bool(checks[key])
        marker = "✓" if is_correct else "↺"
        css = "feedback-good" if is_correct else "feedback-fix"
        status = "Correct" if is_correct else "Incorrect"
        detail = (
            f"Your answer: {submitted}"
            if is_correct
            else f"Your answer: {submitted} · Correct answer: {correct}"
        )
        st.markdown(
            f'<div class="feedback-row"><strong>{html.escape(label)}</strong><br>'
            f'<span class="{css}">{marker} {status}</span><br>'
            f'<small>{html.escape(detail)}</small></div>',
            unsafe_allow_html=True,
        )


def render_ratio_lab() -> None:
    st.header("Ratio Lab")
    st.write("Use the following balance-sheet totals. Round ratios to two decimals and percentages to one decimal.")

    render_financial_tiles()

    result = st.session_state.results.get("ratios")
    expected = calculate_ratios(CURRENT_FINANCIALS)

    if result is None:
        with st.form("ratio_form"):
            left, right = st.columns(2)
            with left:
                working_capital = st.number_input(
                    "Working capital ($)", value=None, step=10_000, placeholder="Enter dollars"
                )
                current_ratio = st.number_input(
                    "Current ratio", value=None, step=0.01, placeholder="Example: 1.75"
                )
            with right:
                debt_to_assets = st.number_input(
                    "Debt-to-assets ratio (%)", value=None, step=0.1, placeholder="Enter a percent"
                )
                debt_to_equity = st.number_input(
                    "Debt-to-equity ratio (%)", value=None, step=0.1, placeholder="Enter a percent"
                )
            submitted = st.form_submit_button("Record Vital Signs", type="primary", width="stretch")

        if submitted:
            entries = {
                "working_capital": working_capital,
                "current_ratio": current_ratio,
                "debt_to_assets": debt_to_assets,
                "debt_to_equity": debt_to_equity,
            }
            if any(value is None for value in entries.values()):
                st.error("Enter all four financial vital signs before submitting.")
            else:
                checks = {
                    "working_capital": score_ratio_entry(working_capital, expected.working_capital, 100),
                    "current_ratio": score_ratio_entry(current_ratio, expected.current_ratio, 0.01),
                    "debt_to_assets": score_ratio_entry(debt_to_assets, expected.debt_to_assets, 0.1),
                    "debt_to_equity": score_ratio_entry(debt_to_equity, expected.debt_to_equity, 0.1),
                }
                st.session_state.results["ratios"] = {
                    "score": sum(checks.values()),
                    "max": MAX_SCORES["ratios"],
                    "checks": checks,
                    "entries": entries,
                }
                st.rerun()
        return

    stage_result_banner(result["score"], result["max"])
    with st.expander("Review Each Ratio Answer", expanded=True):
        render_ratio_answer_feedback(result, expected)
    st.subheader("Calculation Notes")
    st.markdown(
        f"""
        <div class="formula-chip">Working capital = $580,000 − $320,000 = <strong>{format_currency(expected.working_capital)}</strong></div>
        <div class="formula-chip">Current ratio = $580,000 ÷ $320,000 = <strong>{expected.current_ratio:.2f}:1</strong></div>
        <div class="formula-chip">Debt to assets = $720,000 ÷ $1,320,000 = <strong>{expected.debt_to_assets:.1f}%</strong></div>
        <div class="formula-chip">Debt to equity = $720,000 ÷ $600,000 = <strong>{expected.debt_to_equity:.1f}%</strong></div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Continue to Comparisons", type="primary", width="stretch"):
        advance()


def comparison_rows() -> list[dict[str, str]]:
    current = calculate_ratios(CURRENT_FINANCIALS)
    prior = calculate_ratios(PRIOR_FINANCIALS)
    return [
        {
            "Comparison": "Gem City — current year",
            "Working capital": format_currency(current.working_capital),
            "Current ratio": f"{current.current_ratio:.2f}:1",
            "Debt to assets": f"{current.debt_to_assets:.1f}%",
            "Debt to equity": f"{current.debt_to_equity:.1f}%",
        },
        {
            "Comparison": "Gem City — prior year",
            "Working capital": format_currency(prior.working_capital),
            "Current ratio": f"{prior.current_ratio:.2f}:1",
            "Debt to assets": f"{prior.debt_to_assets:.1f}%",
            "Debt to equity": f"{prior.debt_to_equity:.1f}%",
        },
        *[
            {
                "Comparison": name,
                "Working capital": "Not provided" if values["working_capital"] is None else format_currency(values["working_capital"]),
                "Current ratio": f"{values['current_ratio']:.2f}:1",
                "Debt to assets": f"{values['debt_to_assets']:.1f}%",
                "Debt to equity": f"{values['debt_to_equity']:.1f}%",
            }
            for name, values in BENCHMARKS.items()
        ],
    ]


def render_analysis() -> None:
    st.header("Comparisons")
    st.write("A ratio is an indicator—not a complete diagnosis. Compare the results before reaching a conclusion.")
    st.dataframe(comparison_rows(), hide_index=True, width="stretch")

    result = st.session_state.results.get("analysis")
    if result is None:
        with st.form("analysis_form"):
            answers = {}
            for question in ANALYSIS_QUESTIONS:
                answers[str(question["id"])] = st.radio(
                    str(question["prompt"]),
                    tuple(question["options"]),
                    index=None,
                    key=f"analysis_{question['id']}",
                )

            st.subheader("Name Each Comparison")
            comparison_answers = {}
            for question in COMPARISON_QUESTIONS:
                comparison_answers[str(question["id"])] = st.selectbox(
                    str(question["label"]),
                    ("Select a comparison",) + COMPARISON_OPTIONS,
                    key=f"comparison_{question['id']}",
                )
            submitted = st.form_submit_button("Submit Trend Analysis", type="primary", width="stretch")

        if submitted:
            if any(value is None for value in answers.values()) or "Select a comparison" in comparison_answers.values():
                st.error("Answer each trend and comparison question before submitting.")
            else:
                analysis_score, feedback = score_multiple_choice(answers, ANALYSIS_QUESTIONS)
                comparison_score, comparison_feedback = score_multiple_choice(
                    comparison_answers, COMPARISON_QUESTIONS
                )
                st.session_state.results["analysis"] = {
                    "score": analysis_score + comparison_score,
                    "max": MAX_SCORES["analysis"],
                    "feedback": feedback,
                    "comparison_score": comparison_score,
                    "comparison_feedback": comparison_feedback,
                }
                st.rerun()
        return

    stage_result_banner(result["score"], result["max"])
    with st.expander("Review the trend analysis", expanded=True):
        feedback_list(result["feedback"])
        st.markdown(
            f"**Comparison vocabulary:** {result['comparison_score']} of "
            f"{len(COMPARISON_QUESTIONS)} correct.  \n"
            "Prior year = intracompany · Peer average = industry-average · Competitor = intercompany"
        )
        feedback_list(result["comparison_feedback"], show_name=True)
    if st.button("Continue to Diagnosis", type="primary", width="stretch"):
        advance()


def chart_table(title: str, rows: tuple[tuple[str, str, float | None], ...]) -> str:
    body = []
    for row_type, label, amount in rows:
        css_class = f"chart-{row_type}"
        amount_text = "" if amount is None else format_currency(amount)
        body.append(
            f'<tr class="{css_class}"><td>{html.escape(label)}</td>'
            f'<td>{html.escape(amount_text)}</td></tr>'
        )
    return (
        f'<table class="chart-table"><thead><tr><th colspan="2">{html.escape(title)}</th></tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
    )


def render_completed_chart() -> None:
    assets = (
        ("section", "Current Assets", None),
        ("item", "Cash", 90_000),
        ("item", "Accounts receivable", 160_000),
        ("item", "Inventory", 300_000),
        ("item", "Prepaid insurance", 30_000),
        ("total", "Total Current Assets", 580_000),
        ("section", "Long-Term Investments", None),
        ("item", "Corporate bonds held for three years", 120_000),
        ("item", "Land held for a future store", 180_000),
        ("total", "Total Long-Term Investments", 300_000),
        ("section", "Property, Plant, and Equipment", None),
        ("item", "Store equipment", 480_000),
        ("item", "Less: accumulated depreciation", -120_000),
        ("total", "Net Property, Plant, and Equipment", 360_000),
        ("section", "Intangible Assets", None),
        ("item", "Trademark", 80_000),
        ("total", "Total Assets", 1_320_000),
    )
    liabilities_and_equity = (
        ("section", "Current Liabilities", None),
        ("item", "Accounts payable", 180_000),
        ("item", "Salaries and wages payable", 40_000),
        ("item", "Note payable due in eight months", 100_000),
        ("total", "Total Current Liabilities", 320_000),
        ("section", "Long-Term Liabilities", None),
        ("item", "Bonds payable due in 2032", 400_000),
        ("total", "Total Liabilities", 720_000),
        ("section", "Shareholders' Equity", None),
        ("item", "Common stock", 250_000),
        ("item", "Retained earnings", 350_000),
        ("total", "Total Shareholders' Equity", 600_000),
        ("total", "Total Liabilities and Shareholders' Equity", 1_320_000),
    )

    st.subheader("Completed Patient Chart")
    left, right = st.columns(2)
    with left:
        st.markdown(chart_table("Assets", assets), unsafe_allow_html=True)
    with right:
        st.markdown(
            chart_table("Liabilities and Shareholders' Equity", liabilities_and_equity),
            unsafe_allow_html=True,
        )

    st.markdown("#### Financial Vital Signs and Comparisons")
    st.dataframe(comparison_rows(), hide_index=True, width="stretch")


def render_evidence_feedback(result: dict[str, object]) -> None:
    st.markdown(f"**Evidence selection: {result['evidence_score']} of 4 points**")
    for item in result["evidence_feedback"]:
        selected = bool(item["selected"])
        should_select = bool(item["should_select"])
        if selected and should_select:
            marker, css, message = "✓", "feedback-good", "Correctly selected"
        elif not selected and should_select:
            marker, css, message = "↺", "feedback-fix", "Supporting evidence was missed"
        elif selected:
            marker, css, message = "↺", "feedback-fix", "This statement does not support the diagnosis"
        else:
            marker, css, message = "✓", "feedback-good", "Correctly left unselected"
        st.markdown(
            f'<div class="feedback-row"><span class="{css}">{marker} {message}</span><br>'
            f'<small>{html.escape(str(item["option"]))}</small></div>',
            unsafe_allow_html=True,
        )


def render_reflection_feedback(result: dict[str, object]) -> None:
    st.markdown(f"**Written rationale: {result['reflection_score']} of 3 points**")
    for item in result["reflection_feedback"]:
        marker = "✓" if item["met"] else "↺"
        css = "feedback-good" if item["met"] else "feedback-fix"
        status = "Criterion met" if item["met"] else "Add this element"
        st.markdown(
            f'<div class="feedback-row"><span class="{css}">{marker} '
            f'{html.escape(str(item["label"]))}: {status}</span><br>'
            f'<small>{html.escape(str(item["guidance"]))}</small></div>',
            unsafe_allow_html=True,
        )
    st.info(
        "Model response: Consider approving the credit line with conditions. Liquidity is currently adequate, but the declining current ratio and inventory concentration require monitoring, while the elevated debt ratios show increased solvency risk."
    )


def render_diagnosis() -> None:
    st.header("Make the Diagnosis")
    clinical_card(
        "Clinical reminder",
        "Use the whole chart",
        "A single ratio cannot establish financial health. Balance positive evidence against warning signs and explain your judgment.",
    )
    render_completed_chart()

    result = st.session_state.results.get("diagnosis")
    if result is None:
        with st.form("diagnosis_form"):
            answers = {}
            for question in DIAGNOSIS_QUESTIONS:
                answers[str(question["id"])] = st.radio(
                    str(question["prompt"]),
                    tuple(question["options"]),
                    index=None,
                    key=f"diagnosis_{question['id']}",
                )

            evidence = st.multiselect(
                "Which evidence supports the best overall diagnosis? Select all that apply.",
                EVIDENCE_OPTIONS,
            )
            reflection = st.text_area(
                "In one or two sentences, explain your recommendation to the lender.",
                placeholder="The company appears ... because ...",
                max_chars=500,
                help="Three points: state a recommendation, cite liquidity evidence, and cite solvency evidence.",
            )
            st.caption(
                "Written rationale rubric (3 points): recommendation · liquidity evidence · solvency evidence"
            )
            submitted = st.form_submit_button("Sign the Patient Chart", type="primary", width="stretch")

        if submitted:
            if any(value is None for value in answers.values()) or not evidence or len(reflection.strip()) < 20:
                st.error("Complete all diagnoses, select supporting evidence, and provide a brief explanation of at least 20 characters.")
            else:
                diagnosis_score, feedback = score_multiple_choice(answers, DIAGNOSIS_QUESTIONS)
                evidence_score, evidence_feedback = score_evidence(
                    evidence, CORRECT_EVIDENCE, EVIDENCE_OPTIONS
                )
                reflection_score, reflection_feedback = score_reflection(reflection)
                st.session_state.results["diagnosis"] = {
                    "score": diagnosis_score + evidence_score + reflection_score,
                    "max": MAX_SCORES["diagnosis"],
                    "feedback": feedback,
                    "evidence_score": evidence_score,
                    "evidence_feedback": evidence_feedback,
                    "reflection_score": reflection_score,
                    "reflection_feedback": reflection_feedback,
                }
                st.session_state.reflection = reflection.strip()
                st.rerun()
        return

    stage_result_banner(result["score"], result["max"])
    with st.expander("Review the Diagnosis", expanded=True):
        feedback_list(result["feedback"])
        render_evidence_feedback(result)
        render_reflection_feedback(result)
    if st.button("Complete the Case", type="primary", width="stretch"):
        advance()


def performance_label(percent: float) -> tuple[str, str]:
    if percent >= 90:
        return "Chief Financial Diagnostician", "Excellent work connecting classification, calculation, comparison, and judgment."
    if percent >= 75:
        return "Strong Clinical Judgment", "Your diagnosis is well supported. Review the missed notes to sharpen the details."
    if percent >= 60:
        return "Developing Diagnostician", "You found several important signals. Revisit the chart to connect the ratios with their meaning."
    return "Vital Signs Review Recommended", "Use the debrief to revisit each step before trying the case again."


def render_debrief() -> None:
    total = sum(int(result["score"]) for result in st.session_state.results.values())
    maximum = sum(MAX_SCORES.values())
    percent = (total / maximum) * 100
    label, message = performance_label(percent)

    st.header("Case Debrief")
    clinical_card("Case status", label, message)

    left, middle = st.columns(2)
    left.metric("Total score", f"{total} / {maximum}")
    middle.metric("Accuracy", f"{percent:.0f}%")

    st.subheader("Section Results")
    for key, title in (
        ("classification", "Account classification"),
        ("liquidity", "Liquidity and context"),
        ("ratios", "Ratio calculations"),
        ("analysis", "Comparisons and trends"),
        ("diagnosis", "Financial diagnosis"),
    ):
        result = st.session_state.results[key]
        st.write(f"**{title}:** {result['score']} of {result['max']}")
        st.progress(result["score"] / result["max"])

    st.subheader("Recommended Diagnosis")
    st.markdown(
        """
        **Liquidity:** Gem City has positive working capital of $260,000 and a current ratio of 1.81:1, slightly above the peer average. However, the ratio declined from 2.00:1 and more than half of current assets are inventory. Short-term coverage is generally adequate, but it deserves monitoring.

        **Solvency:** Debt finances 54.5% of assets, and liabilities equal 120.0% of equity. Both measures worsened and exceed the peer average and competitor. Long-term financial risk has increased.

        **Lender recommendation:** Consider the expanded credit line with conditions, such as continued ratio monitoring or limits on additional borrowing. The evidence does not support either automatic approval or rejection based on one fact.
        """
    )

    if st.button("Try the Case Again", type="primary", width="stretch"):
        reset_case()


inject_styles()
initialize_state()
scroll_to_top_on_stage_change()
render_header()
render_progress()
render_sidebar()

renderers = (
    render_intake,
    render_classification,
    render_liquidity,
    render_ratio_lab,
    render_analysis,
    render_diagnosis,
    render_debrief,
)
renderers[st.session_state.stage]()
