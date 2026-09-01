import unittest

from streamlit.testing.v1 import AppTest

from diagnosing_dollars.case_data import ACCOUNTS, CONTEXT_QUESTIONS, LIQUIDITY_ORDER
from diagnosing_dollars.progress import SNAPSHOT_PARAMETER, decode_snapshot


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def saved_progress(app: AppTest) -> str:
    value = app.query_params[SNAPSHOT_PARAMETER]
    return value[0] if isinstance(value, list) else value


def reach_ratio_review() -> AppTest:
    app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    button(app, "Open the Case").click().run()

    for index, account in enumerate(ACCOUNTS):
        app.selectbox(key=f"class_{index}").set_value(account["category"])
    button(app, "Submit Classifications").click().run()
    button(app, "Continue to Liquidity").click().run()

    app.multiselect(key="liquidity_order").set_value(list(LIQUIDITY_ORDER))
    for question in CONTEXT_QUESTIONS:
        app.selectbox(key=f"context_{question['id']}").set_value(question["correct"])
    button(app, "Submit Judgment Checks").click().run()
    button(app, "Continue to Ratio Lab").click().run()

    for key, value in (
        ("ratio_working_capital", 260_000),
        ("ratio_current_ratio", 1.70),
        ("ratio_debt_to_assets", 54.5),
        ("ratio_debt_to_equity", 120.0),
    ):
        app.number_input(key=key).set_value(value)
    button(app, "Record Vital Signs").click().run()
    return app


class ProgressRecoveryTests(unittest.TestCase):
    def test_malformed_snapshot_is_replaced_with_fresh_progress(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=30)
        app.query_params[SNAPSHOT_PARAMETER] = "not-a-valid-snapshot"
        app.run()

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.stage, 0)
        self.assertEqual(dict(app.session_state.results), {})
        restored = decode_snapshot(saved_progress(app))
        self.assertIsNotNone(restored)
        self.assertEqual(restored["p"], 0)
        self.assertEqual(restored["s"], {})
        self.assertFalse(restored["c"])

    def test_new_session_restores_mid_activity_page_and_results(self):
        app = reach_ratio_review()
        saved = saved_progress(app)
        payload = decode_snapshot(saved)

        self.assertLess(len(saved), 1000)
        self.assertEqual(payload["p"], 3)
        self.assertEqual(set(payload["s"]), {"cl", "li", "ra"})
        self.assertFalse(payload["c"])

        restored = AppTest.from_file("streamlit_app.py", default_timeout=30)
        restored.query_params[SNAPSHOT_PARAMETER] = saved
        restored.run()

        self.assertFalse(restored.exception)
        self.assertEqual(restored.session_state.stage, 3)
        self.assertEqual(set(restored.session_state.results), {"classification", "liquidity", "ratios"})
        self.assertEqual(restored.session_state.results["ratios"]["score"], 3)
        self.assertEqual([item.value for item in restored.header], ["Ratio Lab"])

    def test_restart_replaces_saved_progress(self):
        app = reach_ratio_review()
        previous = saved_progress(app)

        button(app, "Restart Case").click().run()

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.stage, 0)
        self.assertEqual(dict(app.session_state.results), {})
        self.assertEqual(dict(app.session_state.submissions), {})
        replacement = saved_progress(app)
        payload = decode_snapshot(replacement)
        self.assertNotEqual(replacement, previous)
        self.assertEqual(payload["p"], 0)
        self.assertEqual(payload["s"], {})
        self.assertFalse(payload["c"])


if __name__ == "__main__":
    unittest.main()
