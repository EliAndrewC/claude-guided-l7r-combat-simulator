import logging
import sys
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import DeathEvent, UnconsciousEvent
from simulation.exceptions import CombatEnded
from simulation.log import logger

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestEngineContext(unittest.TestCase):
    def test_death_combat_continues(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        chiba = Character("Chiba")
        doji = Character("Doji")
        context = EngineContext([[akodo, bayushi], [chiba, doji]])
        # chiba dies
        chiba.take_sw(5)
        event = DeathEvent(chiba)
        # doji is still fighting, combat should continue
        try:
            context.update_status(event)
        except Exception:
            self.fail("Combat should continue when only one character dies!")

    def test_death_combat_ends_death(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        chiba = Character("Chiba")
        doji = Character("Doji")
        context = EngineContext([[akodo, bayushi], [chiba, doji]])
        # akodo and bayushi both die
        akodo.take_sw(5)
        bayushi.take_sw(5)
        event = DeathEvent(bayushi)
        # combat should end
        with self.assertRaises(CombatEnded):
            context.update_status(event)

    def test_combat_ends_unconsciousness(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        chiba = Character("Chiba")
        doji = Character("Doji")
        context = EngineContext([[akodo, bayushi], [chiba, doji]])
        # akodo and bayushi both die
        akodo.take_sw(5)
        bayushi.take_sw(4)
        event = UnconsciousEvent(bayushi)
        # combat should end
        with self.assertRaises(CombatEnded):
            context.update_status(event)

    def test_initialize(self):
        context = EngineContext(
            [
                [
                    Character(),
                ],
                [
                    Character(),
                ],
            ]
        )
        context.initialize()
        # P(1) on 1k1 should be 1.0
        self.assertEqual(1.00, context.p(1, 1, 1))
        # P(10) on 10k10 should be 1.0
        self.assertEqual(1.00, context.p(10, 10, 10))

    def test_mean_rolls(self):
        context = EngineContext(
            [
                [
                    Character(),
                ],
                [
                    Character(),
                ],
            ]
        )
        context.initialize()
        for kept in range(1, 11):
            for rolled in range(kept, 11):
                context.mean_roll(rolled, kept)


class TestEngineContextIaijutsuPhase(unittest.TestCase):
    """The EngineContext tracks which characters are currently in an
    iaijutsu duel's first-strike phase.

    Used by ``HidaWoundCheckStrategy`` to gate the Hida 4th Dan
    SW-for-LW trade per rules/04-schools.md "Hida Bushi School:
    Fourth Dan" — "You may not do this during the iaijutsu phase of
    a duel."  Per Q4 pre-resolution, the gate applies only to the
    actual duelists; bystanders are NOT in the iaijutsu phase.
    """

    def _make_context(self):
        return EngineContext([
            [Character("A"), Character("B")],
            [Character("C"), Character("D")],
        ])

    def test_in_iaijutsu_phase_false_by_default(self):
        """No duel active → all characters are NOT in the iaijutsu phase."""
        context = self._make_context()
        for character in context.characters():
            self.assertFalse(context.in_iaijutsu_phase(character))

    def test_note_duel_event_sets_iaijutsu_phase(self):
        """A DuelInitiativeRolledEvent flags both duelists as being in
        the iaijutsu phase; non-duelists remain out of it.
        """
        from simulation.duel import DuelInitiativeRolledEvent

        context = self._make_context()
        chars = context.characters()
        a, b, c, d = chars[0], chars[1], chars[2], chars[3]
        context.note_duel_event(DuelInitiativeRolledEvent(a, c, 20, 15, a))
        self.assertTrue(context.in_iaijutsu_phase(a))
        self.assertTrue(context.in_iaijutsu_phase(c))
        # Bystanders unaffected (Q4 pre-resolution).
        self.assertFalse(context.in_iaijutsu_phase(b))
        self.assertFalse(context.in_iaijutsu_phase(d))

    def test_note_duel_event_clears_iaijutsu_phase(self):
        """A DuelEndedEvent clears the iaijutsu-phase flag for both
        named duelists.
        """
        from simulation.duel import DuelEndedEvent, DuelInitiativeRolledEvent

        context = self._make_context()
        chars = context.characters()
        a, c = chars[0], chars[2]
        context.note_duel_event(DuelInitiativeRolledEvent(a, c, 20, 15, a))
        self.assertTrue(context.in_iaijutsu_phase(a))
        context.note_duel_event(DuelEndedEvent(a, c))
        self.assertFalse(context.in_iaijutsu_phase(a))
        self.assertFalse(context.in_iaijutsu_phase(c))

    def test_note_duel_event_is_idempotent_on_repeat_initiative(self):
        """The duel loop fires DuelInitiativeRolledEvent on every
        contested-initiative round (multiple rolls if neither hits
        and they resheathe).  Re-adding the same characters is a
        no-op — the flag stays set.
        """
        from simulation.duel import DuelInitiativeRolledEvent

        context = self._make_context()
        chars = context.characters()
        a, c = chars[0], chars[2]
        for _ in range(3):
            context.note_duel_event(DuelInitiativeRolledEvent(a, c, 20, 15, a))
        self.assertTrue(context.in_iaijutsu_phase(a))
        self.assertTrue(context.in_iaijutsu_phase(c))

    def test_note_duel_event_ignored_for_non_duel_events(self):
        """Events other than the two duel-boundary events have no
        effect on iaijutsu-phase tracking.
        """
        from simulation.events import NewPhaseEvent

        context = self._make_context()
        chars = context.characters()
        context.note_duel_event(NewPhaseEvent(phase=1))
        for character in chars:
            self.assertFalse(context.in_iaijutsu_phase(character))

    def test_reset_clears_iaijutsu_phase(self):
        """``context.reset()`` clears the iaijutsu-phase tracker so a
        fresh combat run does not inherit duel state from a previous
        one.
        """
        from simulation.duel import DuelInitiativeRolledEvent

        context = self._make_context()
        chars = context.characters()
        a, c = chars[0], chars[2]
        context.note_duel_event(DuelInitiativeRolledEvent(a, c, 20, 15, a))
        self.assertTrue(context.in_iaijutsu_phase(a))
        context.reset()
        self.assertFalse(context.in_iaijutsu_phase(a))
        self.assertFalse(context.in_iaijutsu_phase(c))
