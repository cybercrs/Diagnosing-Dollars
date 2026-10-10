"""Bounded, typed, non-identifying browser drafts for the existing case."""
import base64
import json
import math
import zlib
from diagnosing_dollars.case_data import ACCOUNTS, CATEGORIES, CONTEXT_QUESTIONS, LIQUIDITY_ORDER, ANALYSIS_QUESTIONS, COMPARISON_QUESTIONS, COMPARISON_OPTIONS, DIAGNOSIS_QUESTIONS, EVIDENCE_OPTIONS


def schema(stage):
    fields = {}
    if stage >= 1:
        fields.update({f'class_{i}': ('choice', ('Select a section',) + CATEGORIES) for i in range(len(ACCOUNTS))})
    if stage >= 2:
        fields['liquidity_order'] = ('many', LIQUIDITY_ORDER)
        fields.update({f'context_{q["id"]}': ('choice', ('Select an answer',) + q['options']) for q in CONTEXT_QUESTIONS})
    if stage >= 3:
        fields.update({f'ratio_{key}': ('number', ()) for key in ('working_capital','current_ratio','debt_to_assets','debt_to_equity')})
    if stage >= 4:
        fields.update({f'analysis_{q["id"]}': ('choice', q['options']) for q in ANALYSIS_QUESTIONS})
        fields.update({f'comparison_{q["id"]}': ('choice', ('Select a comparison',) + COMPARISON_OPTIONS) for q in COMPARISON_QUESTIONS})
    if stage >= 5:
        fields.update({f'diagnosis_{q["id"]}': ('choice', q['options']) for q in DIAGNOSIS_QUESTIONS})
        fields['diagnosis_evidence'] = ('many', EVIDENCE_OPTIONS)
    # Written rationale deliberately remains session-only, like the server app.
    return fields


def valid(value, rule):
    kind, options = rule
    if value is None:
        return True
    if kind == 'choice':
        return isinstance(value, str) and value in options
    if kind == 'many':
        return isinstance(value, list) and len(value) <= len(options) and len(set(value)) == len(value) and all(isinstance(v, str) and v in options for v in value)
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1e12


def restore(state, token):
    if not isinstance(token, str) or len(token) > 16000:
        return
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True), 32001)
        if len(raw) > 32000 or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
            return
        payload = json.loads(raw)
        fields = schema(state['stage'])
        if not isinstance(payload, dict) or set(payload) - set(fields):
            return
        if not all(valid(value, fields[key]) for key, value in payload.items()):
            return
        for key, value in payload.items():
            state[key] = value
        # Mark restored fields as session-owned on later review runs. This also
        # sends their saved value to a newly mounted stlite widget on Forward.
        state['_browser_widgets'] = sorted(set(state.get('_browser_widgets', [])) | set(payload))
    except (ValueError, TypeError, zlib.error):
        return


def save(state, query):
    payload = {key: state[key] for key, rule in schema(state['stage']).items() if key in state and valid(state[key], rule)}
    token = base64.urlsafe_b64encode(zlib.compress(json.dumps(payload, separators=(',', ':')).encode())).decode().rstrip('=')
    if query.get('draft') != token:
        query['draft'] = token
