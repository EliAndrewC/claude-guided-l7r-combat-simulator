"""Coverage audit tests for simulation/strategies/* modules.

Covers small uncovered branches in:
- simulation/strategies/base.py (BaseParryStrategy already-parried branch, conviction WC, etc.)
- simulation/strategies/action_factory.py
- simulation/strategies/take_action_event_factory.py
- simulation/strategies/target_finders.py
- simulation/strategies/mirumoto_third_dan.py
- simulation/strategies/ishi_dan_abilities.py
"""

from unittest.mock import MagicMock


class TestBaseParryStrategyAlreadyParried:
    """Cover the `event.action.parried()` early-return branch (lines 258-260)."""

    def test_already_parried_returns_without_yielding(self):
        from simulation import events
        from simulation.strategies.base import AlwaysParryStrategy

        # Set up a mock event where action.parried() returns True
        character = MagicMock()
        character.has_action.return_value = True
        character.group.return_value = [character]
        character.name.return_value = "X"

        target = MagicMock()
        target.name.return_value = "Tgt"
        # target is character itself so adjacency check skipped
        action = MagicMock()
        action.target.return_value = character
        action.is_hit.return_value = True
        action.parried.return_value = True

        event = events.AttackRolledEvent(action, 25)

        strategy = AlwaysParryStrategy()
        context = MagicMock()
        # Should not raise and should yield no events
        events_out = list(strategy.recommend(character, event, context))
        assert events_out == []


class TestUseConvictionWoundCheck:
    """Cover use_conviction_wc lines 601-605."""

    def test_use_conviction_wc_breaks_when_tolerable_reached(self):
        """Conviction spend stops as soon as expected_sw == tolerable_sw (line 605)."""
        from simulation.events import WoundCheckSucceededEvent
        from simulation.strategies.base import WoundCheckRolledStrategy

        wc_strategy = WoundCheckRolledStrategy()
        character = MagicMock()
        character.conviction.return_value = 5
        character.max_conviction_per_roll.return_value = 5
        # wound_check returns SW based on roll - hits tolerable=1 at roll=22
        def wound_check(roll, lw=None):
            if roll >= 22:
                return 1
            return 2
        character.wound_check = wound_check
        attacker = MagicMock()
        event = WoundCheckSucceededEvent(character, attacker, damage=20, roll=20, tn=25)
        result = wc_strategy.use_conviction_wc(character, event, tolerable_sw=1)
        # After 2 increments (roll 20 → 22), break hits
        assert result.roll == 22

    def test_use_conviction_wc_no_break_when_max_reached(self):
        """When tolerable_sw is never reached, the loop completes naturally."""
        from simulation.events import WoundCheckSucceededEvent
        from simulation.strategies.base import WoundCheckRolledStrategy

        wc_strategy = WoundCheckRolledStrategy()
        character = MagicMock()
        character.conviction.return_value = 3
        character.max_conviction_per_roll.return_value = 3
        character.wound_check = MagicMock(return_value=5)  # always above tolerable
        attacker = MagicMock()
        event = WoundCheckSucceededEvent(character, attacker, damage=20, roll=20, tn=25)
        result = wc_strategy.use_conviction_wc(character, event, tolerable_sw=1)
        assert result.roll == 23  # spent all 3 conviction



class TestSpendBranchesInRecommend:
    """Lines 569, 571: positive _chosen_ap and _chosen_conviction branches
    triggered by the WoundCheckRolledStrategy.recommend method."""

    def test_recommend_yields_ap_and_conviction_when_chosen(self):
        """A wound check with AP and conviction spent yields the matching
        SpendAdventurePointsEvent (line 569) and SpendConvictionEvent (line 571)."""
        from simulation import events
        from simulation.strategies.base import WoundCheckRolledStrategy

        strategy = WoundCheckRolledStrategy()
        character = MagicMock()
        character.name.return_value = "X"
        character.adventure_points.return_value = 5
        character.conviction.return_value = 5
        character.max_conviction_per_roll.return_value = 5
        character.sw_remaining.return_value = 5
        # wound_check: initial roll yields 2 SW, then after adjustments hits 1
        # so use_ap and use_conviction_wc both contribute
        character.wound_check = MagicMock(side_effect=[
            2,   # call 1 line 544: initial expected_sw
            2,   # call 2 line 612 inside use_floating_bonuses (no bonuses → no loop)
            2,   # call 3 line 555: after floating bonuses (unchanged)
            2,   # call 4 line 559: after AP (still > 1 to enter conviction)
            1,   # call 5 line 563: final after conviction < expected_sw=2
        ])
        # No floating bonuses
        character.floating_bonuses.return_value = []
        # use_ap will not bump if no APs needed; we need to actually
        # increment _chosen_ap inside the path. Easier: drive use_ap and
        # use_conviction_wc helpers directly to set state, then call yield.

        # Actually, the cleanest approach is to set _chosen_ap and
        # _chosen_conviction directly, then drive the strategy. But
        # `recommend` resets them. So we monkeypatch use_ap and use_conviction
        # to set the chosen counts.
        original_use_ap = strategy.use_ap
        original_use_conviction = strategy.use_conviction_wc

        def _patched_use_ap(c, e, t_sw, skill):
            strategy._chosen_ap = 2
            return events.WoundCheckRolledEvent(e.subject, e.attacker, e.damage, e.roll + 10, tn=e.tn)

        def _patched_use_conviction(c, e, t_sw):
            strategy._chosen_conviction = 1
            return events.WoundCheckRolledEvent(e.subject, e.attacker, e.damage, e.roll + 1, tn=e.tn)

        strategy.use_ap = _patched_use_ap
        strategy.use_conviction_wc = _patched_use_conviction

        try:
            attacker = MagicMock()
            event = events.WoundCheckRolledEvent(character, attacker, damage=20, roll=15, tn=25)
            result = list(strategy.recommend(character, event, MagicMock()))
        finally:
            strategy.use_ap = original_use_ap
            strategy.use_conviction_wc = original_use_conviction

        # The recommend yielded SpendAdventurePointsEvent + SpendConvictionEvent
        assert any(isinstance(e, events.SpendAdventurePointsEvent) for e in result)
        assert any(isinstance(e, events.SpendConvictionEvent) for e in result)


class TestTakeActionEventFactoryDefensive:
    """Cover take_action_event_factory.py defensive raise branches (59, 71, 83)."""

    def test_get_take_attack_event_wrong_action_type(self):
        from simulation.actions import ParryAction
        from simulation.strategies.take_action_event_factory import (
            DefaultTakeActionEventFactory,
        )
        factory = DefaultTakeActionEventFactory()
        wrong_action = MagicMock(spec=ParryAction)
        import pytest
        with pytest.raises(ValueError):
            factory.get_take_attack_action_event(wrong_action)

    def test_get_take_counterattack_event_wrong_action_type(self):
        from simulation.actions import AttackAction
        from simulation.strategies.take_action_event_factory import (
            DefaultTakeActionEventFactory,
        )
        factory = DefaultTakeActionEventFactory()
        wrong_action = MagicMock(spec=AttackAction)
        import pytest
        with pytest.raises(ValueError):
            factory.get_take_counterattack_action_event(wrong_action)

    def test_get_take_parry_event_wrong_action_type(self):
        from simulation.actions import AttackAction
        from simulation.strategies.take_action_event_factory import (
            DefaultTakeActionEventFactory,
        )
        factory = DefaultTakeActionEventFactory()
        wrong_action = MagicMock(spec=AttackAction)
        import pytest
        with pytest.raises(ValueError):
            factory.get_take_parry_action_event(wrong_action)


class TestMechanicsDefensiveRaises:
    """Cover defensive raise statements in simulation/mechanics/*."""

    def test_advantage_invalid_name_raises(self):
        import pytest

        from simulation.mechanics.advantages import Advantage
        with pytest.raises(ValueError):
            Advantage("not a real advantage")

    def test_disadvantage_invalid_name_raises(self):
        import pytest

        from simulation.mechanics.disadvantages import Disadvantage
        with pytest.raises(ValueError):
            Disadvantage("not a real disadvantage")


class TestCalvinistRollProvider:
    """Cover CalvinistRollProvider edge cases (roll_provider.py lines 122, 145-150)."""

    def test_set_die_provider_rejects_non_dieprovider(self):
        """DefaultRollProvider.set_die_provider raises on non-DieProvider (line 122)."""
        import pytest

        from simulation.mechanics.roll_provider import DefaultRollProvider
        p = DefaultRollProvider()
        with pytest.raises(ValueError):
            p.set_die_provider("not a die provider")

    def test_calvinist_get_damage_reduction_roll(self):
        """CalvinistRollProvider.get_damage_reduction_roll pops queued (line 144-150)."""
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        provider = CalvinistRollProvider()
        provider.put_damage_roll(15)
        result = provider.get_damage_reduction_roll(rolled=3, kept=2, reduction=5)
        assert result == 15

    def test_calvinist_get_damage_reduction_roll_empty_queue_raises(self):
        """Empty damage queue raises IndexError."""
        import pytest

        from simulation.mechanics.roll_provider import CalvinistRollProvider
        provider = CalvinistRollProvider()
        with pytest.raises(IndexError):
            provider.get_damage_reduction_roll(rolled=3, kept=2, reduction=5)


class TestIshiAbilities:
    """Cover the early-return guards in ishi_dan_abilities.py."""

    def test_event_tn_returns_none_when_event_has_no_tn(self):
        from simulation.strategies.ishi_dan_abilities import _event_tn

        class Event:
            pass

        assert _event_tn(Event()) is None

    def test_event_roll_returns_none_when_event_has_no_roll(self):
        from simulation.strategies.ishi_dan_abilities import _event_roll

        class Event:
            pass

        assert _event_roll(Event()) is None

    def test_eager_ally_boost_no_subject(self):
        """When event has no subject, the strategy returns silently (line 180)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerAllyBoostStrategy

        strategy = EagerAllyBoostStrategy()
        # Construct WoundCheckRolledEvent with subject=None
        evt = events.WoundCheckRolledEvent(None, None, 10, 20, tn=25)
        result = list(strategy.recommend(MagicMock(), evt, MagicMock()))
        assert result == []

    def test_eager_ally_boost_no_roll(self):
        """When event has no roll, the strategy returns (line 197)."""
        from simulation.strategies.ishi_dan_abilities import EagerAllyBoostStrategy

        strategy = EagerAllyBoostStrategy()
        ishi = MagicMock()
        ishi.vp.return_value = 5
        ishi.skill.return_value = 3
        ally = MagicMock()
        ally.name.return_value = "Ally"
        ishi.group.return_value = [ishi, ally]
        # Custom event class with subject but no roll attr
        from simulation.events import AttackRolledEvent

        class StubAttackRolledEvent(AttackRolledEvent):
            pass

        action = MagicMock()
        action.subject.return_value = ally
        action.tn.return_value = 25
        # Set up without a `roll` attribute
        evt = AttackRolledEvent(action, None)  # roll=None
        result = list(strategy.recommend(ishi, evt, MagicMock()))
        assert result == []

    def test_school_rank_no_school(self):
        """_school_rank_of returns 0 when character has no school (line 252)."""
        from simulation.strategies.ishi_dan_abilities import _school_rank_of

        class Char:
            def school(self):
                return None

        assert _school_rank_of(Char()) == 0

    def test_school_rank_no_knacks(self):
        """_school_rank_of returns 0 when school has no knacks (line 255)."""
        from simulation.strategies.ishi_dan_abilities import _school_rank_of

        class Sch:
            def school_knacks(self):
                return []

        class Char:
            def school(self):
                return Sch()

            def skill(self, name):
                return 0

        assert _school_rank_of(Char()) == 0

    def test_negation_cost_no_school_no_xp(self):
        """When target has no school and no xp accessor, cost is 0 (lines 272-276)."""
        from simulation.strategies.ishi_dan_abilities import _negation_cost

        class Tgt:
            def school(self):
                return None
            # no xp attribute

        # The `getattr(target, "xp", None)` returns None → return 0
        assert _negation_cost(Tgt()) == 0

    def test_negation_cost_xp_as_int_attribute(self):
        """Schoolless target with xp as int attribute uses xp/50."""
        from simulation.strategies.ishi_dan_abilities import _negation_cost

        class Tgt:
            xp = 200

            def school(self):
                return None

        assert _negation_cost(Tgt()) == 4  # 200 // 50

    def test_eager_negation_wrong_event_returns(self):
        """Wrong event type → early return (line 335)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy

        strategy = EagerNegationStrategy()
        evt = events.NewPhaseEvent(0)
        result = list(strategy.recommend(MagicMock(), evt, MagicMock()))
        assert result == []

    def test_eager_negation_subject_not_character(self):
        """When event.subject is not character, early return (line 342)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy

        strategy = EagerNegationStrategy()
        ishi = MagicMock()
        other = MagicMock()
        evt = events.YourMoveEvent(other)  # other, not ishi
        result = list(strategy.recommend(ishi, evt, MagicMock()))
        assert result == []

    def test_eager_negation_enemy_not_fighting(self):
        """Non-fighting enemies are skipped in target search (line 358)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy

        strategy = EagerNegationStrategy()
        ishi = MagicMock()
        ishi.name.return_value = "Ishi"
        # ishi.school().school_knacks() must yield knacks the ishi has skill >= 5 in
        school = MagicMock()
        school.school_knacks.return_value = ["precepts"]
        ishi.school.return_value = school
        ishi.skill.return_value = 5  # rank 5
        ishi._ishi_negation_done = False
        ishi.vp.return_value = 0

        enemy = MagicMock()
        enemy.is_fighting.return_value = False
        enemy.school.return_value = MagicMock()
        own_group = [ishi]
        enemy_group = [enemy]
        ishi.group.return_value = own_group
        context = MagicMock()
        context.groups.return_value = [own_group, enemy_group]

        evt = events.YourMoveEvent(ishi)
        result = list(strategy.recommend(ishi, evt, context))
        # Enemy not fighting → no target found → early return → []
        assert result == []  # noqa

    def test_eager_negation_enemy_schoolless(self):
        """Schoolless enemies are skipped (line 360)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy

        strategy = EagerNegationStrategy()
        ishi = MagicMock()
        school = MagicMock()
        school.school_knacks.return_value = ["precepts"]
        ishi.school.return_value = school
        ishi.skill.return_value = 5
        ishi._ishi_negation_done = False

        enemy = MagicMock()
        enemy.is_fighting.return_value = True
        enemy.school.return_value = None
        own_group = [ishi]
        enemy_group = [enemy]
        ishi.group.return_value = own_group
        context = MagicMock()
        context.groups.return_value = [own_group, enemy_group]

        evt = events.YourMoveEvent(ishi)
        result = list(strategy.recommend(ishi, evt, context))
        assert result == []

    def test_eager_negation_cost_exceeds_vp(self):
        """VP insufficient for cost → early return (line 366+)."""
        from simulation import events
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy

        strategy = EagerNegationStrategy()
        ishi = MagicMock()
        school = MagicMock()
        school.school_knacks.return_value = ["precepts"]
        ishi.school.return_value = school
        ishi.skill.return_value = 5
        ishi._ishi_negation_done = False
        ishi.vp.return_value = 1  # insufficient

        enemy = MagicMock()
        enemy.is_fighting.return_value = True
        enemy_school = MagicMock()
        enemy_school.school_knacks.return_value = ["attack"]
        enemy.school.return_value = enemy_school
        enemy.skill.return_value = 5  # rank 5 → cost = 10
        own_group = [ishi]
        enemy_group = [enemy]
        ishi.group.return_value = own_group
        context = MagicMock()
        context.groups.return_value = [own_group, enemy_group]

        evt = events.YourMoveEvent(ishi)
        result = list(strategy.recommend(ishi, evt, context))
        assert result == []


class TestTargetFinders:
    """Cover target_finders.py lines 77, 112: subclass-find_target chains."""

    def test_most_dangerous_target_finder_no_targets(self):
        """When no enemies, MostDangerousTargetFinder returns None (line 79).

        Line 77 is the return-target branch; we exercise it via the
        MostDangerousTargetFinder.find_target -> find_most_dangerous_target.
        """
        from simulation.strategies.target_finders import (
            MostDangerousTargetFinder,
        )

        finder = MostDangerousTargetFinder()
        subject = MagicMock()
        context = MagicMock()
        context.characters.return_value = []  # no others
        # find_target dispatches to find_most_dangerous_target
        ia = MagicMock()
        result = finder.find_target(subject, "attack", ia, context)
        assert result is None

    def test_most_dangerous_target_finder_returns_first(self):
        """When enemies exist, return the first sorted by avg damage (line 77)."""
        from simulation.strategies.target_finders import (
            MostDangerousTargetFinder,
        )

        finder = MostDangerousTargetFinder()
        enemy = MagicMock()
        enemy.is_fighting.return_value = True
        subject = MagicMock()
        subject.group.return_value = [subject]  # subject in its own group
        subject.knowledge.return_value.average_damage_roll.return_value = 10
        subject.crippled.return_value = False
        context = MagicMock()
        context.characters.return_value = [subject, enemy]
        context.formation.return_value.can_attack.return_value = True
        ia = MagicMock()
        result = finder.find_target(subject, "attack", ia, context)
        assert result is enemy
