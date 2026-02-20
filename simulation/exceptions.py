
class CombatEnded(Exception):
  def __init__(self, message):
    self.message = message

class NotEnoughActions(Exception):
  pass

