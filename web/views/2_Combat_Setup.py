import streamlit as st

from web.models import GroupConfig
from web.state import save_state

st.title("Combat Setup")

available_names = list(st.session_state.characters.keys())

if not available_names:
    st.warning("No characters available. Go to the Characters page to load or create characters first.")
else:
    # Restore previous selections as defaults
    default_control = [
        n for n in (st.session_state.control_group.character_names if st.session_state.control_group else [])
        if n in available_names
    ]
    default_test = [
        n for n in (st.session_state.test_group.character_names if st.session_state.test_group else [])
        if n in available_names
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Control Group")
        control_names = st.multiselect("Control group characters", available_names, default=default_control, key="control_chars")

    with col2:
        st.subheader("Test Group")
        test_names = st.multiselect("Test group characters", available_names, default=default_test, key="test_chars")

    # Validation and auto-update groups
    overlap = set(control_names) & set(test_names)
    if overlap:
        st.error(f"Characters cannot be in both groups: {', '.join(overlap)}")
        st.session_state.control_group = None
        st.session_state.test_group = None
        save_state()
    elif not control_names or not test_names:
        if not control_names:
            st.info("Select at least one character for the Control group.")
        if not test_names:
            st.info("Select at least one character for the Test group.")
        st.session_state.control_group = None
        st.session_state.test_group = None
        save_state()
    else:
        st.session_state.control_group = GroupConfig(name="control", is_control=True, character_names=control_names)
        st.session_state.test_group = GroupConfig(name="test", is_control=False, character_names=test_names)
        save_state()
        st.success("Groups configured!")

    # Show current configuration
    if st.session_state.control_group and st.session_state.test_group:
        st.divider()
        st.subheader("Current Configuration")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Control:** {', '.join(st.session_state.control_group.character_names)}")
        with c2:
            st.write(f"**Test:** {', '.join(st.session_state.test_group.character_names)}")
