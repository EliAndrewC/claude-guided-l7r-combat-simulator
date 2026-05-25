from typing import Any


class Knowledge:
    """
    Store and return information based on observations of the capabilities and status of other characters.
    Does not make decisions with the knowledge - it only stores and returns observations.
    Strategy classes should use the information from a character or group's Knowledge to help make decisions.
    """

    def __init__(self) -> None:
        self._actions_per_round: dict[str, int] = {}
        self._actions_this_round: dict[str, int] = {}
        self._attack_rolls: dict[str, list[int]] = {}
        self._damage_rolls: dict[str, list[int]] = {}
        self._modifiers: dict[str, list[Any]] = {}
        self._parry_rolls: dict[str, list[int]] = {}
        self._rings: dict[str, dict[str, int]] = {}
        self._skills: dict[str, dict[str, int]] = {}
        self._tn_to_hit: dict[str, int] = {}
        self._wounds: dict[str, int] = {}

    def actions_per_round(self, character: Any) -> int:
        return self._actions_per_round.get(character.name(), 2)

    def actions_remaining(self, character: Any) -> int:
        return max(0, self.actions_per_round(character) - self.actions_taken(character))

    def actions_taken(self, character: Any) -> int:
        return self._actions_this_round.get(character.name(), 0)

    def average_attack_roll(self, character: Any) -> int:
        name = character.name()
        if name in self._attack_rolls.keys():
            return int(sum(self._attack_rolls[name]) / len(self._attack_rolls[name]))
        else:
            return 27

    def average_damage_roll(self, character: Any) -> int:
        name = character.name()
        if name in self._damage_rolls.keys():
            return int(sum(self._damage_rolls[name]) / len(self._damage_rolls[name]))
        else:
            return 18

    def clear(self) -> None:
        self._actions_per_round.clear()
        self._actions_this_round.clear()
        self._attack_rolls.clear()
        self._damage_rolls.clear()
        self._modifiers.clear()
        self._parry_rolls.clear()
        self._rings.clear()
        self._skills.clear()
        self._tn_to_hit.clear()
        self._wounds.clear()

    def end_of_round(self) -> None:
        for name, n in self._actions_this_round.items():
            prev_n = self._actions_per_round.get(name, 0)
            self._actions_per_round[name] = max(prev_n, n)
            self._actions_this_round[name] = 0

    def lw(self, character: Any) -> int:
        result: int = character.lw()
        return result

    def modifier(self, character: Any, target: Any, skill: str) -> int:
        name = character.name()
        if name in self._modifiers.keys():
            return sum([m.apply(target, skill) for m in self._modifiers[name]])
        else:
            return 0

    def observe_action(self, character: Any) -> None:
        name = character.name()
        if name in self._actions_this_round.keys():
            self._actions_this_round[name] += 1
        else:
            self._actions_this_round[name] = 1
        if name not in self._actions_per_round.keys():
            self._actions_per_round[name] = self._actions_this_round[name]
        else:
            if self._actions_this_round[name] > self._actions_per_round[name]:
                self._actions_per_round[name] = self._actions_this_round[name]

    def observe_attack_roll(self, character: Any, roll: int) -> None:
        name = character.name()
        if name in self._attack_rolls.keys():
            self._attack_rolls[name].append(roll)
        else:
            self._attack_rolls[name] = [roll]

    def observe_damage_roll(self, character: Any, damage: int) -> None:
        name = character.name()
        if name in self._damage_rolls.keys():
            self._damage_rolls[name].append(damage)
        else:
            self._damage_rolls[name] = [damage]

    def observe_modifier_added(self, character: Any, modifier: Any) -> None:
        name = character.name()
        if name not in self._modifiers.keys():
            self._modifiers[name] = [modifier]
        else:
            self._modifiers[name].append(modifier)

    def observe_modifier_removed(self, character: Any, modifier: Any) -> None:
        self._modifiers[character.name()].remove(modifier)

    def observe_ring(self, character: Any, ring: str, rank: int) -> None:
        name = character.name()
        if not isinstance(ring, str):
            raise ValueError("observe_ring ring must be str")
        if not isinstance(rank, int):
            raise ValueError("observe_ring rank must be int")
        if name not in self._rings.keys():
            self._rings[name] = {}
        self._rings[name][ring] = rank

    def observe_skill(self, character: Any, skill: str, rank: int) -> None:
        name = character.name()
        if not isinstance(skill, str):
            raise ValueError("observe_skill skill must be str")
        if not isinstance(rank, int):
            raise ValueError("observe_skill rank must be int")
        if name not in self._skills.keys():
            self._skills[name] = {}
        self._skills[name][skill] = rank

    def observe_tn_to_hit(self, character: Any, tn: int) -> None:
        name = character.name()
        adjustment = self.modifier(character, None, "tn to hit")
        if name not in self._tn_to_hit.keys():
            self._tn_to_hit[name] = tn - adjustment

    def observe_wounds(self, character: Any, damage: int) -> None:
        name = character.name()
        if name in self._wounds.keys():
            self._wounds[name] += damage
        else:
            self._wounds[name] = damage

    def sw(self, character: Any) -> int:
        result: int = character.sw()
        return result

    def tn_to_hit(self, target: Any) -> int:
        return self._tn_to_hit.get(target.name(), 20)

    def weapon(self, character: Any) -> Any:
        return character.weapon()

    def wounds(self, character: Any) -> int:
        return self._wounds.get(character.name(), 0)


class TheoreticalCharacter:
    """
    A partial implementation of the Character API that uses knowledge of a character.
    Used when speculating about the character as a target of attacks, parries, etc, in strategy classes.
    """

    def __init__(self, knowledge: Knowledge, character: Any) -> None:
        self._knowledge = knowledge
        self._character = character

    def actions(self) -> list[int]:
        result: list[int] = self._character.actions()
        return result

    def lw(self) -> int:
        result: int = self._character.lw()
        return result

    def ring(self, ring: str) -> int:
        # TODO: figure out how to estimate rings
        return 3

    def sw(self) -> int:
        result: int = self._character.sw()
        return result

    def tn_to_hit(self) -> int:
        return self._knowledge.tn_to_hit(self._character) + self._knowledge.modifier(self._character, None, "tn to hit")

    def attack_rolled_penalty(self) -> int:
        return 0

    def damage_reroll_reduction(self) -> int:
        return 0

    def weapon(self) -> Any:
        return self._knowledge.weapon(self._character)
