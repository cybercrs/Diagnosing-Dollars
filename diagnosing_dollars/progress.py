"""Compact, non-identifying progress snapshots for refresh-safe sessions."""

from __future__ import annotations

import base64
import binascii
import json
from math import isfinite
import zlib
from typing import Any, Mapping, Sequence

from diagnosing_dollars.case_data import (
    ACCOUNTS,
    ANALYSIS_QUESTIONS,
    CATEGORIES,
    COMPARISON_OPTIONS,
    COMPARISON_QUESTIONS,
    CONTEXT_QUESTIONS,
    CORRECT_EVIDENCE,
    CURRENT_FINANCIALS,
    DIAGNOSIS_QUESTIONS,
    EVIDENCE_OPTIONS,
    LIQUIDITY_ORDER,
)
from diagnosing_dollars.engine import (
    calculate_ratios,
    reflection_feedback_from_flags,
    score_classifications,
    score_evidence,
    score_multiple_choice,
    score_order,
    score_ratio_entry,
)


SNAPSHOT_PARAMETER = "progress"
SNAPSHOT_VERSION = 1
MAX_ENCODED_LENGTH = 4096
MAX_JSON_BYTES = 16_384
SUBMISSION_KEYS = ("cl", "li", "ra", "an", "di")


def _is_int(value: object) -> bool:
    return type(value) is int


def _index_list(value: object, lengths: Sequence[int]) -> list[int]:
    if not isinstance(value, list) or len(value) != len(lengths):
        raise ValueError("Invalid option-index list.")
    if any(not _is_int(item) or item < 0 or item >= maximum for item, maximum in zip(value, lengths)):
        raise ValueError("Option index is outside its allowed range.")
    return list(value)


def _permutation(value: object, size: int) -> list[int]:
    indexes = _index_list(value, [size] * size)
    if sorted(indexes) != list(range(size)):
        raise ValueError("Saved order is not a complete permutation.")
    return indexes


def _numeric_list(value: object, size: int) -> list[float]:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("Invalid numeric answer list.")
    normalized = []
    for item in value:
        if type(item) not in (int, float) or not isfinite(float(item)) or abs(float(item)) > 1e12:
            raise ValueError("Saved numeric answer is invalid.")
        normalized.append(float(item))
    return normalized


def validate_snapshot(payload: object) -> dict[str, Any]:
    """Validate and normalize a decoded snapshot against the current activity."""
    if not isinstance(payload, dict) or set(payload) != {"v", "p", "o", "s", "c"}:
        raise ValueError("Snapshot fields are invalid.")
    if not _is_int(payload["v"]) or payload["v"] != SNAPSHOT_VERSION:
        raise ValueError("Snapshot version is unsupported.")

    stage = payload["p"]
    if not _is_int(stage) or stage < 0 or stage > len(SUBMISSION_KEYS) + 1:
        raise ValueError("Saved page is invalid.")

    orders = payload["o"]
    if not isinstance(orders, list) or len(orders) != 2:
        raise ValueError("Saved display orders are invalid.")
    account_order = _permutation(orders[0], len(ACCOUNTS))
    liquidity_order = _permutation(orders[1], len(LIQUIDITY_ORDER))

    submissions = payload["s"]
    if not isinstance(submissions, dict):
        raise ValueError("Saved submissions are invalid.")
    submission_count = len(submissions)
    if set(submissions) != set(SUBMISSION_KEYS[:submission_count]):
        raise ValueError("Saved submissions are not a valid activity prefix.")
    minimum = max(0, stage - 1)
    maximum = min(stage, len(SUBMISSION_KEYS))
    if submission_count < minimum or submission_count > maximum:
        raise ValueError("Saved submissions do not match the current page.")

    normalized: dict[str, Any] = {}
    if "cl" in submissions:
        normalized["cl"] = _index_list(submissions["cl"], [len(CATEGORIES)] * len(ACCOUNTS))
    if "li" in submissions:
        value = submissions["li"]
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Saved liquidity submission is invalid.")
        normalized["li"] = [
            _permutation(value[0], len(LIQUIDITY_ORDER)),
            _index_list(value[1], [len(question["options"]) for question in CONTEXT_QUESTIONS]),
        ]
    if "ra" in submissions:
        normalized["ra"] = _numeric_list(submissions["ra"], 4)
    if "an" in submissions:
        value = submissions["an"]
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Saved comparison submission is invalid.")
        normalized["an"] = [
            _index_list(value[0], [len(question["options"]) for question in ANALYSIS_QUESTIONS]),
            _index_list(value[1], [len(COMPARISON_OPTIONS)] * len(COMPARISON_QUESTIONS)),
        ]
    if "di" in submissions:
        value = submissions["di"]
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError("Saved diagnosis submission is invalid.")
        answer_indexes = _index_list(value[0], [len(question["options"]) for question in DIAGNOSIS_QUESTIONS])
        evidence_mask, reflection_mask = value[1], value[2]
        if not _is_int(evidence_mask) or evidence_mask < 1 or evidence_mask >= 1 << len(EVIDENCE_OPTIONS):
            raise ValueError("Saved evidence selection is invalid.")
        if not _is_int(reflection_mask) or reflection_mask < 0 or reflection_mask >= 1 << 3:
            raise ValueError("Saved rubric result is invalid.")
        normalized["di"] = [answer_indexes, evidence_mask, reflection_mask]

    completed = payload["c"]
    expected_completion = stage == len(SUBMISSION_KEYS) + 1 and submission_count == len(SUBMISSION_KEYS)
    if type(completed) is not bool or completed != expected_completion:
        raise ValueError("Saved completion status is inconsistent.")

    return {
        "v": SNAPSHOT_VERSION,
        "p": stage,
        "o": [account_order, liquidity_order],
        "s": normalized,
        "c": completed,
    }


def encode_snapshot(payload: Mapping[str, Any]) -> str:
    """Encode a validated payload as compact URL-safe compressed JSON."""
    normalized = validate_snapshot(dict(payload))
    raw = json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(zlib.compress(raw, level=9)).decode("ascii").rstrip("=")
    if len(encoded) > MAX_ENCODED_LENGTH:
        raise ValueError("Snapshot exceeds the query-parameter size limit.")
    return encoded


def decode_snapshot(encoded: object) -> dict[str, Any] | None:
    """Decode untrusted query text, returning None when any check fails."""
    if not isinstance(encoded, str) or not encoded or len(encoded) > MAX_ENCODED_LENGTH:
        return None
    try:
        padded = encoded + "=" * (-len(encoded) % 4)
        compressed = base64.b64decode(padded, altchars=b"-_", validate=True)
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES or decompressor.unconsumed_tail or not decompressor.eof:
            return None
        raw += decompressor.flush()
        if len(raw) > MAX_JSON_BYTES:
            return None
        return validate_snapshot(json.loads(raw.decode("utf-8")))
    except (ValueError, TypeError, binascii.Error, zlib.error, UnicodeDecodeError, json.JSONDecodeError):
        return None


def create_snapshot(
    stage: int,
    account_order: Sequence[int],
    liquidity_option_order: Sequence[str],
    submissions: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the canonical compact payload from current session state."""
    liquidity_indexes = [LIQUIDITY_ORDER.index(item) for item in liquidity_option_order]
    return validate_snapshot(
        {
            "v": SNAPSHOT_VERSION,
            "p": stage,
            "o": [list(account_order), liquidity_indexes],
            "s": dict(submissions),
            "c": stage == len(SUBMISSION_KEYS) + 1 and len(submissions) == len(SUBMISSION_KEYS),
        }
    )


def state_from_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Expand a validated snapshot into the session state used by the UI."""
    normalized = validate_snapshot(dict(payload))
    return {
        "stage": normalized["p"],
        "account_order": normalized["o"][0],
        "liquidity_option_order": [LIQUIDITY_ORDER[index] for index in normalized["o"][1]],
        "submissions": normalized["s"],
        "results": results_from_submissions(normalized["s"]),
        "completed": normalized["c"],
    }


def pack_classification(answers: Mapping[str, str]) -> list[int]:
    return [CATEGORIES.index(answers[str(account["name"])]) for account in ACCOUNTS]


def pack_liquidity(order: Sequence[str], answers: Mapping[str, str]) -> list[list[int]]:
    return [
        [LIQUIDITY_ORDER.index(item) for item in order],
        [tuple(question["options"]).index(answers[str(question["id"])]) for question in CONTEXT_QUESTIONS],
    ]


def pack_ratios(entries: Mapping[str, float]) -> list[float]:
    return [
        float(entries["working_capital"]),
        float(entries["current_ratio"]),
        float(entries["debt_to_assets"]),
        float(entries["debt_to_equity"]),
    ]


def pack_analysis(answers: Mapping[str, str], comparisons: Mapping[str, str]) -> list[list[int]]:
    return [
        [tuple(question["options"]).index(answers[str(question["id"])]) for question in ANALYSIS_QUESTIONS],
        [COMPARISON_OPTIONS.index(comparisons[str(question["id"])]) for question in COMPARISON_QUESTIONS],
    ]


def pack_diagnosis(
    answers: Mapping[str, str],
    evidence: Sequence[str],
    reflection_feedback: Sequence[Mapping[str, object]],
) -> list[Any]:
    answer_indexes = [
        tuple(question["options"]).index(answers[str(question["id"])])
        for question in DIAGNOSIS_QUESTIONS
    ]
    evidence_mask = sum(1 << EVIDENCE_OPTIONS.index(item) for item in evidence)
    reflection_mask = sum(1 << index for index, item in enumerate(reflection_feedback) if item["met"])
    return [answer_indexes, evidence_mask, reflection_mask]


def results_from_submissions(submissions: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Recalculate display feedback and scores from compact submitted answers."""
    results: dict[str, dict[str, Any]] = {}

    if "cl" in submissions:
        answers = {
            str(account["name"]): CATEGORIES[index]
            for account, index in zip(ACCOUNTS, submissions["cl"])
        }
        score, feedback = score_classifications(answers, ACCOUNTS)
        results["classification"] = {"score": score, "max": len(ACCOUNTS), "feedback": feedback}

    if "li" in submissions:
        order = [LIQUIDITY_ORDER[index] for index in submissions["li"][0]]
        answers = {
            str(question["id"]): tuple(question["options"])[index]
            for question, index in zip(CONTEXT_QUESTIONS, submissions["li"][1])
        }
        context_score, feedback = score_multiple_choice(answers, CONTEXT_QUESTIONS)
        order_correct = score_order(order, LIQUIDITY_ORDER)
        results["liquidity"] = {
            "score": context_score + int(order_correct),
            "max": 1 + len(CONTEXT_QUESTIONS),
            "order_correct": order_correct,
            "submitted_order": order,
            "feedback": feedback,
        }

    if "ra" in submissions:
        values = submissions["ra"]
        entries = dict(zip(("working_capital", "current_ratio", "debt_to_assets", "debt_to_equity"), values))
        expected = calculate_ratios(CURRENT_FINANCIALS)
        checks = {
            "working_capital": score_ratio_entry(entries["working_capital"], expected.working_capital, 100),
            "current_ratio": score_ratio_entry(entries["current_ratio"], expected.current_ratio, 0.01),
            "debt_to_assets": score_ratio_entry(entries["debt_to_assets"], expected.debt_to_assets, 0.1),
            "debt_to_equity": score_ratio_entry(entries["debt_to_equity"], expected.debt_to_equity, 0.1),
        }
        results["ratios"] = {"score": sum(checks.values()), "max": 4, "checks": checks, "entries": entries}

    if "an" in submissions:
        answers = {
            str(question["id"]): tuple(question["options"])[index]
            for question, index in zip(ANALYSIS_QUESTIONS, submissions["an"][0])
        }
        comparisons = {
            str(question["id"]): COMPARISON_OPTIONS[index]
            for question, index in zip(COMPARISON_QUESTIONS, submissions["an"][1])
        }
        analysis_score, feedback = score_multiple_choice(answers, ANALYSIS_QUESTIONS)
        comparison_score, comparison_feedback = score_multiple_choice(comparisons, COMPARISON_QUESTIONS)
        results["analysis"] = {
            "score": analysis_score + comparison_score,
            "max": len(ANALYSIS_QUESTIONS) + len(COMPARISON_QUESTIONS),
            "feedback": feedback,
            "comparison_score": comparison_score,
            "comparison_feedback": comparison_feedback,
        }

    if "di" in submissions:
        answer_indexes, evidence_mask, reflection_mask = submissions["di"]
        answers = {
            str(question["id"]): tuple(question["options"])[index]
            for question, index in zip(DIAGNOSIS_QUESTIONS, answer_indexes)
        }
        evidence = [item for index, item in enumerate(EVIDENCE_OPTIONS) if evidence_mask & (1 << index)]
        reflection_flags = [bool(reflection_mask & (1 << index)) for index in range(3)]
        reflection_feedback = reflection_feedback_from_flags(reflection_flags)
        diagnosis_score, feedback = score_multiple_choice(answers, DIAGNOSIS_QUESTIONS)
        evidence_score, evidence_feedback = score_evidence(evidence, CORRECT_EVIDENCE, EVIDENCE_OPTIONS)
        reflection_score = sum(reflection_flags)
        results["diagnosis"] = {
            "score": diagnosis_score + evidence_score + reflection_score,
            "max": len(DIAGNOSIS_QUESTIONS) + 4 + 3,
            "feedback": feedback,
            "evidence_score": evidence_score,
            "evidence_feedback": evidence_feedback,
            "reflection_score": reflection_score,
            "reflection_feedback": reflection_feedback,
        }

    return results
