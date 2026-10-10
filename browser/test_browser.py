"""Actual Chromium/Wasm lesson walkthrough. External requests are blocked."""
from __future__ import annotations
import argparse
import json
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class Walkthrough:
    def __init__(self, page, results, result_dir):
        self.page, self.results, self.directory = page, results, result_dir
        self.runs = 0
        def completed(message):
            if message.text.startswith("BROWSER_VERSIONS="):
                self.runs += 1
        page.on("console", completed)

    def query(self):
        return {k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.page.url).query).items()}

    def idle(self):
        self.page.wait_for_timeout(100)
        self.page.locator('[data-test-script-state="notRunning"]').wait_for(timeout=30000)
        assert self.page.locator('[data-testid="stException"]').count() == 0

    def wait_run(self, previous):
        deadline = time.monotonic() + 45
        while self.runs <= previous and time.monotonic() < deadline:
            self.page.wait_for_timeout(50)
        assert self.runs > previous, "Python rerun did not finish"
        self.idle()

    def loaded(self):
        self.page.get_by_role('button', name='Back', exact=True).wait_for(timeout=120000)
        self.idle()

    def view(self, index):
        self.page.wait_for_function('(v)=>new URLSearchParams(location.search).get("view")===String(v)', arg=index, timeout=30000)
        self.idle()
        assert self.query()['view'] == str(index)

    def click(self, label, sidebar=False):
        loc = self.page.locator('[data-testid="stSidebar"]' if sidebar else '[data-testid="stMain"]')
        previous = self.runs
        loc.get_by_role('button', name=label, exact=True).click()
        self.wait_run(previous)

    def changed(self, url):
        self.page.wait_for_function('(url)=>location.href!==url', arg=url, timeout=30000)
        self.idle()

    def select(self, key, value):
        combobox = self.page.locator(f'[class~="st-key-{key}"]').get_by_role('combobox')
        if self.page.locator(f'[class~="st-key-{key}"] [data-baseweb=select]').inner_text().strip() == value:
            return
        previous = self.runs
        previous_url = self.page.url
        combobox.click()
        self.page.get_by_role('option', name=value, exact=True).click()
        self.wait_run(previous)
        self.changed(previous_url)

    def radio(self, key, value):
        loc = self.page.locator(f'[class~="st-key-{key}"]')
        radio = loc.get_by_role('radio', name=value.replace(r'\$', '$'), exact=True)
        if radio.is_checked():
            return
        previous = self.runs
        previous_url = self.page.url
        radio.locator('xpath=ancestor::label').click()
        self.wait_run(previous)
        self.changed(previous_url)

    def many(self, key, values):
        loc = self.page.locator(f'[class~="st-key-{key}"]')
        for value in values:
            previous = self.runs
            previous_url = self.page.url
            loc.get_by_role('combobox').click()
            self.page.get_by_role('option', name=value, exact=True).click()
            self.wait_run(previous)
            self.changed(previous_url)
        self.page.keyboard.press('Escape')

    def number(self, key, value):
        loc = self.page.locator(f'[class~="st-key-{key}"]').get_by_role('spinbutton')
        previous = self.runs
        previous_url = self.page.url
        loc.fill(str(value))
        loc.press('Tab')
        self.wait_run(previous)
        self.changed(previous_url)

    def disabled(self, label):
        expect(self.page.get_by_role('button', name=label, exact=True)).to_be_disabled()

    def text(self, value):
        expect(self.page.locator('body')).to_contain_text(value, timeout=30000)

    def shot(self, name):
        self.page.screenshot(path=str(self.directory / (name + '.png')), full_page=True)

    def passed(self, label):
        self.results['checks'].append({'name':label,'status':'passed'})
        print('PASSED:', label, flush=True)

    def review(self, current, repeats=2):
        snapshot = {k:v for k,v in self.query().items() if k != 'view'}
        for _ in range(repeats):
            self.click('Back'); self.view(current-1)
            self.text('Review only. Return to your current page to continue the activity.')
            expect(self.page.locator('[data-testid="stMain"] [data-testid="stButton"]').get_by_role('button')).to_have_count(2)
            assert self.page.get_by_role('radio').count() == 0
            assert self.page.get_by_role('combobox').count() == 0
            assert self.page.get_by_role('spinbutton').count() == 0
            assert self.page.locator('[data-testid=stTextArea] textarea').count() == 0
            assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
            self.click('Forward'); self.view(current)
            assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
            self.disabled('Forward')
        self.passed('Read-only repeat review leaves progress, answers and scores unchanged')

    def refresh_review(self, current):
        snapshot = {k:v for k,v in self.query().items() if k != 'view'}
        self.click('Back'); self.view(current-1)
        bookmark = self.page.url
        self.page.reload(wait_until='domcontentloaded'); self.loaded(); self.view(current-1)
        assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
        clone=self.page.context.new_page()
        test=Walkthrough(clone,self.results,self.directory)
        clone.goto(bookmark,wait_until='domcontentloaded'); test.loaded(); test.view(current-1)
        assert {k:v for k,v in test.query().items() if k != 'view'} == snapshot
        test.click('Forward'); test.view(current)
        clone.goto(urllib.parse.urlunsplit(urllib.parse.urlsplit(clone.url)._replace(query=urllib.parse.urlencode({**test.query(),'view':'999'}))), wait_until='domcontentloaded')
        test.loaded(); test.view(current); test.disabled('Forward')
        assert {k:v for k,v in test.query().items() if k != 'view'} == snapshot
        clone.close()
        self.click('Forward'); self.view(current)
        self.passed('Review refresh, bookmark and future-view rejection preserve canonical work')

    def layout(self, kind):
        nav=self.page.locator('.st-key-browser_navigation')
        boxes=[nav.get_by_role('button',name=name,exact=True).bounding_box() for name in ('Back','Forward')]
        assert all(box and 44<=box['width']<=45 and 44<=box['height']<=45 for box in boxes), boxes
        assert abs(boxes[0]['y']-boxes[1]['y'])<=1, boxes
        assert 0<boxes[1]['x']-boxes[0]['x']<=60, boxes
        main=self.page.locator('.block-container').bounding_box()
        assert boxes[0]['x']>main['x']+main['width']/2, (main, boxes)
        assert self.page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        self.results.setdefault('navigation_layout',{})[kind]=boxes
        self.shot(kind)

    def finish(self, current, start, reset, sidebar):
        self.shot('completed')
        final_query={k:v for k,v in self.query().items() if k!='view'}
        bookmark=self.page.url
        self.results['completion_bookmark'] = bookmark
        for index in range(current-1,-1,-1):
            self.click('Back'); self.view(index)
            expect(self.page.locator('[data-testid="stMain"] [data-testid="stButton"]').get_by_role('button')).to_have_count(2)
            assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.shot('readonly')
        forward=self.page.get_by_role('button',name='Forward',exact=True)
        forward.focus()
        self.page.keyboard.press('Tab')
        self.page.keyboard.press('Shift+Tab')
        expect(forward).to_be_focused()
        assert forward.evaluate("e=>e.matches(':focus-visible')")
        assert forward.evaluate('e=>getComputedStyle(e).outlineWidth')=='2px'
        self.page.keyboard.press('Enter'); self.view(1)
        for index in range(2,current+1):
            self.click('Forward'); self.view(index)
            assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.disabled('Forward')
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(current)
        assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.passed('Complete lesson, every reached review page, keyboard focus and refresh')
        clean=self.page.context.new_page();t=Walkthrough(clean,self.results,self.directory)
        clean.goto(self.results['url'],wait_until='domcontentloaded');t.loaded();t.view(0)
        assert t.query()['progress']!=final_query['progress']
        clean.close()
        other_context = self.page.context.browser.new_context()
        other = other_context.new_page(); independent = Walkthrough(other, self.results, self.directory)
        other.goto(self.results['url'], wait_until='domcontentloaded'); independent.loaded(); independent.view(0)
        assert independent.query()['progress'] != final_query['progress']
        other.goto(bookmark, wait_until='domcontentloaded'); independent.loaded(); independent.view(current)
        assert {k:v for k,v in independent.query().items() if k!='view'} == final_query
        other_context.close()
        self.click(reset,sidebar);self.view(start)
        assert self.query()['progress']!=final_query['progress']
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(start)
        self.passed('Independent tab and reset replace progress without changing old bookmarks')
        self.page.set_viewport_size({'width':390,'height':844})
        if start==0:
            self.click(START);self.view(1)
        self.layout('narrow')
        self.passed('Narrow viewport: accessible boxed 44px arrows aligned at upper right')
        self.page.set_viewport_size({'width':1280,'height':900})
        self.page.goto(self.results['url']+'/classroom/',wait_until='domcontentloaded');self.loaded();self.view(0)
        self.click(START);self.view(1)
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(1)
        assert urllib.parse.urlsplit(self.page.url).path=='/classroom/'
        self.passed('Subdirectory paths, runtime assets and refresh')
        self.page.goto(self.results['url'] + '/?progress=invalid-token&view=999', wait_until='domcontentloaded')
        self.loaded(); self.view(0); self.disabled('Forward')
        self.passed('Malformed progress and future view reset to a fresh lesson')


from diagnosing_dollars.case_data import ACCOUNTS, ANALYSIS_QUESTIONS, COMPARISON_QUESTIONS, CONTEXT_QUESTIONS, CORRECT_EVIDENCE, DIAGNOSIS_QUESTIONS, LIQUIDITY_ORDER
START='Open the Case'


def lesson(h):
    h.click(START);h.view(1)
    h.click('Submit Classifications');h.text('Classify every account before submitting')
    h.select('class_0',ACCOUNTS[0]['category']);h.review(1);h.refresh_review(1)
    expect(h.page.locator('.st-key-class_0')).to_contain_text(ACCOUNTS[0]['category'])
    for i,a in enumerate(ACCOUNTS):
        h.select(f'class_{i}',a['category'] if i else 'Current liabilities')
    h.click('Submit Classifications');h.text('Review');h.disabled('Forward')
    h.passed('Required classifications, wrong-answer scoring and draft/bookmark recovery')
    h.click('Continue to Liquidity');h.view(2)
    h.many('liquidity_order',LIQUIDITY_ORDER)
    for q in CONTEXT_QUESTIONS:h.select('context_'+q['id'],q['correct'])
    h.click('Submit Judgment Checks');h.click('Continue to Ratio Lab');h.view(3)
    for key,value in zip(('working_capital','current_ratio','debt_to_assets','debt_to_equity'),(260000,1.70,54.5,120.0)):
        h.number('ratio_'+key,value)
    h.click('Record Vital Signs');h.text('Incorrect');h.review(3)
    h.click('Continue to Comparisons');h.view(4)
    for q in ANALYSIS_QUESTIONS:h.radio('analysis_'+q['id'],q['correct'])
    for q in COMPARISON_QUESTIONS:h.select('comparison_'+q['id'],q['correct'])
    h.click('Submit Trend Analysis');h.click('Continue to Diagnosis');h.view(5)
    for q in DIAGNOSIS_QUESTIONS:h.radio('diagnosis_'+q['id'],q['correct'])
    h.many('diagnosis_evidence',CORRECT_EVIDENCE)
    previous = h.runs
    h.page.locator('.st-key-diagnosis_reflection').get_by_role('textbox').fill('Approve with conditions because liquidity is adequate while debt risk has increased.')
    h.page.locator('.st-key-diagnosis_reflection').get_by_role('textbox').press('Tab');h.wait_run(previous)
    h.review(5)
    expect(h.page.locator('.st-key-diagnosis_reflection').get_by_role('textbox')).to_have_value('Approve with conditions because liquidity is adequate while debt risk has increased.')
    h.click('Sign the Patient Chart');h.text('Written rationale: 3 of 3 points')
    h.click('Complete the Case');h.view(6);h.text('Case Debrief')
    expect(h.page.locator('[data-testid=stMetricValue]').first).to_contain_text('37 / 39', timeout=30000)
    expect(h.page.locator('[data-testid=stMetricValue]').nth(1)).to_contain_text('95%', timeout=30000)
    h.passed('Complete case retains deliberate classification/ratio mistakes and rationale rubric')
    h.finish(6,0,'Restart Case',True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist',type=Path,default=ROOT/'browser/dist')
    parser.add_argument('--results',type=Path,default=ROOT/'browser/test-results')
    args=parser.parse_args();args.results.mkdir(parents=True,exist_ok=True)
    requests=[]
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            requests.append(self.path)
            if self.path.startswith('/classroom/'):
                self.path=self.path[len('/classroom'):]
            if self.path=='/favicon.ico':
                self.send_response(204);self.end_headers()
            elif self.path=='/app.json':
                config=json.loads((args.dist/'app.json').read_text())
                config['files']['browser/app.py']+='\nimport sys,json,pyodide\nprint("BROWSER_VERSIONS="+json.dumps({"python":sys.version.split()[0],"streamlit":st.__version__,"pyodide":pyodide.__version__}))\n'
                payload=json.dumps(config).encode();self.send_response(200)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            else:super().do_GET()
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(args.dist)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results={'url':f'http://127.0.0.1:{server.server_port}','transport':'actual local static stlite/Wasm; external requests blocked','checks':[],'page_errors':[],'console_errors':[],'external_requests':[]}
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,proxy={'server':'http://127.0.0.1:9','bypass':'127.0.0.1,localhost'})
        context=browser.new_context(viewport={'width':1280,'height':900})
        context.on('request',lambda r:results['external_requests'].append(r.url) if r.url.startswith('http') and not r.url.startswith(results['url']) else None)
        page=context.new_page()
        page.on('pageerror',lambda e:results['page_errors'].append(str(e)))
        def console(message):
            if message.text.startswith('BROWSER_VERSIONS='):results['runtime']=json.loads(message.text.split('=',1)[1])
            if message.type=='error':results['console_errors'].append(message.text)
        page.on('console',console)
        h=Walkthrough(page,results,args.results)
        try:
            start=time.monotonic();page.goto(results['url'],wait_until='domcontentloaded');h.loaded();h.view(0)
            results['initial_render_seconds']=round(time.monotonic()-start,2)
            assert results['runtime']['streamlit']=='1.57.0' and results['runtime']['pyodide']=='0.29.3'
            h.disabled('Back');h.disabled('Forward');h.layout('desktop')
            h.passed('Actual stlite/Streamlit/Pyodide runtime and initial navigation')
            lesson(h)
            assert not results['page_errors'],results['page_errors']
            assert not results['console_errors'],results['console_errors']
            assert not results['external_requests'],results['external_requests']
            assert not any(r.startswith('/_stcore/') for r in requests)
            h.passed('No external requests, server connection or runtime errors')
        except Exception:
            results['checks'].append({'name':'Walkthrough stopped','status':'failed','error':traceback.format_exc()})
            results['body_on_failure']=page.locator('body').inner_text();h.shot('failure')
        browser.close()
    server.shutdown();results['static_requests']=sorted(set(requests))
    (args.results/'browser-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({k:v for k,v in results.items() if k not in ('static_requests','body_on_failure')},indent=2),flush=True)
    return int(any(c['status']=='failed' for c in results['checks']))


if __name__=='__main__':
    raise SystemExit(main())
