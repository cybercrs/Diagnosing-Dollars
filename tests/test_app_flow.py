import unittest

from streamlit.testing.v1 import AppTest

from diagnosing_dollars.case_data import (
    ACCOUNTS,
    ANALYSIS_QUESTIONS,
    COMPARISON_QUESTIONS,
    CONTEXT_QUESTIONS,
    CORRECT_EVIDENCE,
    DIAGNOSIS_QUESTIONS,
    LIQUIDITY_ORDER,
)
from diagnosing_dollars.progress import SNAPSHOT_PARAMETER, decode_snapshot


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


class PerfectCaseFlowTests(unittest.TestCase):
    def test_complete_case_reaches_full_score_debrief(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()

        button(app, "Open the Case").click().run()
        self.assertEqual(set(app.session_state.account_order), set(range(len(ACCOUNTS))))
        self.assertEqual(len(app.session_state.account_order), len(ACCOUNTS))
        self.assertIn("Shareholders' Equity", app.selectbox(key="class_0").options)
        self.assertNotIn("Common stock", app.selectbox(key="class_0").options)
        self.assertNotIn("Retained earnings", app.selectbox(key="class_0").options)
        for index, account in enumerate(ACCOUNTS):
            app.selectbox(key=f"class_{index}").set_value(account["category"])
        button(app, "Submit Classifications").click().run()
        button(app, "Continue to Liquidity").click().run()

        app.multiselect[0].set_value(list(LIQUIDITY_ORDER))
        for question in CONTEXT_QUESTIONS:
            app.selectbox(key=f"context_{question['id']}").set_value(question["correct"])
        button(app, "Submit Judgment Checks").click().run()
        button(app, "Continue to Ratio Lab").click().run()

        ratio_markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("vital-grid", ratio_markup)
        self.assertIn("$1,320,000", ratio_markup)
        self.assertEqual(len(app.metric), 0)

        for widget, value in zip(app.number_input, (260_000, 1.81, 54.5, 120.0)):
            widget.set_value(value)
        button(app, "Record Vital Signs").click().run()
        button(app, "Continue to Comparisons").click().run()

        self.assertEqual(
            app.selectbox(key="comparison_industry_type").label,
            "Current year compared with the average of all peers",
        )

        for question in ANALYSIS_QUESTIONS:
            app.radio(key=f"analysis_{question['id']}").set_value(question["correct"])
        for question in COMPARISON_QUESTIONS:
            app.selectbox(key=f"comparison_{question['id']}").set_value(question["correct"])
        button(app, "Submit Trend Analysis").click().run()
        button(app, "Continue to Diagnosis").click().run()

        diagnosis_markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Total Liabilities", diagnosis_markup)
        self.assertIn("Shareholders&#x27; Equity", diagnosis_markup)
        self.assertEqual([item.value for item in app.subheader][:1], ["Completed Patient Chart"])
        self.assertEqual(len(app.dataframe), 1)

        for question in DIAGNOSIS_QUESTIONS:
            app.radio(key=f"diagnosis_{question['id']}").set_value(question["correct"])
        app.multiselect[0].set_value(list(CORRECT_EVIDENCE))
        app.text_area[0].set_value(
            "Approve with conditions because liquidity is adequate while debt risk has increased."
        )
        button(app, "Sign the Patient Chart").click().run()
        feedback_markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("Evidence selection: 4 of 4 points", feedback_markup)
        self.assertIn("Written rationale: 3 of 3 points", feedback_markup)
        button(app, "Complete the Case").click().run()

        self.assertFalse(app.exception)
        self.assertEqual([item.value for item in app.header], ["Case Debrief"])
        self.assertEqual(app.metric[0].value, "39 / 39")
        self.assertEqual(app.metric[1].value, "100%")
        self.assertEqual(len(app.metric), 2)
        self.assertEqual(len(app.download_button), 0)
        final_text = "\n".join(item.value for item in app.markdown)
        self.assertNotIn("profitability", final_text.lower())
        self.assertNotIn("efficiency", final_text.lower())
        saved_value = app.query_params[SNAPSHOT_PARAMETER]
        saved = decode_snapshot(saved_value[0] if isinstance(saved_value, list) else saved_value)
        self.assertEqual(saved["p"], 6)
        self.assertTrue(saved["c"])


if __name__ == "__main__":
    unittest.main()
