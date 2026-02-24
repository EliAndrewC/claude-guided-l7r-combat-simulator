import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from web.adapters.character_adapter import load_data_directory
from web.state import _validate_groups, clear_state, restore_state, save_state

st.set_page_config(page_title="L7R Combat Simulator", page_icon="⚔️", layout="wide")

# Full-width CSS so content expands when sidebar is collapsed
_FULL_WIDTH_CSS = """
<style>
.stMainBlockContainer { max-width: 100%; }
</style>
"""
st.markdown(_FULL_WIDTH_CSS, unsafe_allow_html=True)

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
