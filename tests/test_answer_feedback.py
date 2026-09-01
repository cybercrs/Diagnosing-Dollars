import unittest

from streamlit.testing.v1 import AppTest

from diagnosing_dollars.case_data import (
    ACCOUNTS,
    ANALYSIS_QUESTIONS,
    CATEGORIES,
    COMPARISON_QUESTIONS,
    CONTEXT_QUESTIONS,
    LIQUIDITY_ORDER,
)
from diagnosing_dollars.progress import results_from_submissions


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def correct_prior_submissions(count: int) -> dict[str, object]:
    submissions: dict[str, object] = {}
    if count >= 1:
        submissions["cl"] = [CATEGORIES.index(account["category"]) for account in ACCOUNTS]
    if count >= 2:
        submissions["li"] = [
            list(range(len(LIQUIDITY_ORDER))),
            [tuple(question["options"]).index(question["correct"]) for question in CONTEXT_QUESTIONS],
        ]
    if count >= 3:
        submissions["ra"] = [260_000.0, 1.81, 54.5, 120.0]
    return submissions


def set_stage(app: AppTest, stage: int) -> None:
    submissions = correct_prior_submissions(max(0, stage - 1))
    app.session_state.stage = stage
    app.session_state.submissions = submissions
    app.session_state.results = results_from_submissions(submissions)
    app.session_state.completed = False


class AnswerFeedbackTests(unittest.TestCase):
    def test_ratio_review_distinguishes_correct_and_incorrect_answers(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
        set_stage(app, 3)
        app.run()

        for widget, value in zip(app.number_input, (260_000, 1.70, 54.5, 100.0)):
            widget.set_value(value)
        button(app, "Record Vital Signs").click().run()

        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Working capital", markup)
        self.assertIn("✓ Correct", markup)
        self.assertIn("Current ratio", markup)
        self.assertIn("↺ Incorrect", markup)
        self.assertIn("Your answer: 1.70:1 · Correct answer: 1.81:1", markup)
        self.assertIn("Your answer: 100.0% · Correct answer: 120.0%", markup)

    def test_comparison_vocabulary_review_shows_each_answer(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
        set_stage(app, 4)
        app.run()

        for question in ANALYSIS_QUESTIONS:
            app.radio(key=f"analysis_{question['id']}").set_value(question["correct"])

        app.selectbox(key="comparison_prior_type").set_value(
            COMPARISON_QUESTIONS[0]["correct"]
        )
        app.selectbox(key="comparison_industry_type").set_value(
            "Intercompany comparison"
        )
        app.selectbox(key="comparison_competitor_type").set_value(
            COMPARISON_QUESTIONS[2]["correct"]
        )
        button(app, "Submit Trend Analysis").click().run()

        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("**Comparison vocabulary:** 2 of 3 correct", markup)
        self.assertIn("Current year compared with Gem City Outfitters last year", markup)
        self.assertIn("Current year compared with the average of all peers", markup)
        self.assertIn(
            "Your answer: Intercompany comparison · Correct: Industry-average comparison",
            markup,
        )
        self.assertIn("Comparing one company with a specific competitor", markup)


if __name__ == "__main__":
    unittest.main()
