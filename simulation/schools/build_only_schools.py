#!/usr/bin/env python3

#
# build_only_schools.py
#
# BUILD-ONLY stubs for three non-player-character schools
# (rules/11-non_pc_schools.md): Kitsune Warden, Mantis Wave-Treader and
# Suzume Overseer.
#
# They exist so the template generator can build characters of these
# schools - the L7R character sheet generates NPCs from
# simulation/templates/generator.py::generate_template - and they carry
# only what building needs: school ring (with the rules' ring choice),
# school knacks, the standard 1st Dan extra die / 2nd Dan free raise, and
# the standard 4th Dan school-ring +1 and 5 XP discount (which changes
# what the builder can afford).  Special abilities and the 3rd and 5th Dan
# techniques are NOT simulated, so these schools are refused for combat:
# see BUILD_ONLY_SCHOOLS in simulation/templates/strategies.py, enforced by
# web/adapters/character_adapter.py and simulation/character_file.py.
# Implementing them for real goes through the per-school speckit workflow
# (BACKLOG.md).
#

from typing import Any

from simulation.schools.base import BaseSchool

_NON_VOID_RINGS = {"air", "earth", "fire", "water"}
_ALL_RINGS = _NON_VOID_RINGS | {"void"}


class BuildOnlySchool(BaseSchool):
    """Shared behavior for the build-only stubs.

    Subclasses set ``_NAME``, ``_KNACKS``, ``_DEFAULT_RING``, ``_VALID_RINGS``,
    ``_EXTRA_ROLLED`` and ``_FREE_RAISE``; ``school_ring``, the 1st Dan dice
    and the 2nd Dan free raise honor a ``school_choices`` override the same
    way the Ide Diplomat's do.
    """

    BUILD_ONLY = True

    _NAME: str = ""
    _KNACKS: list[str] = []
    _DEFAULT_RING: str = ""
    _VALID_RINGS: set[str] = set()
    _EXTRA_ROLLED: list[str] = []
    _FREE_RAISE: str = ""

    def apply_special_ability(self, character: Any) -> None:
        # Not simulated (build-only stub).
        pass

    def apply_rank_three_ability(self, character: Any) -> None:
        # Not simulated (build-only stub).
        pass

    def apply_rank_four_ability(self, character: Any) -> None:
        # rules/11-non_pc_schools.md, every one of these schools' 4th Dan:
        # "Raise your current and maximum School Ring by 1.  Raising your
        # School Ring now costs 5 fewer XP."  The rest of each 4th Dan is
        # not simulated.
        self.apply_school_ring_raise_and_discount(character)

    def apply_rank_five_ability(self, character: Any) -> None:
        # Not simulated (build-only stub).
        pass

    def extra_rolled(self) -> list[str]:
        chosen = self.choice("first_dan_extra_rolled", self._EXTRA_ROLLED)
        return list(chosen)

    def free_raise_skills(self) -> list[str]:
        return [self.choice("second_dan_free_raise", self._FREE_RAISE)]

    def name(self) -> str:
        return self._NAME

    def school_knacks(self) -> list[str]:
        return list(self._KNACKS)

    def school_ring(self) -> str:
        chosen = self.choice("school_ring", self._DEFAULT_RING)
        if chosen not in self._VALID_RINGS:
            raise ValueError(f"{self._NAME} cannot take {chosen!r} as its school ring")
        return str(chosen)


class KitsuneWardenSchool(BuildOnlySchool):
    # School Ring: Any non-Void.  1st Dan: "Roll one extra die on any three
    # types of rolls."  2nd Dan: "a free raise on any one type of roll."
    _NAME = "Kitsune Warden School"
    _KNACKS = ["absorb void", "commune", "iaijutsu"]
    # Fire: the Special Ability's ring swap cannot reach damage or iaijutsu,
    # so a native Fire ring covers what the swap cannot (progression design).
    _DEFAULT_RING = "fire"
    _VALID_RINGS = _NON_VOID_RINGS
    _EXTRA_ROLLED = ["attack", "damage", "wound check"]
    _FREE_RAISE = "wound check"


class MantisWaveTreaderSchool(BuildOnlySchool):
    # School Ring: Any.  1st Dan: "Roll one extra die on initiative,
    # athletics, and wound checks."  2nd Dan: "a free raise on any one type
    # of roll."
    _NAME = "Mantis Wave-Treader School"
    _KNACKS = ["athletics", "iaijutsu", "worldliness"]
    # Fire: both offensive-posture clauses boost attack AND damage (progression design).
    _DEFAULT_RING = "fire"
    _VALID_RINGS = _ALL_RINGS
    _EXTRA_ROLLED = ["initiative", "athletics", "wound check"]
    _FREE_RAISE = "attack"


class SuzumeOverseerSchool(BuildOnlySchool):
    # School Ring: Water.  1st Dan: "Roll one extra die on precepts,
    # commerce, and wound checks."  2nd Dan: "a free raise on any one type
    # of roll."
    _NAME = "Suzume Overseer School"
    _KNACKS = ["oppose social", "pontificate", "worldliness"]
    _DEFAULT_RING = "water"
    _VALID_RINGS = {"water"}
    _EXTRA_ROLLED = ["precepts", "commerce", "wound check"]
    _FREE_RAISE = "wound check"
