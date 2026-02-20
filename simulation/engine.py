
from abc import abstractmethod

from simulation import events
from simulation.exceptions import CombatEnded
from simulation.log import logger

class Engine(object):
  '''
  Generic event loop for the L7R combat simulator.
  This runs a loop that runs events on characters in the appropriate order.
  '''

  def __init__(self, context):
    self._context = context
    self._history = []

  def context(self):
    return self._context

  def event(self, event):
    logger.debug('Got {} event'.format(event.name))
    self.history().append(event)
    self.context().features().observe_event(event, self.context())
    # status events might end the run
    if isinstance(event, events.StatusEvent):
      logger.debug('Evaluating status event')
      self.context().update_status(event)
    # take action events require reevaluating initiative priority
    if isinstance(event, events.InitiativeChangedEvent) or isinstance(event, events.TakeActionEvent):
      logger.debug('Reevaluating initiative priority')
      self.context().reevaluate_initiative()
    # playable events should be played out completely
    if hasattr(event, 'play'):
      # event play method is a generator for more events
      for next_event in event.play(self.context()):
        self.event(next_event)
    else:
      # play event on each character in initiative order
      for character in self.context().characters():
        for response in character.event(event, self.context()):
          self.event(response)

  def history(self):
    return self._history

  def reset(self):
    self.history().clear()
    self.context().reset()

  @abstractmethod
  def run(self):
    raise NotImplementedError()


class CombatEngine(Engine):
  '''
  Class to represent the combat event loop.
  Combat timing is broken up into rounds.
  Each round is timed in eleven phases, numbered 0 through 10.
  In each phase, each character is given the option to act in initiative order.
  Characters can choose to take actions, which are also resolved as a series of events.
  During combat, characters may lose consciousness, die, surrender, or flee.
  The loop ends when only one side is still fighting.
  '''

  def __init__(self, context):
    super().__init__(context)

  def run(self):
    while (True):
      try:
        self.run_round()
      except CombatEnded:
        logger.info('---------- Combat ended ----------')
        break
      except KeyboardInterrupt:
        break

  def run_duel(self):
    # validate groups and characters
    if len(self.context.groups()) != 2:
      raise RuntimeError('Duel requires two groups')
    for group in self.context.groups():
      if len(group) != 1:
        raise RuntimeError('Duel must be a one-on-one fight')
    # determine challenger and defender
    # challenger is always the test group
    challenger = self.context.test_group().get(0)
    defender = self.context.groups().get(0).get(0)
    # run iaijutsu duels until somebody is cut or defeated
    while (True):
      try:
        self.event(IaijutsuDuelEvent(challenger, defender))
      except CombatEnded:
        logger.info('---------- Combat ended ----------')
        return
      except DuelEnded:
        logger.info('---- Duel ended, melee begins ----')
        break
    # continue in normal melee combat
    self.run()

  def run_round(self):
    logger.info('Starting Round {}'.format(self.context().round()))
    self.event(events.NewRoundEvent(self.context().round()))
    if self.context().phase() != 0:
      raise RuntimeError('New round should begin in phase 0')
    self.context().reevaluate_initiative()
    while True:
      logger.info('Starting Phase {}'.format(self.context().phase()))
      # start new phase
      self.event(events.NewPhaseEvent(self.context().phase()))
      # play YourMoveEvent on characters who have actions
      # until they have all responded with HoldActionEvent
      self.context().reset_still_moving()
      while self.context().is_anybody_still_moving():
        for character in self.context().characters():
          if self.context().is_still_moving(character):
            self.event(events.YourMoveEvent(character))
      # end phase
      self.event(events.EndOfPhaseEvent(self.context().phase()))
      # next phase
      if self.context().phase() < 10:
        self.context().next_phase()
      else:
        break
    # end of round
    self.event(events.EndOfRoundEvent(self.context().round()))
    self.context().next_round()

