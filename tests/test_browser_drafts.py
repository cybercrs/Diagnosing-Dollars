import unittest
import base64
import json
import zlib
from browser.drafts import restore, save


def token(payload):
    return base64.urlsafe_b64encode(zlib.compress(json.dumps(payload).encode())).decode().rstrip('=')


class BrowserDraftTests(unittest.TestCase):
    def test_future_fields_and_nonfinite_numbers_are_rejected(self):
        state={'stage':1}
        restore(state,token({'ratio_current_ratio':1.81}))
        self.assertEqual(state,{'stage':1})
        state={'stage':3}
        restore(state,token({'ratio_current_ratio':float('inf')}))
        self.assertEqual(state,{'stage':3})
        restore(state,token({'stage':6}))
        self.assertEqual(state,{'stage':3})

    def test_restore_draft_without_submitting_or_saving_written_text(self):
        state={'stage':5,'ratio_current_ratio':1.70,'diagnosis_reflection':'Private written response'}
        query={}
        save(state,query)
        resumed={'stage':5}
        restore(resumed,query['draft'])
        self.assertEqual(resumed['ratio_current_ratio'],1.70)
        self.assertNotIn('diagnosis_reflection',resumed)
        self.assertNotIn('submissions',resumed)
