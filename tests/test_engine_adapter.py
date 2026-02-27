import os

from web.adapters.character_adapter import load_data_directory
from web.adapters.engine_adapter import run_batch, run_single
from web.models import BatchResult, GroupConfig, SingleCombatResult


def _load_test_configs():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "simulation", "data")
    return load_data_directory(data_dir)


def _find_config(configs, name):
    for c in configs:
        if c.name == name:
            return c
    raise ValueError(f"Config {name} not found")


class TestRunBatch:
    def test_run_batch_returns_batch_result(self):
        configs = _load_test_configs()
        akodo = _find_config(configs, "Akodo")
        bayushi = _find_config(configs, "Bayushi")
        control = GroupConfig(name="east", is_control=True, character_names=["Akodo"])
        test = GroupConfig(name="west", is_control=False, character_names=["Bayushi"])
        result = run_batch([akodo, bayushi], [control, test], num_trials=3)
        assert isinstance(result, BatchResult)
        assert result.num_trials == 3
        assert result.control_victories + result.test_victories == 3
        assert len(result.per_trial_winners) == 3
        for w in result.per_trial_winners:
            assert w in (-1, 1)

    def test_run_batch_summary_has_keys(self):
        configs = _load_test_configs()
        akodo = _find_config(configs, "Akodo")
        bayushi = _find_config(configs, "Bayushi")
        control = GroupConfig(name="east", is_control=True, character_names=["Akodo"])
        test = GroupConfig(name="west", is_control=False, character_names=["Bayushi"])
        result = run_batch([akodo, bayushi], [control, test], num_trials=5)
        assert "duration_rounds_mean" in result.summary
        assert "duration_phases_mean" in result.summary


class TestRunSingle:
    def test_run_single_returns_single_combat_result(self):
        configs = _load_test_configs()
        akodo = _find_config(configs, "Akodo")
        bayushi = _find_config(configs, "Bayushi")
        control = GroupConfig(name="east", is_control=True, character_names=["Akodo"])
        test = GroupConfig(name="west", is_control=False, character_names=["Bayushi"])
        result = run_single([akodo, bayushi], [control, test])
        assert isinstance(result, SingleCombatResult)
        assert result.winner in (-1, 1)
        assert len(result.play_by_play) > 0
        assert result.duration_rounds >= 1
        assert result.duration_phases >= 1

    def test_run_single_play_by_play_has_round(self):
        configs = _load_test_configs()
        akodo = _find_config(configs, "Akodo")
        bayushi = _find_config(configs, "Bayushi")
        control = GroupConfig(name="east", is_control=True, character_names=["Akodo"])
        test = GroupConfig(name="west", is_control=False, character_names=["Bayushi"])
        result = run_single([akodo, bayushi], [control, test])
        assert any("Round" in line for line in result.play_by_play)


class TestCounterattackSchoolsDoNotCrash:
    """Regression tests for counterattack schools.

    Schools with CounterattackInterruptStrategy can cause VP spending
    errors if a counterattack forces the original attacker to spend VP
    on a wound check before the attack's VP are spent. Verify these
    matchups complete without errors.
    """

    def test_mirumoto_vs_kakita_batch(self):
        configs = _load_test_configs()
        mirumoto = _find_config(configs, "Mirumoto")
        kakita = _find_config(configs, "Kakita")
        control = GroupConfig(name="east", is_control=True, character_names=["Mirumoto"])
        test = GroupConfig(name="west", is_control=False, character_names=["Kakita"])
        result = run_batch([mirumoto, kakita], [control, test], num_trials=10)
        assert isinstance(result, BatchResult)
        assert result.num_trials == 10

    def test_mirumoto_vs_akodo_batch(self):
        configs = _load_test_configs()
        mirumoto = _find_config(configs, "Mirumoto")
        akodo = _find_config(configs, "Akodo")
        control = GroupConfig(name="east", is_control=True, character_names=["Mirumoto"])
        test = GroupConfig(name="west", is_control=False, character_names=["Akodo"])
        result = run_batch([mirumoto, akodo], [control, test], num_trials=10)
        assert isinstance(result, BatchResult)
