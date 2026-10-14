"""Export the unchanged fixed case, teaching variants and Python scoring oracles."""
from __future__ import annotations
import copy
import itertools
import json
import random
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from browser.build import shared_source
from diagnosing_dollars import case_data as case, engine, progress

class State(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        self[key] = value


class Container:
    def __init__(self, recorder, node):
        self.recorder, self.node = recorder, node

    def __enter__(self):
        self.recorder.stack.append(self.node["children"])
        return self

    def __exit__(self, *args):
        self.recorder.stack.pop()

    def metric(self, label, value, **kwargs):
        self.node["children"].append({"kind": "metric", "label": label, "value": value})


class Recorder:
    def __init__(self):
        self.session_state = State()
        self.stack = [[]]

    def node(self, kind, **kwargs):
        node = {"kind": kind, **kwargs}
        self.stack[-1].append(node)
        return node

    def set_page_config(self, **kwargs):
        pass

    def markdown(self, text, unsafe_allow_html=False):
        self.node("html" if unsafe_allow_html else "markdown", text=text.strip())

    def __getattr__(self, kind):
        if kind in {"title", "header", "subheader", "write", "success", "warning", "info", "caption", "error"}:
            return lambda text: self.node(kind, text=text.replace(r"\$", "$"))
        raise AttributeError(kind)

    def radio(self, label, options, **kwargs):
        options = list(options)
        self.node("radio", label=label.replace(r"\$", "$"),
                  options=[x.replace(r"\$", "$") for x in options], key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def selectbox(self, label, options, **kwargs):
        options = list(options)
        self.node("select", label=label, options=options, key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def button(self, label, **kwargs):
        self.node("button", label=label, key=kwargs.get("key"),
                  disabled=kwargs.get("disabled", False),
                  action=kwargs.get("on_click").__name__ if kwargs.get("on_click") else None)
        return False

    def form_submit_button(self, label, **kwargs):
        self.node("button", label=label, action=kwargs["on_click"].__name__)
        return False

    def progress(self, value, **kwargs):
        self.node("progress", value=value)

    def columns(self, count):
        count = count if isinstance(count, int) else len(count)
        group = self.node("columns", children=[])
        columns = []
        for _ in range(count):
            node = {"kind": "column", "children": []}
            group["children"].append(node)
            columns.append(Container(self, node))
        return columns

    def tabs(self, labels):
        group = self.node("tabs", children=[])
        tabs = []
        for label in labels:
            node = {"kind": "tab", "label": label, "children": []}
            group["children"].append(node)
            tabs.append(Container(self, node))
        return tabs

    def form(self, key):
        return Container(self, self.node("form", key=key, children=[]))

    def expander(self, label, **kwargs):
        return Container(self, self.node("details", label=label,
                                        expanded=kwargs.get("expanded", False), children=[]))


    def number_input(self, label, **kwargs):
        self.node("number", label=label, key=kwargs["key"], value=kwargs.get("value"),
                  step=kwargs.get("step", 1), placeholder=kwargs.get("placeholder", ""))
        return self.session_state.get(kwargs["key"], kwargs.get("value"))

    def multiselect(self, label, options, **kwargs):
        self.node("many", label=label, options=list(options), key=kwargs["key"], help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], [])

    def text_area(self, label, **kwargs):
        self.node("text", label=label, key=kwargs["key"], placeholder=kwargs.get("placeholder"),
                  maxLength=kwargs.get("max_chars"), help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], "")

    def dataframe(self, rows, **kwargs):
        self.node("table", rows=rows)

    def divider(self):
        self.node("divider")

    @property
    def sidebar(self):
        return Container(self, self.node("sidebar", children=[]))

    @contextmanager
    def capture(self):
        self.stack = [[]]
        yield self.stack[0]


KEYS = ("cl", "li", "ra", "an", "di")
RENDERERS = ("render_intake", "render_classification", "render_liquidity",
             "render_ratio_lab", "render_analysis", "render_diagnosis", "render_debrief")
CATEGORIES = ("classification", "liquidity", "ratios", "analysis", "diagnosis")


def submissions(correct=True):
    choice = lambda question: question["correct"] if correct else next(
        answer for answer in question["options"] if answer != question["correct"])
    classes = {str(account["name"]): account["category"] if correct else next(
        category for category in case.CATEGORIES if category != account["category"]) for account in case.ACCOUNTS}
    context = {str(question["id"]): choice(question) for question in case.CONTEXT_QUESTIONS}
    analysis = {str(question["id"]): choice(question) for question in case.ANALYSIS_QUESTIONS}
    comparisons = {str(question["id"]): question["correct"] if correct else next(
        value for value in case.COMPARISON_OPTIONS if value != question["correct"]) for question in case.COMPARISON_QUESTIONS}
    diagnoses = {str(question["id"]): choice(question) for question in case.DIAGNOSIS_QUESTIONS}
    _, rubric = engine.score_reflection("Recommend approval with conditions; monitor liquidity and debt." if correct else "")
    ratios = asdict(engine.calculate_ratios(case.CURRENT_FINANCIALS)) if correct else {
        key: 0 for key in ("working_capital", "current_ratio", "debt_to_assets", "debt_to_equity")}
    return {
        "cl": progress.pack_classification(classes),
        "li": progress.pack_liquidity(case.LIQUIDITY_ORDER if correct else tuple(reversed(case.LIQUIDITY_ORDER)), context),
        "ra": progress.pack_ratios(ratios),
        "an": progress.pack_analysis(analysis, comparisons),
        "di": progress.pack_diagnosis(diagnoses, tuple(case.CORRECT_EVIDENCE) if correct else case.EVIDENCE_OPTIONS[4:], rubric),
    }


def export():
    here = Path(__file__).resolve().parent
    recorder = Recorder()
    namespace = {}
    with patch.dict(sys.modules, {"streamlit": recorder}):
        exec(compile(shared_source(), "original_teaching_renderer", "exec"), namespace)
    with recorder.capture() as css_nodes:
        namespace["inject_styles"]()
    with recorder.capture() as hero:
        namespace["render_header"]()
    correct, wrong = submissions(True), submissions(False)

    def feedback(items, show_name=False):
        for category, result in recorder.session_state.results.items():
            for key in ("feedback", "comparison_feedback"):
                if result.get(key) is items:
                    recorder.node("feedback", path=[category, key], showName=show_name)
                    return
        raise ValueError("Unknown feedback source")

    namespace["feedback_list"] = feedback
    namespace["stage_result_banner"] = lambda score, maximum: recorder.node("result-banner")
    namespace["render_ratio_answer_feedback"] = lambda result, expected: recorder.node("ratio-feedback")
    namespace["render_evidence_feedback"] = lambda result: recorder.node("evidence-feedback")
    namespace["render_reflection_feedback"] = lambda result: recorder.node("reflection-feedback")
    screens, legacy = [], []
    account_order, liquidity_order = list(range(len(case.ACCOUNTS))), list(range(4))
    for stage in range(7):
        variants = {}
        for status in ("unanswered", "wrong", "correct"):
            count = min(max(0, stage - 1), 5)
            answers = {key: correct[key] for key in KEYS[:count]}
            if 1 <= stage <= 5 and status != "unanswered":
                key = KEYS[stage - 1]
                answers[key] = (correct if status == "correct" else wrong)[key]
            payload = {"v": 1, "p": stage, "o": [account_order, liquidity_order],
                       "s": answers, "c": stage == 6}
            state = progress.state_from_snapshot(payload)
            recorder.session_state = State(state)
            with recorder.capture() as nodes:
                namespace[RENDERERS[stage]]()
            variants[status] = nodes
            if status == "unanswered":
                legacy.append({"token": progress.encode_snapshot(payload), "payload": payload})
        screens.append(variants)
    recorder.session_state = State(progress.state_from_snapshot(legacy[0]["payload"]))
    with recorder.capture() as sidebar:
        namespace["render_sidebar"]()
    errors = {}
    for name in CATEGORIES:
        stage = CATEGORIES.index(name) + 1
        recorder.session_state = State({"stage": stage, "submissions": {}, "results": {},
            "account_order": account_order, "liquidity_option_order": list(case.LIQUIDITY_ORDER)})
        namespace["submit_" + name]()
        errors[name] = next(value for key, value in recorder.session_state.items() if key.endswith("_error"))
    with recorder.capture() as reflection_model:
        original = {}
        with patch.dict(sys.modules, {"streamlit": recorder}):
            exec(compile(shared_source(), "original_feedback", "exec"), original)
        original["render_reflection_feedback"](progress.results_from_submissions({"di": correct["di"]})["diagnosis"])
    # The model response is original static teaching content; rubric rows are computed natively.
    model_response = next(node["text"] for node in reflection_model if node["kind"] == "info")
    data = {
        "title": "Diagnosing Dollars", "company": case.COMPANY_NAME,
        "stages": namespace["STAGES"], "maximumScores": namespace["MAX_SCORES"],
        "accounts": case.ACCOUNTS, "categories": case.CATEGORIES,
        "liquidityOrder": case.LIQUIDITY_ORDER, "context": case.CONTEXT_QUESTIONS,
        "current": case.CURRENT_FINANCIALS, "prior": case.PRIOR_FINANCIALS,
        "benchmarks": case.BENCHMARKS, "analysis": case.ANALYSIS_QUESTIONS,
        "comparisons": case.COMPARISON_QUESTIONS, "comparisonOptions": case.COMPARISON_OPTIONS,
        "diagnoses": case.DIAGNOSIS_QUESTIONS, "evidence": case.EVIDENCE_OPTIONS,
        "correctEvidence": [option for option in case.EVIDENCE_OPTIONS if option in case.CORRECT_EVIDENCE],
        "rubric": engine.REFLECTION_CRITERIA, "modelResponse": model_response,
        "screens": screens, "sidebar": sidebar, "hero": hero, "errors": errors,
        "performance": [{"minimum": value, "label": namespace["performance_label"](value)[0],
                         "message": namespace["performance_label"](value)[1]} for value in (90, 75, 60, 0)],
    }
    (here / "content.js").write_text("// Generated from unchanged Python teaching content.\nexport const DATA="
        + json.dumps(data, ensure_ascii=True, separators=(",", ":")) + ";\n")
    (here / "original.css").write_text(css_nodes[0]["text"].replace("<style>", "").replace("</style>", "").strip() + "\n")
    (here / "tests/legacy-links.json").write_text(json.dumps(legacy, indent=2) + "\n")
    fixtures = []
    rng = random.Random(7029)
    for stage in range(7):
        for attempt in range(12):
            answers = {}
            count = min(stage, 5) if stage else 0
            count = max(stage - 1, 0) if attempt == 0 else count
            for key in KEYS[:count]:
                answers[key] = copy.deepcopy(rng.choice([correct, wrong])[key])
            if "ra" in answers:
                answers["ra"] = [rng.choice([value, value + offset, 0.0]) for value, offset in
                    zip(asdict(engine.calculate_ratios(case.CURRENT_FINANCIALS)).values(), (100.0, 0.01, 0.1, 0.1))]
            payload = {"v": 1, "p": stage, "o": [account_order, liquidity_order],
                       "s": answers, "c": stage == 6}
            progress.validate_snapshot(payload)
            fixtures.append({"payload": payload, "results": progress.results_from_submissions(answers)})
    reflections = ["", "Recommend approval with conditions; monitor liquidity and debt.",
        "unapproved inventory creditor financing", "No conclusion can be made.", "CURRENT RATIO / LIABILITIES / REJECT",
        "The lender should extend the loan while monitoring current assets and solvency."]
    numbers = [-1000.5, -2.5, -1.5, -0.5, 0, 0.5, 1.5, 2.5, 1.125, 1.815, 1.005, 1000.5, 54.54545454545]
    oracles = {
        "submissions": fixtures,
        "perfect": correct, "wrong": wrong,
        "ratios": [{"input": values, "output": asdict(engine.calculate_ratios(values))}
                   for values in (case.CURRENT_FINANCIALS, case.PRIOR_FINANCIALS)],
        "reflections": [{"text": text, "result": engine.score_reflection(text)} for text in reflections],
        "format": [{"value": value, "currency": engine.format_currency(value),
                    "fixed": {str(n): f"{value:.{n}f}" for n in (0, 1, 2)}} for value in numbers],
    }
    (here / "tests/python-oracles.json").write_text(json.dumps(oracles, indent=2) + "\n")
    print(json.dumps({"stages": 7, "variants": 21, "scored_points": sum(namespace["MAX_SCORES"].values()),
                      "app_owned_assets": [], "curriculum_changes": []}, indent=2))


if __name__ == "__main__":
    export()
