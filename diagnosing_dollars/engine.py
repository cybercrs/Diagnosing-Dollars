"""Calculation and scoring logic kept separate from the Streamlit interface."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
import re
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RatioSnapshot:
    working_capital: float
    current_ratio: float
    debt_to_assets: float
    debt_to_equity: float


def calculate_ratios(financials: Mapping[str, float]) -> RatioSnapshot:
    """Calculate the four financial-health measures used in the case."""
    current_liabilities = financials["current_liabilities"]
    total_assets = financials["total_assets"]
    total_equity = financials["total_equity"]

    if current_liabilities == 0 or total_assets == 0 or total_equity == 0:
        raise ValueError("Ratio denominators must be nonzero.")

    return RatioSnapshot(
        working_capital=financials["current_assets"] - current_liabilities,
        current_ratio=financials["current_assets"] / current_liabilities,
        debt_to_assets=(financials["total_liabilities"] / total_assets) * 100,
        debt_to_equity=(financials["total_liabilities"] / total_equity) * 100,
    )


def score_classifications(
    submitted: Mapping[str, str], accounts: Sequence[Mapping[str, object]]
) -> tuple[int, list[dict[str, object]]]:
    """Score account classifications and return item-level feedback."""
    feedback = []
    for account in accounts:
        name = str(account["name"])
        chosen = submitted.get(name, "")
        correct = str(account["category"])
        feedback.append(
            {
                "name": name,
                "chosen": chosen,
                "correct": correct,
                "is_correct": chosen == correct,
                "why": str(account["why"]),
            }
        )
    return sum(bool(item["is_correct"]) for item in feedback), feedback


def score_multiple_choice(
    submitted: Mapping[str, str], questions: Sequence[Mapping[str, object]]
) -> tuple[int, list[dict[str, object]]]:
    """Score a group of multiple-choice questions."""
    feedback = []
    for question in questions:
        question_id = str(question["id"])
        chosen = submitted.get(question_id, "")
        correct = str(question["correct"])
        feedback.append(
            {
                "id": question_id,
                "name": str(question.get("prompt", question.get("label", ""))),
                "chosen": chosen,
                "correct": correct,
                "is_correct": chosen == correct,
                "why": str(question.get("why", "")),
            }
        )
    return sum(bool(item["is_correct"]) for item in feedback), feedback


def score_ratio_entry(value: float | None, expected: float, tolerance: float) -> bool:
    """Accept conventional rounding without accepting materially wrong answers."""
    return value is not None and isclose(value, expected, abs_tol=tolerance)


def score_order(submitted: Sequence[str], correct: Sequence[str]) -> bool:
    """Require a complete liquidity order from most to least liquid."""
    return tuple(submitted) == tuple(correct)


def score_evidence(
    selected: Sequence[str], correct: Sequence[str], all_options: Sequence[str]
) -> tuple[int, list[dict[str, object]]]:
    """Award partial credit for valid evidence and deduct unsupported selections."""
    selected_set = set(selected)
    correct_set = set(correct)
    score = max(0, len(selected_set & correct_set) - len(selected_set - correct_set))
    feedback = []

    for option in all_options:
        was_selected = option in selected_set
        should_select = option in correct_set
        feedback.append(
            {
                "option": option,
                "selected": was_selected,
                "should_select": should_select,
                "is_correct": was_selected == should_select,
            }
        )

    return score, feedback


def score_reflection(text: str) -> tuple[int, list[dict[str, object]]]:
    """Apply a transparent three-part rubric to the written lender rationale."""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    criteria = (
        {
            "label": "Recommendation",
            "patterns": ("approve", "approval", "condition", "monitor", "recommend", "reject", "extend", "caution"),
            "guidance": "State what the lender should do, including any conditions or monitoring.",
        },
        {
            "label": "Liquidity evidence",
            "patterns": ("liquidity", "working capital", "current ratio", "current assets", "inventory"),
            "guidance": "Cite a liquidity fact such as working capital, the current ratio, or inventory concentration.",
        },
        {
            "label": "Solvency evidence",
            "patterns": ("solvency", "debt", "liabilities", "creditor financing"),
            "guidance": "Cite a solvency fact such as a debt ratio or increased reliance on creditor financing.",
        },
    )

    feedback = []
    for criterion in criteria:
        met = any(pattern in normalized for pattern in criterion["patterns"])
        feedback.append(
            {
                "label": criterion["label"],
                "met": met,
                "guidance": criterion["guidance"],
            }
        )

    return sum(bool(item["met"]) for item in feedback), feedback


def format_currency(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"
