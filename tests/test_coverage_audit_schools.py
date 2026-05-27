"""Coverage audit tests for simulation/schools/*.py.

Each school has small uncovered lines (typically `ap_base_skill`,
`name`, `school_knacks`, `school_ring`, `extra_rolled`,
`free_raise_skills`) — getters that are only invoked from the engine
during character build but aren't exercised by every school in the
existing tests.  This file calls every accessor on every school once.
"""

import pytest

from simulation.schools.factory import get_school

SCHOOL_NAMES = [
    "Akodo Bushi School",
    "Bayushi Bushi School",
    "Brotherhood of Shinsei Monk School",
    "Courtier School",
    "Daidoji Yojimbo School",
    "Doji Artisan School",
    "Hida Bushi School",
    "Hiruma Scout School",
    "Ide Diplomat School",
    "Ikoma Bard School",
    "Isawa Duelist School",
    "Isawa Ishi School",
    "Kakita Bushi School",
    "Kitsuki Magistrate School",
    "Kuni Witch Hunter School",
    "Matsu Bushi School",
    "Merchant School",
    "Mirumoto Bushi School",
    "Otaku Bushi School",
    "Priest School",
    "Shiba Bushi School",
    "Shinjo Bushi School",
    "Shosuro Actor School",
    "Togashi Ise Zumi School",
    "Yogo Warden School",
]


@pytest.mark.parametrize("name", SCHOOL_NAMES)
class TestSchoolAccessorsCoverage:
    """Exercise every school's accessor methods."""

    def test_school_factory_returns_school(self, name):
        school = get_school(name)
        assert school is not None

    def test_school_name_accessor(self, name):
        school = get_school(name)
        assert isinstance(school.name(), str)
        assert school.name() == name

    def test_school_ring_accessor(self, name):
        school = get_school(name)
        ring = school.school_ring()
        assert isinstance(ring, str)

    def test_school_knacks_accessor(self, name):
        school = get_school(name)
        knacks = school.school_knacks()
        assert isinstance(knacks, list)

    def test_school_extra_rolled_accessor(self, name):
        school = get_school(name)
        rolled = school.extra_rolled()
        assert isinstance(rolled, list)

    def test_school_free_raise_skills_accessor(self, name):
        school = get_school(name)
        skills = school.free_raise_skills()
        assert isinstance(skills, list)

    def test_school_ap_base_skill_accessor(self, name):
        school = get_school(name)
        # May return None or a string
        ap_skill = school.ap_base_skill()
        assert ap_skill is None or isinstance(ap_skill, str)


class TestSchoolFactoryDefensive:
    """Cover defensive branches in get_school."""

    def test_unsupported_school_raises(self):
        with pytest.raises(ValueError):
            get_school("Fake School Name")

    def test_non_string_name_raises(self):
        with pytest.raises(ValueError):
            get_school(123)


class TestMerchantRollProvider:
    """Cover MerchantRollProvider methods (lines 247, 252-253, 256-258,
    265-268, 270-273, 275-278, 281, 284, 287, 290, 293, 296, 299, 302, 305, 313)."""

    def _make_provider(self):
        from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
        from simulation.mechanics.roll_provider import DefaultRollProvider
        from simulation.schools.merchant_school import MerchantRollProvider
        inner = DefaultRollProvider()
        return MerchantRollProvider(inner, reroll_die_provider=DEFAULT_DIE_PROVIDER)

    def test_construct_with_reroll_die_provider(self):
        provider = self._make_provider()
        assert provider._reroll_die_provider is not None

    def test_construct_with_default_die_provider(self):
        from simulation.mechanics.roll_provider import DefaultRollProvider
        from simulation.schools.merchant_school import MerchantRollProvider
        inner = DefaultRollProvider()
        provider = MerchantRollProvider(inner)
        assert provider._reroll_die_provider is not None

    def test_die_provider_delegates(self):
        provider = self._make_provider()
        assert provider.die_provider() is provider._inner.die_provider()

    def test_get_damage_reduction_roll(self):
        provider = self._make_provider()
        # Damage reduction roll: result delegated to inner
        result = provider.get_damage_reduction_roll(2, 1, reduction=5)
        assert isinstance(result, int)

    def test_get_damage_roll(self):
        provider = self._make_provider()
        result = provider.get_damage_roll(3, 2)
        assert isinstance(result, int)

    def test_get_initiative_roll(self):
        """Initiative does NOT trigger reroll (line 267-268)."""
        provider = self._make_provider()
        result = provider.get_initiative_roll(3, 2)
        assert isinstance(result, list)

    def test_get_skill_roll(self):
        provider = self._make_provider()
        result = provider.get_skill_roll("attack", 3, 2)
        assert isinstance(result, int)

    def test_get_wound_check_roll(self):
        provider = self._make_provider()
        result = provider.get_wound_check_roll(3, 2)
        assert isinstance(result, int)

    def test_last_methods_all_delegate(self):
        provider = self._make_provider()
        # Roll once so inner state populates
        provider.get_skill_roll("attack", 3, 2)
        assert provider.last_skill_info() is not None
        provider.get_damage_roll(3, 2)
        assert provider.last_damage_info() is not None
        provider.get_wound_check_roll(3, 2)
        assert provider.last_wound_check_info() is not None
        provider.get_initiative_roll(3, 2)
        assert provider.last_initiative_info() is not None
        # last_*_roll accessors (may return None for never-rolled providers)
        provider.last_damage_roll()
        provider.last_initiative_roll()
        provider.last_skill_roll()
        provider.last_wound_check_roll()

    def test_set_die_provider_delegates(self):
        from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
        provider = self._make_provider()
        provider.set_die_provider(DEFAULT_DIE_PROVIDER)
        assert provider.die_provider() is DEFAULT_DIE_PROVIDER

    def test_maybe_reroll_no_info(self):
        """When info is None, returns original total unchanged (line 312-313)."""
        provider = self._make_provider()
        result = provider._maybe_reroll(20, None, 3, 2, "damage")
        assert result == 20

    def test_maybe_reroll_info_no_dice(self):
        """When info has no dice, returns original total unchanged."""
        provider = self._make_provider()
        result = provider._maybe_reroll(20, {"dice": None}, 3, 2, "damage")
        assert result == 20


class TestShosuroRollProvider:
    """Cover shosuro_actor_school.py methods 82-83, 86-87, 117, 123."""

    def _make_provider(self):
        from simulation.mechanics.roll_provider import DefaultRollProvider
        from simulation.schools.shosuro_actor_school import (
            ShosuroActorRollProvider,
        )
        inner = DefaultRollProvider()
        return ShosuroActorRollProvider(inner)

    def test_die_provider(self):
        provider = self._make_provider()
        provider.die_provider()  # smoke test

    def test_get_damage_reduction_roll(self):
        provider = self._make_provider()
        result = provider.get_damage_reduction_roll(3, 2, reduction=5)
        assert isinstance(result, int)

    def test_get_damage_roll(self):
        provider = self._make_provider()
        result = provider.get_damage_roll(3, 2)
        assert isinstance(result, int)

    def test_get_initiative_roll(self):
        provider = self._make_provider()
        result = provider.get_initiative_roll(3, 2)
        assert isinstance(result, list)

    def test_set_die_provider(self):
        from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
        provider = self._make_provider()
        provider.set_die_provider(DEFAULT_DIE_PROVIDER)

    def test_lowest_three_bonus_none(self):
        """Line 123: _lowest_three_bonus with info=None returns 0."""
        from simulation.schools.shosuro_actor_school import (
            ShosuroActorRollProvider,
        )
        assert ShosuroActorRollProvider._lowest_three_bonus(None) == 0

    def test_lowest_three_bonus_no_dice(self):
        from simulation.schools.shosuro_actor_school import (
            ShosuroActorRollProvider,
        )
        assert ShosuroActorRollProvider._lowest_three_bonus({"dice": None}) == 0


class TestKitsukiSchool:
    """Cover kitsuki_school.py lines 98-100."""

    def test_kitsuki_new_round_listener_unwrapped_path(self):
        """Lines 98-100: When wrapped is None, the listener uses default
        roll_initiative path."""
        from unittest.mock import MagicMock

        from simulation import events
        from simulation.schools.kitsuki_school import (
            KitsukiFifthDanNewRoundListener,
        )
        # wrapped=None triggers the default roll_initiative path
        listener = KitsukiFifthDanNewRoundListener(wrapped_listener=None)
        character = MagicMock()
        character.group.return_value = [character]
        event = events.NewRoundEvent(1)
        context = MagicMock()
        context.characters.return_value = [character]
        result = list(listener.handle(character, event, context))
        character.roll_initiative.assert_called_once()
        assert result == []
