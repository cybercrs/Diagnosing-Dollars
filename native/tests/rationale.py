"""Verify session-only rationale survives native review but clears on refresh."""
import importlib.util
import json
import threading
import urllib.parse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("clinical_native_qa", HERE / "browser.py")
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(qa.Handler, directory=str(qa.NATIVE / "dist")))
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = "http://127.0.0.1:" + str(server.server_port)
address = origin + qa.PREFIX + "?progress=" + qa.LEGACY[5]["token"]
errors = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
        proxy={"server": "http://127.0.0.1:9", "bypass": "127.0.0.1,localhost"})
    page = browser.new_page()
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(address, wait_until="networkidle")
    page.wait_for_function("document.documentElement.dataset.ready==='true'&&document.documentElement.dataset.saving==='false'")
    before = qa.decode_snapshot(urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["progress"][0])
    phrase = "Recommend approval with conditions; working capital supports liquidity while debt increases risk."
    exact_url = page.url
    page.locator("#diagnosis_reflection").fill(phrase)
    assert page.url == exact_url
    page.get_by_role("button", name="Back", exact=True).click()
    page.wait_for_function("document.documentElement.dataset.view==='4'&&document.documentElement.dataset.saving==='false'")
    expect(page.locator("#lesson input,#lesson select,#lesson textarea")).to_have_count(0)
    assert qa.decode_snapshot(urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["progress"][0]) == before
    page.get_by_role("button", name="Forward", exact=True).click()
    page.wait_for_function("document.documentElement.dataset.view==='5'&&document.documentElement.dataset.saving==='false'")
    expect(page.locator("#diagnosis_reflection")).to_have_value(phrase)
    assert page.url == exact_url
    page.reload(wait_until="networkidle")
    page.wait_for_function("document.documentElement.dataset.ready==='true'&&document.documentElement.dataset.saving==='false'")
    expect(page.locator("#diagnosis_reflection")).to_have_value("")
    assert page.url == exact_url
    browser.close()
server.shutdown()
assert not errors, errors
path = qa.RESULTS / "browser-results.json"
result = json.loads(path.read_text())
assert all(check["status"] == "passed" for check in result["checks"])
result["checks"].append({"name": "Raw rationale preserved across native Back/Forward, absent from URL, cleared by refresh", "status": "passed"})
path.write_text(json.dumps(result, indent=2) + "\n")
print("PASS: session-only rationale navigation and refresh; no browser errors", flush=True)
