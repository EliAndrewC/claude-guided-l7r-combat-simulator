"""Shared formatting helper for trace-component breakdowns.

Both ``TextRenderer`` and ``BulletedRenderer`` (and any future renderer
such as ``JsonRenderer``) call :func:`format_breakdown_component` to
render per-source contributions in a multi-source aggregate.  This
single helper is the canonical source of truth for the rendering
decision and prevents cross-renderer drift (spec 008, FR-001/2/3).

The special case the helper handles is the synthetic
``"from dice in excess of 10k10"`` aggregate-reconciliation component
produced by the engine's roll-parameter providers when dice are
"dropped" off the top because the rolled count exceeds the L7R 10k10
cap.  Each dropped die is worth +2 to the kept total (the L7R
kept-to-bonus conversion), so the user-facing rendering shows the
mechanical effect (``"+{2N} from {N} dropped dice in excess of
10k10"``) rather than the raw negative dice-notation delta
(``"-3k3 from dice in excess of 10k10"``) which is confusing.
"""

EXCESS_10K10_SOURCE = "from dice in excess of 10k10"


def format_breakdown_component(rolled: int, kept: int, source: str) -> str:
    """Format a single ``(rolled, kept, source)`` component as a string.

    Special-cases the synthetic ``"from dice in excess of 10k10"``
    source when its delta represents actual overflow (``rolled < 0``
    or ``kept < 0``, meaning dice were dropped off the top): emits
    the narrative form ``"+{2*dropped} from {dropped} dropped die(s)
    in excess of 10k10"`` so the reader sees the L7R rule reflected
    rather than a confusing negative dice-notation delta.

    The dropped count is the magnitude of the negative deltas summed:
    ``max(0, -rolled) + max(0, -kept)``.

    All other cases — including positive non-overflow reconciliation
    deltas that share the same label, and all non-overflow sources —
    use the standard ``"{rolled}k{kept} {source}"`` form.

    Args:
        rolled: The component's contribution to the rolled-dice count.
        kept: The component's contribution to the kept-dice count.
        source: The human-readable source attribution.

    Returns:
        A formatted single-component string ready for inline display.
    """
    if source == EXCESS_10K10_SOURCE and (rolled < 0 or kept < 0):
        dropped = max(0, -rolled) + max(0, -kept)
        bonus = 2 * dropped
        noun = "die" if dropped == 1 else "dice"
        return f"+{bonus} from {dropped} dropped {noun} in excess of 10k10"
    return f"{rolled}k{kept} {source}"
