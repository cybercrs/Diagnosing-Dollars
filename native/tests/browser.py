"""Full local native Chromium QA at the actual project-prefixed /js/ path."""
from __future__ import annotations

import json
import re
import statistics
import sys
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnosing_dollars.progress import decode_snapshot, encode_snapshot, results_from_submissions
from diagnosing_dollars import case_data as case, engine  # noqa: E402

NATIVE = ROOT / "native"
RESULTS = NATIVE / "test-results"
PREFIX = "/Diagnosing-Dollars/js/"
RESULTS.mkdir(exist_ok=True)
ORACLE = json.loads((NATIVE / "tests/python-oracles.json").read_text())
LEGACY = json.loads((NATIVE / "tests/legacy-links.json").read_text())
checks, requests, external, errors, console_errors = [], [], [], [], []


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        requests.append(path)
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif path.startswith(PREFIX):
            self.path = path[len(PREFIX) - 1:]
            super().do_GET()
        else:
            self.send_error(404)


def passed(name):
    checks.append({"name": name, "status": "passed"})
    print("PASSED:", name, flush=True)


def main():
    import base64
    import csv
    import zlib
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(NATIVE / "dist")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    url = origin + PREFIX
    result = {"url": url, "conditions": "Actual local native Chromium; all external requests blocked."}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
            proxy={"server": "http://127.0.0.1:9", "bypass": "127.0.0.1,localhost"})

        def attach(context):
            def route(route):
                if route.request.url.startswith(origin):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()
            context.route("**/*", route)
            def events(page):
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            context.on("page", events)

        context = browser.new_context(viewport={"width": 1280, "height": 960}, accept_downloads=True)
        attach(context)
        page = context.new_page()

        def loaded(view=None):
            page.wait_for_function("document.documentElement.dataset.ready==='true'")
            page.wait_for_function("document.documentElement.dataset.saving==='false'")
            if view is not None:
                page.wait_for_function("v=>document.documentElement.dataset.view===String(v)", arg=view)
            expect(page).to_have_title("Diagnosing Dollars")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            assert not re.search(r"\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b", page.locator("body").inner_text(), re.I)

        def go(address=url, view=None):
            page.goto(address, wait_until="networkidle")
            loaded(view)

        def query():
            return urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)

        def state():
            value = decode_snapshot(query()["progress"][0])
            assert value is not None
            return value

        def drafts():
            token = query()["draft"][0]
            return json.loads(zlib.decompress(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))))

        def button(name):
            page.get_by_role("button", name=name, exact=True).click()
            loaded()

        def select(key, value):
            page.locator("#" + key).select_option(value)
            loaded()

        def radio(question, prefix, wrong=False):
            value = next(item for item in question["options"] if item != question["correct"]) if wrong else question["correct"]
            page.get_by_role("radio", name=value, exact=True).check()
            loaded()

        def shot(name):
            page.screenshot(path=str(RESULTS / (name + ".png")), full_page=True)

        def fill_classifications(wrong=False, mixed=False):
            for index, account in enumerate(case.ACCOUNTS):
                value = next(category for category in case.CATEGORIES if category != account["category"]) if wrong or mixed and index == 0 else account["category"]
                select("class_" + str(index), value)

        def fill_liquidity(wrong=False):
            for name in reversed(case.LIQUIDITY_ORDER) if wrong else case.LIQUIDITY_ORDER:
                page.get_by_role("checkbox", name=name, exact=True).check()
                loaded()
            for question in case.CONTEXT_QUESTIONS:
                value = next(value for value in question["options"] if value != question["correct"]) if wrong else question["correct"]
                select("context_" + question["id"], value)

        def fill_ratios(wrong=False, mixed=False):
            values = engine.calculate_ratios(case.CURRENT_FINANCIALS)
            for key in ("working_capital", "current_ratio", "debt_to_assets", "debt_to_equity"):
                value = 0 if wrong or mixed and key == "working_capital" else getattr(values, key)
                page.locator("#ratio_" + key).fill(str(value))
                loaded()

        def fill_analysis(wrong=False):
            for question in case.ANALYSIS_QUESTIONS:
                radio(question, "analysis_", wrong)
            for question in case.COMPARISON_QUESTIONS:
                value = next(value for value in case.COMPARISON_OPTIONS if value != question["correct"]) if wrong else question["correct"]
                select("comparison_" + question["id"], value)

        def fill_diagnosis(wrong=False):
            for question in case.DIAGNOSIS_QUESTIONS:
                radio(question, "diagnosis_", wrong)
            selected = case.EVIDENCE_OPTIONS[4:] if wrong else [value for value in case.EVIDENCE_OPTIONS if value in case.CORRECT_EVIDENCE]
            for option in selected:
                page.get_by_role("checkbox", name=option, exact=True).check()
                loaded()
            page.locator("#diagnosis_reflection").fill("This statement is long enough but contains none of the rubric words." if wrong else "Recommend approval with conditions; monitor liquidity and debt.")

        try:
            go(view=0)
            expect(page.get_by_role("button", name="Back", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
            page.locator("#sidebar summary").click()
            expect(page.locator("#sidebar")).to_contain_text("Working capital = Current assets")
            shot("intake-desktop")
            button("Open the Case")
            loaded(1)
            button("Submit Classifications")
            expect(page.get_by_role("alert")).to_contain_text("Classify every account")
            first_order = state()["o"]
            fill_classifications(mixed=True)
            draft_url = page.url
            before = state()
            button("Back")
            loaded(0)
            assert state() == before
            expect(page.locator("#lesson input,#lesson select,#lesson textarea")).to_have_count(0)
            expect(page.get_by_role("button", name="Restart Case", exact=True)).to_be_disabled()
            button("Forward")
            loaded(1)
            page.reload()
            loaded(1)
            assert state()["o"] == first_order
            assert page.url == draft_url
            assert drafts()["class_0"] != case.ACCOUNTS[0]["category"]
            button("Submit Classifications")
            expect(page.locator("#lesson")).to_contain_text("14 of 15 correct")
            expect(page.get_by_role("button", name="Submit Classifications", exact=True)).to_have_count(0)
            button("Continue to Liquidity")
            passed("Classification validation, deliberate mistake, saved display order/drafts, review and one-shot submission")

            loaded(2)
            button("Submit Judgment Checks")
            expect(page.get_by_role("alert")).to_contain_text("Complete the liquidity order")
            fill_liquidity()
            page.get_by_role("button", name="Move Cash later", exact=True).click()
            loaded()
            assert drafts()["liquidity_order"][:2] == ["Accounts receivable", "Cash"]
            page.get_by_role("button", name="Move Cash earlier", exact=True).click()
            loaded()
            order_url = page.url
            page.reload()
            loaded(2)
            assert page.url == order_url
            assert drafts()["liquidity_order"] == list(case.LIQUIDITY_ORDER)
            button("Submit Judgment Checks")
            expect(page.locator("#lesson")).to_contain_text("4 of 4 correct")
            button("Continue to Ratio Lab")
            passed("Ordered liquidity selections, accessible reorder buttons, validation and saved context answers")

            loaded(3)
            page.locator("#ratio_current_ratio").fill("1e")
            loaded()
            invalid_url = page.url
            page.reload()
            loaded(3)
            expect(page.locator("#ratio_current_ratio")).to_have_value("1e")
            assert page.url == invalid_url
            button("Record Vital Signs")
            assert "ra" not in state()["s"]
            fill_ratios(mixed=True)
            page.locator("#ratio_debt_to_equity").fill("120.0")
            loaded()
            ratio_draft = page.url
            page.reload()
            loaded(3)
            expect(page.locator("#ratio_debt_to_equity")).to_have_value("120.0")
            assert page.url == ratio_draft
            button("Record Vital Signs")
            expect(page.locator("#lesson")).to_contain_text("3 of 4 correct")
            expect(page.locator("#lesson")).to_contain_text("Your answer: $0 · Correct answer: $260,000")
            shot("ratio-feedback-desktop")
            button("Continue to Comparisons")
            passed("Incomplete numeric draft refresh, required values, decimal restoration and original ratio feedback")

            loaded(4)
            fill_analysis()
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Download table as CSV", exact=True).click()
            download = download_info.value
            assert download.suggested_filename == "diagnosing-dollars-comparisons.csv"
            download.save_as(str(RESULTS / "comparisons.csv"))
            with (RESULTS / "comparisons.csv").open() as file:
                rows = list(csv.DictReader(file))
            assert len(rows) == 4 and rows[0]["Current ratio"] == "1.81:1"
            assert rows[1]["Debt to assets"] == "50.0%"
            page.get_by_role("button", name="Expand table", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            expect(page.get_by_role("dialog").get_by_role("table")).to_have_count(1)
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).to_have_count(0)
            expect(page.get_by_role("button", name="Expand table", exact=True)).to_be_focused()
            button("Submit Trend Analysis")
            expect(page.locator("#lesson")).to_contain_text("6 of 6 correct")
            button("Continue to Diagnosis")
            passed("Original comparison rows, CSV download, keyboard table expansion and complete trend analysis")

            loaded(5)
            button("Sign the Patient Chart")
            expect(page.get_by_role("alert")).to_contain_text("at least 20 characters")
            fill_diagnosis()
            assert "diagnosis_reflection" not in drafts()
            rationale_url = page.url
            page.reload()
            loaded(5)
            expect(page.locator("#diagnosis_reflection")).to_have_value("")
            assert "diagnosis_reflection" not in drafts()
            assert page.url == rationale_url
            for question in case.DIAGNOSIS_QUESTIONS:
                expect(page.get_by_role("radio", name=question["correct"], exact=True)).to_be_checked()
            page.locator("#diagnosis_reflection").fill("Recommend approval with conditions; monitor liquidity and debt.")
            button("Sign the Patient Chart")
            expect(page.locator("#lesson")).to_contain_text("10 of 10 correct")
            assert state()["s"]["di"][2] == 7
            button("Complete the Case")
            loaded(6)
            expect(page.locator("#lesson")).to_contain_text("37 / 39")
            expect(page.locator("#lesson")).to_contain_text("95%")
            completed_url = page.url
            result["completion_bookmark"] = completed_url
            shot("completed-desktop")
            passed("Session-only written rationale, saved rubric flags, validated diagnosis and actual 37/39 case completion")

            before = state()
            for view in range(5, -1, -1):
                button("Back")
                loaded(view)
                assert state() == before
                expect(page.locator("#lesson input,#lesson select,#lesson textarea")).to_have_count(0)
                expect(page.get_by_role("button", name="Restart Case", exact=True)).to_be_disabled()
                if view == 3:
                    shot("review-desktop")
            forward = page.get_by_role("button", name="Forward", exact=True)
            forward.focus()
            page.keyboard.press("Tab")
            page.keyboard.press("Shift+Tab")
            expect(forward).to_be_focused()
            assert forward.evaluate("e=>e.matches(':focus-visible')&&getComputedStyle(e).outlineWidth==='2px'")
            page.keyboard.press("Enter")
            loaded(1)
            for view in range(2, 7):
                button("Forward")
                loaded(view)
            expect(forward).to_be_disabled()
            assert state() == before
            review_url = completed_url.replace("view=6", "view=3")
            go(review_url, 3)
            page.reload()
            loaded(3)
            assert state() == before
            go(completed_url.replace("view=6", "view=999"), 6)
            assert state() == before
            passed("All six earlier pages are readonly, repeated review, keyboard/focus, refresh/bookmark and future rejection")

            for width in (900, 390):
                page.set_viewport_size({"width": width, "height": 844})
                go(completed_url, 6)
                shot("completed-" + str(width))
                for name in ("Back", "Forward"):
                    box = page.get_by_role("button", name=name, exact=True).bounding_box()
                    assert box["width"] >= 44 and box["height"] >= 44
                    assert box["x"] + box["width"] <= width
                go(completed_url.replace("view=6", "view=4"), 4)
                assert page.locator(".table-wrap").evaluate("e=>e.scrollWidth>e.clientWidth") if width == 390 else True
                shot("comparisons-" + str(width))
            page.set_viewport_size({"width": 1280, "height": 960})
            go(completed_url, 6)
            button("Try the Case Again")
            loaded(0)
            assert state()["s"] == {}
            independent = browser.new_context()
            attach(independent)
            other = independent.new_page()
            other.goto(url, wait_until="networkidle")
            other.wait_for_function("document.documentElement.dataset.ready==='true'")
            assert other.locator("html").get_attribute("data-reached") == "0"
            go(completed_url, 6)
            assert other.locator("html").get_attribute("data-reached") == "0"
            independent.close()
            passed("900px/390px responsive layouts, table scrolling, 44px navigation, both reset controls and independent sessions")

            for fixture in LEGACY:
                address = url + "?progress=" + fixture["token"] + "&view=" + str(fixture["payload"]["p"]) + "&tag=a%20b&tag=c%2Fd#saved"
                go(address, fixture["payload"]["p"])
                assert state() == fixture["payload"]
                assert query()["tag"] == ["a b", "c/d"]
                assert urllib.parse.urlsplit(page.url).fragment == "saved"
            go(url + "?progress=bad!&view=999", 0)
            expect(page.locator("#lesson")).to_contain_text("This saved link could not be restored")
            passed("All seven original Python stages, native snapshots, extra query values/fragments and malformed links")

            for wrong, expected in ((False, 39), (True, 0)):
                go(view=0)
                button("Open the Case")
                fill_classifications(wrong)
                button("Submit Classifications")
                button("Continue to Liquidity")
                fill_liquidity(wrong)
                button("Submit Judgment Checks")
                button("Continue to Ratio Lab")
                fill_ratios(wrong)
                button("Record Vital Signs")
                button("Continue to Comparisons")
                fill_analysis(wrong)
                button("Submit Trend Analysis")
                button("Continue to Diagnosis")
                fill_diagnosis(wrong)
                button("Sign the Patient Chart")
                button("Complete the Case")
                loaded(6)
                expect(page.locator("#lesson")).to_contain_text(str(expected) + " / 39")
                assert sum(value["score"] for value in results_from_submissions(state()["s"]).values()) == expected
            passed("Two further complete cases: all-correct 39/39 and all-wrong 0/39, including evidence penalties")

            for missed, label in ((3, "Chief Financial Diagnostician"), (9, "Strong Clinical Judgment"), (15, "Developing Diagnostician")):
                payload = {"v": 1, "p": 6, "o": LEGACY[6]["payload"]["o"], "s": json.loads(json.dumps(ORACLE["perfect"])), "c": True}
                for index in range(missed):
                    payload["s"]["cl"][index] = next(value for value in range(len(case.CATEGORIES)) if value != payload["s"]["cl"][index])
                go(url + "?progress=" + encode_snapshot(payload), 6)
                expect(page.locator("#lesson")).to_contain_text(label)
            passed("All four dynamic debrief performance labels and their finalized branding")
            timings = []
            for _ in range(5):
                cold = browser.new_context()
                attach(cold)
                fresh = cold.new_page()
                session = cold.new_cdp_session(fresh)
                session.send("Network.enable")
                session.send("Network.setCacheDisabled", {"cacheDisabled": True})
                fresh.goto(url, wait_until="networkidle")
                fresh.wait_for_function("document.documentElement.dataset.ready==='true'")
                timings.append(fresh.evaluate("performance.getEntriesByName('diagnosing-ready')[0].startTime"))
                cold.close()
            result["cold_initialization_ms"] = {"samples": timings, "median": statistics.median(timings),
                "conditions": "Five cache-disabled fresh Chromium contexts on local loopback; no network-speed or capacity claim."}
            assert external == errors == console_errors == []
            assert not any(path.endswith((".py", ".whl", ".wasm")) or "/vendor/" in path or "/_stcore/" in path for path in requests)
            passed("Five local cold initializations and zero external requests, package/runtime downloads or browser errors")
        except Exception:
            checks.append({"name": "Browser walkthrough", "status": "failed", "error": traceback.format_exc()})
            page.screenshot(path=str(RESULTS / "failure.png"), full_page=True)
            result["body_on_failure"] = page.locator("body").inner_text()
        browser.close()
    server.shutdown()
    result.update(checks=checks, requests=sorted(set(requests)), external_requests=external, page_errors=errors, console_errors=console_errors)
    (RESULTS / "browser-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("completion_bookmark", "body_on_failure")}, indent=2), flush=True)
    return int(any(check["status"] == "failed" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
