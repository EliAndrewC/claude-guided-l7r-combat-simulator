"""Tests for web.adapters.html_renderer."""

from web.adapters.html_renderer import _classify_line, _md_to_html, render_play_by_play_html

# ── _classify_line tests ──────────────────────────────────────────────


class TestClassifyLine:
    """Tests for the _classify_line helper."""

    def test_empty_line(self):
        assert _classify_line("", {}) == ("spacer", None)

    def test_round_header(self):
        assert _classify_line("═══ Round 1 ═══", {}) == ("header", None)

    def test_separator(self):
        assert _classify_line("  ─────", {}) == ("separator", None)

    def test_status_line(self):
        line = "  Akodo:  Light 5 | Serious 0/2 | Void 2/2 | Actions: 2"
        assert _classify_line(line, {}) == ("status", None)

    def test_initiative_header(self):
        assert _classify_line("🎲 Initiative:", {}) == ("info", None)

    def test_initiative_detail(self):
        line = "  Akodo: 6k3 rolled [**10**, **8**, **5**, ~~3~~, ~~2~~, ~~1~~] → Actions: 2"
        assert _classify_line(line, {}) == ("info", None)

    def test_action_phase_prefix_group0(self):
        group_names = {"Akodo": 0, "Hida": 1}
        line = "Phase 1 | Akodo | ⚔️ attacks Hida (kenjutsu)"
        kind, align = _classify_line(line, group_names)
        assert kind == "action"
        assert align == "left"

    def test_action_no_phase_group1(self):
        group_names = {"Akodo": 0, "Hida": 1}
        line = "Hida | 🛡️ parries Akodo"
        kind, align = _classify_line(line, group_names)
        assert kind == "action"
        assert align == "right"

    def test_action_unknown_actor_defaults_left(self):
        group_names = {"Akodo": 0}
        line = "Unknown | ⚔️ attacks someone"
        kind, align = _classify_line(line, group_names)
        assert kind == "action"
        assert align == "left"


# ── _md_to_html tests ─────────────────────────────────────────────────


class TestMdToHtml:
    """Tests for the _md_to_html helper."""

    def test_bold_converted(self):
        assert _md_to_html("**hello**") == "<b>hello</b>"

    def test_strikethrough_converted(self):
        assert _md_to_html("~~gone~~") == "<s>gone</s>"

    def test_html_escaped(self):
        result = _md_to_html("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_mixed_formatting(self):
        result = _md_to_html("**kept** and ~~dropped~~")
        assert "<b>kept</b>" in result
        assert "<s>dropped</s>" in result


# ── render_play_by_play_html tests ────────────────────────────────────


class TestRenderPlayByPlay:
    """Tests for the main render_play_by_play_html function."""

    def test_status_lines_centered_and_dimmed(self):
        lines = ["  ─────", "  Akodo:  Light 5 | Serious 0/2 | Void 2/2 | Actions: 2", "  ─────"]
        result = render_play_by_play_html(lines, {})
        assert "text-align:center" in result
        assert "opacity:0.5" in result

    def test_action_lines_aligned_by_group(self):
        group_names = {"Akodo": 0, "Hida": 1}
        lines = [
            "Phase 1 | Akodo | ⚔️ attacks Hida (kenjutsu)",
            "Hida | 🛡️ parries Akodo",
        ]
        result = render_play_by_play_html(lines, group_names)
        assert "text-align:left" in result
        assert "text-align:right" in result

    def test_round_header_centered_bold(self):
        lines = ["═══ Round 1 ═══"]
        result = render_play_by_play_html(lines, {})
        assert "text-align:center" in result
        assert "font-weight:bold" in result

    def test_empty_lines_become_br(self):
        lines = [""]
        result = render_play_by_play_html(lines, {})
        assert "<br>" in result

    def test_full_sequence(self):
        """End-to-end test with a realistic multi-line block."""
        group_names = {"Akodo": 0, "Hida": 1}
        lines = [
            "═══ Round 1 ═══",
            "",
            "🎲 Initiative:",
            "  Akodo: 6k3 rolled [**10**, **8**, **5**, ~~3~~, ~~2~~, ~~1~~] → Actions: 2",
            "  Hida: 5k3 rolled [**9**, **7**, **4**, ~~2~~, ~~1~~] → Actions: 1",
            "  ─────",
            "  Akodo:  Light 0 | Serious 0/2 | Void 2/2 | Actions: 2",
            "  Hida:  Light 0 | Serious 0/2 | Void 2/2 | Actions: 1",
            "  ─────",
            "Phase 1 | Akodo | ⚔️ attacks Hida (kenjutsu)",
            "Hida | 🛡️ parries Akodo",
        ]
        result = render_play_by_play_html(lines, group_names)
        # Verify it's valid-looking HTML with multiple divs
        assert result.count("<div") >= len(lines)
        # Header is centered and bold
        assert "font-weight:bold" in result
        # Status lines are dimmed
        assert "opacity:0.5" in result
        # Action lines are aligned
        assert "text-align:left" in result
        assert "text-align:right" in result
        # Bold markdown is converted
        assert "<b>" in result
        # Strikethrough markdown is converted
        assert "<s>" in result
