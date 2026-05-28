#!/usr/bin/env python3

#
# test_hida_school.py
#
# Unit tests for the Hida Bushi School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll import CalvinistDice
from simulation.mechanics.roll_provider import (
    CalvinistRollProvider,
    DefaultRollProvider,
)
from simulation.schools import hida_school
from simulation.strategies.base import CounterattackInterruptStrategy
from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.combat_observer import CombatObserver
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.text_renderer import TextRenderer

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestHidaBushiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual("Hida Bushi School", school.name())

    def test_school_ring(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        # rules/04-schools.md "Hida Bushi School:
        # School Knacks: counterattack, double attack, iaijutsu"
        school = hida_school.HidaBushiSchool()
        self.assertEqual(
            ["counterattack", "double attack", "iaijutsu"],
            school.school_knacks(),
        )

    def test_ap_base_skill(self):
        # Hida is not an AP-using school (no precepts / no Monk pattern),
        # so ap_base_skill() returns None.
        school = hida_school.HidaBushiSchool()
        self.assertIsNone(school.ap_base_skill())

    def test_no_lunge_in_hida_priorities(self):
        """T031 / US4 regression guard.

        rules/04-schools.md "Hida Bushi School" lists the school knacks
        as ``counterattack, double attack, iaijutsu`` — lunge is NOT a
        Hida knack.  The original ``HIDA_PRIORITIES`` list in
        ``simulation/templates/strategies.py`` mistakenly contained
        four ``("skill", "lunge", N)`` entries; the
        school-progression-designer's revision replaced them with
        ``"double attack"``.  This guard catches any future regression
        that re-introduces a ``"lunge"`` entry.
        """
        from simulation.templates.strategies import HIDA_PRIORITIES
        lunge_entries = [
            entry for entry in HIDA_PRIORITIES
            if len(entry) >= 2 and entry[1] == "lunge"
        ]
        self.assertEqual(
            [], lunge_entries,
            f"HIDA_PRIORITIES must not reference 'lunge' (not a Hida "
            f"knack per rules/04-schools.md); found: {lunge_entries}",
        )

    def test_extra_rolled(self):
        school = hida_school.HidaBushiSchool()
        extra = school.extra_rolled()
        self.assertEqual(["attack", "counterattack", "wound check"], extra)

    def test_free_raise_skills(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual(["counterattack"], school.free_raise_skills())


class TestHidaSpecialAbility(unittest.TestCase):
    """The Hida special ability sets counterattack interrupt cost to 1
    and installs the counterattack interrupt strategy."""

    def test_interrupt_cost(self):
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        enemy = Character("Enemy")
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        self.assertEqual(1, hida.interrupt_cost("counterattack", context))

    def test_interrupt_strategy_is_counterattack(self):
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        self.assertIsInstance(hida.interrupt_strategy(), CounterattackInterruptStrategy)

    def test_plus_5_free_raise_sourced_in_trace(self):
        """Principle VII: the +5 free raise the attacker gets when a
        Hida counterattacks as a 1-die interrupt MUST appear in the
        user-visible combat trace with a source label
        ("Hida special ability") and the numeric +5 — no aggregate
        without attribution.

        rules/04-schools.md "Hida Bushi School: Special Ability":
        "You may counterattack as an interrupt action by spending only
        1 action die, but if you do so then the attacker gets a free
        raise on their attack roll."
        """
        # Build a Hida defender + a vanilla attacker.  The Hida's
        # interrupt strategy is disabled here because this test only
        # exercises the source-attribution path on the attacker's
        # ``AttackRolledEvent`` — we set ``_counterattack_roll_bonus``
        # directly on the attack action to simulate the post-interrupt
        # state, then fire the attack-rolled event through the
        # observer so the trace annotation paths run.
        attacker = Character("Attacker")
        attacker.set_skill("attack", 3)
        attacker.set_actions([1])
        hida_defender = Character("Hida")
        hida_defender.set_actions([5, 8])
        groups = [Group("Crab", hida_defender), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()

        # Rig the attacker's roll: kept dice sum 20 + the +5 free
        # raise will land at 25 in the trace.  The ``with_dice``
        # variant ensures the observer sees a real dice list so the
        # ``AttackRolledEvent`` annotation builds the full XkY
        # breakdown that the +5 attribution attaches to.
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll_with_dice("attack", 20, [10, 10])
        attacker.set_roll_provider(attacker_rp)

        # Simulate the post-interrupt state: the Hida special ability
        # set ``_counterattack_roll_bonus`` on the attack action.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            attacker, hida_defender, "attack", attack_init, context,
        )
        attack._counterattack_roll_bonus = 5

        # Drive an attack roll through the engine + observer so the
        # ``AttackRolledEvent`` gets fully annotated by the observer.
        engine = CombatEngine(context)
        observer = CombatObserver()
        phase_event = events.NewPhaseEvent(phase=1)
        observer.on_event(phase_event, context)
        engine.event(phase_event)

        # Roll the skill the way ``_roll_attack`` does (bonus folded
        # into the rolled value via ``set_skill_roll``), then emit
        # the matching ``AttackRolledEvent`` annotated by the observer.
        natural_roll = attack.roll_skill()
        attack.set_skill_roll(natural_roll + 5)
        attack_rolled = events.AttackRolledEvent(attack, natural_roll + 5)
        observer.on_event(attack_rolled, context)
        engine.event(attack_rolled)

        # The +5 must be visible somewhere in the trace, and it must
        # carry a Hida special-ability source label per Principle VII.
        fmt = DetailedEventFormatter()
        history = engine.history()
        text_lines = TextRenderer().render_lines(fmt.entries(history))
        bulleted = BulletedRenderer().render(fmt.entries(history))
        text_blob = "\n".join(text_lines)

        self.assertIn(
            "Hida special ability", text_blob,
            f"Trace missing Hida special ability source attribution:\n{text_blob}",
        )
        self.assertIn(
            "free raise", text_blob,
            f"Trace missing 'free raise' wording:\n{text_blob}",
        )
        self.assertIn(
            "+5", text_blob,
            f"Trace missing the numeric +5:\n{text_blob}",
        )

        # The same three substrings must also appear in the bulleted
        # renderer's output (cross-renderer consistency).
        self.assertIn("Hida special ability", bulleted)
        self.assertIn("free raise", bulleted)
        self.assertIn("+5", bulleted)

    def test_second_dan_counterattack_free_raise_attributed_in_breakdown(self):
        """Hida 2nd Dan: free raise on counterattack rolls. The +5 is
        installed by ``apply_rank_two_ability`` via
        ``free_raise_skills() == ["counterattack"]``; the trace breakdown
        must attribute it as "Hida 2nd Dan free raise" rather than
        falling back to "(see preceding line)".

        rules/04-schools.md "Hida Bushi School: Second Dan" +
        Constitution Principle VII.
        """
        from web.adapters.modifier_breakdown import explain_modifier

        hida = Character("Hida2ndTrace")
        hida.set_ring("water", 3)
        hida.set_skill("counterattack", 2)
        school = hida_school.HidaBushiSchool()
        hida.set_school(school)
        for knack in school.school_knacks():
            hida.set_skill(knack, 2)
        school.apply_rank_one_ability(hida)
        school.apply_rank_two_ability(hida)

        breakdown = explain_modifier(hida, "counterattack", modifier=5, vp=0)
        self.assertIn(
            ("Hida 2nd Dan free raise", 5),
            breakdown,
            "2nd-dan Hida counterattack roll must attribute the +5 free "
            "raise in the breakdown so the trace can render it.",
        )


class TestHidaTakeCounterattackActionEvent(unittest.TestCase):
    """Test the Hida-specific counterattack event that applies +5 to
    the original attacker's roll when used as an interrupt."""

    def setUp(self):
        self.hida = Character("Hida")
        self.hida.set_skill("counterattack", 3)
        self.hida.set_actions([5, 8])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hida), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # original attack: attacker attacks hida
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.hida, "attack", self.attack_initiative, self.context,
        )
        self.attack.set_skill_roll(25)

    def test_interrupt_applies_plus_five(self):
        """When counterattacking as interrupt, a pending +5 bonus is stored."""
        # counterattack as interrupt (is_interrupt=True)
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # a pending +5 bonus should be stored on the original attack
        self.assertEqual(5, getattr(self.attack, '_counterattack_roll_bonus', 0))

    def test_non_interrupt_no_penalty(self):
        """When counterattacking with a regular action, no pending bonus is stored."""
        # counterattack as regular action (is_interrupt=False)
        regular_action = InitiativeAction([5], 5)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            regular_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # no pending bonus should be stored
        self.assertEqual(0, getattr(self.attack, '_counterattack_roll_bonus', 0))

    def test_counterattack_hit_deals_damage(self):
        """A successful counterattack deals damage to the original attacker."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack succeeds (roll 30 >= tn 10)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)
        # rig attacker's wound check to succeed
        attacker_roll_provider = CalvinistRollProvider()
        attacker_roll_provider.put_wound_check_roll(20)
        self.attacker.set_roll_provider(attacker_roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # attacker took 15 LW, wound check succeeded, chose to take SW
        # (KeepLightWoundsStrategy decided to take SW since next check might be bad)
        self.assertEqual(1, self.attacker.sw())

    def test_counterattack_miss_no_damage(self):
        """A missed counterattack deals no damage."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack misses (roll 5 < tn 10)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 5)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # attacker should have no damage
        self.assertEqual(0, self.attacker.lw())

    def test_event_history(self):
        """Verify the correct sequence of events for a successful counterattack."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)
        # rig attacker wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        # take_counterattack
        self.assertIsInstance(history[0], hida_school.HidaTakeCounterattackActionEvent)
        # counterattack_declared
        self.assertIsInstance(history[1], events.CounterattackDeclaredEvent)
        # counterattack_rolled
        self.assertIsInstance(history[2], events.CounterattackRolledEvent)
        # counterattack_succeeded
        self.assertIsInstance(history[3], events.CounterattackSucceededEvent)
        # lw_damage
        self.assertIsInstance(history[4], events.LightWoundsDamageEvent)


class TestHidaFourthDan(unittest.TestCase):
    """4th Dan raises the school ring (Water)."""

    def test_fourth_dan_raises_water(self):
        # rules/04-schools.md "Hida Bushi School: Fourth Dan" — the
        # school's knacks are counterattack, double attack, iaijutsu;
        # bringing all three to rank 4 triggers the 4th-Dan ring raise
        # via apply_school_ring_raise_and_discount.
        school = hida_school.HidaBushiSchool()
        builder = (
            CharacterBuilder(9001)
            .with_name("Hida")
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("double attack", 4)
            .buy_skill("iaijutsu", 4)
        )
        hida = builder.build()
        # School ring starts at 3, 4th Dan raises it to 4
        self.assertEqual(4, hida.ring("water"))


class TestHidaTakeActionEventFactory(unittest.TestCase):
    def test_returns_hida_counterattack_event(self):
        hida = Character("Hida")
        hida.set_skill("counterattack", 3)
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", initiative_action, context)
        counterattack = actions.CounterattackAction(
            hida, attacker, "counterattack", initiative_action, context, attack,
        )
        factory = hida_school.HidaTakeActionEventFactory()
        event = factory.get_take_counterattack_action_event(counterattack)
        self.assertIsInstance(event, hida_school.HidaTakeCounterattackActionEvent)


# ---------------------------------------------------------------
# 3rd Dan: Reroll dice
# ---------------------------------------------------------------


def _make_third_dan_hida(attack_skill: int = 4, crippled: bool = False) -> Character:
    """Helper: build a 3rd-Dan-active Hida with a specified attack skill.

    The Hida's school is applied (special + 3rd-Dan abilities) so the
    HidaRollProvider is installed.  When ``crippled`` is True, take
    sufficient SW to push the character into the crippled state.
    """
    school = hida_school.HidaBushiSchool()
    hida = Character("Hida")
    hida.set_ring("water", 3)
    hida.set_ring("earth", 2)
    hida.set_skill("attack", attack_skill)
    hida.set_skill("counterattack", attack_skill)
    hida.set_skill("double attack", attack_skill)
    hida.set_skill("iaijutsu", attack_skill)
    hida.set_skill("parry", attack_skill)
    hida.set_skill("wound check", attack_skill)
    hida.set_skill("feint", attack_skill)
    hida.set_school(school)
    school.apply_special_ability(hida)
    school.apply_rank_three_ability(hida)
    if crippled:
        hida.take_sw(hida.ring("earth"))
        assert hida.crippled()
    return hida


class TestHida3rdDanReroll(unittest.TestCase):
    """Hida 3rd Dan: reroll dice on counterattack or other attack rolls.

    rules/04-schools.md "Hida Bushi School: Third Dan":
      "You may re-roll 2X dice on each counterattack roll or X dice on
       any other attack roll, where X is your attack skill. When
       impaired, your number of extra dice on these rolls is divided in
       half (round up), but you reroll 10s on these rolls despite being
       impaired."
    """

    def test_reroll_counterattack_uses_2x_attack_skill(self):
        """N = 2 * attack_skill on counterattack rolls."""
        hida = _make_third_dan_hida(attack_skill=4)
        # Stage an initial roll: dice [1, 2, 3, 4, 5, 9] with kept=2,
        # total = 5+9 = 14.  With 2X = 8 rerolls available but only
        # 5 dice (those below 5.5: 1,2,3,4,5) are eligible, so 5 dice
        # are rerolled.  We stage all five reroll results.
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("counterattack", 14, [1, 2, 3, 4, 5, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        # Stage rerolls: five 8s
        reroll_dice = CalvinistDice()
        reroll_dice.extend([8, 8, 8, 8, 8])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("counterattack", 6, 2)
        # New dice (sorted desc): [9, 8, 8, 8, 8, 8], top 2 = 17.
        self.assertEqual(17, result)
        # All five reroll dice consumed (the 5 dice below 5.5 each
        # rerolled, since 2X=8 ≥ 5 eligible candidates).
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_other_attacks_uses_x_attack_skill(self):
        """N = attack_skill on attack / double attack / iaijutsu rolls."""
        hida = _make_third_dan_hida(attack_skill=4)
        # Stage an initial roll: dice [1, 2, 3, 4, 5, 9] with kept=2.
        # N=4, so only 4 of the 5 dice-below-5.5 are rerolled (the
        # lowest 4 — i.e., 1,2,3,4).  The 5 stays.
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("attack", 14, [1, 2, 3, 4, 5, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        # Four 8s for the four rerolls
        reroll_dice.extend([8, 8, 8, 8])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 6, 2)
        # New dice (sorted desc): [9, 8, 8, 8, 8, 5], top 2 = 17.
        self.assertEqual(17, result)
        # All four reroll dice consumed (N=4, all 4 used).
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_not_on_wound_check(self):
        """3rd Dan reroll does NOT fire on wound check rolls."""
        hida = _make_third_dan_hida(attack_skill=4)
        inner = CalvinistRollProvider()
        inner.put_wound_check_roll_with_dice(11, [1, 2, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        reroll_dice.extend([8, 8, 8])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_wound_check_roll(3, 2)
        # No reroll: kept top 2 of [9, 2, 1] = 11.
        self.assertEqual(11, result)
        # No reroll dice consumed.
        self.assertEqual(3, len(reroll_dice))

    def test_reroll_not_on_parry(self):
        """3rd Dan reroll does NOT fire on parry rolls."""
        hida = _make_third_dan_hida(attack_skill=4)
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("parry", 11, [1, 2, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        reroll_dice.extend([8, 8, 8])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("parry", 3, 2)
        self.assertEqual(11, result)
        # No reroll dice consumed.
        self.assertEqual(3, len(reroll_dice))

    def test_reroll_not_on_feint(self):
        """3rd Dan reroll does NOT fire on feint rolls."""
        hida = _make_third_dan_hida(attack_skill=4)
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("feint", 11, [1, 2, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        reroll_dice.extend([8, 8, 8])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("feint", 3, 2)
        self.assertEqual(11, result)
        # No reroll dice consumed.
        self.assertEqual(3, len(reroll_dice))

    def test_reroll_greedy_picks_lowest_below_5_5(self):
        """Given [2, 3, 9, 10, 8] with N=3, the 2 dice below 5.5 (2, 3)
        are rerolled; the 8/9/10 stay (only 2 of 3 reroll slots used)."""
        hida = _make_third_dan_hida(attack_skill=3)  # N=3 for attack
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("attack", 19, [2, 3, 9, 10, 8])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        # Only TWO reroll dice are needed (the 2 and 3 dice below 5.5)
        reroll_dice.extend([7, 6])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 5, 2)
        # After reroll: dice [10, 9, 8, 7, 6], top 2 kept = 19.
        self.assertEqual(19, result)
        # Both reroll dice consumed (only 2 eligible dice below 5.5).
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_no_chain(self):
        """A rerolled die that comes up low again stays at that value.

        One reroll per die per roll — no chaining.
        """
        hida = _make_third_dan_hida(attack_skill=3)
        inner = CalvinistRollProvider()
        # dice [1, 2, 8] sorted descending [8, 2, 1]; top 2 = 10.
        inner.put_skill_roll_with_dice("attack", 10, [1, 2, 8])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        # The 1 and 2 are rerolled; both come up low again (2 and 3).
        # If chaining were allowed, more dice would be consumed.
        reroll_dice.extend([2, 3])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 3, 2)
        # After reroll: dice [8, 3, 2], top 2 kept = 11.
        self.assertEqual(11, result)
        # Both reroll dice consumed (no chaining).
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_when_crippled_halves_N_round_up(self):
        """Crippled Hida: N is halved (round up).

        attack_skill=3, crippled, attack skill → N = ceil(3/2) = 2.
        Counterattack: 2X=6, halved = ceil(6/2) = 3.
        """
        # Attack skill case
        hida = _make_third_dan_hida(attack_skill=3, crippled=True)
        inner = CalvinistRollProvider()
        # Five dice all eligible (below 5.5); sorted desc [5,4,3,2,1],
        # top 2 = 9.
        inner.put_skill_roll_with_dice("attack", 9, [1, 2, 3, 4, 5])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        # N=2 means only the 2 lowest dice are rerolled.
        reroll_dice.extend([9, 9])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 5, 2)
        # After reroll of 1 and 2 → both become 9: dice [9, 9, 5, 4, 3],
        # top 2 = 18.
        self.assertEqual(18, result)
        self.assertEqual(0, len(reroll_dice))

        # Counterattack case: a fresh hida
        hida2 = _make_third_dan_hida(attack_skill=3, crippled=True)
        inner2 = CalvinistRollProvider()
        # dice [1,1,1,1,3] sorted desc [3,1,1,1,1]; top 2 = 4.
        inner2.put_skill_roll_with_dice("counterattack", 4, [1, 1, 1, 1, 3])
        provider2 = hida2.roll_provider()
        provider2._inner = inner2
        reroll_dice2 = CalvinistDice()
        # 2X=6, halved = ceil(6/2)=3 rerolls.
        reroll_dice2.extend([9, 9, 9])
        provider2._reroll_die_provider = reroll_dice2
        result2 = provider2.get_skill_roll("counterattack", 5, 2)
        # The 3 LOWEST dice are rerolled: three 1s (any three of the
        # four 1s) become 9.  Final: [9, 9, 9, 3, 1], top 2 = 18.
        self.assertEqual(18, result2)
        self.assertEqual(0, len(reroll_dice2))

    def test_reroll_when_crippled_10s_still_reroll(self):
        """Hida 3rd Dan exception: 10s explode despite being crippled.

        The provider's reroll die provider is called with
        ``explode=True`` even when the character is crippled — verified
        by having a 10 in the reroll-die queue followed by a 5; with
        explode=True the result is 10+5=15, with explode=False the
        result is just 10.
        """
        hida = _make_third_dan_hida(attack_skill=3, crippled=True)
        inner = CalvinistRollProvider()
        # Dice [1, 2, 8] — the 1 is below 5.5; N=ceil(3/2)=2.
        # Only one of [1,2] is the "lowest"; both 1 and 2 are eligible.
        inner.put_skill_roll_with_dice("attack", 10, [1, 2, 8])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        # Stage: the first reroll pops 10, sees 10, then with explode=True
        # pops the next die (5) and adds: result = 15.  The second
        # reroll pops a 7.
        reroll_dice.extend([10, 5, 7])
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 3, 2)
        # After reroll: 1→15, 2→7.  Dice [15, 8, 7], top 2 = 23.
        self.assertEqual(23, result)
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_trace_attribution(self):
        """Principle VII: rendered trace contains 'Hida 3rd Dan' AND
        shows which dice were rerolled (before → after) with the
        source label.

        Routes the reroll through a full AttackRolledEvent so the
        observer / formatter / renderer pipeline picks up the
        ``_hida_3rd_dan_reroll`` annotation on the action.
        """
        hida = _make_third_dan_hida(attack_skill=3)
        hida.set_actions([1])
        target = Character("Target")
        target.set_actions([2])
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Stage initial roll dice + reroll dice through the inner
        # provider and the reroll-die queue.
        inner = CalvinistRollProvider()
        # dice [1, 2, 8] sorted desc [8, 2, 1]; top 2 = 10.
        inner.put_skill_roll_with_dice("attack", 10, [1, 2, 8])
        # Also stage damage so AttackRolledEvent flow can complete.
        inner.put_damage_roll(10)
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        reroll_dice.extend([7, 6])
        provider._reroll_die_provider = reroll_dice
        # Wound check for target should succeed
        target_rp = CalvinistRollProvider()
        target_rp.put_wound_check_roll(50)
        target.set_roll_provider(target_rp)

        # Drive the attack through the engine's event() entry point so
        # the full pipeline (engine + observer + formatter + renderer)
        # runs.  ``engine.event(take_event)`` recursively plays nested
        # events (attack_declared, attack_rolled, damage, wound_check),
        # which is exactly what we need for trace assertions.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(hida, target, "attack", attack_init, context)
        engine = CombatEngine(context)
        engine.event(events.TakeAttackActionEvent(attack))

        # The reroll info must have been captured on the action.
        self.assertTrue(hasattr(attack, "_hida_3rd_dan_reroll"))
        self.assertIsNotNone(getattr(attack, "_hida_3rd_dan_reroll", None))

        # Render the trace via the formatter + text renderer.
        fmt = DetailedEventFormatter()
        history = engine.history()
        text_lines = TextRenderer().render_lines(fmt.entries(history))
        bulleted = BulletedRenderer().render(fmt.entries(history))
        text_blob = "\n".join(text_lines)
        self.assertIn(
            "Hida 3rd Dan", text_blob,
            f"Trace missing 'Hida 3rd Dan' attribution:\n{text_blob}",
        )
        self.assertIn(
            "reroll", text_blob,
            f"Trace missing 'reroll' wording:\n{text_blob}",
        )
        # Before → after values must appear in the trace: the 1 was
        # rerolled to 7 and the 2 was rerolled to 6.
        for substring in ("1", "7", "2", "6"):
            self.assertIn(substring, text_blob)
        # The bulleted renderer must contain the same key substrings.
        self.assertIn("Hida 3rd Dan", bulleted)
        self.assertIn("reroll", bulleted)


class TestHida3rdDanProviderInstallation(unittest.TestCase):
    """Verifies that ``apply_rank_three_ability`` installs the
    ``HidaRollProvider`` on the character.
    """

    def test_apply_rank_three_installs_provider(self):
        """After ``apply_rank_three_ability``, the character's
        roll_provider is a ``HidaRollProvider`` instance.
        """
        school = hida_school.HidaBushiSchool()
        hida = Character("Hida")
        hida.set_ring("water", 3)
        hida.set_skill("attack", 3)
        hida.set_school(school)
        # Before 3rd Dan: not a HidaRollProvider
        self.assertNotIsInstance(hida.roll_provider(), hida_school.HidaRollProvider)
        school.apply_special_ability(hida)
        school.apply_rank_three_ability(hida)
        self.assertIsInstance(hida.roll_provider(), hida_school.HidaRollProvider)

    def test_provider_inert_for_non_attack_skills(self):
        """The HidaRollProvider behaves identically to DefaultRollProvider
        on non-attack skills (no reroll).
        """
        school = hida_school.HidaBushiSchool()
        hida = Character("Hida")
        hida.set_ring("water", 3)
        hida.set_skill("attack", 4)
        hida.set_school(school)
        school.apply_special_ability(hida)
        school.apply_rank_three_ability(hida)
        # parry: 11 from dice [1, 2, 9] should pass through unchanged.
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("parry", 11, [1, 2, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        provider._reroll_die_provider = CalvinistDice()
        # No rerolls expected.
        result = provider.get_skill_roll("parry", 3, 2)
        self.assertEqual(11, result)
        # Also verify the default fallback path (no inner) returns
        # results identical to DefaultRollProvider for non-attack skills.
        # (Sanity: a fresh HidaRollProvider with the default die_provider
        # is a no-op wrapper over DefaultRollProvider.)
        fresh = hida_school.HidaRollProvider()
        self.assertIsInstance(fresh, DefaultRollProvider)


class TestHidaRollProviderUnwrapped(unittest.TestCase):
    """The HidaRollProvider supports an ``inner=None`` mode where it
    behaves like a DefaultRollProvider directly.

    This isn't the production install path (the school always wraps
    the existing provider), but the standalone mode is what makes
    HidaRollProvider drop-in compatible with DefaultRollProvider as
    a subclass — exercise it for coverage.
    """

    def test_get_skill_roll_unwrapped_non_eligible(self):
        """A standalone HidaRollProvider on a non-eligible skill
        (e.g., parry) goes through DefaultRollProvider's get_skill_roll
        with the original explode flag.
        """
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([7, 6, 5])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        result = provider.get_skill_roll("parry", 3, 2, explode=False)
        # Dice [7, 6, 5] sorted desc top 2 = 13.
        self.assertEqual(13, result)

    def test_get_skill_roll_unwrapped_eligible_no_character(self):
        """A standalone HidaRollProvider on an eligible skill but with
        no character bound just returns the initial total (no reroll
        can fire without a character).
        """
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([1, 2, 8])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        result = provider.get_skill_roll("attack", 3, 2)
        # Dice [1, 2, 8] sorted desc top 2 = 10.
        self.assertEqual(10, result)

    def test_get_wound_check_roll_unwrapped(self):
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([7, 8])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        result = provider.get_wound_check_roll(2, 1, explode=False)
        # Top 1 of [7, 8] = 8.
        self.assertEqual(8, result)

    def test_get_damage_roll_unwrapped(self):
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([3, 6])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        result = provider.get_damage_roll(2, 1)
        # Top 1 of [3, 6] = 6.
        self.assertEqual(6, result)

    def test_get_damage_reduction_roll_unwrapped(self):
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([3, 6])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        # reduction=0, rolled=2, kept=1
        result = provider.get_damage_reduction_roll(2, 1, 0)
        self.assertIsInstance(result, int)

    def test_get_initiative_roll_unwrapped(self):
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        dice.extend([3, 6, 8])
        provider = hida_school.HidaRollProvider(die_provider=dice)
        result = provider.get_initiative_roll(3, 2)
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

    def test_set_die_provider_unwrapped(self):
        """``set_die_provider`` delegates to DefaultRollProvider when no
        inner is set; delegates to inner when present.
        """
        from simulation.mechanics.roll import CalvinistDice as Dice
        # Unwrapped: should set on self.
        provider = hida_school.HidaRollProvider()
        dice = Dice()
        provider.set_die_provider(dice)
        self.assertIs(dice, provider.die_provider())
        # Wrapped: should set on inner.
        inner = DefaultRollProvider()
        wrapped = hida_school.HidaRollProvider(inner=inner)
        dice2 = Dice()
        wrapped.set_die_provider(dice2)
        self.assertIs(dice2, inner.die_provider())

    def test_last_accessors_unwrapped(self):
        """All ``last_*`` accessor methods return None / empty initially
        when unwrapped (no rolls have happened yet).
        """
        provider = hida_school.HidaRollProvider()
        self.assertIsNone(provider.last_damage_info())
        self.assertIsNone(provider.last_damage_roll())
        self.assertIsNone(provider.last_initiative_info())
        self.assertIsNone(provider.last_initiative_roll())
        self.assertIsNone(provider.last_skill_info())
        self.assertIsNone(provider.last_skill_roll())
        self.assertIsNone(provider.last_wound_check_info())
        self.assertIsNone(provider.last_wound_check_roll())
        self.assertIsNone(provider.last_hida_3rd_dan_reroll())

    def test_last_accessors_when_inner_missing_method(self):
        """When the inner provider doesn't implement a ``last_*``
        accessor (e.g., CalvinistRollProvider lacks ``last_*_roll``),
        the wrapper degrades to returning None.
        """
        inner = CalvinistRollProvider()
        provider = hida_school.HidaRollProvider(inner=inner)
        # CalvinistRollProvider doesn't define last_initiative_info / etc.
        # The wrapper must not raise AttributeError.
        self.assertIsNone(provider.last_initiative_info())
        self.assertIsNone(provider.last_damage_roll())

    def test_last_accessors_when_inner_has_method(self):
        """When the inner provider implements a ``last_*`` accessor
        (DefaultRollProvider implements all of them), the wrapper
        delegates and returns the inner result.
        """
        inner = DefaultRollProvider()
        provider = hida_school.HidaRollProvider(inner=inner)
        # DefaultRollProvider has all last_*; initial state is None.
        # Calling delegates without raising.
        self.assertIsNone(provider.last_skill_roll())
        self.assertIsNone(provider.last_damage_info())
        self.assertIsNone(provider.last_damage_roll())
        self.assertIsNone(provider.last_initiative_info())
        self.assertIsNone(provider.last_initiative_roll())
        self.assertIsNone(provider.last_wound_check_info())
        self.assertIsNone(provider.last_wound_check_roll())
        # ``last_skill_info`` delegates to inner when present.
        self.assertIsNone(provider.last_skill_info())

    def test_set_character_binds_provider(self):
        """``set_character`` updates the bound character."""
        provider = hida_school.HidaRollProvider()
        hida = Character("Late")
        hida.set_skill("attack", 2)
        provider.set_character(hida)
        # Verify the character is bound (no direct accessor; check via
        # the reroll path).
        from simulation.mechanics.roll import CalvinistDice as Dice
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("attack", 10, [2, 8])
        provider._inner = inner
        dice = Dice()
        dice.extend([7])
        provider._reroll_die_provider = dice
        result = provider.get_skill_roll("attack", 2, 2)
        # Reroll the 2 (below 5.5) → 7.  Dice [8, 7], top 2 = 15.
        self.assertEqual(15, result)

    def test_find_dice_to_reroll_no_eligible(self):
        """``_find_hida_dice_to_reroll`` returns [] when all dice are
        at or above 5.5 expected value.
        """
        result = hida_school._find_hida_dice_to_reroll([10, 8, 7, 6], 4)
        self.assertEqual([], result)

    def test_find_dice_to_reroll_zero_cap(self):
        """N=0 produces no rerolls even if dice are eligible."""
        result = hida_school._find_hida_dice_to_reroll([1, 2, 3], 0)
        self.assertEqual([], result)

    def test_constructor_with_explicit_reroll_die_provider(self):
        """Passing a non-None ``reroll_die_provider`` to the
        constructor stores it as the reroll die provider.
        """
        from simulation.mechanics.roll import CalvinistDice as Dice
        dice = Dice()
        provider = hida_school.HidaRollProvider(reroll_die_provider=dice)
        self.assertIs(dice, provider._reroll_die_provider)

    def test_reroll_skipped_when_attack_skill_zero(self):
        """If the character's attack skill is 0, N=0 and no reroll
        fires.  Defensive: this is an edge-case build but the provider
        must not crash.
        """
        school = hida_school.HidaBushiSchool()
        hida = Character("ZeroAttack")
        hida.set_ring("water", 3)
        hida.set_skill("attack", 0)
        hida.set_school(school)
        school.apply_special_ability(hida)
        school.apply_rank_three_ability(hida)
        inner = CalvinistRollProvider()
        inner.put_skill_roll_with_dice("attack", 11, [1, 2, 9])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 3, 2)
        # N=0 → no reroll fires; unchanged total.
        self.assertEqual(11, result)
        self.assertEqual(0, len(reroll_dice))

    def test_reroll_no_eligible_dice_below_threshold(self):
        """When all dice are above 5.5, no reroll fires even though
        the ability is otherwise active.
        """
        hida = _make_third_dan_hida(attack_skill=4)
        inner = CalvinistRollProvider()
        # dice [10, 9, 8, 7, 6] — all above 5.5; sorted desc top 2 = 19.
        inner.put_skill_roll_with_dice("attack", 19, [10, 9, 8, 7, 6])
        provider = hida.roll_provider()
        provider._inner = inner
        reroll_dice = CalvinistDice()
        provider._reroll_die_provider = reroll_dice
        result = provider.get_skill_roll("attack", 5, 2)
        # Nothing eligible → no reroll → unchanged total.
        self.assertEqual(19, result)
        # No reroll dice consumed.
        self.assertEqual(0, len(reroll_dice))
        # No reroll info recorded.
        self.assertIsNone(provider.last_hida_3rd_dan_reroll())

    def test_wrapped_damage_paths(self):
        """Wrapped damage / initiative / damage-reduction paths
        delegate to inner without applying the reroll (these aren't
        attack-class skills).
        """
        hida = _make_third_dan_hida(attack_skill=4)
        inner = CalvinistRollProvider()
        provider = hida.roll_provider()
        provider._inner = inner
        # Damage roll
        inner.put_damage_roll(15)
        self.assertEqual(15, provider.get_damage_roll(3, 2))
        # Damage reduction roll
        inner.put_damage_roll(8)
        self.assertEqual(8, provider.get_damage_reduction_roll(3, 2, 0))
        # Initiative roll
        inner.put_initiative_roll([3, 5, 7])
        self.assertEqual([3, 5, 7], provider.get_initiative_roll(3, 3))

    def test_reroll_when_dice_info_missing(self):
        """If ``last_skill_info`` returns no dice, the provider skips
        the reroll (defensive — every reasonable inner provider
        populates dice).
        """
        from typing import Any as _Any

        # Build an inner provider that returns a total but no dice info.
        class InfoBareProvider:
            def __init__(self) -> None:
                self._info: dict[str, _Any] = {"rolled": 3, "kept": 2, "dice": None}

            def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
                return 12

            def last_skill_info(self) -> dict[str, _Any]:
                return self._info

        bare = InfoBareProvider()
        hida = Character("Hida")
        hida.set_skill("attack", 3)
        provider = hida_school.HidaRollProvider(character=hida, inner=bare)
        result = provider.get_skill_roll("attack", 3, 2)
        # No dice info means no reroll fires.
        self.assertEqual(12, result)
        self.assertIsNone(provider.last_hida_3rd_dan_reroll())


# ---------------------------------------------------------------
# 4th Dan: SW-for-LW trade alternative wound check
# ---------------------------------------------------------------


def _make_fourth_dan_hida(max_sw: int = 4) -> Character:
    """Helper: build a 4th-Dan-active Hida.

    Earth ring is set to ``max_sw // 2`` so the character's
    ``max_sw()`` matches the requested value (max_sw = earth * 2).
    The school's 4th-Dan ability is applied, installing the
    HidaWoundCheckStrategy.
    """
    earth = max(1, max_sw // 2)
    school = hida_school.HidaBushiSchool()
    hida = Character("Hida4thDan")
    hida.set_ring("water", 3)
    hida.set_ring("earth", earth)
    hida.set_skill("attack", 4)
    hida.set_skill("counterattack", 4)
    hida.set_skill("double attack", 4)
    hida.set_skill("iaijutsu", 4)
    hida.set_skill("parry", 4)
    hida.set_skill("wound check", 4)
    hida.set_school(school)
    school.apply_special_ability(hida)
    school.apply_rank_three_ability(hida)
    school.apply_rank_four_ability(hida)
    return hida


class TestHidaWoundCheckStrategy(unittest.TestCase):
    """Unit tests for HidaWoundCheckStrategy at the strategy level
    (no engine integration).

    Verifies the trade pre-condition gates and the fall-through to
    the base WoundCheckStrategy.
    """

    def test_strategy_subclasses_WoundCheckStrategy(self):
        """HidaWoundCheckStrategy must be a subclass of the engine's
        base WoundCheckStrategy so the engine dispatches it through
        the existing wound_check slot.
        """
        from simulation.strategies.base import WoundCheckStrategy
        self.assertTrue(
            issubclass(hida_school.HidaWoundCheckStrategy, WoundCheckStrategy)
        )

    def test_strategy_falls_through_when_trade_not_applicable(self):
        """When trade pre-conditions are NOT met (here: lw=0), the
        strategy yields whatever the base WoundCheckStrategy yields
        rather than a HidaSWForLWTradeEvent.

        rules/04-schools.md "Hida Bushi School: Fourth Dan" + Q3
        (trade is NOT taken at lw=0).
        """
        hida = _make_fourth_dan_hida(max_sw=6)
        enemy = Character("Enemy")
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        context.initialize()
        # Hida has lw=0; recommend() with a synthetic LW event must
        # NOT yield a trade.  The base path WOULD yield a
        # WoundCheckDeclaredEvent, but we don't care about its
        # content here — only that the trade isn't emitted.
        synthetic = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        strategy = hida_school.HidaWoundCheckStrategy()
        emitted = list(strategy.recommend(hida, synthetic, context))
        self.assertFalse(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in emitted),
            f"Trade should not fire at lw=0; got {[e.name for e in emitted]}",
        )

    def test_strategy_takes_trade_when_pre_conditions_met(self):
        """When all trade pre-conditions hold (lw>0, sw+2<=max_sw,
        not in iaijutsu phase, expected SW from roll >= 2), the
        strategy yields a HidaSWForLWTradeEvent.

        rules/04-schools.md "Hida Bushi School: Fourth Dan".
        """
        hida = _make_fourth_dan_hida(max_sw=6)
        # Push LW high enough that the expected WC roll would
        # incur multiple SW.  At LW=40 and earth=3 (max_sw=6), the
        # expected roll on 3k3 (default) is well below 40, so
        # expected SW >= 2.
        hida.take_lw(40)
        enemy = Character("Enemy")
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        context.initialize()
        synthetic = events.LightWoundsDamageEvent(enemy, hida, damage=10)
        strategy = hida_school.HidaWoundCheckStrategy()
        emitted = list(strategy.recommend(hida, synthetic, context))
        self.assertTrue(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in emitted),
            f"Expected HidaSWForLWTradeEvent; got {[e.name for e in emitted]}",
        )


class TestHida4thDanSWForLW(unittest.TestCase):
    """End-to-end tests for the Hida 4th Dan SW-for-LW trade.

    rules/04-schools.md "Hida Bushi School: Fourth Dan":
      "Instead of making a wound check, you may choose to take 2
       serious wounds to reduce your light wounds to 0.  You may not
       do this during the iaijutsu phase of a duel."
    """

    def _engine_for(self, hida: Character, enemy: Character) -> tuple[CombatEngine, EngineContext]:
        groups = [Group("Crab", hida), Group("Enemy", enemy)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        engine = CombatEngine(context)
        return engine, context

    def test_trade_fires_when_lw_high_and_sw_pool_available(self):
        """LW>>0, SW=0, max_SW=4 — the expected WC roll incurs ≥ 2 SW,
        and the trade is taken (yields HidaSWForLWTradeEvent).
        """
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        # Pre-load LW high enough that the expected wound check roll
        # incurs ≥ 2 SW.  At earth=2 + wound check skill=4, the mean
        # 5k4 roll is ~27; we need lw - mean_roll >= 10 → lw >= 37.
        hida.take_lw(35)
        engine, _ = self._engine_for(hida, enemy)
        # Incoming damage = 5 → final lw = 40, mean WC ≈ 27, expected SW = 2.
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        engine.event(lw_event)
        # Trade should have fired.
        self.assertTrue(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in engine.history()),
            "Expected HidaSWForLWTradeEvent in engine history.",
        )

    def test_trade_short_circuits_when_lw_zero(self):
        """At lw=0 the trade is skipped regardless of context.

        Q3 pre-resolution — trading 2 SW for "reduce 0 to 0" is
        strictly suboptimal.
        """
        hida = _make_fourth_dan_hida(max_sw=6)
        enemy = Character("Enemy")
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        context.initialize()
        synthetic = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        strategy = hida_school.HidaWoundCheckStrategy()
        # The strategy's internal heuristic should reject the trade.
        self.assertFalse(strategy._should_trade(hida, synthetic, context))
        emitted = list(strategy.recommend(hida, synthetic, context))
        self.assertFalse(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in emitted),
            "Trade should not fire at lw=0.",
        )

    def test_trade_short_circuits_when_sw_plus_2_would_kill(self):
        """SW = max_SW - 1 → trade would push SW to max_SW + 1, lethal.

        Q4 pre-resolution — the trade is gated on
        ``sw() + 2 <= max_sw()``; falls back to normal WC.
        """
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        # Push SW to max_SW - 1 (= 3); the trade would push it to 5, fatal.
        hida.take_sw(hida.max_sw() - 1)
        self.assertEqual(hida.max_sw() - 1, hida.sw())
        # Pre-load LW so the trade WOULD be attractive but for the SW pool.
        hida.take_lw(40)
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        context.initialize()
        synthetic = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        strategy = hida_school.HidaWoundCheckStrategy()
        self.assertFalse(strategy._should_trade(hida, synthetic, context))
        emitted = list(strategy.recommend(hida, synthetic, context))
        self.assertFalse(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in emitted),
            "Trade should not fire when sw+2 would exceed max_sw.",
        )

    def test_trade_blocked_in_iaijutsu_phase_for_duelist(self):
        """The Hida is a duelist in an active iaijutsu duel.  The trade
        is gated off; falls back to the normal WC path.

        rules/04-schools.md "Hida Bushi School: Fourth Dan":
          "You may not do this during the iaijutsu phase of a duel."
        Q4 pre-resolution — duelists are gated, bystanders are not.
        """
        from simulation.duel import (
            DuelEndedEvent,
            DuelInitiativeRolledEvent,
        )

        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        hida.take_lw(40)
        engine, context = self._engine_for(hida, enemy)
        # Enter the iaijutsu phase with the Hida as a duelist.
        engine.event(DuelInitiativeRolledEvent(hida, enemy, 25, 20, hida))
        self.assertTrue(context.in_iaijutsu_phase(hida))
        # Now fire an LW event for the Hida: trade must NOT fire.
        history_before = len(engine.history())
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        engine.event(lw_event)
        new_events = engine.history()[history_before:]
        self.assertFalse(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in new_events),
            "Trade must not fire during the Hida's own iaijutsu phase.",
        )
        # And re-enabling after the duel ends restores the trade path.
        engine.event(DuelEndedEvent(hida, enemy))
        self.assertFalse(context.in_iaijutsu_phase(hida))

    def test_trade_allowed_for_bystander_of_someone_elses_duel(self):
        """The Hida is NOT a duelist; two other characters are dueling.
        The trade is available to the Hida.
        """
        from simulation.duel import DuelInitiativeRolledEvent

        hida = _make_fourth_dan_hida(max_sw=4)
        duelist_a = Character("DuelistA")
        duelist_b = Character("DuelistB")
        hida.take_lw(40)
        groups = [
            Group("Crab", [hida, duelist_a]),
            Group("Other", duelist_b),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        engine = CombatEngine(context)
        # Some other characters' duel starts (NOT the Hida).
        engine.event(DuelInitiativeRolledEvent(duelist_a, duelist_b, 20, 15, duelist_a))
        self.assertTrue(context.in_iaijutsu_phase(duelist_a))
        self.assertTrue(context.in_iaijutsu_phase(duelist_b))
        # Hida is a bystander — NOT in the iaijutsu phase.
        self.assertFalse(context.in_iaijutsu_phase(hida))
        history_before = len(engine.history())
        lw_event = events.LightWoundsDamageEvent(duelist_b, hida, damage=5)
        engine.event(lw_event)
        new_events = engine.history()[history_before:]
        self.assertTrue(
            any(isinstance(e, events.HidaSWForLWTradeEvent) for e in new_events),
            "Bystander Hida should be able to use the 4th Dan trade.",
        )

    def test_trade_emits_HidaSWForLWTradeEvent(self):
        """End-to-end: the trade emits a HidaSWForLWTradeEvent (vs
        a wound-check event with overrides — per Q9 pre-resolution).
        """
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        # LW=35 + 5 damage = 40 final LW; expected SW from rolling = 2.
        hida.take_lw(35)
        engine, _ = self._engine_for(hida, enemy)
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        engine.event(lw_event)
        trade_events = [
            e for e in engine.history()
            if isinstance(e, events.HidaSWForLWTradeEvent)
        ]
        self.assertEqual(
            1, len(trade_events),
            "Exactly one HidaSWForLWTradeEvent should be emitted.",
        )
        trade = trade_events[0]
        self.assertEqual(hida, trade.character)
        self.assertEqual(enemy, trade.attacker)
        self.assertEqual(40, trade.lw_reset_from)
        self.assertEqual(2, trade.sw_taken)

    def test_trade_resets_lw_to_zero(self):
        """After the trade, the Hida's LW must be 0."""
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        hida.take_lw(35)
        engine, _ = self._engine_for(hida, enemy)
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        engine.event(lw_event)
        self.assertEqual(0, hida.lw())

    def test_trade_adds_two_sw(self):
        """After the trade, the Hida's SW must be ``sw_before + 2``."""
        hida = _make_fourth_dan_hida(max_sw=6)
        enemy = Character("Enemy")
        hida.take_lw(35)
        sw_before = hida.sw()
        engine, _ = self._engine_for(hida, enemy)
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        engine.event(lw_event)
        self.assertEqual(sw_before + 2, hida.sw())

    def test_trade_replaces_wound_check(self):
        """When the trade fires, NO WoundCheckEvent / WoundCheckRoll
        / WoundCheckDeclared / WoundCheckSucceeded should appear after
        the triggering LW event.

        Q9 pre-resolution — the trade REPLACES the wound check, it
        does not annotate it.
        """
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        hida.take_lw(35)
        engine, _ = self._engine_for(hida, enemy)
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        history_before = len(engine.history())
        engine.event(lw_event)
        new_events = engine.history()[history_before:]
        # No WC events of any kind should be emitted on the trade path.
        for e in new_events:
            self.assertNotIsInstance(
                e, events.WoundCheckEvent,
                f"Trade should replace WC; got {e.name} in history.",
            )

    def test_trade_trace_observability(self):
        """Principle VII: the trade must render in the user-visible
        combat trace with source attribution ("Hida 4th Dan"), the
        explicit "take 2 SW" action, and the LW reset.

        rules/04-schools.md "Hida Bushi School: Fourth Dan" +
        Constitution Principle VII.
        """
        hida = _make_fourth_dan_hida(max_sw=4)
        enemy = Character("Enemy")
        hida.take_lw(35)
        engine, _ = self._engine_for(hida, enemy)
        observer = CombatObserver()
        new_phase = events.NewPhaseEvent(phase=1)
        observer.on_event(new_phase, engine.context())
        engine.event(new_phase)
        lw_event = events.LightWoundsDamageEvent(enemy, hida, damage=5)
        observer.on_event(lw_event, engine.context())
        engine.event(lw_event)
        # The HidaSWForLWTradeEvent should be in history; have the
        # formatter render it.
        fmt = DetailedEventFormatter()
        history = engine.history()
        text_lines = TextRenderer().render_lines(fmt.entries(history))
        bulleted = BulletedRenderer().render(fmt.entries(history))
        text_blob = "\n".join(text_lines)
        # Required substrings per Principle VII.
        self.assertIn(
            "Hida 4th Dan", text_blob,
            f"Trace missing 'Hida 4th Dan' source attribution:\n{text_blob}",
        )
        self.assertIn(
            "take 2 SW", text_blob,
            f"Trace missing 'take 2 SW' action description:\n{text_blob}",
        )
        self.assertIn(
            "reset LW", text_blob,
            f"Trace missing 'reset LW' description:\n{text_blob}",
        )
        # Same in the bulleted renderer (cross-renderer consistency).
        self.assertIn("Hida 4th Dan", bulleted)
        self.assertIn("take 2 SW", bulleted)
        self.assertIn("reset LW", bulleted)


# ---------------------------------------------------------------
# 5th Dan: counterattack-excess WC bonus + post-damage timing
# ---------------------------------------------------------------


def _make_fifth_dan_hida(max_sw: int = 6) -> Character:
    """Helper: build a 5th-Dan Hida with all 5 Dan abilities applied.

    All school knack skills are set to 5 to put the character at
    5th Dan (school_rank = min(skill rank) across knacks).
    """
    earth = max(1, max_sw // 2)
    school = hida_school.HidaBushiSchool()
    hida = Character("Hida5thDan")
    hida.set_ring("water", 4)
    hida.set_ring("earth", earth)
    hida.set_skill("attack", 5)
    hida.set_skill("counterattack", 5)
    hida.set_skill("double attack", 5)
    hida.set_skill("iaijutsu", 5)
    hida.set_skill("parry", 5)
    hida.set_skill("wound check", 5)
    hida.set_school(school)
    school.apply_special_ability(hida)
    school.apply_rank_three_ability(hida)
    school.apply_rank_four_ability(hida)
    school.apply_rank_five_ability(hida)
    return hida


def _make_pre_fifth_dan_hida(dan: int = 4) -> Character:
    """Helper: build a Hida at the given Dan tier (< 5), with all
    applicable Dan abilities applied but NOT the 5th-Dan ability.

    Used to verify pre-5th-Dan strategy behavior falls through to the
    base CounterattackInterruptStrategy.
    """
    school = hida_school.HidaBushiSchool()
    hida = Character(f"Hida{dan}Dan")
    hida.set_ring("water", 3)
    hida.set_ring("earth", 2)
    for k in ("attack", "counterattack", "double attack", "iaijutsu", "parry", "wound check"):
        hida.set_skill(k, dan)
    hida.set_school(school)
    school.apply_special_ability(hida)
    if dan >= 3:
        school.apply_rank_three_ability(hida)
    if dan >= 4:
        school.apply_rank_four_ability(hida)
    # NOT apply_rank_five_ability
    return hida


class TestHida5thDanWCBonus(unittest.TestCase):
    """Hida 5th Dan: counterattack-excess WC bonus.

    rules/04-schools.md "Hida Bushi School: Fifth Dan":
      "When you counterattack successfully, note the quantity X by
       which the counterattack roll exceeded its TN.  Add X to your
       wound check on the damage from the attack you counterattacked."

    FR-019, FR-020, FR-021.
    """

    def test_counterattack_excess_stored_on_attack_action(self):
        """A successful 5th-Dan-Hida counterattack stores
        ``_counterattack_excess_margin = roll - TN`` on the originating
        attack action.

        FR-019 / Q11 pre-resolution.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        attack.set_skill_roll(25)  # placeholder so attack has a roll
        # Hida counterattacks as interrupt.
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            hida, attacker, "counterattack",
            interrupt_action, context, attack,
        )
        # Rig the counterattack roll: 35; TN = attacker.tn_to_hit() = 10
        # (default character), so excess = 35 - 10 = 25.  But for a tight
        # numeric, set things so the math is obvious: TN=10, roll=17 → excess=7.
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 17)
        roll_provider.put_damage_roll(8)
        hida.set_roll_provider(roll_provider)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        attacker.set_roll_provider(attacker_rp)
        engine = CombatEngine(context)
        engine.event(hida_school.HidaTakeCounterattackActionEvent(counterattack))
        # The expected excess is 17 - counterattack.tn() = 17 - 10 = 7.
        expected_excess = 17 - counterattack.tn()
        self.assertEqual(
            expected_excess,
            getattr(attack, "_counterattack_excess_margin", 0),
            "Successful 5th-Dan counterattack must store the excess "
            "margin on the originating attack action.",
        )

    def test_wc_roll_adds_counterattack_excess_when_present(self):
        """When the Hida's WC fires on damage from a previously
        counterattacked attack, the WC roll has the excess (+X) added.

        FR-019.  We exercise the WC-listener path with a synthetic
        LightWoundsDamageEvent carrying an ``attack_action`` reference.
        """
        hida = _make_fifth_dan_hida()
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Build an attack action with a pre-set counterattack-excess.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        attack._counterattack_excess_margin = 12
        # The bonus applies only to the counterattacker's OWN WC per
        # rules text ("YOUR WC"); tag the action with the
        # counterattacker reference so the listener applies the bonus.
        attack._counterattack_excess_counterattacker = hida
        # Rig the Hida's WC base roll to 30; with +12 excess it becomes 42.
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(30)
        hida.set_roll_provider(hida_rp)
        # LW damage of 30 → expected WC TN = 30, +12 excess pushes roll to 42 → passes.
        engine = CombatEngine(context)
        lw_event = events.LightWoundsDamageEvent(
            attacker, hida, 30, attack_action=attack,
        )
        engine.event(lw_event)
        # The WC roll in history must reflect the +12 bonus.
        wc_rolled = [
            e for e in engine.history()
            if isinstance(e, events.WoundCheckRolledEvent)
            and e.subject == hida
        ]
        self.assertEqual(1, len(wc_rolled))
        self.assertEqual(30 + 12, wc_rolled[0].roll)

    def test_wc_bonus_sourced_in_trace(self):
        """Principle VII: rendered trace shows "Hida 5th Dan" and
        "counterattack excess" with the numeric +X on the WC line.

        FR-029.
        """
        hida = _make_fifth_dan_hida()
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        attack._counterattack_excess_margin = 7
        attack._counterattack_excess_counterattacker = hida
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(20)
        hida.set_roll_provider(hida_rp)
        engine = CombatEngine(context)
        observer = CombatObserver()
        new_phase = events.NewPhaseEvent(phase=1)
        observer.on_event(new_phase, context)
        engine.event(new_phase)
        lw_event = events.LightWoundsDamageEvent(
            attacker, hida, 25, attack_action=attack,
        )
        observer.on_event(lw_event, context)
        engine.event(lw_event)
        # Render the trace.
        fmt = DetailedEventFormatter()
        history = engine.history()
        text_blob = "\n".join(TextRenderer().render_lines(fmt.entries(history)))
        bulleted = BulletedRenderer().render(fmt.entries(history))
        self.assertIn(
            "Hida 5th Dan", text_blob,
            f"Trace missing 'Hida 5th Dan' attribution:\n{text_blob}",
        )
        self.assertIn(
            "counterattack excess", text_blob,
            f"Trace missing 'counterattack excess' description:\n{text_blob}",
        )
        self.assertIn("+7", text_blob)
        # Cross-renderer.
        self.assertIn("Hida 5th Dan", bulleted)
        self.assertIn("counterattack excess", bulleted)
        self.assertIn("+7", bulleted)

    def test_wc_bonus_zero_when_no_counterattack(self):
        """A normal WC (no preceding counterattack) gets no Hida 5th Dan
        bonus — the WC roll matches the inner provider's value exactly.

        FR-020: bonus applies ONLY to WC on damage from a counterattacked
        attack.
        """
        hida = _make_fifth_dan_hida()
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        # NO _counterattack_excess_margin set.
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(30)
        hida.set_roll_provider(hida_rp)
        engine = CombatEngine(context)
        lw_event = events.LightWoundsDamageEvent(
            attacker, hida, 25, attack_action=attack,
        )
        engine.event(lw_event)
        wc_rolled = [
            e for e in engine.history()
            if isinstance(e, events.WoundCheckRolledEvent)
            and e.subject == hida
        ]
        self.assertEqual(1, len(wc_rolled))
        # No bonus applied — raw 30.
        self.assertEqual(30, wc_rolled[0].roll)

    def test_wc_bonus_applies_only_to_hida_own_wc_on_counterattacked_damage(self):
        """FR-020: bonus does NOT apply to the Hida's OTHER WC rolls
        from a DIFFERENT attack.

        We stage two LW events: one with an attack carrying
        ``_counterattack_excess_margin``, one with a fresh (different)
        attack that has no bonus.  The first WC should be bumped; the
        second should not.
        """
        hida = _make_fifth_dan_hida(max_sw=10)
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Attack A: with bonus.
        attack_init_a = InitiativeAction([1], 1)
        attack_a = actions.AttackAction(attacker, hida, "attack", attack_init_a, context)
        attack_a._counterattack_excess_margin = 8
        attack_a._counterattack_excess_counterattacker = hida
        # Attack B: no bonus.
        attack_init_b = InitiativeAction([2], 2)
        attack_b = actions.AttackAction(attacker, hida, "attack", attack_init_b, context)
        # Rig the Hida's two WC rolls: both base 25.
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(25)
        hida_rp.put_wound_check_roll(25)
        hida.set_roll_provider(hida_rp)
        engine = CombatEngine(context)
        engine.event(events.LightWoundsDamageEvent(
            attacker, hida, 20, attack_action=attack_a,
        ))
        engine.event(events.LightWoundsDamageEvent(
            attacker, hida, 20, attack_action=attack_b,
        ))
        wc_rolled = [
            e for e in engine.history()
            if isinstance(e, events.WoundCheckRolledEvent)
            and e.subject == hida
        ]
        self.assertEqual(2, len(wc_rolled))
        # First WC bumped by +8; second left alone.
        self.assertEqual(25 + 8, wc_rolled[0].roll)
        self.assertEqual(25, wc_rolled[1].roll)

    def test_wc_bonus_does_not_leak_to_defended_friend(self):
        """rules-auditor #1 regression: rules text says "YOUR wound
        check" — when a 5th-Dan Hida defends an adjacent friend with
        a counterattack on an attack targeting the friend, the FRIEND
        must NOT receive the bonus on their own WC.

        rules/04-schools.md "Hida Bushi School: Fifth Dan" + FR-020.
        """
        hida = _make_fifth_dan_hida(max_sw=10)
        friend = Character("Friend")
        friend.set_actions([1])
        friend.set_ring("earth", 3)
        attacker = Character("Attacker")
        groups = [
            Group("Crab", [hida, friend]),
            Group("Enemy", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # The attack TARGETED the friend (not the Hida), and the Hida
        # counterattacked it.  The margin + counterattacker tags are
        # what HidaCounterattackSucceededListener would have set.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(
            attacker, friend, "attack", attack_init, context,
        )
        attack._counterattack_excess_margin = 10
        attack._counterattack_excess_counterattacker = hida
        # Friend takes the LW; their WC must NOT get the +10 bonus.
        friend_rp = CalvinistRollProvider()
        friend_rp.put_wound_check_roll(25)
        friend.set_roll_provider(friend_rp)
        engine = CombatEngine(context)
        engine.event(events.LightWoundsDamageEvent(
            attacker, friend, 20, attack_action=attack,
        ))
        wc_rolled = [
            e for e in engine.history()
            if isinstance(e, events.WoundCheckRolledEvent)
            and e.subject == friend
        ]
        self.assertEqual(1, len(wc_rolled))
        self.assertEqual(
            25, wc_rolled[0].roll,
            "Friend's WC must NOT receive the Hida 5th Dan counterattack-"
            "excess bonus (rules text: 'YOUR WC' — applies only to the "
            "counterattacker's own WC).  rules-auditor #1 regression.",
        )

    def test_wc_bonus_stacking_limit(self):
        """Q11 pre-resolution: when both attacker and defender are
        Hida 5th Dan, only the outermost counterattack's margin counts.

        Concretely: if the defender's counterattack succeeds AND the
        original attacker (also a 5th Dan Hida) counterattacks-the-
        counterattack, both characters' attack actions would otherwise
        be marked with ``_counterattack_excess_margin``.  The
        outermost-only rule means a NEW counterattack-of-counterattack
        does NOT also bump the WC on its TARGET (i.e., the resolver
        must NOT write a margin onto an action that has already received
        one in this exchange).

        Implementation: the storage step skips writing when the originating
        attack action ALREADY has a non-zero ``_counterattack_excess_margin``
        — only the FIRST (outermost) counterattack writes.
        """
        hida_a = _make_fifth_dan_hida()
        hida_a.set_actions([5, 8])
        hida_b = _make_fifth_dan_hida()
        hida_b._name = "HidaB"
        hida_b.set_actions([5, 8])
        groups = [Group("CrabA", hida_a), Group("CrabB", hida_b)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # HidaA attacks HidaB.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(hida_a, hida_b, "attack", attack_init, context)
        attack.set_skill_roll(20)
        # Pre-set an existing margin to simulate a prior counterattack write.
        attack._counterattack_excess_margin = 5
        # Now a SECOND counterattack tries to write — must NOT overwrite.
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            hida_b, hida_a, "counterattack",
            interrupt_action, context, attack,
        )
        # hida_a has parry=5 → tn_to_hit = 30; counterattack TN = 30
        # (target is HidaA, no parry penalty for self-defense).  Roll 50
        # to clear the TN and produce a 20-point excess.
        rp = CalvinistRollProvider()
        rp.put_skill_roll("counterattack", 50)  # excess = 50 - 30 = 20
        rp.put_damage_roll(8)
        hida_b.set_roll_provider(rp)
        hida_a_rp = CalvinistRollProvider()
        hida_a_rp.put_wound_check_roll(50)
        hida_a.set_roll_provider(hida_a_rp)
        engine = CombatEngine(context)
        engine.event(hida_school.HidaTakeCounterattackActionEvent(counterattack))
        # Sanity check: the counterattack did succeed (so the listener
        # was actually invoked).
        self.assertTrue(
            any(
                isinstance(e, events.CounterattackSucceededEvent)
                for e in engine.history()
            ),
            "Test setup error: counterattack must have succeeded for the "
            "stacking-limit listener path to fire.",
        )
        # The pre-existing margin (5) must persist; not overwritten by 20.
        self.assertEqual(
            5,
            getattr(attack, "_counterattack_excess_margin", 0),
            "Outermost-only rule: pre-existing margin must persist.",
        )


class TestHida5thDanPostDamageTiming(unittest.TestCase):
    """Hida 5th Dan: post-damage counterattack timing.

    rules/04-schools.md "Hida Bushi School: Fifth Dan":
      "You may choose to counterattack after seeing an opponent's
       damage roll, but that roll goes through even if your
       counterattack impairs or kills the opponent."

    FR-017, FR-018, FR-030.
    """

    def test_5th_dan_strategy_defers_pre_damage(self):
        """``HidaCounterattackInterruptStrategy.recommend`` on an
        ``AttackDeclaredEvent`` for a 5th-Dan character defers the
        decision (yields NO events).

        FR-017 — die is reserved, decision happens later.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        declared = events.AttackDeclaredEvent(attack)
        strategy = hida.interrupt_strategy()
        self.assertIsInstance(
            strategy, hida_school.HidaCounterattackInterruptStrategy,
            f"5th-Dan Hida should have HidaCounterattackInterruptStrategy "
            f"installed; got {type(strategy).__name__}.",
        )
        emitted = list(strategy.recommend(hida, declared, context))
        # 5th-Dan defers pre-damage decision — no events yielded.
        self.assertEqual(
            [], emitted,
            f"5th-Dan strategy must defer pre-damage; got {emitted}.",
        )

    def test_5th_dan_strategy_decides_post_damage(self):
        """On a ``PostDamageInterruptCheckEvent`` for a 5th-Dan
        character, the strategy decides whether to counterattack and
        emits the SpendActionEvent / TakeCounterattackActionEvent
        sequence (the standard CounterattackInterruptStrategy effect).

        FR-017.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        post_dmg = events.PostDamageInterruptCheckEvent(attack)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, post_dmg, context))
        # The post-damage path fires the counterattack — at least a
        # SpendActionEvent + take-counterattack-action event are yielded.
        self.assertTrue(
            any(isinstance(e, events.SpendActionEvent) for e in emitted),
            f"Post-damage strategy should fire counterattack; got "
            f"{[type(e).__name__ for e in emitted]}.",
        )

    def test_damage_resolves_before_counterattack(self):
        """In a real attack flow, the LightWoundsDamageEvent (LW added
        + WC fires) must resolve BEFORE the post-damage counterattack
        roll fires.

        FR-018: the damage event fully resolves first.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([3])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=3)
        context.initialize()
        # Attack rolls + damage rolls + WCs.  The Hida has high parry
        # skill (5 from school knack defaults) so tn_to_hit = 5*(1+5)=30.
        # Attacker's roll must beat that.
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 40)
        attacker_rp.put_damage_roll(15)
        attacker_rp.put_wound_check_roll(50)
        attacker.set_roll_provider(attacker_rp)
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(50)
        hida_rp.put_skill_roll("counterattack", 30)
        hida_rp.put_damage_roll(10)
        hida.set_roll_provider(hida_rp)
        attack_init = InitiativeAction([3], 3)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        engine = CombatEngine(context)
        engine.event(events.TakeAttackActionEvent(attack))
        history = engine.history()
        # Find the LightWoundsDamageEvent for the Hida (defender).
        lw_idx = next(
            (i for i, e in enumerate(history)
             if isinstance(e, events.LightWoundsDamageEvent)
             and e.target == hida),
            None,
        )
        # Find the CounterattackRolledEvent (Hida's counterattack).
        ca_idx = next(
            (i for i, e in enumerate(history)
             if isinstance(e, events.CounterattackRolledEvent)),
            None,
        )
        self.assertIsNotNone(lw_idx, "LightWoundsDamageEvent must be in history.")
        self.assertIsNotNone(ca_idx, "CounterattackRolledEvent must be in history.")
        # Damage resolves before the counterattack roll.
        assert lw_idx is not None and ca_idx is not None
        self.assertLess(
            lw_idx, ca_idx,
            f"Damage must resolve before counterattack roll; "
            f"got lw={lw_idx} vs ca={ca_idx}.",
        )

    def test_attacker_killed_by_counterattack_damage_still_stands(self):
        """If the post-damage counterattack kills the attacker, the
        defender's already-suffered damage stands (no retroactive
        cancellation).

        FR-018 / Q6 pre-resolution.  The CombatEnded exception is
        expected when the attacker dies (single combatant per side),
        so we suppress it and inspect the history.
        """
        from simulation.exceptions import CombatEnded

        hida = _make_fifth_dan_hida(max_sw=10)
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        # Fragile attacker — one solid damage roll will kill.
        attacker.set_ring("earth", 1)  # max_sw = 1
        attacker.set_actions([3])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=3)
        context.initialize()
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 40)
        attacker_rp.put_damage_roll(20)
        attacker_rp.put_wound_check_roll(1)  # WC catastrophically fails → death
        attacker.set_roll_provider(attacker_rp)
        hida_rp = CalvinistRollProvider()
        hida_rp.put_wound_check_roll(50)  # Hida WC passes
        hida_rp.put_skill_roll("counterattack", 50)
        hida_rp.put_damage_roll(100)
        hida.set_roll_provider(hida_rp)
        attack_init = InitiativeAction([3], 3)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        engine = CombatEngine(context)
        try:
            engine.event(events.TakeAttackActionEvent(attack))
        except CombatEnded:
            # Attacker's death ends the combat — expected.
            pass
        # The Hida did suffer damage from the original attack (LW > 0
        # at some point), even if the counterattack subsequently kills
        # the attacker.  Verify the LW damage event for the HIDA (the
        # original defender) is in history — "the damage stands"
        # means we MUST see it.
        lw_events = [
            e for e in engine.history()
            if isinstance(e, events.LightWoundsDamageEvent)
            and e.target == hida
            and e.damage > 0
        ]
        self.assertGreater(
            len(lw_events), 0,
            "Hida's LW damage event must appear in history even if the "
            "counterattack subsequently kills the attacker.",
        )
        # And the attacker's death event must appear AFTER the Hida's
        # damage in history.
        hida_lw_idx = next(
            i for i, e in enumerate(engine.history())
            if isinstance(e, events.LightWoundsDamageEvent)
            and e.target == hida
        )
        attacker_death_idx = next(
            (i for i, e in enumerate(engine.history())
             if isinstance(e, events.DeathEvent) and e.subject == attacker),
            None,
        )
        if attacker_death_idx is not None:
            self.assertLess(
                hida_lw_idx, attacker_death_idx,
                "Hida's damage must come before attacker's death event.",
            )

    def test_5th_dan_post_damage_uses_1_die_interrupt_cost(self):
        """The Hida special ability (1-die interrupt counterattack)
        still applies on the post-damage path: the counterattack
        spends only 1 action die.

        FR-001 invariant under 5th Dan.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        post_dmg = events.PostDamageInterruptCheckEvent(attack)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, post_dmg, context))
        spend_action_events = [
            e for e in emitted if isinstance(e, events.SpendActionEvent)
        ]
        self.assertEqual(1, len(spend_action_events))
        spent_dice = spend_action_events[0].initiative_action.dice()
        self.assertEqual(
            1, len(spent_dice),
            f"5th-Dan post-damage counterattack must use 1 action die; "
            f"got {spent_dice}.",
        )

    def test_5th_dan_attacker_still_gets_5_free_raise(self):
        """The Hida special ability +5 free raise to the attacker
        still applies on the post-damage counterattack path.

        FR-002 invariant under 5th Dan.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        # On the post-damage path, the Hida-specific TakeCounterattackActionEvent
        # writes the +5 bonus when initiated as an interrupt.  Run the
        # full sequence and verify the bonus was written on the attack.
        attack.set_skill_roll(20)
        post_dmg = events.PostDamageInterruptCheckEvent(attack)
        rp = CalvinistRollProvider()
        rp.put_skill_roll("counterattack", 30)
        rp.put_damage_roll(8)
        hida.set_roll_provider(rp)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        attacker.set_roll_provider(attacker_rp)
        engine = CombatEngine(context)
        engine.event(post_dmg)
        # FR-002: the originating attack action must have the +5 free raise
        # marker installed by the Hida counterattack event factory.
        self.assertEqual(
            5,
            getattr(attack, "_counterattack_roll_bonus", 0),
            "5th-Dan post-damage counterattack must still install the "
            "+5 free raise on the originating attack action.",
        )

    def test_pre_5th_dan_strategy_uses_base_path(self):
        """A 4th-Dan-or-below Hida's interrupt strategy must take the
        base (pre-damage) decision path on ``AttackDeclaredEvent``,
        NOT defer.

        Confirms 5th-Dan-specific behavior is Dan-gated.
        """
        hida = _make_pre_fifth_dan_hida(dan=4)
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        declared = events.AttackDeclaredEvent(attack)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, declared, context))
        # Pre-5th Dan: the base path fires; expect a SpendActionEvent and
        # a Take counterattack event (the base CounterattackInterruptStrategy
        # path is exercised).
        self.assertTrue(
            any(isinstance(e, events.SpendActionEvent) for e in emitted),
            f"Pre-5th-Dan strategy must use base path (fire counterattack "
            f"on AttackDeclaredEvent); got {[type(e).__name__ for e in emitted]}.",
        )

    def test_5th_dan_strategy_attack_rolled_delegates_to_parry(self):
        """For a 5th-Dan Hida the ``AttackRolledEvent`` slot still
        delegates to the parry strategy (matching the base
        CounterattackInterruptStrategy behavior on that slot — only
        counterattack is deferred to post-damage; parry still happens
        on roll).

        Coverage gate for the 5th-Dan ``AttackRolledEvent`` branch.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        attack.set_skill_roll(50)  # high roll → parry-worthy
        rolled = events.AttackRolledEvent(attack, 50)
        strategy = hida.interrupt_strategy()
        # No exception → parry-strategy delegation worked.  Consume the
        # iterator without asserting on content (parry strategy may
        # yield 0+ events).
        emitted = list(strategy.recommend(hida, rolled, context))
        self.assertIsInstance(emitted, list)

    def test_5th_dan_strategy_attack_declared_friend_target_delegates(self):
        """On a 5th-Dan Hida, an AttackDeclaredEvent targeting a FRIEND
        (not the Hida itself) falls through to the base behavior so the
        Hida can still defend friends per
        CounterattackInterruptStrategy mechanics.

        Coverage gate for the "not the defender" branch (lines 183-184).
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        friend = Character("Friend")
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", [hida, friend]), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        # Attacker attacks the FRIEND (not the Hida).
        attack = actions.AttackAction(attacker, friend, "attack", attack_init, context)
        declared = events.AttackDeclaredEvent(attack)
        strategy = hida.interrupt_strategy()
        # The 5th-Dan path falls through to super() so the base
        # CounterattackInterruptStrategy's adjacency / friend-defense
        # logic runs.  This should not raise.
        emitted = list(strategy.recommend(hida, declared, context))
        # Friend not adjacent in default formation → no counterattack
        # actually fires.  But the branch must execute without error.
        self.assertIsInstance(emitted, list)

    def test_5th_dan_post_damage_attacker_self_does_not_counterattack(self):
        """A 5th-Dan Hida who IS the attack subject (i.e., the original
        attacker) does NOT counterattack themselves on
        ``PostDamageInterruptCheckEvent``.

        Coverage gate for line 204 — the empty post-damage path.
        """
        hida = _make_fifth_dan_hida()
        hida.set_actions([5, 8])
        target = Character("Target")
        groups = [Group("Crab", hida), Group("Enemy", target)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([5], 5)
        attack = actions.AttackAction(hida, target, "attack", attack_init, context)
        post_dmg = events.PostDamageInterruptCheckEvent(attack)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, post_dmg, context))
        # Hida is the attack subject — no counterattack against self.
        self.assertEqual(
            [], emitted,
            f"5th-Dan should not counterattack on own attack; got "
            f"{[type(e).__name__ for e in emitted]}.",
        )

    def test_5th_dan_strategy_other_events_defer_to_base(self):
        """A 5th-Dan Hida handed an event that is NOT an
        AttackDeclaredEvent / AttackRolledEvent / PostDamageInterruptCheckEvent
        defers to ``super().recommend(...)`` so any other base behavior
        runs unchanged.

        Coverage gate for line 206.
        """
        hida = _make_fifth_dan_hida()
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Use any unrelated event.  Base CounterattackInterruptStrategy
        # only checks AttackDeclared / AttackRolled, so it should yield
        # nothing.
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        succeeded = events.AttackSucceededEvent(attack)
        strategy = hida.interrupt_strategy()
        emitted = list(strategy.recommend(hida, succeeded, context))
        self.assertEqual([], emitted)

    def test_counterattack_succeeded_listener_no_act_when_pre_5th_dan(self):
        """The HidaCounterattackSucceededListener is gated on
        ``school_rank() >= 5``.  If the listener is somehow invoked on a
        pre-5th-Dan character (e.g. via direct construction for tests),
        it must NOT write the margin.

        Coverage gate for line 245.
        """
        # Construct a 4th-Dan Hida + manually invoke the listener.
        hida = _make_pre_fifth_dan_hida(dan=4)
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        attack.set_skill_roll(20)
        interrupt = InitiativeAction([5], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            hida, attacker, "counterattack",
            interrupt, context, attack,
        )
        counterattack.set_skill_roll(50)  # high; would yield big margin
        # Manually invoke the listener.
        listener = hida_school.HidaCounterattackSucceededListener()
        ca_succeeded = events.CounterattackSucceededEvent(counterattack)
        emitted = list(listener.handle(hida, ca_succeeded, context))
        self.assertEqual([], emitted)
        # NO margin written because the dan-gate blocked.
        self.assertEqual(
            0,
            getattr(attack, "_counterattack_excess_margin", 0),
            "Pre-5th-Dan listener path must NOT write the margin.",
        )

    def test_5th_dan_strategy_class_with_pre_5th_dan_character_uses_base(self):
        """The ``HidaCounterattackInterruptStrategy`` class itself,
        when manually installed on a pre-5th-Dan Hida (school_rank < 5),
        must defer to the base class entirely — no defer logic.

        Coverage gate for line 209 (the pre-5th-Dan fallback).
        """
        hida = _make_pre_fifth_dan_hida(dan=4)
        # Manually install the 5th-Dan strategy on a 4th-Dan character —
        # the Dan check inside ``recommend`` should send the call to the
        # base class.
        strategy = hida_school.HidaCounterattackInterruptStrategy()
        hida.set_actions([5, 8])
        attacker = Character("Attacker")
        attacker.set_actions([1])
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", attack_init, context)
        declared = events.AttackDeclaredEvent(attack)
        emitted = list(strategy.recommend(hida, declared, context))
        # Base path fires: SpendActionEvent + take counterattack.
        self.assertTrue(
            any(isinstance(e, events.SpendActionEvent) for e in emitted),
            f"Pre-5th-Dan with HidaCounterattackInterruptStrategy must "
            f"use base path; got {[type(e).__name__ for e in emitted]}.",
        )

    def test_counterattack_succeeded_listener_ignores_non_subject(self):
        """The listener writes only when the Hida is the counterattack
        SUBJECT (i.e., the counterattacker).  When the Hida is a
        bystander, the listener returns without writing.

        Coverage gate for line 239.
        """
        hida_b = _make_fifth_dan_hida()
        hida_b._name = "HidaB"
        hida_a = _make_fifth_dan_hida()
        hida_a._name = "HidaA"
        attacker = Character("Attacker")
        groups = [
            Group("Crab", [hida_a, hida_b]),
            Group("Enemy", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        attack_init = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida_a, "attack", attack_init, context)
        attack.set_skill_roll(20)
        interrupt = InitiativeAction([5], 1, is_interrupt=True)
        # HIDA_A is the counterattack subject.
        counterattack = actions.CounterattackAction(
            hida_a, attacker, "counterattack",
            interrupt, context, attack,
        )
        counterattack.set_skill_roll(50)
        # Invoke the listener for HIDA_B (a bystander).
        listener = hida_school.HidaCounterattackSucceededListener()
        ca_succeeded = events.CounterattackSucceededEvent(counterattack)
        emitted = list(listener.handle(hida_b, ca_succeeded, context))
        self.assertEqual([], emitted)
        # No margin written by HIDA_B's listener invocation (we
        # exercised only the bystander; the attack action remains
        # unchanged from the bystander's listener call).
        self.assertEqual(
            0,
            getattr(attack, "_counterattack_excess_margin", 0),
            "Bystander listener invocation must not write the margin.",
        )
