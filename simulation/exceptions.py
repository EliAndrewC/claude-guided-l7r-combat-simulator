class CombatEnded(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class DuelEnded(Exception):
    def __init__(self, message: str = "Duel ended") -> None:
        self.message = message


class NotEnoughActions(Exception):
    pass
