"""Tests for DetailedEventFormatter with emoji, phase prefixes, and combined events."""

import unittest
from unittest.mock import MagicMock

from simulation import events
from simulation.schools.kakita_school import (
    ContestedIaijutsuAttackDeclaredEvent,
    ContestedIaijutsuAttackRolledEvent,
    TakeContestedIaijutsuAttackAction,
)
from web.adapters.detailed_formatter import DetailedEventFormatter, _format_dice


def _make_action(subject_name="Akodo", target_name="Bayushi", skill="attack"):
    action = MagicMock()
    subject = MagicMock()
    subject.name.return_value = subject_name
    subject.get_damage_roll_params.return_value = (6, 2, 0)
    target = MagicMock()
    target.name.return_value = target_name
    action.subject.return_value = subject
    action.target.return_value = target
    action.skill.return_value = skill
    action.skill_roll.return_value = 29
    action.vp.return_value = 0
    action.parry_attempted.return_value = False
    action.is_hit.return_value = True
    action.parried.return_value = False
    return action


def _make_status(name1="Akodo", name2="Bayushi", **overrides):
    """Create a default two-character status dict."""
    defaults = {
        name1: {"lw": 0, "sw": 0, "max_sw": 4, "vp": 3, "max_vp": 3, "actions": [4, 7], "crippled": False},
        name2: {"lw": 0, "sw": 0, "max_sw": 4, "vp": 2, "max_vp": 2, "actions": [5, 6], "crippled": False},
    }
    for key, val in overrides.items():
        if key in defaults:
            defaults[key].update(val)
    return defaults


class TestFormatterRoundHeader(unittest.TestCase):
    def test_round_zero_displays_as_round_1(self):
        fmt = DetailedEventFormatter()
        event = events.NewRoundEvent(0)
        lines = fmt.format_history([event])
        header = [ln for ln in lines if "Round" in ln][0]
        self.assertIn("Round 1", header)

    def test_round_header_uses_unicode_box_chars(self):
        fmt = DetailedEventFormatter()
        event = events.NewRoundEvent(1)
        lines = fmt.format_history([event])
        header = [ln for ln in lines if "Round 2" in ln][0]
        self.assertIn("═══", header)

    def test_round_header_blank_line_before(self):
        fmt = DetailedEventFormatter()
        e1 = events.NewRoundEvent(1)
        e2 = events.NewRoundEvent(2)
        lines = fmt.format_history([e1, e2])
        # Second round header should have blank line before it
        idx = next(i for i, ln in enumerate(lines) if "Round 3" in ln)
        self.assertEqual("", lines[idx - 1])


class TestFormatterInitiative(unittest.TestCase):
    def test_initiative_block_with_emoji_and_dice(self):
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_initiative = {
            "Akodo Bushi": {
                "all_dice": [2, 4, 7],
                "actions": [4, 7],
                "roll_params": (3, 2),
            },
            "Bayushi Bushi": {
                "all_dice": [1, 5, 6],
                "actions": [5, 6],
                "roll_params": (3, 2),
            },
        }
        phase._detail_status = _make_status("Akodo Bushi", "Bayushi Bushi")
        lines = fmt.format_history([phase])
        # Should have dice emoji
        init_header = [ln for ln in lines if "Initiative" in ln][0]
        self.assertIn("🎲", init_header)
        # Should have dice info
        akodo_line = [ln for ln in lines if "Akodo Bushi" in ln and "3k2" in ln][0]
        self.assertIn("**2**", akodo_line)
        self.assertIn("**4**", akodo_line)
        self.assertIn("~~7~~", akodo_line)
        self.assertIn("Actions: [4, 7]", akodo_line)


class TestFormatterOpeningStatus(unittest.TestCase):
    def test_opening_status_block_format(self):
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_status = {
            "Akodo": {"lw": 0, "sw": 0, "max_sw": 4, "vp": 3, "max_vp": 3, "actions": [4, 7], "crippled": False},
            "Bayushi": {"lw": 5, "sw": 1, "max_sw": 4, "vp": 1, "max_vp": 2, "actions": [5, 6], "crippled": True},
        }
        lines = fmt.format_history([phase])
        akodo_line = [ln for ln in lines if "Akodo" in ln and "Light" in ln][0]
        self.assertIn("Light 0", akodo_line)
        self.assertIn("Serious 0/4", akodo_line)
        self.assertIn("Void 3/3", akodo_line)
        self.assertIn("Actions: [4, 7]", akodo_line)
        bayushi_line = [ln for ln in lines if "Bayushi" in ln and "Light" in ln][0]
        self.assertIn("Light 5", bayushi_line)
        self.assertIn("Serious 1/4", bayushi_line)
        self.assertIn("Void 1/2", bayushi_line)
        self.assertIn("Actions: [5, 6]", bayushi_line)
        self.assertIn("CRIPPLED", bayushi_line)

    def test_opening_status_has_separator_lines(self):
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_status = _make_status()
        lines = fmt.format_history([phase])
        # Find separator lines
        sep_indices = [i for i, ln in enumerate(lines) if "─────" in ln]
        self.assertEqual(2, len(sep_indices), f"Expected 2 separator lines, got {sep_indices} in {lines}")
        # Status lines should be between separators
        status_indices = [i for i, ln in enumerate(lines) if "Light" in ln and "Serious" in ln]
        for si in status_indices:
            self.assertGreater(si, sep_indices[0])
            self.assertLess(si, sep_indices[1])

    def test_opening_status_shown_once(self):
        fmt = DetailedEventFormatter()
        status = _make_status()
        p0 = events.NewPhaseEvent(0)
        p0._detail_status = status
        p1 = events.NewPhaseEvent(1)
        p1._detail_status = status
        p2 = events.NewPhaseEvent(2)
        p2._detail_status = status
        lines = fmt.format_history([p0, p1, p2])
        status_lines = [ln for ln in lines if "Light" in ln and "Serious" in ln]
        # Only opening status = 2 lines (one per character)
        self.assertEqual(2, len(status_lines))

    def test_no_duplicate_status_when_no_actions_in_phase_zero(self):
        """When Phase 0 has no actions (no 5th Dan), the first attack should
        not re-render the status block immediately after the opening status."""
        fmt = DetailedEventFormatter()
        status = _make_status()
        # Phase 0 with opening status, but no actions
        p0 = events.NewPhaseEvent(0)
        p0._detail_status = status
        p0._detail_initiative = {
            "Akodo": {"all_dice": [4, 7], "actions": [4, 7], "roll_params": (3, 2)},
            "Bayushi": {"all_dice": [5, 6], "actions": [5, 6], "roll_params": (3, 2)},
        }
        # Phase 4: first actual attack
        p4 = events.NewPhaseEvent(4)
        p4._detail_status = status  # same status, nothing happened
        action = _make_action("Akodo", "Bayushi")
        take_atk = events.TakeAttackActionEvent(action)
        take_atk._detail_status = status

        lines = fmt.format_history([p0, p4, take_atk])
        status_lines = [ln for ln in lines if "Light" in ln and "Serious" in ln]
        # Should have exactly 2 status lines (one per character) from opening,
        # NOT 4 (which would mean the status block was duplicated)
        self.assertEqual(2, len(status_lines), f"Status duplicated: {lines}")

    def test_status_shown_again_after_combat_action(self):
        """After a combat action occurs, subsequent attacks should show updated status."""
        fmt = DetailedEventFormatter()
        status1 = _make_status()
        status2 = _make_status(Akodo={"lw": 10, "sw": 1})

        p0 = events.NewPhaseEvent(0)
        p0._detail_status = status1
        # First attack
        action1 = _make_action("Bayushi", "Akodo")
        take_atk1 = events.TakeAttackActionEvent(action1)
        take_atk1._detail_status = status1
        # Damage happens (status changes)...
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        target = MagicMock()
        target.name.return_value = "Akodo"
        lw_event = events.LightWoundsDamageEvent(attacker, target, 10)
        # Second attack should show updated status
        action2 = _make_action("Akodo", "Bayushi")
        take_atk2 = events.TakeAttackActionEvent(action2)
        take_atk2._detail_status = status2

        lines = fmt.format_history([p0, take_atk1, lw_event, take_atk2])
        status_lines = [ln for ln in lines if "Light" in ln and "Serious" in ln]
        # 2 from opening + 2 from before second attack = 4
        self.assertEqual(4, len(status_lines))


class TestFormatterAttackAction(unittest.TestCase):
    def test_phase_prefix_on_attack_action(self):
        fmt = DetailedEventFormatter()
        status = _make_status()
        phase = events.NewPhaseEvent(4)
        phase._detail_status = status
        action = _make_action("Akodo", "Bayushi", "attack")
        attack = events.TakeAttackActionEvent(action)
        attack._detail_status = status
        lines = fmt.format_history([phase, attack])
        attack_line = [ln for ln in lines if "attacks" in ln][0]
        self.assertIn("Phase 4", attack_line)
        self.assertIn("Akodo", attack_line)
        self.assertIn("⚔️", attack_line)

    def test_attack_action_shows_target_and_skill(self):
        fmt = DetailedEventFormatter()
        status = _make_status()
        phase = events.NewPhaseEvent(4)
        phase._detail_status = status
        action = _make_action("Akodo", "Bayushi", "attack")
        attack = events.TakeAttackActionEvent(action)
        attack._detail_status = status
        lines = fmt.format_history([phase, attack])
        attack_line = [ln for ln in lines if "attacks" in ln][0]
        self.assertIn("Bayushi", attack_line)
        self.assertIn("attack", attack_line)


class TestFormatterAttackRolledHit(unittest.TestCase):
    def test_attack_hit_combined_line(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2
        action.damage_roll_params.return_value = (6, 2, 0)
        event = events.AttackRolledEvent(action, 29)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 15

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("🎯", attack_line)
        self.assertIn("7k3", attack_line)
        self.assertIn("**9**", attack_line)
        self.assertIn("~~6~~", attack_line)
        self.assertIn("HIT", attack_line)
        self.assertIn("TN 15", attack_line)

    def test_attack_hit_shows_modifier(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2
        action.damage_roll_params.return_value = (6, 2, 0)
        event = events.AttackRolledEvent(action, 29)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 15

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("+5", attack_line)

    def test_attack_hit_shows_damage_preview(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2
        action.damage_roll_params.return_value = (6, 2, 0)
        event = events.AttackRolledEvent(action, 29)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 15

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("damage will be 6k2", attack_line)

    def test_attack_hit_shows_extra_dice_count(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2
        action.damage_roll_params.return_value = (6, 2, 0)
        event = events.AttackRolledEvent(action, 29)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 15

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("2 extra damage dice", attack_line)

    def test_attack_hit_shows_singular_extra_die(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 1
        action.damage_roll_params.return_value = (5, 2, 0)
        event = events.AttackRolledEvent(action, 24)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 20

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("1 extra damage die", attack_line)
        self.assertNotIn("1 extra damage dice", attack_line)


class TestFormatterAttackExtraDiceUseCapturedTN(unittest.TestCase):
    def test_extra_dice_uses_captured_tn_not_dynamic(self):
        """Extra damage dice must be computed from the captured TN at roll time,
        not from the action's dynamic tn() which may change during combat."""
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        # Simulate: tn was 30 at roll time, but post-combat tn_to_hit() rose to 62.
        # calculate_extra_damage_dice(tn=30) => (82-30)//5 = 10  (correct)
        # calculate_extra_damage_dice()       => (82-62)//5 = 4   (wrong, uses dynamic tn)
        action.calculate_extra_damage_dice.side_effect = (
            lambda skill_roll=None, tn=None: (82 - (tn if tn is not None else 62)) // 5
        )
        subject = action.subject()
        subject.get_damage_roll_params.return_value = (14, 4, 0)
        action.damage_roll_params.return_value = (10, 5, 0)  # wrong (uses dynamic tn)

        event = events.AttackRolledEvent(action, 82)
        event._detail_dice = [18, 16, 14, 9, 9, 8, 8, 8, 4, 4]
        event._detail_params = (10, 7, 0)
        event._detail_tn = 30  # captured at roll time

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        # margin = 82 - 30 = 52, extra_dice = 52 // 5 = 10
        self.assertIn("10 extra damage dice", attack_line)
        self.assertNotIn("4 extra damage dice", attack_line)

    def test_damage_preview_uses_correct_extra_dice(self):
        """Damage preview should use the correctly computed extra dice."""
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.side_effect = (
            lambda skill_roll=None, tn=None: (82 - (tn if tn is not None else 62)) // 5
        )
        subject = action.subject()
        subject.get_damage_roll_params.return_value = (14, 4, 0)
        action.damage_roll_params.return_value = (10, 5, 0)

        event = events.AttackRolledEvent(action, 82)
        event._detail_dice = [18, 16, 14, 9, 9, 8, 8, 8, 4, 4]
        event._detail_params = (10, 7, 0)
        event._detail_tn = 30

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        # Should use damage params from subject.get_damage_roll_params with correct extra_dice
        self.assertIn("damage will be 14k4", attack_line)
        self.assertNotIn("damage will be 10k5", attack_line)


class TestFormatterAttackRolledMiss(unittest.TestCase):
    def test_attack_miss_combined_line(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = False
        action.parried.return_value = False
        event = events.AttackRolledEvent(action, 16)
        event._detail_dice = [9, 4, 3, 2, 1, 1, 1]
        event._detail_params = (7, 3, 0)
        event._detail_tn = 20

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("❌", attack_line)
        self.assertIn("MISS", attack_line)
        self.assertIn("TN 20", attack_line)


class TestFormatterParryRolled(unittest.TestCase):
    def test_parry_rolled_combined_with_result(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        action.subject.return_value = subject
        action.is_success.return_value = False
        event = events.ParryRolledEvent(action, 18)
        event._detail_dice = [8, 6, 4, 3, 1]
        event._detail_params = (5, 3, 0)
        event._detail_tn = 29

        lines = fmt.format_history([event])
        parry_line = [ln for ln in lines if "Parry:" in ln][0]
        self.assertIn("🛡️", parry_line)
        self.assertIn("5k3", parry_line)
        self.assertIn("FAILED", parry_line)
        self.assertIn("TN 29", parry_line)

    def test_parry_rolled_succeeded(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        action.subject.return_value = subject
        action.is_success.return_value = True
        event = events.ParryRolledEvent(action, 30)
        event._detail_dice = [10, 9, 8, 5, 3]
        event._detail_params = (5, 3, 0)
        event._detail_tn = 29

        lines = fmt.format_history([event])
        parry_line = [ln for ln in lines if "Parry:" in ln][0]
        self.assertIn("SUCCEEDED", parry_line)


class TestFormatterDamage(unittest.TestCase):
    def test_damage_line_with_emoji_and_dice(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(subject, target, 15)
        event._detail_dice = [8, 7, 5, 4, 3, 1]
        event._detail_params = (6, 2)
        event._detail_lw_after = 30

        lines = fmt.format_history([event])
        damage_line = [ln for ln in lines if "Damage:" in ln][0]
        self.assertIn("💥", damage_line)
        self.assertIn("6k2", damage_line)
        self.assertIn("**8**", damage_line)
        self.assertIn("**7**", damage_line)
        self.assertIn("~~5~~", damage_line)
        # Combined onto single line
        self.assertIn("takes", damage_line)
        self.assertIn("light wounds", damage_line)

    def test_lw_taken_line_with_running_total(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(subject, target, 15)
        event._detail_dice = [8, 7, 5, 4, 3, 1]
        event._detail_params = (6, 2)
        event._detail_lw_after = 30

        lines = fmt.format_history([event])
        # Running total appears on the same combined Damage line
        damage_line = [ln for ln in lines if "Damage:" in ln][0]
        self.assertIn("total: 30", damage_line)

    def test_lw_damage_without_annotations_graceful(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(subject, target, 15)
        # No _detail_* attributes
        lines = fmt.format_history([event])
        self.assertTrue(any("Bayushi" in ln and "15 light wounds" in ln for ln in lines))

    def test_serious_wounds_damage(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.SeriousWoundsDamageEvent(subject, target, 1)
        lines = fmt.format_history([event])
        self.assertTrue(any("💔" in ln and "Bayushi" in ln and "serious" in ln.lower() for ln in lines))


class TestFormatterVoidPoints(unittest.TestCase):
    def test_vp_spending_single_with_black_square(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SpendVoidPointsEvent(subject, "attack", 1)
        lines = fmt.format_history([event])
        vp_line = [ln for ln in lines if "VP" in ln][0]
        self.assertIn("⬛", vp_line)
        self.assertIn("Akodo", vp_line)
        self.assertIn("1 VP", vp_line)
        self.assertIn("attack", vp_line)

    def test_vp_spending_multiple_shows_multiple_squares(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SpendVoidPointsEvent(subject, "wound check", 3)
        lines = fmt.format_history([event])
        vp_line = [ln for ln in lines if "VP" in ln][0]
        self.assertIn("⬛⬛⬛", vp_line)
        self.assertIn("3 VP", vp_line)


class TestFormatterWoundCheckPassed(unittest.TestCase):
    def test_wound_check_passed_combined_line(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        # roll 20 >= tn 30 is False, but for this test we want pass: roll >= tn
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 35, tn=30)
        event._detail_dice = [9, 6, 5, 2]
        event._detail_params = (4, 3)

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("💔", wc_line)
        self.assertIn("PASSED", wc_line)
        self.assertIn("TN 30", wc_line)
        self.assertIn("4k3", wc_line)


class TestFormatterWoundCheckFailed(unittest.TestCase):
    def test_wound_check_failed_combined_line(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        event._detail_dice = [5, 4, 3, 2]
        event._detail_params = (4, 3)

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("🖤", wc_line)
        self.assertIn("FAILED", wc_line)
        self.assertIn("TN 30", wc_line)


class TestFormatterKeepLightWounds(unittest.TestCase):
    def test_keep_lw_line_with_emoji(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.KeepLightWoundsEvent(subject, attacker, 30)
        event._detail_lw_total = 30

        lines = fmt.format_history([event])
        keep_line = [ln for ln in lines if "keeping" in ln][0]
        self.assertIn("🖤", keep_line)
        self.assertIn("30", keep_line)
        self.assertIn("light wounds", keep_line)


class TestFormatterTakeSeriousWound(unittest.TestCase):
    def test_take_sw_line_with_emoji(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.TakeSeriousWoundEvent(subject, attacker, 30)
        event._detail_lw_total = 30

        lines = fmt.format_history([event])
        sw_line = [ln for ln in lines if "serious wound" in ln.lower()][0]
        self.assertIn("💔", sw_line)
        self.assertIn("Bayushi", sw_line)

    def test_voluntary_sw_after_passed_wound_check(self):
        """When wound check passed but character takes SW, say 'chooses to take'."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 28, tn=28)
        wc._detail_dice = [9, 7, 6, 6, 3]
        wc._detail_params = (5, 4)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 28)
        take_sw._detail_lw_total = 28

        lines = fmt.format_history([wc, take_sw])
        sw_line = [ln for ln in lines if "serious wound" in ln.lower()][0]
        self.assertIn("chooses to take", sw_line)

    def test_forced_sw_after_failed_wound_check(self):
        """When wound check failed, just say 'takes'."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        wc._detail_dice = [5, 4, 3, 2]
        wc._detail_params = (4, 3)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)
        take_sw._detail_lw_total = 30

        lines = fmt.format_history([wc, take_sw])
        sw_line = [ln for ln in lines if "serious wound" in ln.lower()][0]
        self.assertNotIn("chooses", sw_line)

    def test_sw_damage_merged_with_take_sw(self):
        """SeriousWoundsDamageEvent should be skipped when preceded by TakeSeriousWoundEvent."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)
        take_sw._detail_lw_total = 30

        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 1)

        lines = fmt.format_history([take_sw, sw_dmg])
        # Should only have one serious wound line, not two
        sw_lines = [ln for ln in lines if "serious wound" in ln.lower()]
        self.assertEqual(1, len(sw_lines))

    def test_standalone_sw_damage_not_skipped(self):
        """SeriousWoundsDamageEvent without preceding TakeSeriousWoundEvent should show."""
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"

        sw_dmg = events.SeriousWoundsDamageEvent(attacker, target, 1)

        lines = fmt.format_history([sw_dmg])
        self.assertTrue(any("serious wound" in ln.lower() for ln in lines))

    def test_sw_damage_multiple_shows_multiple_hearts(self):
        """Standalone SeriousWoundsDamageEvent with damage > 1 shows multiple 🖤."""
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"

        sw_dmg = events.SeriousWoundsDamageEvent(attacker, target, 3)

        lines = fmt.format_history([sw_dmg])
        sw_line = [ln for ln in lines if "serious wound" in ln.lower()][0]
        self.assertIn("💔💔💔", sw_line)


class TestFormatterDefeat(unittest.TestCase):
    def test_death_with_emoji(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        event = events.DeathEvent(subject)
        lines = fmt.format_history([event])
        death_line = [ln for ln in lines if "killed" in ln.lower()][0]
        self.assertIn("☠️", death_line)

    def test_unconscious_with_emoji(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        event = events.UnconsciousEvent(subject)
        lines = fmt.format_history([event])
        line = [ln for ln in lines if "unconscious" in ln.lower()][0]
        self.assertIn("💀", line)

    def test_surrender_with_emoji(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        event = events.SurrenderEvent(subject)
        lines = fmt.format_history([event])
        line = [ln for ln in lines if "surrender" in ln.lower()][0]
        self.assertIn("🏳️", line)


class TestFormatterStatusBlock(unittest.TestCase):
    def test_no_duplicate_status_when_no_combat_between(self):
        """Opening status + immediate attack should NOT duplicate the status block."""
        fmt = DetailedEventFormatter()
        status = {
            "Akodo": {"lw": 0, "sw": 0, "max_sw": 4, "vp": 2, "max_vp": 3, "actions": [7], "crippled": False},
            "Bayushi": {"lw": 30, "sw": 1, "max_sw": 4, "vp": 0, "max_vp": 2, "actions": [], "crippled": True},
        }
        phase = events.NewPhaseEvent(0)
        phase._detail_status = status
        action = _make_action("Akodo", "Bayushi", "attack")
        attack = events.TakeAttackActionEvent(action)
        attack._detail_status = status

        lines = fmt.format_history([phase, attack])
        # Should have opening status separator
        self.assertTrue(any("─────" in ln for ln in lines))
        bayushi_status = [ln for ln in lines if "Bayushi" in ln and "Light" in ln]
        # Only 1 status block (opening), not duplicated before the attack
        self.assertEqual(1, len(bayushi_status))


class TestFormatterSkippedEvents(unittest.TestCase):
    def test_attack_succeeded_skipped(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        event = events.AttackSucceededEvent(action)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_attack_failed_skipped(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        event = events.AttackFailedEvent(action)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_wound_check_succeeded_skipped(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "A"
        attacker = MagicMock()
        event = events.WoundCheckSucceededEvent(subject, attacker, 15, 20)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_wound_check_failed_skipped(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "A"
        attacker = MagicMock()
        event = events.WoundCheckFailedEvent(subject, attacker, 15, 10)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_attack_declared_skipped(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        event = events.AttackDeclaredEvent(action)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_parry_declared_skipped(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        event = events.ParryDeclaredEvent(action)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_wound_check_declared_skipped(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "A"
        attacker = MagicMock()
        event = events.WoundCheckDeclaredEvent(subject, attacker, 15)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_your_move_skipped(self):
        fmt = DetailedEventFormatter()
        event = events.YourMoveEvent(MagicMock())
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_hold_action_skipped(self):
        fmt = DetailedEventFormatter()
        event = events.HoldActionEvent(MagicMock())
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_no_action_skipped(self):
        fmt = DetailedEventFormatter()
        event = events.NoActionEvent(MagicMock())
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_end_of_phase_skipped(self):
        fmt = DetailedEventFormatter()
        event = events.EndOfPhaseEvent(0)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_end_of_round_skipped(self):
        fmt = DetailedEventFormatter()
        event = events.EndOfRoundEvent(1)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)


class TestFormatterGracefulDegradation(unittest.TestCase):
    def test_attack_rolled_without_detail_attributes(self):
        """When _detail_* attributes are missing, should still produce output."""
        fmt = DetailedEventFormatter()
        action = _make_action()
        event = events.AttackRolledEvent(action, 29)
        # No _detail_dice, _detail_params, _detail_tn
        lines = fmt.format_history([event])
        self.assertTrue(len(lines) > 0)
        self.assertTrue(any("29" in ln for ln in lines))

    def test_wound_check_without_detail_attributes(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 15, 20, tn=15)
        lines = fmt.format_history([event])
        self.assertTrue(len(lines) > 0)

    def test_parry_rolled_without_detail_attributes(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        action.subject.return_value = subject
        event = events.ParryRolledEvent(action, 18)
        lines = fmt.format_history([event])
        self.assertTrue(len(lines) > 0)

    def test_keep_lw_without_detail_lw_total(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.KeepLightWoundsEvent(subject, attacker, 30)
        # No _detail_lw_total
        lines = fmt.format_history([event])
        self.assertTrue(any("keeping" in ln for ln in lines))

    def test_take_sw_without_detail_lw_total(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.TakeSeriousWoundEvent(subject, attacker, 30)
        # No _detail_lw_total
        lines = fmt.format_history([event])
        self.assertTrue(any("serious wound" in ln.lower() for ln in lines))


class TestFormatterTakeParryAction(unittest.TestCase):
    def test_parry_action_without_rolled_falls_back(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        target = MagicMock()
        target.name.return_value = "Akodo"
        action.subject.return_value = subject
        action.target.return_value = target
        event = events.TakeParryActionEvent(action)
        lines = fmt.format_history([event])
        parry_line = [ln for ln in lines if "parr" in ln.lower()][0]
        self.assertIn("🛡️", parry_line)
        self.assertIn("Bayushi", parry_line)
        self.assertIn("Akodo", parry_line)

    def test_combined_parry_shows_target_and_roll(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        target = MagicMock()
        target.name.return_value = "Mighty Kyō'ude"
        action.subject.return_value = subject
        action.target.return_value = target
        action.is_success.return_value = False

        take_event = events.TakeParryActionEvent(action)
        rolled_event = events.ParryRolledEvent(action, 16)
        rolled_event._detail_dice = [7, 5, 4, 4, 3, 2, 2, 1]
        rolled_event._detail_params = (8, 3, 0)
        rolled_event._detail_tn = 76

        lines = fmt.format_history([take_event, rolled_event])
        # Should produce a single combined line, not two separate lines
        parry_lines = [ln for ln in lines if "parr" in ln.lower()]
        self.assertEqual(1, len(parry_lines))
        line = parry_lines[0]
        self.assertIn("🛡️", line)
        self.assertIn("Kakita", line)
        self.assertIn("Mighty Kyō'ude", line)
        self.assertIn("8k3", line)
        self.assertIn("TN 76", line)
        self.assertIn("FAILED", line)

    def test_combined_parry_succeeded(self):
        fmt = DetailedEventFormatter()
        action = MagicMock()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        target = MagicMock()
        target.name.return_value = "Akodo"
        action.subject.return_value = subject
        action.target.return_value = target
        action.is_success.return_value = True

        take_event = events.TakeParryActionEvent(action)
        rolled_event = events.ParryRolledEvent(action, 30)
        rolled_event._detail_dice = [10, 9, 8, 5, 3]
        rolled_event._detail_params = (5, 3, 0)
        rolled_event._detail_tn = 25

        lines = fmt.format_history([take_event, rolled_event])
        parry_lines = [ln for ln in lines if "parr" in ln.lower()]
        self.assertEqual(1, len(parry_lines))
        self.assertIn("SUCCEEDED", parry_lines[0])
        self.assertIn("Akodo", parry_lines[0])


class TestFormatterPhaseTracking(unittest.TestCase):
    def test_phase_prefix_updates_across_phases(self):
        """Phase number should track correctly across multiple phases."""
        fmt = DetailedEventFormatter()
        status = _make_status()

        p4 = events.NewPhaseEvent(4)
        p4._detail_status = status
        action1 = _make_action("Akodo", "Bayushi", "attack")
        attack1 = events.TakeAttackActionEvent(action1)
        attack1._detail_status = status

        p7 = events.NewPhaseEvent(7)
        p7._detail_status = status
        action2 = _make_action("Bayushi", "Akodo", "attack")
        attack2 = events.TakeAttackActionEvent(action2)
        attack2._detail_status = status

        lines = fmt.format_history([p4, attack1, p7, attack2])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        # First event in each phase gets "Phase N |" prefix
        self.assertIn("Phase 4", attack_lines[0])
        self.assertIn("Phase 7", attack_lines[1])


class TestFormatterHistory(unittest.TestCase):
    def test_format_history_concatenates_rounds(self):
        fmt = DetailedEventFormatter()
        e1 = events.NewRoundEvent(1)
        e2 = events.NewRoundEvent(2)
        lines = fmt.format_history([e1, e2])
        self.assertTrue(any("Round 2" in ln for ln in lines))
        self.assertTrue(any("Round 3" in ln for ln in lines))

    def test_no_phase_header_line_in_history(self):
        """format_history should NOT produce '--- Phase N ---' lines."""
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(4)
        phase._detail_status = _make_status()
        lines = fmt.format_history([phase])
        self.assertFalse(any("--- Phase" in ln for ln in lines))


def _make_contested_iaijutsu_action(
    subject_name="Kakita",
    target_name="Opponent",
    is_challenger=True,
    skill="iaijutsu",
    skill_roll=45,
    opponent_skill_roll=30,
    extra_damage_dice=3,
    skill_roll_params=(10, 6, 5),
):
    """Create a mock ContestedIaijutsuAttackAction."""
    action = MagicMock()
    subject = MagicMock()
    subject.name.return_value = subject_name
    target = MagicMock()
    target.name.return_value = target_name
    action.subject.return_value = subject
    action.target.return_value = target
    action.challenger.return_value = subject if is_challenger else target
    action.skill.return_value = skill
    action.skill_roll.return_value = skill_roll
    action.opponent_skill_roll.return_value = opponent_skill_roll
    action.calculate_extra_damage_dice.return_value = extra_damage_dice
    action.skill_roll_params.return_value = skill_roll_params
    return action


class TestFormatterContestedIaijutsuSkipped(unittest.TestCase):
    def test_declared_event_skipped(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action()
        event = ContestedIaijutsuAttackDeclaredEvent(action)
        lines = fmt.format_history([event])
        self.assertEqual([], lines)

    def test_take_event_skipped(self):
        fmt = DetailedEventFormatter()
        event = TakeContestedIaijutsuAttackAction(
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        lines = fmt.format_history([event])
        self.assertEqual([], lines)


class TestFormatterContestedIaijutsuRolled(unittest.TestCase):
    def test_challenger_won_shows_dice_and_result(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action(
            subject_name="Kakita",
            target_name="Opponent",
            is_challenger=True,
            skill="iaijutsu",
            skill_roll=45,
            opponent_skill_roll=30,
            extra_damage_dice=3,
            skill_roll_params=(10, 6, 5),
        )
        event = ContestedIaijutsuAttackRolledEvent(action)
        event._detail_dice = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        event._detail_params = (10, 6, 5)

        lines = fmt.format_history([event])
        self.assertEqual(1, len(lines))
        line = lines[0]
        self.assertIn("Kakita", line)
        self.assertIn("Contested Iaijutsu", line)
        self.assertIn("5th Dan", line)
        self.assertIn("10k6", line)
        self.assertIn("WON", line)
        self.assertIn("3 extra damage dice", line)

    def test_challenger_lost_shows_result(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action(
            subject_name="Kakita",
            is_challenger=True,
            skill_roll=20,
            opponent_skill_roll=35,
            extra_damage_dice=-3,
        )
        event = ContestedIaijutsuAttackRolledEvent(action)
        event._detail_dice = [8, 5, 4, 3, 2, 1]
        event._detail_params = (10, 6, 0)

        lines = fmt.format_history([event])
        line = lines[0]
        self.assertIn("LOST", line)

    def test_defender_line_shows_skill_name(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action(
            subject_name="Opponent",
            target_name="Kakita",
            is_challenger=False,
            skill="attack",
            skill_roll=30,
            opponent_skill_roll=45,
            extra_damage_dice=-3,
        )
        event = ContestedIaijutsuAttackRolledEvent(action)
        event._detail_dice = [9, 7, 5, 3, 2, 1]
        event._detail_params = (7, 3, 0)

        lines = fmt.format_history([event])
        line = lines[0]
        self.assertIn("Opponent", line)
        self.assertIn("attack", line)
        self.assertIn("LOST", line)

    def test_totals_consistent_across_challenger_and_defender(self):
        """Both lines should show the same comparison values.

        The challenger's 'vs X' should match what the defender's line shows
        as their total, and vice versa.
        """
        fmt = DetailedEventFormatter()
        # Kakita (challenger): dice top 6 = 41, skill_roll = 46 (+5 from free raise)
        kakita_action = _make_contested_iaijutsu_action(
            subject_name="Kakita",
            target_name="Opponent",
            is_challenger=True,
            skill="iaijutsu",
            skill_roll=46,
            opponent_skill_roll=40,
            extra_damage_dice=1,
            skill_roll_params=(10, 6, 5),
        )
        kakita_event = ContestedIaijutsuAttackRolledEvent(kakita_action)
        kakita_event._detail_dice = [14, 7, 6, 6, 4, 4, 4, 3, 1, 1]
        kakita_event._detail_params = (10, 6, 5)

        # Opponent (defender): dice top 5 = 40, skill_roll = 40 (no char modifier)
        # action.skill_roll_params returns -5 but that was never applied to roll
        opponent_action = _make_contested_iaijutsu_action(
            subject_name="Opponent",
            target_name="Kakita",
            is_challenger=False,
            skill="attack",
            skill_roll=40,
            opponent_skill_roll=46,
            extra_damage_dice=-1,
            skill_roll_params=(10, 5, -5),
        )
        opponent_event = ContestedIaijutsuAttackRolledEvent(opponent_action)
        opponent_event._detail_dice = [9, 9, 8, 7, 7, 6, 3, 3, 2, 2]
        opponent_event._detail_params = (10, 5, -5)

        kakita_lines = fmt.format_history([kakita_event])
        fmt2 = DetailedEventFormatter()
        opponent_lines = fmt2.format_history([opponent_event])

        kakita_line = kakita_lines[0]
        opponent_line = opponent_lines[0]

        # Kakita's total should be 46, shown as "= 46" or just "46"
        self.assertIn("46", kakita_line)
        # Kakita's "vs" should be 40 (opponent's actual roll)
        self.assertIn("vs 40", kakita_line)
        # Opponent's total should be 40 (NOT 35)
        self.assertIn("vs 46", opponent_line)
        # The opponent's displayed total should match what Kakita sees as "vs 40"
        # i.e., the "→ 40" part (kept_sum = 40, no effective modifier shown)
        self.assertIn("→ 40 vs", opponent_line)

    def test_without_detail_attributes_graceful(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action()
        event = ContestedIaijutsuAttackRolledEvent(action)
        # No _detail_dice or _detail_params
        lines = fmt.format_history([event])
        self.assertTrue(len(lines) > 0)

    def test_tied_shows_tied(self):
        fmt = DetailedEventFormatter()
        action = _make_contested_iaijutsu_action(
            skill_roll=30,
            opponent_skill_roll=30,
            extra_damage_dice=0,
            is_challenger=True,
        )
        event = ContestedIaijutsuAttackRolledEvent(action)
        event._detail_dice = [8, 7, 6, 5, 4, 3]
        event._detail_params = (10, 6, 0)

        lines = fmt.format_history([event])
        line = lines[0]
        self.assertIn("TIED", line)


class TestFormatterCombinedAttack(unittest.TestCase):
    def test_combined_attack_hit(self):
        """Single combined line with 'attacks' and 'HIT'."""
        fmt = DetailedEventFormatter()
        action = _make_action("Kakita", "Target", "iaijutsu")
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2

        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 73)
        rolled._detail_dice = [18, 16, 14, 9, 8, 8, 7, 6, 4, 2]
        rolled._detail_params = (10, 6, 0)
        rolled._detail_tn = 30

        lines = fmt.format_history([take, rolled])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(1, len(attack_lines))
        line = attack_lines[0]
        self.assertIn("attacks Target", line)
        self.assertIn("HIT", line)
        self.assertIn("10k6", line)
        self.assertIn("TN 30", line)
        # No separate AttackRolledEvent line
        self.assertFalse(any("Attack:" in ln for ln in lines))

    def test_combined_attack_miss(self):
        """Single combined line with 'attacks' and 'MISS'."""
        fmt = DetailedEventFormatter()
        action = _make_action("Kakita", "Target", "attack")
        action.is_hit.return_value = False
        action.parried.return_value = False

        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 16)
        rolled._detail_dice = [9, 4, 3, 2, 1, 1, 1]
        rolled._detail_params = (7, 3, 0)
        rolled._detail_tn = 20

        lines = fmt.format_history([take, rolled])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(1, len(attack_lines))
        line = attack_lines[0]
        self.assertIn("MISS", line)
        self.assertIn("TN 20", line)

    def test_combined_attack_with_vp_between(self):
        """VP between take-attack and rolled is merged onto the combined attack line."""
        fmt = DetailedEventFormatter()
        action = _make_action("Kakita", "Target", "attack")
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 0

        subject = action.subject()

        take = events.TakeAttackActionEvent(action)
        vp = events.SpendVoidPointsEvent(subject, "attack", 1)
        rolled = events.AttackRolledEvent(action, 30)
        rolled._detail_dice = [10, 9, 8, 3]
        rolled._detail_params = (4, 3, 0)
        rolled._detail_tn = 25

        lines = fmt.format_history([take, vp, rolled])
        # No separate VP line — merged onto attack line
        standalone_vp = [ln for ln in lines if "VP" in ln and "attacks" not in ln]
        self.assertEqual(0, len(standalone_vp))
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(1, len(attack_lines))
        self.assertIn("HIT", attack_lines[0])
        # VP info is on the same line
        self.assertIn("⬛", attack_lines[0])
        self.assertIn("spends 1 VP on attack", attack_lines[0])

    def test_attack_action_without_rolled_falls_back(self):
        """Graceful fallback when no AttackRolledEvent follows."""
        fmt = DetailedEventFormatter()
        action = _make_action("Kakita", "Target", "attack")

        take = events.TakeAttackActionEvent(action)

        lines = fmt.format_history([take])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(1, len(attack_lines))
        self.assertIn("⚔️", attack_lines[0])


class TestFormatterCombinedWoundCheckSW(unittest.TestCase):
    def test_combined_wc_passed_voluntary_sw(self):
        """Single line with 'PASSED' and 'chooses to take'."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 28, tn=28)
        wc._detail_dice = [9, 7, 6, 6, 3]
        wc._detail_params = (5, 4)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 28)

        lines = fmt.format_history([wc, take_sw])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("PASSED", line)
        self.assertIn("chooses to take", line)

    def test_combined_wc_failed_forced_sw(self):
        """Single line with 'FAILED' and 'takes'."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        wc._detail_dice = [5, 4, 3, 2]
        wc._detail_params = (4, 3)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 1)

        lines = fmt.format_history([wc, take_sw, sw_dmg])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("FAILED", line)
        self.assertIn("takes 1 serious wound", line)
        self.assertNotIn("chooses", line)

    def test_combined_wc_failed_multiple_sw(self):
        """Multiple serious wounds show correct count and repeated hearts."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        wc = events.WoundCheckRolledEvent(subject, attacker, 43, 29, tn=43)
        wc._detail_dice = [9, 9, 6, 5, 3]
        wc._detail_params = (5, 4)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 43)
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 2)

        lines = fmt.format_history([wc, take_sw, sw_dmg])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("FAILED", line)
        self.assertIn("takes 2 serious wounds", line)
        self.assertIn("💔💔", line)
        # Should be exactly 2 hearts, not 3
        self.assertNotIn("💔💔💔", line)

    def test_wc_passed_keep_lw_combined(self):
        """When KeepLightWoundsEvent follows, wound check and keep LW are combined."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 28, tn=28)
        wc._detail_dice = [9, 7, 6, 6, 3]
        wc._detail_params = (5, 4)

        keep_lw = events.KeepLightWoundsEvent(subject, attacker, 28)
        keep_lw._detail_lw_total = 28

        lines = fmt.format_history([wc, keep_lw])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        # Combined onto one line
        self.assertIn("PASSED", line)
        self.assertIn("keeping 28 light wounds", line)
        # Only one 🖤, at the start — no separate keep line
        self.assertIn("🖤", line)
        self.assertFalse(any("keeping" in ln for ln in lines if ln != line))

    def test_combined_preserves_sw_damage_dedup(self):
        """SeriousWoundsDamageEvent still suppressed after combined WC+SW."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        wc._detail_dice = [5, 4, 3, 2]
        wc._detail_params = (4, 3)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 1)

        lines = fmt.format_history([wc, take_sw, sw_dmg])
        sw_lines = [ln for ln in lines if "serious wound" in ln.lower()]
        # Only the combined WC+SW line, not the SeriousWoundsDamageEvent
        self.assertEqual(1, len(sw_lines))


class TestFormatterCombinedVP(unittest.TestCase):
    def test_vp_combined_with_attack_hit(self):
        """VP on attack merged onto combined attack HIT line."""
        fmt = DetailedEventFormatter()
        action = _make_action("Kakita", "Target", "attack")
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 1

        subject = action.subject()

        take = events.TakeAttackActionEvent(action)
        vp = events.SpendVoidPointsEvent(subject, "attack", 1)
        rolled = events.AttackRolledEvent(action, 35)
        rolled._detail_dice = [10, 9, 8, 5, 3]
        rolled._detail_params = (5, 3, 0)
        rolled._detail_tn = 25

        lines = fmt.format_history([take, vp, rolled])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(1, len(attack_lines))
        line = attack_lines[0]
        self.assertIn("⬛ spends 1 VP on attack →", line)
        self.assertIn("⚔️", line)
        self.assertIn("HIT", line)
        # No separate VP line
        standalone_vp = [ln for ln in lines if "VP" in ln and "attacks" not in ln]
        self.assertEqual(0, len(standalone_vp))

    def test_vp_combined_with_wound_check_failed(self):
        """VP on wound check merged onto standalone WC FAILED line."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        vp = events.SpendVoidPointsEvent(subject, "wound check", 2)
        wc = events.WoundCheckRolledEvent(subject, attacker, 43, 37, tn=43)
        wc._detail_dice = [10, 9, 8, 7, 6, 3]
        wc._detail_params = (6, 5)

        lines = fmt.format_history([vp, wc])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("⬛⬛ spends 2 VP on wound check →", line)
        self.assertIn("FAILED", line)
        # No separate VP line
        standalone_vp = [ln for ln in lines if "VP" in ln and "Wound Check" not in ln]
        self.assertEqual(0, len(standalone_vp))

    def test_vp_combined_with_wound_check_and_keep_lw(self):
        """VP + WC + KeepLW all on one line."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        vp = events.SpendVoidPointsEvent(subject, "wound check", 1)
        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 30, tn=28)
        wc._detail_dice = [9, 8, 7, 6, 3]
        wc._detail_params = (5, 4)
        keep_lw = events.KeepLightWoundsEvent(subject, attacker, 28)
        keep_lw._detail_lw_total = 28

        lines = fmt.format_history([vp, wc, keep_lw])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("⬛ spends 1 VP on wound check →", line)
        self.assertIn("PASSED", line)
        self.assertIn("keeping 28 light wounds", line)
        # No separate VP or keep line
        standalone_vp = [ln for ln in lines if "VP" in ln and "Wound Check" not in ln]
        self.assertEqual(0, len(standalone_vp))
        standalone_keep = [ln for ln in lines if "keeping" in ln and "Wound Check" not in ln]
        self.assertEqual(0, len(standalone_keep))

    def test_vp_combined_with_wound_check_and_take_sw(self):
        """VP + WC + TakeSW all on one line."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        vp = events.SpendVoidPointsEvent(subject, "wound check", 1)
        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        wc._detail_dice = [5, 4, 3, 2]
        wc._detail_params = (4, 3)
        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)

        lines = fmt.format_history([vp, wc, take_sw])
        wc_lines = [ln for ln in lines if "Wound Check:" in ln]
        self.assertEqual(1, len(wc_lines))
        line = wc_lines[0]
        self.assertIn("⬛ spends 1 VP on wound check →", line)
        self.assertIn("FAILED", line)
        self.assertIn("takes 1 serious wound", line)
        # No separate VP line
        standalone_vp = [ln for ln in lines if "VP" in ln and "Wound Check" not in ln]
        self.assertEqual(0, len(standalone_vp))


class TestFormatDice(unittest.TestCase):
    def test_kept_dice_are_bold(self):
        """First `kept` dice should be wrapped in ** for bold."""
        result = _format_dice([9, 8, 7, 6, 4, 3, 2], 3)
        self.assertIn("**9**", result)
        self.assertIn("**8**", result)
        self.assertIn("**7**", result)

    def test_dropped_dice_are_strikethrough(self):
        """Remaining dice after `kept` should be wrapped in ~~ for strikethrough."""
        result = _format_dice([9, 8, 7, 6, 4, 3, 2], 3)
        self.assertIn("~~6~~", result)
        self.assertIn("~~4~~", result)
        self.assertIn("~~3~~", result)
        self.assertIn("~~2~~", result)

    def test_format_dice_full_string(self):
        """Full formatted string should have brackets and commas."""
        result = _format_dice([19, 18, 8], 2)
        self.assertEqual("[**19**, **18**, ~~8~~]", result)

    def test_all_kept(self):
        """When all dice are kept, none should be strikethrough."""
        result = _format_dice([5, 3], 2)
        self.assertEqual("[**5**, **3**]", result)

    def test_empty_dice(self):
        result = _format_dice([], 0)
        self.assertEqual("[]", result)

    def test_attack_line_contains_bold_and_strikethrough_dice(self):
        """End-to-end: attack output should use formatted dice."""
        fmt = DetailedEventFormatter()
        action = _make_action()
        action.is_hit.return_value = True
        action.parried.return_value = False
        action.calculate_extra_damage_dice.return_value = 2
        event = events.AttackRolledEvent(action, 29)
        event._detail_dice = [9, 8, 7, 6, 4, 3, 2]
        event._detail_params = (7, 3, 5)
        event._detail_tn = 15

        lines = fmt.format_history([event])
        line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("**9**", line)
        self.assertIn("~~6~~", line)

    def test_damage_line_contains_formatted_dice(self):
        """End-to-end: damage output should use formatted dice."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(subject, target, 15)
        event._detail_dice = [8, 7, 5, 4, 3, 1]
        event._detail_params = (6, 2)
        event._detail_lw_after = 30

        lines = fmt.format_history([event])
        line = [ln for ln in lines if "Damage:" in ln][0]
        self.assertIn("**8**", line)
        self.assertIn("**7**", line)
        self.assertIn("~~5~~", line)

    def test_wound_check_line_contains_formatted_dice(self):
        """End-to-end: wound check output should use formatted dice."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 35, tn=30)
        event._detail_dice = [9, 6, 5, 2]
        event._detail_params = (4, 3)

        lines = fmt.format_history([event])
        line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("**9**", line)
        self.assertIn("**6**", line)
        self.assertIn("**5**", line)
        self.assertIn("~~2~~", line)

    def test_initiative_line_contains_formatted_dice(self):
        """End-to-end: initiative output should use formatted dice."""
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_initiative = {
            "Akodo": {
                "all_dice": [7, 4, 2],
                "actions": [4, 7],
                "roll_params": (3, 2),
            },
        }
        phase._detail_status = {
            "Akodo": {"lw": 0, "sw": 0, "max_sw": 4, "vp": 3, "max_vp": 3, "actions": [4, 7], "crippled": False},
        }
        lines = fmt.format_history([phase])
        init_line = [ln for ln in lines if "Akodo" in ln and "3k2" in ln][0]
        self.assertIn("**7**", init_line)
        self.assertIn("**4**", init_line)
        self.assertIn("~~2~~", init_line)


class TestPhaseShownAfterStatusBlock(unittest.TestCase):
    def test_phase_reappears_after_mid_phase_status_block(self):
        """Phase N should reappear on the first line after a status separator."""
        fmt = DetailedEventFormatter()
        status = _make_status("Kakita", "Kyoude")

        phase = events.NewPhaseEvent(4)
        phase._detail_status = status

        # First exchange in this phase
        action1 = _make_action("Kakita", "Kyoude", "iaijutsu")
        attack1 = events.TakeAttackActionEvent(action1)
        attack1._detail_status = status

        # Second exchange in same phase — has status block too
        action2 = _make_action("Kyoude", "Kakita", "attack")
        attack2 = events.TakeAttackActionEvent(action2)
        attack2._detail_status = status

        lines = fmt.format_history([phase, attack1, attack2])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(2, len(attack_lines))
        # Both attack lines should show "Phase 4" since each follows a status block
        self.assertIn("Phase 4", attack_lines[0])
        self.assertIn("Phase 4", attack_lines[1])


class TestPhaseShownOnce(unittest.TestCase):
    def test_phase_prefix_on_first_line_only(self):
        """Phase N should appear on the first line of a phase, not subsequent lines."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        phase = events.NewPhaseEvent(3)
        # No _detail_status so no opening status block
        action = _make_action("Kakita", "Akodo", "attack")
        attack = events.TakeAttackActionEvent(action)
        # No _detail_status on attack either, so no status block before it

        lw_event = events.LightWoundsDamageEvent(subject, attacker, 10)
        lw_event._detail_dice = [6, 5, 3]
        lw_event._detail_params = (3, 2)

        lines = fmt.format_history([phase, attack, lw_event])
        content_lines = [ln for ln in lines if ln.strip() and "─" not in ln]
        # First content line should have "Phase 3"
        self.assertTrue(any("Phase 3" in ln for ln in content_lines))
        # Only one line should contain "Phase 3"
        phase_lines = [ln for ln in content_lines if "Phase 3" in ln]
        self.assertEqual(1, len(phase_lines), f"Expected Phase 3 once, got: {phase_lines}")

    def test_phase_resets_across_phases(self):
        """Each new phase should show 'Phase N' on its first line."""
        fmt = DetailedEventFormatter()

        p3 = events.NewPhaseEvent(3)
        action1 = _make_action("Kakita", "Akodo", "attack")
        attack1 = events.TakeAttackActionEvent(action1)

        p5 = events.NewPhaseEvent(5)
        action2 = _make_action("Akodo", "Kakita", "attack")
        attack2 = events.TakeAttackActionEvent(action2)

        lines = fmt.format_history([p3, attack1, p5, attack2])
        attack_lines = [ln for ln in lines if "attacks" in ln]
        self.assertEqual(2, len(attack_lines))
        self.assertIn("Phase 3", attack_lines[0])
        self.assertIn("Phase 5", attack_lines[1])


class TestWoundCheckOutcomeEmoji(unittest.TestCase):
    def test_combined_wc_sw_uses_broken_heart(self):
        """Combined WC+SW line should use 💔 (took serious wound)."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 12, tn=30)
        wc._detail_dice = [5, 4, 3, 2]
        wc._detail_params = (4, 3)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 30)
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 1)

        lines = fmt.format_history([wc, take_sw, sw_dmg])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("💔", wc_line)

    def test_combined_wc_sw_passed_also_uses_broken_heart(self):
        """Combined WC+SW that PASSED should still use 💔 (chose to take SW)."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"

        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 28, tn=28)
        wc._detail_dice = [9, 7, 6, 6, 3]
        wc._detail_params = (5, 4)

        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 28)
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, subject, 1)

        lines = fmt.format_history([wc, take_sw, sw_dmg])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("💔", wc_line)

    def test_combined_wc_keep_lw_uses_black_heart(self):
        """Combined WC+KeepLW line should use 🖤 (kept light wounds)."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Kakita"
        attacker = MagicMock()

        wc = events.WoundCheckRolledEvent(subject, attacker, 28, 28, tn=28)
        wc._detail_dice = [9, 7, 6, 6, 3]
        wc._detail_params = (5, 4)

        keep_lw = events.KeepLightWoundsEvent(subject, attacker, 28)
        keep_lw._detail_lw_total = 28

        lines = fmt.format_history([wc, keep_lw])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("🖤", wc_line)
        self.assertIn("keeping", wc_line)


class TestSingularPlural(unittest.TestCase):
    def test_one_serious_wound_singular(self):
        """'1 serious wound' should be singular."""
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"

        sw_dmg = events.SeriousWoundsDamageEvent(attacker, target, 1)

        lines = fmt.format_history([sw_dmg])
        sw_line = [ln for ln in lines if "serious" in ln.lower()][0]
        self.assertIn("1 serious wound", sw_line)
        self.assertNotIn("wounds", sw_line)

    def test_multiple_serious_wounds_plural(self):
        """'2 serious wounds' should be plural."""
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"

        sw_dmg = events.SeriousWoundsDamageEvent(attacker, target, 2)

        lines = fmt.format_history([sw_dmg])
        sw_line = [ln for ln in lines if "serious" in ln.lower()][0]
        self.assertIn("2 serious wounds", sw_line)


if __name__ == "__main__":
    unittest.main()
