import unittest

from diagnosing_dollars.case_data import (
    ACCOUNTS,
    CORRECT_EVIDENCE,
    CURRENT_FINANCIALS,
    EVIDENCE_OPTIONS,
    LIQUIDITY_ORDER,
)
from diagnosing_dollars.engine import (
    calculate_ratios,
    format_currency,
    score_classifications,
    score_evidence,
    score_order,
    score_ratio_entry,
    score_reflection,
)


class RatioTests(unittest.TestCase):
    def test_case_ratios(self):
        ratios = calculate_ratios(CURRENT_FINANCIALS)
        self.assertEqual(ratios.working_capital, 260_000)
        self.assertAlmostEqual(ratios.current_ratio, 1.8125)
        self.assertAlmostEqual(ratios.debt_to_assets, 54.5454545)
        self.assertAlmostEqual(ratios.debt_to_equity, 120.0)

    def test_zero_denominator_is_rejected(self):
        broken = dict(CURRENT_FINANCIALS)
        broken["current_liabilities"] = 0
        with self.assertRaises(ValueError):
            calculate_ratios(broken)


class ScoringTests(unittest.TestCase):
    def test_all_correct_classifications(self):
        answers = {str(item["name"]): str(item["category"]) for item in ACCOUNTS}
        score, feedback = score_classifications(answers, ACCOUNTS)
        self.assertEqual(score, len(ACCOUNTS))
        self.assertTrue(all(item["is_correct"] for item in feedback))

    def test_liquidity_order_requires_exact_sequence(self):
        self.assertTrue(score_order(LIQUIDITY_ORDER, LIQUIDITY_ORDER))
        self.assertFalse(score_order(tuple(reversed(LIQUIDITY_ORDER)), LIQUIDITY_ORDER))

    def test_ratio_rounding_tolerance(self):
        self.assertTrue(score_ratio_entry(1.81, 1.8125, 0.01))
        self.assertFalse(score_ratio_entry(1.70, 1.8125, 0.01))

    def test_negative_currency_format(self):
        self.assertEqual(format_currency(-120_000), "-$120,000")

    def test_evidence_scoring_awards_partial_credit_and_penalizes_distractors(self):
        three_valid = list(CORRECT_EVIDENCE)[:3]
        score, feedback = score_evidence(three_valid, CORRECT_EVIDENCE, EVIDENCE_OPTIONS)
        self.assertEqual(score, 3)
        self.assertEqual(len(feedback), len(EVIDENCE_OPTIONS))

        with_distractor = three_valid + [EVIDENCE_OPTIONS[-1]]
        score, _ = score_evidence(with_distractor, CORRECT_EVIDENCE, EVIDENCE_OPTIONS)
        self.assertEqual(score, 2)

    def test_reflection_rubric_scores_three_required_elements(self):
        response = (
            "Approve with monitoring because working capital is positive, but the debt ratios "
            "show increased creditor risk."
        )
        score, feedback = score_reflection(response)
        self.assertEqual(score, 3)
        self.assertTrue(all(item["met"] for item in feedback))

    def test_reflection_rubric_identifies_missing_solvency_evidence(self):
        score, feedback = score_reflection(
            "Approve with conditions because the current ratio remains above the peer average."
        )
        self.assertEqual(score, 2)
        self.assertFalse(feedback[-1]["met"])


if __name__ == "__main__":
    unittest.main()
