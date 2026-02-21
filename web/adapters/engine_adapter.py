import tempfile

from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.features import SummaryFeatures, write_feature_file_header
from simulation.groups import Group
from web.adapters.character_adapter import config_to_character
from web.adapters.combat_observer import CombatObserver, DetailedCombatEngine, TrackingRollProvider
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.models import BatchResult, CharacterConfig, GroupConfig, SingleCombatResult


def _build_characters_and_context(characters: list[CharacterConfig], groups: list[GroupConfig]):
    """Build Character objects, Groups, and an EngineContext from configs."""
    # build character objects
    char_objects = {}
    for config in characters:
        char_objects[config.name] = config_to_character(config)

    # sort groups so control is first
    sorted_groups = sorted(groups, key=lambda g: 0 if g.is_control else 1)

    # build groups
    group_objects = []
    for group_config in sorted_groups:
        chars = [char_objects[name] for name in group_config.character_names]
        group_objects.append(Group(group_config.name, chars))

    # create context
    context = EngineContext(group_objects)
    context.initialize()
    return char_objects, context


def _build_engine(characters: list[CharacterConfig], groups: list[GroupConfig]):
    """Build Character objects, Groups, and a CombatEngine from configs."""
    char_objects, context = _build_characters_and_context(characters, groups)
    engine = CombatEngine(context)
    return engine, context


def run_batch(characters: list[CharacterConfig], groups: list[GroupConfig], num_trials: int) -> BatchResult:
    """Run N trials and return aggregated results."""
    engine, context = _build_engine(characters, groups)

    per_trial_winners = []
    test_victories = 0
    control_victories = 0

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as feature_file:
        feature_path = feature_file.name
        write_feature_file_header(feature_file)
        for _ in range(num_trials):
            engine.run()
            features = context.features()
            features.complete(context)
            features.write(feature_file)
            winner = features.winner()
            per_trial_winners.append(winner)
            if winner == 1:
                test_victories += 1
            else:
                control_victories += 1
            engine.reset()

    # summarize
    summary = SummaryFeatures()
    summary.summarize(feature_path, num_trials)

    return BatchResult(
        num_trials=num_trials,
        control_victories=control_victories,
        test_victories=test_victories,
        summary=dict(summary._summary),
        per_trial_winners=per_trial_winners,
    )


def run_single(characters: list[CharacterConfig], groups: list[GroupConfig]) -> SingleCombatResult:
    """Run a single combat and return detailed play-by-play results."""
    char_objects, context = _build_characters_and_context(characters, groups)

    # Wrap each character's existing RollProvider with TrackingRollProvider
    # so dice data is captured regardless of provider implementation
    for char in char_objects.values():
        char.set_roll_provider(TrackingRollProvider(char.roll_provider()))

    # Use DetailedCombatEngine with observer for rich output
    observer = CombatObserver()
    engine = DetailedCombatEngine(context, observer)

    engine.run()
    features = context.features()
    features.complete(context)

    play_by_play = DetailedEventFormatter().format_history(engine.history())
    winner = features.winner()
    duration_rounds = features.data().get("duration_rounds", 0)
    duration_phases = features.data().get("duration_phases", 0)

    return SingleCombatResult(
        play_by_play=play_by_play,
        winner=winner,
        features=dict(features.data()),
        duration_rounds=duration_rounds,
        duration_phases=duration_phases,
    )
