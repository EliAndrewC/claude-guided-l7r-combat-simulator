#!/usr/bin/env python3

#
# duel.py
#
# Iaijutsu duel system for the L7R combat simulator.
#
# Duel rules summary:
# 1. Show Me Your Stance: each duelist rolls Air+Iaijutsu (open, no exploding 10s)
#    to discern opponent's Fire ring (roll / 5) and starting TN (roll / 5).
# 2. Contested Iaijutsu: both roll Fire+Iaijutsu. Winner chooses first in focus/strike.
# 3. Starting TN: each duelist's TN = XP / 10 (rounded down).
# 4. Focus/Strike Loop: winner of contested roll chooses first.
#    Focus: your TN += 5. Strike: triggers simultaneous attacks.
# 5. Strike Resolution: both attack with iaijutsu.
#    Extra damage dice = +1 per 1 exceeded TN (not per 5).
#    Excess kept dice above 10k10 = +5 each (not +2).
#    No VP, no exploding 10s on attack/wound checks.
#    10s DO explode on damage.
# 6. Neither hits: resheathe, restart. Higher roller gets free raise on future damage.
# 7. Either/both hit: transition to normal melee combat.
#

from simulation.events import Event, LightWoundsDamageEvent
from simulation.exceptions import DuelEnded
from simulation.log import logger
from simulation.mechanics.floating_bonuses import FloatingBonus
from simulation.strategies.base import Strategy


def normalize_duel_roll_params(rolled, kept, bonus=0):
    """Normalize roll params with duel rules: excess kept above 10 = +5 each (not +2)."""
    if rolled > 10:
        excess_rolled = rolled - 10
        rolled = 10
        kept += excess_rolled
    if kept > 10:
        excess_kept = kept - 10
        kept = 10
        bonus += 5 * excess_kept
    if rolled < kept:
        kept = rolled
    rolled = max(rolled, 0)
    kept = max(kept, 0)
    return (rolled, kept, bonus)


# ── Duel Events ──────────────────────────────────────────────────────

class ShowMeYourStanceDeclaredEvent(Event):
    def __init__(self, subject):
        super().__init__("duel_stance_declared")
        self.subject = subject


class ShowMeYourStanceRolledEvent(Event):
    def __init__(self, subject, roll, discerned_fire, discerned_tn):
        super().__init__("duel_stance_rolled")
        self.subject = subject
        self.roll = roll
        self.discerned_fire = discerned_fire
        self.discerned_tn = discerned_tn


class DuelInitiativeRolledEvent(Event):
    def __init__(self, challenger, defender, challenger_roll, defender_roll, winner):
        super().__init__("duel_initiative_rolled")
        self.challenger = challenger
        self.defender = defender
        self.challenger_roll = challenger_roll
        self.defender_roll = defender_roll
        self.winner = winner


class IaijutsuFocusEvent(Event):
    def __init__(self, subject, challenger, defender, challenger_tn, defender_tn):
        super().__init__("duel_focus")
        self.subject = subject
        self.challenger = challenger
        self.defender = defender
        self.challenger_tn = challenger_tn
        self.defender_tn = defender_tn


class IaijutsuStrikeEvent(Event):
    def __init__(self, subject, challenger, defender, challenger_tn, defender_tn):
        super().__init__("duel_strike")
        self.subject = subject
        self.challenger = challenger
        self.defender = defender
        self.challenger_tn = challenger_tn
        self.defender_tn = defender_tn


class DuelStrikeRolledEvent(Event):
    def __init__(self, subject, target, roll, tn, is_hit, extra_damage_dice):
        super().__init__("duel_strike_rolled")
        self.subject = subject
        self.target = target
        self.roll = roll
        self.tn = tn
        self.is_hit = is_hit
        self.extra_damage_dice = extra_damage_dice


class DuelResheathEvent(Event):
    def __init__(self, challenger, defender, higher_roller):
        super().__init__("duel_resheath")
        self.challenger = challenger
        self.defender = defender
        self.higher_roller = higher_roller


class DuelEndedEvent(Event):
    def __init__(self, challenger, defender):
        super().__init__("duel_ended")
        self.challenger = challenger
        self.defender = defender


# ── Duel Strike Action ───────────────────────────────────────────────

class DuelStrikeAction:
    """Encapsulates the strike roll and damage for a duel attack."""

    def __init__(self, subject, target, tn):
        self._subject = subject
        self._target = target
        self._tn = tn
        self._skill_roll = None
        self._damage_roll = None

    def subject(self):
        return self._subject

    def target(self):
        return self._target

    def tn(self):
        return self._tn

    def skill_roll(self):
        return self._skill_roll

    def is_hit(self):
        return self._skill_roll is not None and self._skill_roll >= self._tn

    def extra_damage_dice(self):
        if self._skill_roll is None:
            return 0
        return max(0, self._skill_roll - self._tn)

    def roll_skill(self):
        """Roll Fire+Iaijutsu with no exploding 10s."""
        (rolled, kept, mod) = self._subject.get_skill_roll_params(
            self._target, "iaijutsu", ring=None, vp=0
        )
        roll = self._subject.roll_provider().get_skill_roll("iaijutsu", rolled, kept, explode=False) + mod
        self._skill_roll = roll
        logger.info(f"{self._subject.name()} duel strike roll: {roll} vs TN {self._tn}")
        return roll

    def roll_damage(self):
        """Roll damage with duel normalization (+5 per excess kept above 10k10)."""
        extra = self.extra_damage_dice()
        ring = self._subject.ring(self._subject.get_skill_ring("damage"))
        extra_rolled = self._subject.extra_rolled("damage")
        rolled = ring + extra_rolled + extra + self._subject.weapon().rolled()
        kept = self._subject.weapon().kept() + self._subject.extra_kept("damage")
        mod = self._subject.modifier(None, "damage")
        rolled, kept, mod = normalize_duel_roll_params(rolled, kept, mod)
        # Damage rolls DO explode in duels
        roll = self._subject.roll_provider().get_damage_roll(rolled, kept) + mod
        roll = max(0, roll)
        self._damage_roll = roll
        logger.info(f"{self._subject.name()} duel damage roll: {roll}")
        return roll

    def damage_roll(self):
        return self._damage_roll

    def damage_roll_params(self):
        """Return the (rolled, kept, mod) for damage, for annotation purposes."""
        extra = self.extra_damage_dice()
        ring = self._subject.ring(self._subject.get_skill_ring("damage"))
        extra_rolled = self._subject.extra_rolled("damage")
        rolled = ring + extra_rolled + extra + self._subject.weapon().rolled()
        kept = self._subject.weapon().kept() + self._subject.extra_kept("damage")
        mod = self._subject.modifier(None, "damage")
        return normalize_duel_roll_params(rolled, kept, mod)

    def skill_roll_params(self):
        """Return the (rolled, kept, mod) for the skill roll, for annotation purposes."""
        return self._subject.get_skill_roll_params(
            self._target, "iaijutsu", ring=None, vp=0
        )


# ── Duel Strategy ────────────────────────────────────────────────────

class DuelState:
    """State passed to duel strategies to inform focus/strike decisions."""

    def __init__(self, subject_tn, opponent, opponent_tn, focus_count):
        self.subject_tn = subject_tn
        self.opponent = opponent
        self.opponent_tn = opponent_tn
        self.focus_count = focus_count


class AlwaysStrikeDuelStrategy(Strategy):
    """Simple duel strategy: always choose to strike immediately."""

    def recommend(self, character, event, context):
        return "strike"


class FocusThenStrikeDuelStrategy(Strategy):
    """Duel strategy: focus a specified number of times, then strike."""

    def __init__(self, focus_count=1):
        self._focus_count = focus_count
        self._focuses_done = 0

    def recommend(self, character, event, context):
        if self._focuses_done < self._focus_count:
            self._focuses_done += 1
            return "focus"
        self._focuses_done = 0
        return "strike"


class SurvivalDuelStrategy(Strategy):
    """Focus until TN is high enough that opponent's expected strike
    won't deal overwhelming damage. If the character can't realistically
    hit the opponent, focuses defensively to minimize incoming damage."""

    MAX_FOCUSES = 5

    def recommend(self, character, event, context):
        if event is None or not hasattr(event, 'opponent'):
            return "strike"
        if event.focus_count >= self.MAX_FOCUSES:
            return "strike"
        opponent = event.opponent
        opponent_expected = self._estimate_roll(opponent, character, context)
        my_expected = self._estimate_roll(character, opponent, context)
        # If we can't realistically hit, focus defensively to minimize damage.
        # Each focus raises our TN by 5, reducing the extra damage dice by 5.
        if my_expected < event.opponent_tn:
            # Keep focusing until opponent just barely hits us
            if event.subject_tn < opponent_expected:
                return "focus"
            return "strike"
        # We can hit — focus until our TN is within 5 of opponent's expected roll
        if event.subject_tn < opponent_expected - 5:
            return "focus"
        return "strike"

    @staticmethod
    def _estimate_roll(character, opponent, context):
        """Estimate a character's expected iaijutsu strike roll.

        Uses get_skill_roll_params to account for school bonuses,
        extra rolled/kept conversions, and modifiers.
        """
        (rolled, kept, mod) = character.get_skill_roll_params(
            opponent, "iaijutsu", ring=None, vp=0
        )
        if context is not None:
            return context.mean_roll(rolled, kept) + mod
        return kept * 6 + mod


# ── Duel Orchestrator ────────────────────────────────────────────────

class IaijutsuDuelEvent(Event):
    """Top-level playable event that runs the full iaijutsu duel."""

    def __init__(self, challenger, defender):
        super().__init__("iaijutsu_duel")
        self.challenger = challenger
        self.defender = defender

    def play(self, context):
        challenger = self.challenger
        defender = self.defender

        # ── Show Me Your Stance ──
        yield ShowMeYourStanceDeclaredEvent(challenger)
        yield ShowMeYourStanceDeclaredEvent(defender)

        # Each rolls Air+Iaijutsu (no exploding 10s) to discern opponent
        c_stance_roll = self._roll_stance(challenger, defender)
        d_stance_roll = self._roll_stance(defender, challenger)

        # Discern opponent's Fire ring and starting TN
        c_discerned_fire = c_stance_roll // 5
        c_discerned_tn = c_stance_roll // 5
        d_discerned_fire = d_stance_roll // 5
        d_discerned_tn = d_stance_roll // 5

        yield ShowMeYourStanceRolledEvent(challenger, c_stance_roll, c_discerned_fire, c_discerned_tn)
        yield ShowMeYourStanceRolledEvent(defender, d_stance_roll, d_discerned_fire, d_discerned_tn)

        # ── Starting TNs ──
        c_tn = challenger.xp() // 10
        d_tn = defender.xp() // 10

        # ── Duel Rounds (may repeat if neither hits) ──
        while True:
            # Contested Iaijutsu: Fire+Iaijutsu
            c_init_roll = self._roll_contested(challenger, defender)
            d_init_roll = self._roll_contested(defender, challenger)
            if c_init_roll >= d_init_roll:
                winner = challenger
            else:
                winner = defender

            yield DuelInitiativeRolledEvent(challenger, defender, c_init_roll, d_init_roll, winner)

            # Focus/Strike Loop
            # Winner chooses first, then loser, alternating
            if winner == challenger:
                first, second = challenger, defender
            else:
                first, second = defender, challenger

            someone_struck = False
            first_struck = False
            second_struck = False

            first_focuses = 0
            second_focuses = 0

            while not (first_struck and second_struck):
                # First chooses
                if not first_struck:
                    choice = self._get_duel_choice(
                        first, second, c_tn if first == challenger else d_tn,
                        d_tn if first == challenger else c_tn,
                        first_focuses, context,
                    )
                    if choice == "focus":
                        if first == challenger:
                            c_tn += 5
                        else:
                            d_tn += 5
                        first_focuses += 1
                        yield IaijutsuFocusEvent(first, challenger, defender, c_tn, d_tn)
                    else:
                        first_struck = True
                        yield IaijutsuStrikeEvent(first, challenger, defender, c_tn, d_tn)

                # Second chooses
                if not second_struck:
                    if first_struck and not someone_struck:
                        # First declared strike; second must also strike now
                        someone_struck = True
                        second_struck = True
                        yield IaijutsuStrikeEvent(second, challenger, defender, c_tn, d_tn)
                    else:
                        choice = self._get_duel_choice(
                            second, first, d_tn if second == challenger else c_tn,
                            c_tn if second == challenger else d_tn,
                            second_focuses, context,
                        )
                        if choice == "focus":
                            if second == challenger:
                                c_tn += 5
                            else:
                                d_tn += 5
                            second_focuses += 1
                            yield IaijutsuFocusEvent(second, challenger, defender, c_tn, d_tn)
                        else:
                            second_struck = True
                            yield IaijutsuStrikeEvent(second, challenger, defender, c_tn, d_tn)
                            if not first_struck:
                                # second struck first, so first must also strike
                                first_struck = True
                                yield IaijutsuStrikeEvent(first, challenger, defender, c_tn, d_tn)

            # ── Resolve Simultaneous Strikes ──
            c_action = DuelStrikeAction(challenger, defender, d_tn)
            d_action = DuelStrikeAction(defender, challenger, c_tn)

            c_strike_roll = c_action.roll_skill()
            d_strike_roll = d_action.roll_skill()

            c_hit = c_action.is_hit()
            d_hit = d_action.is_hit()

            yield DuelStrikeRolledEvent(
                challenger, defender, c_strike_roll, d_tn,
                c_hit, c_action.extra_damage_dice(),
            )
            yield DuelStrikeRolledEvent(
                defender, challenger, d_strike_roll, c_tn,
                d_hit, d_action.extra_damage_dice(),
            )

            # Roll damage for hits
            if c_hit:
                damage = c_action.roll_damage()
                yield LightWoundsDamageEvent(challenger, defender, damage, duel=True)
            if d_hit:
                damage = d_action.roll_damage()
                yield LightWoundsDamageEvent(defender, challenger, damage, duel=True)

            if c_hit or d_hit:
                # At least one hit: transition to normal combat
                yield DuelEndedEvent(challenger, defender)
                raise DuelEnded("At least one duelist was hit")
            else:
                # Neither hit: resheathe
                if c_strike_roll >= d_strike_roll:
                    higher_roller = challenger
                else:
                    higher_roller = defender
                yield DuelResheathEvent(challenger, defender, higher_roller)
                # Higher roller gets a free raise on future damage
                higher_roller.gain_floating_bonus(FloatingBonus("damage", 5))
                logger.info(f"{higher_roller.name()} gains a free raise on damage from resheath")

    def _roll_stance(self, subject, opponent):
        """Roll Air+Iaijutsu for Show Me Your Stance (no exploding 10s)."""
        from simulation.mechanics.roll_params import normalize_roll_params
        air = subject.ring("air")
        skill = subject.skill("iaijutsu")
        extra_rolled = subject.extra_rolled("iaijutsu")
        rolled = air + skill + extra_rolled
        kept = air
        rolled, kept, mod = normalize_roll_params(rolled, kept, 0)
        roll = subject.roll_provider().get_skill_roll("iaijutsu", rolled, kept, explode=False) + mod
        return roll

    def _roll_contested(self, subject, opponent):
        """Roll Fire+Iaijutsu for contested initiative."""
        (rolled, kept, mod) = subject.get_skill_roll_params(
            opponent, "iaijutsu", ring=None, vp=0
        )
        roll = subject.roll_provider().get_skill_roll("iaijutsu", rolled, kept, explode=True) + mod
        return roll

    @staticmethod
    def _get_duel_choice(character, opponent, subject_tn, opponent_tn, focus_count, context):
        """Ask the character's duel strategy for focus or strike."""
        strategy = character.duel_focus_or_strike_strategy()
        if strategy is None:
            strategy = SurvivalDuelStrategy()
        state = DuelState(subject_tn, opponent, opponent_tn, focus_count)
        return strategy.recommend(character, state, context)
