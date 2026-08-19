import unittest

from streamlit.testing.v1 import AppTest

from diagnosing_dollars.case_data import ANALYSIS_QUESTIONS, COMPARISON_QUESTIONS


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


class AnswerFeedbackTests(unittest.TestCase):
    def test_ratio_review_distinguishes_correct_and_incorrect_answers(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
        app.session_state.stage = 3
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
        app.session_state.stage = 4
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
