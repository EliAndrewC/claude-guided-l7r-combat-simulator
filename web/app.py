import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="L7R Combat Simulator", page_icon="⚔️", layout="wide")

# Initialize session state
if "characters" not in st.session_state:
    st.session_state.characters = {}
if "control_group" not in st.session_state:
    st.session_state.control_group = None
if "test_group" not in st.session_state:
    st.session_state.test_group = None

st.title("L7R Combat Simulator")
st.markdown("""
Welcome to the L7R Tabletop RPG Combat Simulator.

Use the sidebar to navigate between pages:
1. **Characters** - Create, load, and edit characters
2. **Combat Setup** - Assign characters to groups
3. **Run Simulation** - Run batch simulations or single combats
""")

st.sidebar.success("Select a page above.")
