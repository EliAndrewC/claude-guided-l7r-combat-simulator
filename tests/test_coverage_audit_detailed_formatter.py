"""Coverage audit tests for web/adapters/detailed_formatter.py.

Spec 007 Phase 8 (T023): the legacy ``_format_*`` private methods on
``DetailedEventFormatter`` were deleted after the structured-trace
refactor moved their rendering logic into ``web/adapters/text_renderer.py``.
The byte-identical roundtrip tests in
``tests/test_text_renderer_roundtrip.py`` cover the rendering logic at
the correct layer (via the public ``entries()`` + ``TextRenderer`` path).

This file now retains only tests that exercise still-live helpers
inside ``detailed_formatter.py``:

- ``_compute_damage_breakdown`` (defensive guards)
- ``_render_components`` (module-level helper)
- ``_format_dice`` (module-level helper)
- ``_phase_prefix`` (instance helper, used by every ``_entry_*`` builder)
- ``_unpack_wound_check_params`` (static helper, used by
  ``_build_wound_check_entry``)
- ``_find_*`` and ``_has_counterattack_between`` lookahead helpers
  (used by ``entries()`` for event composition)
- A small set of end-to-end ``format_history`` smoke tests that
  exercise composition branches not naturally hit by other tests.
"""

from unittest.mock import MagicMock

from web.adapters.detailed_formatter import (
    DetailedEventFormatter,
    _compute_damage_breakdown,
    _format_dice,
    _render_components,
)


def _char(name="X"):
    c = MagicMock()
    c.name.return_value = name
    return c


def _action(subj="A", tgt="B", skill="attack", vp=0):
    action = MagicMock()
    action.subject.return_value = _char(subj)
    action.target.return_value = _char(tgt)
    action.skill.return_value = skill
    action.vp.return_value = vp
    return action


class TestComputeDamageBreakdownDefensive:
    """Defensive guards in ``_compute_damage_breakdown``."""

    def test_provider_without_get_breakdown(self):
        """Provider missing get_breakdown returns empty list."""

        class Provider:
            pass

        class Subject:
            def roll_parameter_provider(self):
                return Provider()

        action = _action()
        result = _compute_damage_breakdown(Subject(), Subject(), action, 0)
        assert result == []

    def test_provider_raises_exception(self):
        """Provider get_breakdown raising returns empty list."""

        class Provider:
            def get_breakdown(self, *a, **kw):
                raise RuntimeError("nope")

        class Subject:
            def roll_parameter_provider(self):
                return Provider()

        action = _action()
        result = _compute_damage_breakdown(Subject(), Subject(), action, 0)
        assert result == []

    def test_provider_returns_non_list(self):
        """Non-list return → empty list."""

        class Provider:
            def get_breakdown(self, *a, **kw):
                return "not a list"

        class Subject:
            def roll_parameter_provider(self):
                return Provider()

        action = _action()
        result = _compute_damage_breakdown(Subject(), Subject(), action, 0)
        assert result == []


class TestRenderComponentsDefensive:
    """``_render_components`` filter edge cases."""

    def test_render_components_empty_input(self):
        assert _render_components(None) == ""
        assert _render_components([]) == ""

    def test_render_components_single_zero_filter(self):
        """All-zero contributions filter to empty → returns ''."""
        assert _render_components([("X", 0, 0), ("Y", 0, 0)]) == ""

    def test_render_components_single_nonzero(self):
        """A single nonzero contribution returns '' (need >=2)."""
        assert _render_components([("X", 0, 0), ("Y", 5, 3)]) == ""

    def test_render_components_multi(self):
        assert _render_components(
            [("Fire ring", 5, 5), ("attack", 3, 0)],
        ) == "5k5 Fire ring + 3k0 attack"

    def test_render_components_kept_only_preserved(self):
        """A kept-only contribution (rolled=0, kept>0) is retained."""
        s = _render_components([("Fire ring", 5, 5), ("VP", 0, 2)])
        assert "0k2 VP" in s


class TestFormatDiceEdgeCases:
    """``_format_dice`` handles empty and partial-kept inputs."""

    def test_format_dice_empty(self):
        assert _format_dice([], 0) == "[]"

    def test_format_dice_with_dropped(self):
        s = _format_dice([10, 8, 5], 2)
        assert "**10**" in s and "**8**" in s and "~~5~~" in s


class TestFormatHistoryEmptyBranches:
    """End-to-end ``format_history`` exercises composition branches when
    events lack ``_detail_dice`` or arrive in unusual orders.
    """

    def test_take_attack_without_matching_rolled(self):
        """When no matching AttackRolledEvent follows, render
        TakeAttackActionEvent alone."""
        from simulation.events import TakeAttackActionEvent

        formatter = DetailedEventFormatter()
        history = [TakeAttackActionEvent(_action("A", "B", "attack"))]
        lines = formatter.format_history(history)
        assert any("⚔️ attacks B" in line for line in lines)

    def test_take_attack_with_counterattack_between(self):
        """When TakeCounterattackActionEvent intervenes between
        TakeAttackActionEvent and AttackRolledEvent, the attack is
        rendered standalone."""
        from simulation.events import (
            AttackRolledEvent,
            TakeAttackActionEvent,
            TakeCounterattackActionEvent,
        )

        formatter = DetailedEventFormatter()
        atk_action = _action("A", "B")
        atk_action.is_hit.return_value = True
        atk_action.parried.return_value = False
        atk_action.calculate_extra_damage_dice.return_value = 0
        atk_action.skill_roll_params.return_value = (5, 3, 0)
        atk_action.tn.return_value = 20
        atk_action.target.return_value._tn_to_hit = lambda: 20
        ctr_action = _action("B", "A", skill="counterattack")
        history = [
            TakeAttackActionEvent(atk_action),
            TakeCounterattackActionEvent(ctr_action),
            AttackRolledEvent(atk_action, 25),
        ]
        lines = formatter.format_history(history)
        assert any("attacks" in line for line in lines)

    def test_take_counterattack_with_matching_rolled(self):
        """TakeCounterattackActionEvent followed by CounterattackRolledEvent
        combines them."""
        from simulation.events import (
            CounterattackRolledEvent,
            SpendVoidPointsEvent,
            TakeCounterattackActionEvent,
        )

        formatter = DetailedEventFormatter()
        action = _action("A", "B", skill="counterattack")
        action.is_hit.return_value = False  # MISS path, avoids damage_params unpacking
        action.calculate_extra_damage_dice.return_value = 0
        rolled = CounterattackRolledEvent(action, 20)
        rolled._detail_dice = [10, 7]
        rolled._detail_params = (2, 1, 5)
        rolled._detail_tn = 15
        subj = action.subject()
        history = [
            TakeCounterattackActionEvent(action),
            SpendVoidPointsEvent(subj, "counterattack", 1),
            rolled,
        ]
        lines = formatter.format_history(history)
        assert any("counterattacks" in line for line in lines)

    def test_take_counterattack_without_rolled(self):
        """TakeCounterattackActionEvent with no matching roll renders standalone."""
        from simulation.events import TakeCounterattackActionEvent

        formatter = DetailedEventFormatter()
        action = _action("A", "B", skill="counterattack")
        history = [TakeCounterattackActionEvent(action)]
        lines = formatter.format_history(history)
        assert any("counterattacks" in line for line in lines)


class TestUnpackWoundCheckParams:
    """``_unpack_wound_check_params`` accepts both 2-tuple and 3-tuple shapes."""

    def test_unpack_wound_check_params_legacy_tuple(self):
        """A 2-tuple (rolled, kept) → modifier defaults to 0."""
        rolled, kept, mod = DetailedEventFormatter._unpack_wound_check_params(
            (5, 3),
        )
        assert (rolled, kept, mod) == (5, 3, 0)

    def test_unpack_wound_check_params_none(self):
        """``None`` → all zeros."""
        assert DetailedEventFormatter._unpack_wound_check_params(None) == (0, 0, 0)

    def test_unpack_wound_check_params_three_tuple(self):
        rolled, kept, mod = DetailedEventFormatter._unpack_wound_check_params(
            (5, 3, 10),
        )
        assert (rolled, kept, mod) == (5, 3, 10)


class TestPhasePrefix:
    """``_phase_prefix`` toggles 'Phase N | ' on first call per phase."""

    def test_phase_prefix_first_call_shows_phase(self):
        formatter = DetailedEventFormatter()
        formatter._current_phase = 3
        assert "Phase 3" in formatter._phase_prefix("X")

    def test_phase_prefix_subsequent_calls_omit_phase(self):
        formatter = DetailedEventFormatter()
        formatter._current_phase = 3
        formatter._phase_prefix("A")
        # Second call returns just "Name |" without "Phase".
        assert "Phase" not in formatter._phase_prefix("B")


class TestFindAkodo5thCounterDamage:
    """``_find_akodo_5th_counter_damage`` scan logic."""

    def test_find_akodo_5th_counter_damage_break_on_non_skip(self):
        from simulation.events import (
            LightWoundsDamageEvent,
            NewPhaseEvent,
        )

        formatter = DetailedEventFormatter()
        akodo = _char("Akodo")
        target = _char("Bayushi")
        # NewPhaseEvent is not a _SKIP_EVENT → break loop
        history = [NewPhaseEvent(1)]
        result = formatter._find_akodo_5th_counter_damage(history, 0, akodo)
        assert result is None

        # When match is found, return its index
        lw = LightWoundsDamageEvent(akodo, target, 10)
        lw.source = "Akodo 5th Dan"
        history2 = [lw]
        result = formatter._find_akodo_5th_counter_damage(history2, 0, akodo)
        assert result == 0

    def test_find_akodo_5th_counter_damage_with_skip_in_path(self):
        """Skip events between start and a match should be passed through."""
        from simulation.events import (
            AttackDeclaredEvent,
            LightWoundsDamageEvent,
        )

        formatter = DetailedEventFormatter()
        akodo = _char("Akodo")
        target = _char("Bayushi")
        action = _action("Akodo", "Bayushi")
        skip = AttackDeclaredEvent(action)  # member of _SKIP_EVENTS
        lw = LightWoundsDamageEvent(akodo, target, 10)
        lw.source = "Akodo 5th Dan"
        history = [skip, lw]
        result = formatter._find_akodo_5th_counter_damage(history, 0, akodo)
        assert result == 1


class TestFindParryRolled:
    """``_find_parry_rolled`` and ``_find_counterattack_rolled`` skip-event logic."""

    def test_find_counterattack_rolled_skips_skip_events(self):
        from simulation.events import (
            AttackDeclaredEvent,
            CounterattackRolledEvent,
        )

        formatter = DetailedEventFormatter()
        action = _action(skill="counterattack")
        atk_action = _action("X", "Y")
        skip = AttackDeclaredEvent(atk_action)
        rolled = CounterattackRolledEvent(action, 18)
        history = [skip, rolled]
        idx = formatter._find_counterattack_rolled(history, 0, action)
        assert idx == 1

    def test_find_counterattack_rolled_break_on_other_event(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        action = _action(skill="counterattack")
        history = [NewPhaseEvent(1)]
        idx = formatter._find_counterattack_rolled(history, 0, action)
        assert idx is None

    def test_find_parry_rolled_skips_skip_events(self):
        from simulation.events import AttackDeclaredEvent, ParryRolledEvent

        formatter = DetailedEventFormatter()
        action = _action(skill="parry")
        atk_action = _action("X", "Y")
        skip = AttackDeclaredEvent(atk_action)
        rolled = ParryRolledEvent(action, 18)
        history = [skip, rolled]
        idx = formatter._find_parry_rolled(history, 0, action)
        assert idx == 1

    def test_find_parry_rolled_break_on_other_event(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        action = _action(skill="parry")
        history = [NewPhaseEvent(1)]
        idx = formatter._find_parry_rolled(history, 0, action)
        assert idx is None


class TestFindTakeSwAndKeepLw:
    """Lookahead helpers that pair WoundCheck with TakeSW / KeepLW."""

    def test_find_take_sw_returns_none_on_keep_lw(self):
        """A KeepLightWoundsEvent before any TakeSW → None."""
        from simulation.events import (
            KeepLightWoundsEvent,
            TakeSeriousWoundEvent,
        )

        formatter = DetailedEventFormatter()
        subj = _char("X")
        attacker = _char("Y")
        keep = KeepLightWoundsEvent(subj, attacker, 5)
        sw = TakeSeriousWoundEvent(subj, attacker, 20)
        history = [keep, sw]
        result = formatter._find_take_sw(history, 0, "X")
        assert result is None

    def test_find_take_sw_break_on_other(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        history = [NewPhaseEvent(1)]
        result = formatter._find_take_sw(history, 0, "X")
        assert result is None

    def test_find_sw_damage_break_on_other(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        history = [NewPhaseEvent(1)]
        idx = formatter._find_sw_damage(history, 0, "X")
        assert idx is None

    def test_find_sw_damage_skips_skip_events(self):
        from simulation.events import (
            AttackDeclaredEvent,
            SeriousWoundsDamageEvent,
        )

        formatter = DetailedEventFormatter()
        atk_action = _action("X", "Y")
        skip = AttackDeclaredEvent(atk_action)
        dmg = SeriousWoundsDamageEvent(_char("attacker"), _char("X"), 2)
        history = [skip, dmg]
        idx = formatter._find_sw_damage(history, 0, "X")
        assert idx == 1

    def test_find_keep_lw_returns_none_on_take_sw(self):
        from simulation.events import (
            KeepLightWoundsEvent,
            TakeSeriousWoundEvent,
        )

        formatter = DetailedEventFormatter()
        subj = _char("X")
        attacker = _char("Y")
        sw = TakeSeriousWoundEvent(subj, attacker, 20)
        keep = KeepLightWoundsEvent(subj, attacker, 5)
        history = [sw, keep]
        result = formatter._find_keep_lw(history, 0, "X")
        assert result is None

    def test_find_keep_lw_break_on_other(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        history = [NewPhaseEvent(1)]
        result = formatter._find_keep_lw(history, 0, "X")
        assert result is None

    def test_find_wound_check_rolled_break_on_other(self):
        from simulation.events import NewPhaseEvent

        formatter = DetailedEventFormatter()
        history = [NewPhaseEvent(1)]
        result = formatter._find_wound_check_rolled(history, 0, "X")
        assert result is None

    def test_find_wound_check_rolled_skips_skip_events(self):
        from simulation.events import AttackDeclaredEvent, WoundCheckRolledEvent

        formatter = DetailedEventFormatter()
        atk_action = _action("X", "Y")
        skip = AttackDeclaredEvent(atk_action)
        subject = _char("X")
        attacker = _char("Y")
        wc = WoundCheckRolledEvent(subject, attacker, 22, 25, tn=22)
        history = [skip, wc]
        idx = formatter._find_wound_check_rolled(history, 0, "X")
        assert idx == 1


class TestEndToEndComposition:
    """Composition branches that need a real event stream to hit."""

    def test_duel_strike_miss(self):
        from simulation.duel import DuelStrikeRolledEvent

        formatter = DetailedEventFormatter()
        evt = DuelStrikeRolledEvent(
            _char("A"), _char("B"), roll=10, tn=20,
            is_hit=False, extra_damage_dice=0,
        )
        lines = formatter.format_history([evt])
        assert any("MISS" in line for line in lines)

    def test_duel_resheath(self):
        from simulation.duel import DuelResheathEvent

        formatter = DetailedEventFormatter()
        evt = DuelResheathEvent(_char("A"), _char("B"), _char("A"))
        lines = formatter.format_history([evt])
        assert any("resheathe" in line for line in lines)

    def test_duel_ended(self):
        from simulation.duel import DuelEndedEvent

        formatter = DetailedEventFormatter()
        evt = DuelEndedEvent(_char("A"), _char("B"))
        lines = formatter.format_history([evt])
        assert any("Duel ended" in line for line in lines)

    def test_format_history_consumed_continue_in_vp_loop(self):
        """``consumed.add(j)`` path inside the VP-on-attack lookahead loop —
        the inner loop properly consumes spend events while pairing TakeAttack+Rolled."""
        from simulation.events import (
            AttackRolledEvent,
            NewPhaseEvent,
            SpendVoidPointsEvent,
            TakeAttackActionEvent,
        )

        formatter = DetailedEventFormatter()
        atk = _action("A", "B")
        atk.is_hit.return_value = False
        atk.parried.return_value = False
        atk.calculate_extra_damage_dice.return_value = 0
        rolled = AttackRolledEvent(atk, 15)
        rolled._detail_dice = [5, 4]
        rolled._detail_params = (2, 1, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        subj = atk.subject()
        spend = SpendVoidPointsEvent(subj, "attack", 1)
        phase = NewPhaseEvent(1)
        phase._detail_status = {
            "A": {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3, "max_vp": 3,
                  "actions": [1], "crippled": False},
        }
        history = [
            phase,
            TakeAttackActionEvent(atk),
            spend,
            rolled,
        ]
        lines = formatter.format_history(history)
        # The attack should be combined; spend is consumed and not its own line
        attack_lines = [line for line in lines if "attacks" in line]
        assert len(attack_lines) >= 1
