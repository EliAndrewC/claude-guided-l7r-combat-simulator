"""Post-processor that converts plain-text play-by-play lines to styled HTML.

The formatter (DetailedEventFormatter) stays unchanged — it returns plain
strings.  This module classifies each line and wraps it in a styled ``<div>``
so that status/separator lines are centered and dimmed, action lines are
left/right-aligned by group, and informational lines are centered.
"""

from __future__ import annotations

import html
import re

# Pre-compiled patterns for markdown conversion
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_STRIKE_RE = re.compile(r"~~(.+?)~~")


def _md_to_html(text: str) -> str:
    """Convert a plain-text line with markdown bold/strikethrough to HTML.

    HTML-escapes the text first, then applies conversions.
    """
    text = html.escape(text)
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _STRIKE_RE.sub(r"<s>\1</s>", text)
    return text


def _classify_line(
    line: str,
    group_names: dict[str, int],
) -> tuple[str, str | None]:
    """Classify a play-by-play line for styling purposes.

    Returns ``(kind, alignment)`` where *kind* is one of
    ``"spacer"``, ``"header"``, ``"separator"``, ``"status"``, ``"info"``,
    ``"action"`` and *alignment* is ``"left"``/``"right"`` (only for actions).
    """
    if not line:
        return ("spacer", None)

    if line.startswith("═══"):
        return ("header", None)

    if line.startswith("  "):
        if "─────" in line:
            return ("separator", None)
        if "Light" in line and "Serious" in line:
            return ("status", None)
        return ("info", None)

    if line.startswith("🎲"):
        return ("info", None)

    # Action line — extract actor name and look up group
    # Format: "Phase N | CharName | ..." or "CharName | ..."
    parts = line.split(" | ", 2)
    if len(parts) >= 3 and parts[0].startswith("Phase"):
        actor = parts[1]
    else:
        actor = parts[0]

    group = group_names.get(actor, 0)
    alignment = "left" if group == 0 else "right"
    return ("action", alignment)


def render_play_by_play_html(
    lines: list[str],
    group_names: dict[str, int],
) -> str:
    """Convert plain-text play-by-play lines to a styled HTML string.

    Parameters
    ----------
    lines:
        The list of plain-text lines from ``DetailedEventFormatter.format_history``.
    group_names:
        Mapping of character name → group index (0=control/left, 1=test/right).

    Returns
    -------
    str
        An HTML fragment suitable for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    parts: list[str] = []
    for line in lines:
        kind, alignment = _classify_line(line, group_names)

        if kind == "spacer":
            parts.append("<div><br></div>")
        elif kind == "header":
            parts.append(
                f'<div style="text-align:center; font-weight:bold;">'
                f"{_md_to_html(line)}</div>"
            )
        elif kind in ("separator", "status"):
            parts.append(
                f'<div style="text-align:center; opacity:0.5;">'
                f"{_md_to_html(line)}</div>"
            )
        elif kind == "info":
            parts.append(
                f'<div style="text-align:center;">{_md_to_html(line)}</div>'
            )
        elif kind == "action":
            align = alignment or "left"
            parts.append(
                f'<div style="text-align:{align};">{_md_to_html(line)}</div>'
            )

    return "\n".join(parts)
