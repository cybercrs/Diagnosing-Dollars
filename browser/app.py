"""Browser case with native submissions and read-only review."""
import runpy
from pathlib import Path
import sys
# Stlite puts the entrypoint directory first; keep root packages authoritative.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from browser.common import LiveUI, ReviewUI, VIEW_KEY, restore_view, keep_widgets, navigation, save_view, scroll
from browser.navigation import frontier, can_advance
from browser import drafts

app = runpy.run_path(str(Path(__file__).with_name('shared_app.py')))
g = app['advance'].__globals__
app['initialize_state']()
if VIEW_KEY not in st.session_state:
    restore_view(st.session_state, st.query_params.get('view'), frontier(st.session_state))
    drafts.restore(st.session_state, st.query_params.get('draft'))
keep_widgets(st.session_state)


def advance():
    if st.session_state[VIEW_KEY] == frontier(st.session_state) and can_advance(st.session_state):
        app['advance']()
        st.session_state[VIEW_KEY] = frontier(st.session_state)
        st.session_state['_browser_scroll'] = True


def restart():
    if st.session_state[VIEW_KEY] == frontier(st.session_state):
        app['reset_case']()
        st.session_state[VIEW_KEY] = 0
        st.query_params.pop('draft', None)


class UI(LiveUI):
    def button(self, label, **kwargs):
        if kwargs.get('on_click') is restart:
            kwargs['disabled'] = st.session_state[VIEW_KEY] < frontier(st.session_state)
        return super().button(label, **kwargs)

g.update(st=UI(), advance=advance, reset_case=restart)
app['render_header']()
reached = frontier(st.session_state)
app['render_sidebar']()
navigation(st.session_state, reached, len(app['STAGES']))
view = st.session_state[VIEW_KEY]
if view < reached:
    ui = ReviewUI(st.session_state)
    ui.session_state.stage = view
    g['st'] = ui
app['render_progress']()
renderers = ('render_intake','render_classification','render_liquidity','render_ratio_lab','render_analysis','render_diagnosis','render_debrief')
app[renderers[view]]()
g['st'] = st
app['persist_progress']()
drafts.save(st.session_state, st.query_params)
save_view(st.session_state)
scroll()
