"""Per-session state management for the Streamlit web interface.

Each browser session gets a unique UUID stored in st.query_params["session_id"].
Groups are persisted to per-session JSON files under web/.sessions/ so they
survive server restarts without cross-session contamination.
"""

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from web.models import GroupConfig

_SESSIONS_DIR = Path(__file__).resolve().parent / ".sessions"
_STALE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def _get_session_id() -> str:
    """Return the current session's UUID, creating one if needed."""
    params = st.query_params
    sid = params.get("session_id")
    if not sid:
        sid = uuid.uuid4().hex
        params["session_id"] = sid
    return sid


def _session_file(session_id: str | None = None) -> Path:
    """Return the disk path for a session's state file."""
    if session_id is None:
        session_id = _get_session_id()
    return _SESSIONS_DIR / f"{session_id}.json"


def _cleanup_stale_sessions() -> None:
    """Delete session files older than 7 days."""
    if not _SESSIONS_DIR.exists():
        return
    cutoff = time.time() - _STALE_SECONDS
    for path in _SESSIONS_DIR.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def _validate_groups(characters: dict) -> None:
    """Clear groups that reference characters which no longer exist."""
    for key in ("control_group", "test_group"):
        group = st.session_state.get(key)
        if group is None:
            continue
        if not all(name in characters for name in group.character_names):
            st.session_state[key] = None


def save_state() -> None:
    """Persist groups from session_state to the per-session disk file."""
    data: dict = {}
    for key in ("control_group", "test_group"):
        group = st.session_state.get(key)
        if isinstance(group, GroupConfig):
            data[key] = asdict(group)
        else:
            data[key] = None
    _SESSIONS_DIR.mkdir(exist_ok=True)
    try:
        _session_file().write_text(json.dumps(data))
    except OSError:
        pass


def restore_state() -> None:
    """Load groups from per-session disk file into session_state (only if keys missing)."""
    _cleanup_stale_sessions()
    needs_control = "control_group" not in st.session_state
    needs_test = "test_group" not in st.session_state
    if not needs_control and not needs_test:
        return
    path = _session_file()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    for key in ("control_group", "test_group"):
        if key not in st.session_state:
            val = data.get(key)
            if val is not None:
                st.session_state[key] = GroupConfig(**val)
            else:
                st.session_state[key] = None


def clear_state() -> None:
    """Remove session keys from session_state and delete the session file."""
    for key in ("characters", "control_group", "test_group"):
        if key in st.session_state:
            del st.session_state[key]
    try:
        _session_file().unlink(missing_ok=True)
    except OSError:
        pass
