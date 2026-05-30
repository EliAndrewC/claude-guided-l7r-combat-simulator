import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from web.adapters.character_adapter import load_data_directory
from web.state import _validate_groups, clear_state, restore_state, save_state, set_session_cookie

st.set_page_config(page_title="L7R Combat Simulator", page_icon="⚔️", layout="wide")

# Full-width CSS so content expands when sidebar is collapsed,
# AND make tertiary-button text user-selectable. The combat trace
# renders each roll as a ``st.button(type="tertiary")`` so it can
# pop a modal showing the per-source breakdown on click — but
# Streamlit's default button CSS blocks text selection, which
# means readers can't copy-paste the trace into Discord / chat
# / notes. Overriding ``user-select`` here keeps the click-to-modal
# affordance while letting click+drag select text normally.
_CUSTOM_CSS = """
<style>
.stMainBlockContainer { max-width: 100%; }
/* Make tertiary-button labels selectable for copy/paste. */
button[kind="tertiary"], button[kind="tertiary"] * {
    user-select: text !important;
    -webkit-user-select: text !important;
    cursor: text;
}
</style>
"""
st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# Restore persisted state before setting defaults
restore_state()

# Initialize session state defaults (only sets if not already present)
if "characters" not in st.session_state:
    st.session_state.characters = {}
if "control_group" not in st.session_state:
    st.session_state.control_group = None
if "test_group" not in st.session_state:
    st.session_state.test_group = None

# Auto-load characters from data directory on startup
if not st.session_state.characters:
    data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
    try:
        configs = load_data_directory(data_dir)
        for config in configs:
            st.session_state.characters[config.name] = config
        save_state()
    except Exception:
        pass

# Validate groups against loaded characters (handles deleted characters)
_validate_groups(st.session_state.characters)

# Persist session cookie so the browser can identify this session on refresh
set_session_cookie()

# Sidebar clear button
with st.sidebar:
    if st.button("Clear All Data"):
        clear_state()
        st.rerun()

# Navigation — Combat Setup is the default landing page
pages = [
    st.Page("views/2_Combat_Setup.py", title="Combat Setup", default=True),
    st.Page("views/3_Run_Simulation.py", title="Run Simulation"),
    st.Page("views/1_Characters.py", title="Characters"),
    st.Page("views/4_Analysis.py", title="Analysis"),
]
nav = st.navigation(pages)
nav.run()
