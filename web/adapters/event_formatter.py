from simulation import events


def format_event(event) -> str | None:
    """Convert a single engine event to a human-readable string, or None if irrelevant."""
    if isinstance(event, events.NewRoundEvent):
        return f"--- Round {event.round} ---"
    if isinstance(event, events.NewPhaseEvent):
        return f"  Phase {event.phase}"
    if isinstance(event, events.TakeAttackActionEvent):
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        skill = event.action.skill()
        return f"{subj} attacks {tgt} with {skill}"
    if isinstance(event, events.AttackRolledEvent):
        return f"  Roll: {event.roll}"
    if isinstance(event, events.AttackSucceededEvent):
        return "  Hit!"
    if isinstance(event, events.AttackFailedEvent):
        return "  Miss."
    if isinstance(event, events.LightWoundsDamageEvent):
        return f"  {event.target.name()} takes {event.damage} light wounds"
    if isinstance(event, events.SeriousWoundsDamageEvent):
        return f"  {event.target.name()} takes {event.damage} serious wounds"
    if isinstance(event, events.WoundCheckSucceededEvent):
        return f"  {event.subject.name()} passes wound check (rolled {event.roll} vs {event.damage})"
    if isinstance(event, events.WoundCheckFailedEvent):
        return f"  {event.subject.name()} fails wound check (rolled {event.roll} vs {event.damage})"
    if isinstance(event, events.SpendVoidPointsEvent):
        return f"  {event.subject.name()} spends {event.amount} VP on {event.skill}"
    if isinstance(event, events.DeathEvent):
        return f"  {event.subject.name()} is killed!"
    if isinstance(event, events.UnconsciousEvent):
        return f"  {event.subject.name()} falls unconscious!"
    if isinstance(event, events.SurrenderEvent):
        return f"  {event.subject.name()} surrenders!"
    if isinstance(event, events.TakeParryActionEvent):
        subj = event.action.subject().name()
        tgt = event.action.target().name()
        return f"  {subj} attempts to parry {tgt}"
    if isinstance(event, events.ParrySucceededEvent):
        return "  Parry succeeded!"
    if isinstance(event, events.ParryFailedEvent):
        return "  Parry failed."
    if isinstance(event, events.ParryRolledEvent):
        return f"  Parry roll: {event.roll}"
    return None


def format_history(history: list) -> list[str]:
    """Convert a full event history into a list of human-readable lines, filtering out irrelevant events."""
    lines = []
    for event in history:
        line = format_event(event)
        if line is not None:
            lines.append(line)
    return lines
