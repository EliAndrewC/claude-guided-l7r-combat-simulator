"""Tests for the Kakita interrupt analysis definition."""

from web.adapters.character_adapter import config_to_character
from web.analysis.definitions.kakita_interrupt import build_kakita_interrupt_analysis


class TestKakitaInterruptDefinition:
    def test_correct_matchup_count(self):
        """Should generate 168 matchups:
        7 XP tiers x 4 opponents x 3 XP deltas x 2 strategies = 168
        (minus any impossible combinations where opponent XP < 150 or > 450)
        """
        definition = build_kakita_interrupt_analysis(num_trials=10)
        # 7 tiers, 4 opponents, 3 deltas = 84 pairs x 2 strategies = 168
        # But at 150 XP, delta=-50 gives 100 which is below min (150), so 4 invalid
        # At 450 XP, delta=+50 gives 500 which is above max (450), so 4 invalid
        # So: 168 - (4+4)*2 = 168 - 16 = 152
        # Actually: total valid combos per strategy:
        # tier 150: deltas 0,+50 = 2 valid x 4 opponents = 8
        # tier 200-400: deltas -50,0,+50 = 3 valid x 4 opponents = 12 each -> 5 * 12 = 60
        # tier 450: deltas -50,0 = 2 valid x 4 opponents = 8
        # Total per strategy: 8 + 60 + 8 = 76
        # Two strategies: 76 * 2 = 152
        assert len(definition.matchups) == 152

    def test_unique_ids(self):
        """All matchup IDs should be unique."""
        definition = build_kakita_interrupt_analysis(num_trials=10)
        ids = [m.matchup_id for m in definition.matchups]
        assert len(ids) == len(set(ids))

    def test_all_configs_buildable(self):
        """All character configs in matchups should be buildable."""
        definition = build_kakita_interrupt_analysis(num_trials=10)
        # Test a sample of matchups (not all, for speed)
        for matchup in definition.matchups[:10]:
            for config in matchup.control_characters + matchup.test_characters:
                character = config_to_character(config)
                assert character.is_alive()
                assert character.name() == config.name

    def test_analysis_metadata(self):
        """Analysis definition should have correct metadata."""
        definition = build_kakita_interrupt_analysis(num_trials=100)
        assert definition.analysis_id == "kakita_interrupt"
        assert "Kakita" in definition.title
        assert "interrupt" in definition.question.lower()
        assert definition.description != ""

    def test_matchup_tags(self):
        """Each matchup should have meaningful tags."""
        definition = build_kakita_interrupt_analysis(num_trials=10)
        for matchup in definition.matchups:
            assert "kakita_xp" in matchup.tags
            assert "opponent" in matchup.tags
            assert "strategy" in matchup.tags
            assert matchup.tags["strategy"] in ("no_interrupt", "interrupt")

    def test_matchup_groups_configured(self):
        """Each matchup should have properly configured groups."""
        definition = build_kakita_interrupt_analysis(num_trials=10)
        for matchup in definition.matchups:
            assert matchup.control_group.is_control is True
            assert matchup.test_group.is_control is False
            assert len(matchup.control_group.character_names) == 1
            assert len(matchup.test_group.character_names) == 1

    def test_group_names_use_school_names(self):
        """Group names should use school names, not 'Control'/'Test'."""
        definition = build_kakita_interrupt_analysis(num_trials=10)
        for matchup in definition.matchups:
            assert matchup.control_group.name == "Kakita"
            assert matchup.test_group.name in (
                "Akodo", "Bayushi", "Shiba", "Wave Man",
            )
            assert matchup.control_group.name != "Control"
            assert matchup.test_group.name != "Test"
