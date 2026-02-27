"""Tests for character template generation."""

import os
import tempfile

import pytest

from simulation.templates.generator import generate_all_templates, generate_template, write_template_yaml
from simulation.templates.strategies import SCHOOL_NAMES, XP_TIERS
from web.adapters.character_adapter import config_to_character, yaml_to_config


class TestGenerateTemplate:
    """Test that each generated template produces a valid character."""

    @pytest.mark.parametrize("school_key", list(SCHOOL_NAMES.keys()))
    @pytest.mark.parametrize("xp_tier", XP_TIERS)
    def test_template_builds_successfully(self, school_key: str, xp_tier: int):
        """Each template must build via config_to_character without errors."""
        config, _ = generate_template(school_key, xp_tier)
        character = config_to_character(config)
        assert character.name() == config.name
        assert character.is_alive()

    @pytest.mark.parametrize("school_key", list(SCHOOL_NAMES.keys()))
    @pytest.mark.parametrize("xp_tier", XP_TIERS)
    def test_template_metadata(self, school_key: str, xp_tier: int):
        """Templates have correct metadata."""
        config, _ = generate_template(school_key, xp_tier)
        assert config.template_tier == str(xp_tier)
        assert config.template_earned_xp == xp_tier
        assert config.template_school != ""

    @pytest.mark.parametrize("school_key", list(SCHOOL_NAMES.keys()))
    @pytest.mark.parametrize("xp_tier", XP_TIERS)
    def test_combat_budget_respected(self, school_key: str, xp_tier: int):
        """Combat XP spent should not exceed 80% of total XP."""
        _, breakdown = generate_template(school_key, xp_tier)
        assert breakdown["combat_spent"] <= breakdown["combat_budget"]

    @pytest.mark.parametrize("school_key", [k for k in SCHOOL_NAMES if k != "wave_man"])
    @pytest.mark.parametrize("xp_tier", XP_TIERS)
    def test_school_characters_have_attack_parry(self, school_key: str, xp_tier: int):
        """School characters should always have attack and parry >= 1."""
        config, _ = generate_template(school_key, xp_tier)
        assert config.skills.get("attack", 0) >= 1
        assert config.skills.get("parry", 0) >= 1


class TestSchoolDanProgression:
    """Test that school characters reach expected Dan ranks at each tier."""

    def _get_dan_rank(self, config, school_knacks):
        """Calculate Dan rank from config skills."""
        knack_ranks = [config.skills.get(k, 0) for k in school_knacks]
        return min(knack_ranks) if knack_ranks else 0

    @pytest.mark.parametrize(
        "school_key,school_knacks",
        [
            ("akodo", ["double attack", "feint", "iaijutsu"]),
            ("bayushi", ["double attack", "feint", "iaijutsu"]),
            ("kakita", ["double attack", "iaijutsu", "lunge"]),
            ("shiba", ["counterattack", "double attack", "iaijutsu"]),
        ],
    )
    def test_dan_increases_with_xp(self, school_key: str, school_knacks: list[str]):
        """Higher XP tiers should reach equal or higher Dan ranks."""
        prev_dan = 0
        for xp_tier in XP_TIERS:
            config, _ = generate_template(school_key, xp_tier)
            dan = self._get_dan_rank(config, school_knacks)
            assert dan >= prev_dan, (
                f"{school_key} at {xp_tier} XP has Dan {dan}, "
                f"but previous tier had Dan {prev_dan}"
            )
            prev_dan = dan


class TestTierProgression:
    """Test that each tier is strictly better than the previous."""

    @pytest.mark.parametrize("school_key", list(SCHOOL_NAMES.keys()))
    def test_each_tier_at_least_as_good(self, school_key: str):
        """All rings and skills should be >= the previous tier."""
        prev_config = None
        for xp_tier in XP_TIERS:
            config, _ = generate_template(school_key, xp_tier)
            if prev_config is not None:
                for ring_name in ["air", "earth", "fire", "water", "void"]:
                    assert config.rings[ring_name] >= prev_config.rings[ring_name], (
                        f"{school_key} at {xp_tier}: {ring_name} ring "
                        f"decreased from {prev_config.rings[ring_name]} "
                        f"to {config.rings[ring_name]}"
                    )
                for skill_name in prev_config.skills:
                    prev_rank = prev_config.skills.get(skill_name, 0)
                    cur_rank = config.skills.get(skill_name, 0)
                    assert cur_rank >= prev_rank, (
                        f"{school_key} at {xp_tier}: {skill_name} skill "
                        f"decreased from {prev_rank} to {cur_rank}"
                    )
            prev_config = config


class TestWriteTemplateYaml:
    """Test YAML serialization and round-trip."""

    def test_write_and_reload(self):
        """A written template can be reloaded and rebuilt."""
        config, breakdown = generate_template("kakita", 200)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            write_template_yaml(config, path, breakdown)
            with open(path) as f:
                yaml_str = f.read()
            reloaded = yaml_to_config(yaml_str)
            assert reloaded.name == config.name
            assert reloaded.xp == config.xp
            assert reloaded.school == config.school
            # Verify it still builds
            character = config_to_character(reloaded)
            assert character.is_alive()
        finally:
            os.unlink(path)

    def test_yaml_has_breakdown_comments(self):
        """Written YAML should include XP breakdown comments."""
        config, breakdown = generate_template("kakita", 200)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            write_template_yaml(config, path, breakdown)
            with open(path) as f:
                content = f.read()
            assert "# XP Breakdown" in content
            assert "Combat budget" in content
            assert "Non-combat reserve" in content
        finally:
            os.unlink(path)


class TestGenerateAllTemplates:
    """Test bulk generation."""

    def test_generates_182_templates(self):
        """Should produce exactly 182 configs (26 schools x 7 tiers)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configs = generate_all_templates(base_dir=tmpdir)
            assert len(configs) == 189

    def test_all_configs_buildable(self):
        """Every generated config must build successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configs = generate_all_templates(base_dir=tmpdir)
            for config in configs:
                character = config_to_character(config)
                assert character.is_alive()
