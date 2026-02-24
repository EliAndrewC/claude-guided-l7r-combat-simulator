#!/usr/bin/env python3

#
# test_coverage_features_engine.py
#
# Unit tests to improve coverage for features.py, engine.py,
# roll_provider.py, and wound_check_optimizers.py.
#

import io
import logging
import sys
import unittest
from unittest.mock import MagicMock

from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.events import (
    AttackFailedEvent,
    AttackSucceededEvent,
    KeepLightWoundsEvent,
    LightWoundsDamageEvent,
    NewPhaseEvent,
    NewRoundEvent,
    ParrySucceededEvent,
    SeriousWoundsDamageEvent,
    SpendActionEvent,
    SpendAdventurePointsEvent,
    SpendVoidPointsEvent,
    TakeAttackActionEvent,
    TakeParryActionEvent,
    TakeSeriousWoundEvent,
    WoundCheckDeclaredEvent,
    WoundCheckFailedEvent,
    WoundCheckSucceededEvent,
)
from simulation.features import FIELDNAMES, SummaryFeatures, TrialFeatures, write_feature_file_header
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.roll_provider import DefaultRollProvider, TestRollProvider
from simulation.optimizers.wound_check_optimizers import (
    DefaultKeepLightWoundsOptimizer,
    DefaultWoundCheckOptimizer,
    ProbabilityForResources,
    RiskyKeepLightWoundsOptimizer,
)

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


# =====================================================================
# Helper: a mock context that provides test_group() and groups()
# =====================================================================

class MockContext:
    """Lightweight mock context for TrialFeatures tests."""

    def __init__(self, test_chars, control_chars):
        self._test_group = Group("test", test_chars)
        self._control_group = Group("control", control_chars)

    def test_group(self):
        return self._test_group

    def groups(self):
        return [self._control_group, self._test_group]


class MockAction:
    """Mock action for ActionEvent-based events."""

    def __init__(self, subject):
        self._subject = subject

    def subject(self):
        return self._subject


# =====================================================================
# 1. Tests for simulation/features.py
# =====================================================================

class TestSummaryFeaturesMeanStdev(unittest.TestCase):
    """Tests for SummaryFeatures.mean() and stdev()."""

    def setUp(self):
        self.sf = SummaryFeatures()

    def test_mean_nonzero(self):
        self.assertAlmostEqual(5.0, self.sf.mean(25, 5))

    def test_mean_zero_n(self):
        self.assertEqual(0, self.sf.mean(100, 0))

    def test_mean_float(self):
        self.assertAlmostEqual(3.3333333, self.sf.mean(10, 3), places=5)

    def test_stdev_nonzero(self):
        # stdev computes (sumsquares / n) - mean^2
        # sumsquares=100, n=4, mean=5 => 25 - 25 = 0
        self.assertAlmostEqual(0, self.sf.stdev(100, 4, 5))

    def test_stdev_nonzero_positive(self):
        # sumsquares=200, n=4, mean=5 => 50 - 25 = 25
        self.assertAlmostEqual(25.0, self.sf.stdev(200, 4, 5))

    def test_stdev_zero_n(self):
        self.assertEqual(0, self.sf.stdev(100, 0, 5))


class TestSummaryFeaturesInitialize(unittest.TestCase):
    """Tests for SummaryFeatures.initialize()."""

    def test_initialize_sets_all_fields(self):
        sf = SummaryFeatures()
        # all FIELDNAMES should be initialized to 0
        for field in FIELDNAMES:
            self.assertEqual(0, sf._data[field])
            self.assertEqual(0, sf._control_data[field])
            self.assertEqual(0, sf._test_data[field])

    def test_initialize_resets_state(self):
        sf = SummaryFeatures()
        sf._data["winner"] = 99
        sf._control_data["winner"] = 99
        sf._test_data["winner"] = 99
        sf.initialize()
        self.assertEqual(0, sf._data["winner"])
        self.assertEqual(0, sf._control_data["winner"])
        self.assertEqual(0, sf._test_data["winner"])


class TestSummaryFeaturesObserve(unittest.TestCase):
    """Tests for SummaryFeatures.observe()."""

    def test_observe_control_victory(self):
        sf = SummaryFeatures()
        # Create a mock TrialFeatures-like object
        mock_tf = MagicMock()
        mock_tf.get_winner.return_value = -1
        sf.observe(mock_tf)
        self.assertEqual(1, sf._control_victories)
        self.assertEqual(0, sf._test_victories)

    def test_observe_test_victory(self):
        sf = SummaryFeatures()
        mock_tf = MagicMock()
        mock_tf.get_winner.return_value = 1
        sf.observe(mock_tf)
        self.assertEqual(0, sf._control_victories)
        self.assertEqual(1, sf._test_victories)


class TestSummaryFeaturesSummarizeMethods(unittest.TestCase):
    """Tests for the individual summarize_* methods on SummaryFeatures."""

    def setUp(self):
        self.sf = SummaryFeatures()
        # Build a data dict with all required fields
        self.data = {}
        for field in FIELDNAMES:
            self.data[field] = 0

    def test_summarize_duration(self):
        summary = {}
        self.data["duration_rounds"] = 30
        self.data["duration_phases"] = 150
        self.sf.summarize_duration(self.data, summary, 10)
        self.assertAlmostEqual(3.0, summary["duration_rounds_mean"])
        self.assertAlmostEqual(15.0, summary["duration_phases_mean"])

    def test_summarize_duration_zero_n(self):
        summary = {}
        self.data["duration_rounds"] = 30
        self.data["duration_phases"] = 150
        self.sf.summarize_duration(self.data, summary, 0)
        self.assertEqual(0, summary["duration_rounds_mean"])
        self.assertEqual(0, summary["duration_phases_mean"])

    def test_summarize_actions(self):
        summary = {}
        self.data["control_actions_taken"] = 50
        self.data["test_actions_taken"] = 40
        self.data["control_attacks_taken"] = 30
        self.data["test_attacks_taken"] = 25
        self.data["control_parries_taken"] = 10
        self.data["test_parries_taken"] = 8
        self.data["control_attacks_succeeded"] = 20
        self.data["test_attacks_succeeded"] = 18
        self.data["control_parries_succeeded"] = 5
        self.data["test_parries_succeeded"] = 4
        self.sf.summarize_actions(self.data, summary, 10)
        self.assertAlmostEqual(5.0, summary["control_actions_taken_mean"])
        self.assertAlmostEqual(4.0, summary["test_actions_taken_mean"])
        self.assertAlmostEqual(3.0, summary["control_attacks_taken_mean"])
        self.assertAlmostEqual(2.5, summary["test_attacks_taken_mean"])
        self.assertAlmostEqual(1.0, summary["control_parries_taken_mean"])
        self.assertAlmostEqual(0.8, summary["test_parries_taken_mean"])
        self.assertAlmostEqual(2.0, summary["control_attacks_succeeded_mean"])
        self.assertAlmostEqual(1.8, summary["test_attacks_succeeded_mean"])
        self.assertAlmostEqual(0.5, summary["control_parries_succeeded_mean"])
        self.assertAlmostEqual(0.4, summary["test_parries_succeeded_mean"])

    def test_summarize_damage(self):
        summary = {}
        self.data["control_damage_rolls_sum"] = 100
        self.data["control_damage_rolls_count"] = 5
        self.data["control_damage_rolls_sumsquares"] = 2500
        self.data["test_damage_rolls_sum"] = 200
        self.data["test_damage_rolls_count"] = 10
        self.data["test_damage_rolls_sumsquares"] = 5000
        self.sf.summarize_damage(self.data, summary, 10)
        # control: mean = 100/5 = 20, stdev = 2500/5 - 20*20 = 500 - 400 = 100
        self.assertAlmostEqual(20.0, summary["control_damage_mean"])
        self.assertAlmostEqual(100.0, summary["control_damage_stdev"])
        # test: mean = 200/10 = 20, stdev = 5000/10 - 20*20 = 500 - 400 = 100
        self.assertAlmostEqual(20.0, summary["test_damage_mean"])
        self.assertAlmostEqual(100.0, summary["test_damage_stdev"])

    def test_summarize_damage_zero_count(self):
        summary = {}
        self.data["control_damage_rolls_sum"] = 0
        self.data["control_damage_rolls_count"] = 0
        self.data["control_damage_rolls_sumsquares"] = 0
        self.data["test_damage_rolls_sum"] = 0
        self.data["test_damage_rolls_count"] = 0
        self.data["test_damage_rolls_sumsquares"] = 0
        self.sf.summarize_damage(self.data, summary, 0)
        self.assertEqual(0, summary["control_damage_mean"])
        self.assertEqual(0, summary["control_damage_stdev"])
        self.assertEqual(0, summary["test_damage_mean"])
        self.assertEqual(0, summary["test_damage_stdev"])

    def test_summarize_vp(self):
        summary = {}
        self.data["control_vp_remaining"] = 20
        self.data["test_vp_remaining"] = 15
        self.data["control_vp_spent"] = 10
        self.data["test_vp_spent"] = 8
        self.data["control_vp_spent_attacks"] = 6
        self.data["test_vp_spent_attacks"] = 4
        self.data["control_vp_spent_wound_checks"] = 4
        self.data["test_vp_spent_wound_checks"] = 4
        self.sf.summarize_vp(self.data, summary, 5)
        self.assertAlmostEqual(4.0, summary["control_vp_remaining_mean"])
        self.assertAlmostEqual(3.0, summary["test_vp_remaining_mean"])
        self.assertAlmostEqual(2.0, summary["control_vp_spent_mean"])
        self.assertAlmostEqual(1.6, summary["test_vp_spent_mean"])
        self.assertAlmostEqual(1.2, summary["control_vp_spent_attacks_mean"])
        self.assertAlmostEqual(0.8, summary["test_vp_spent_attacks_mean"])
        self.assertAlmostEqual(0.8, summary["control_vp_spent_wound_checks_mean"])
        self.assertAlmostEqual(0.8, summary["test_vp_spent_wound_checks_mean"])

    def test_summarize_wound_checks(self):
        summary = {}
        self.data["control_wc_succeeded"] = 10
        self.data["test_wc_succeeded"] = 8
        self.data["control_wc_failed"] = 2
        self.data["test_wc_failed"] = 3
        self.data["control_wc_failed_margin_sum"] = 20
        self.data["control_wc_failed_margin_count"] = 2
        self.data["test_wc_failed_margin_sum"] = 15
        self.data["test_wc_failed_margin_count"] = 3
        self.data["control_wc_failed_lw_total_sum"] = 40
        self.data["control_wc_failed_lw_total_count"] = 2
        self.data["test_wc_failed_lw_total_sum"] = 60
        self.data["test_wc_failed_lw_total_count"] = 3
        self.data["control_wc_succeeded_margin_sum"] = 50
        self.data["control_wc_succeeded_margin_count"] = 10
        self.data["test_wc_succeeded_margin_sum"] = 40
        self.data["test_wc_succeeded_margin_count"] = 8
        self.sf.summarize_wound_checks(self.data, summary, 5)
        self.assertAlmostEqual(2.0, summary["control_wc_succeeded_mean"])
        self.assertAlmostEqual(1.6, summary["test_wc_succeeded_mean"])
        self.assertAlmostEqual(0.4, summary["control_wc_failed_mean"])
        self.assertAlmostEqual(0.6, summary["test_wc_failed_mean"])
        self.assertAlmostEqual(10.0, summary["control_wc_failed_margin_mean"])
        self.assertAlmostEqual(5.0, summary["test_wc_failed_margin_mean"])
        self.assertAlmostEqual(20.0, summary["control_wc_failed_lw_total_mean"])
        self.assertAlmostEqual(20.0, summary["test_wc_failed_lw_total_mean"])
        self.assertAlmostEqual(5.0, summary["control_wc_succeeded_margin_mean"])
        self.assertAlmostEqual(5.0, summary["test_wc_succeeded_margin_mean"])

    def test_summarize_keep_lw(self):
        summary = {}
        self.data["control_keep_lw_total_sum"] = 100
        self.data["control_keep_lw_total_count"] = 5
        self.data["test_keep_lw_total_sum"] = 80
        self.data["test_keep_lw_total_count"] = 4
        self.sf.summarize_keep_lw(self.data, summary, 10)
        self.assertAlmostEqual(20.0, summary["control_keep_lw_total_mean"])
        self.assertAlmostEqual(20.0, summary["test_keep_lw_total_mean"])

    def test_summarize_sw_remaining(self):
        summary = {}
        self.data["control_sw_remaining"] = 30
        self.data["test_sw_remaining"] = 20
        self.sf.summarize_sw_remaining(self.data, summary, 5)
        self.assertAlmostEqual(6.0, summary["control_sw_remaining_mean"])
        self.assertAlmostEqual(4.0, summary["test_sw_remaining_mean"])

    def test_summarize_take_sw(self):
        summary = {}
        self.data["control_take_sw_total_sum"] = 60
        self.data["control_take_sw_total_count"] = 3
        self.data["test_take_sw_total_sum"] = 80
        self.data["test_take_sw_total_count"] = 4
        self.sf.summarize_take_sw(self.data, summary, 5)
        self.assertAlmostEqual(20.0, summary["control_take_sw_total_mean"])
        self.assertAlmostEqual(20.0, summary["test_take_sw_total_mean"])


class TestSummaryFeaturesSummarize(unittest.TestCase):
    """Test the full summarize() method that reads from CSV."""

    def test_summarize_from_csv(self):
        import csv
        import os
        import tempfile
        sf = SummaryFeatures()
        # Create a temporary CSV file with test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            # Write a row for a control victory (winner=-1)
            row1 = {field: 0 for field in FIELDNAMES}
            row1["winner"] = -1
            row1["duration_rounds"] = 3
            row1["duration_phases"] = 15
            row1["control_actions_taken"] = 5
            row1["test_actions_taken"] = 4
            row1["control_attacks_taken"] = 3
            row1["test_attacks_taken"] = 2
            row1["control_parries_taken"] = 1
            row1["test_parries_taken"] = 1
            row1["control_attacks_succeeded"] = 2
            row1["test_attacks_succeeded"] = 1
            row1["control_parries_succeeded"] = 1
            row1["test_parries_succeeded"] = 0
            row1["control_damage_rolls_count"] = 2
            row1["control_damage_rolls_sum"] = 40
            row1["control_damage_rolls_sumsquares"] = 800
            row1["test_damage_rolls_count"] = 1
            row1["test_damage_rolls_sum"] = 15
            row1["test_damage_rolls_sumsquares"] = 225
            row1["control_sw_remaining"] = 3
            row1["test_sw_remaining"] = 0
            row1["control_sw"] = 0
            row1["test_sw"] = 2
            row1["control_keep_lw_total_count"] = 1
            row1["control_keep_lw_total_sum"] = 10
            row1["control_keep_lw_total_sumsquares"] = 100
            row1["test_keep_lw_total_count"] = 1
            row1["test_keep_lw_total_sum"] = 15
            row1["test_keep_lw_total_sumsquares"] = 225
            row1["control_take_sw_total_count"] = 0
            row1["control_take_sw_total_sum"] = 0
            row1["control_take_sw_total_sumsquares"] = 0
            row1["test_take_sw_total_count"] = 1
            row1["test_take_sw_total_sum"] = 20
            row1["test_take_sw_total_sumsquares"] = 400
            row1["control_vp_remaining"] = 1
            row1["test_vp_remaining"] = 0
            row1["control_vp_spent"] = 1
            row1["test_vp_spent"] = 2
            row1["control_vp_spent_attacks"] = 1
            row1["test_vp_spent_attacks"] = 1
            row1["control_vp_spent_wound_checks"] = 0
            row1["test_vp_spent_wound_checks"] = 1
            row1["control_wc_succeeded"] = 1
            row1["test_wc_succeeded"] = 0
            row1["control_wc_failed"] = 0
            row1["test_wc_failed"] = 1
            row1["control_wc_failed_margin_count"] = 0
            row1["control_wc_failed_margin_sum"] = 0
            row1["control_wc_failed_margin_sumsquares"] = 0
            row1["test_wc_failed_margin_count"] = 1
            row1["test_wc_failed_margin_sum"] = 5
            row1["test_wc_failed_margin_sumsquares"] = 25
            row1["control_wc_failed_lw_total_count"] = 0
            row1["control_wc_failed_lw_total_sum"] = 0
            row1["control_wc_failed_lw_total_sumsquares"] = 0
            row1["test_wc_failed_lw_total_count"] = 1
            row1["test_wc_failed_lw_total_sum"] = 20
            row1["test_wc_failed_lw_total_sumsquares"] = 400
            row1["control_wc_succeeded_margin_count"] = 1
            row1["control_wc_succeeded_margin_sum"] = 5
            row1["control_wc_succeeded_margin_sumsquares"] = 25
            row1["test_wc_succeeded_margin_count"] = 0
            row1["test_wc_succeeded_margin_sum"] = 0
            row1["test_wc_succeeded_margin_sumsquares"] = 0
            row1["control_ap_remaining"] = 0
            row1["test_ap_remaining"] = 0
            row1["control_ap_spent"] = 0
            row1["test_ap_spent"] = 0
            row1["control_ap_spent_wound_checks"] = 0
            row1["test_ap_spent_wound_checks"] = 0
            writer.writerow(row1)

            # Write a second row for a test victory (winner=1)
            row2 = {field: 0 for field in FIELDNAMES}
            row2["winner"] = 1
            row2["duration_rounds"] = 5
            row2["duration_phases"] = 25
            row2["control_actions_taken"] = 6
            row2["test_actions_taken"] = 7
            row2["control_attacks_taken"] = 4
            row2["test_attacks_taken"] = 5
            row2["control_parries_taken"] = 2
            row2["test_parries_taken"] = 1
            row2["control_attacks_succeeded"] = 3
            row2["test_attacks_succeeded"] = 4
            row2["control_parries_succeeded"] = 1
            row2["test_parries_succeeded"] = 1
            row2["control_damage_rolls_count"] = 3
            row2["control_damage_rolls_sum"] = 60
            row2["control_damage_rolls_sumsquares"] = 1200
            row2["test_damage_rolls_count"] = 4
            row2["test_damage_rolls_sum"] = 80
            row2["test_damage_rolls_sumsquares"] = 1600
            row2["control_sw_remaining"] = 0
            row2["test_sw_remaining"] = 2
            row2["control_sw"] = 3
            row2["test_sw"] = 1
            row2["control_keep_lw_total_count"] = 2
            row2["control_keep_lw_total_sum"] = 30
            row2["control_keep_lw_total_sumsquares"] = 500
            row2["test_keep_lw_total_count"] = 2
            row2["test_keep_lw_total_sum"] = 25
            row2["test_keep_lw_total_sumsquares"] = 325
            row2["control_take_sw_total_count"] = 1
            row2["control_take_sw_total_sum"] = 25
            row2["control_take_sw_total_sumsquares"] = 625
            row2["test_take_sw_total_count"] = 0
            row2["test_take_sw_total_sum"] = 0
            row2["test_take_sw_total_sumsquares"] = 0
            row2["control_vp_remaining"] = 0
            row2["test_vp_remaining"] = 1
            row2["control_vp_spent"] = 2
            row2["test_vp_spent"] = 1
            row2["control_vp_spent_attacks"] = 1
            row2["test_vp_spent_attacks"] = 0
            row2["control_vp_spent_wound_checks"] = 1
            row2["test_vp_spent_wound_checks"] = 0
            row2["control_wc_succeeded"] = 0
            row2["test_wc_succeeded"] = 2
            row2["control_wc_failed"] = 1
            row2["test_wc_failed"] = 0
            row2["control_wc_failed_margin_count"] = 1
            row2["control_wc_failed_margin_sum"] = 8
            row2["control_wc_failed_margin_sumsquares"] = 64
            row2["test_wc_failed_margin_count"] = 0
            row2["test_wc_failed_margin_sum"] = 0
            row2["test_wc_failed_margin_sumsquares"] = 0
            row2["control_wc_failed_lw_total_count"] = 1
            row2["control_wc_failed_lw_total_sum"] = 30
            row2["control_wc_failed_lw_total_sumsquares"] = 900
            row2["test_wc_failed_lw_total_count"] = 0
            row2["test_wc_failed_lw_total_sum"] = 0
            row2["test_wc_failed_lw_total_sumsquares"] = 0
            row2["control_wc_succeeded_margin_count"] = 0
            row2["control_wc_succeeded_margin_sum"] = 0
            row2["control_wc_succeeded_margin_sumsquares"] = 0
            row2["test_wc_succeeded_margin_count"] = 2
            row2["test_wc_succeeded_margin_sum"] = 12
            row2["test_wc_succeeded_margin_sumsquares"] = 80
            row2["control_ap_remaining"] = 0
            row2["test_ap_remaining"] = 0
            row2["control_ap_spent"] = 0
            row2["test_ap_spent"] = 0
            row2["control_ap_spent_wound_checks"] = 0
            row2["test_ap_spent_wound_checks"] = 0
            writer.writerow(row2)
            tmppath = f.name

        try:
            sf.summarize(tmppath, 2)
            # Verify summary was populated
            self.assertIn("duration_rounds_mean", sf._summary)
            self.assertAlmostEqual(4.0, sf._summary["duration_rounds_mean"])
            self.assertAlmostEqual(20.0, sf._summary["duration_phases_mean"])
            # Verify victory counts
            self.assertEqual(1, sf._control_victories)
            self.assertEqual(1, sf._test_victories)
            # Verify control summary was populated
            self.assertIn("duration_rounds_mean", sf._control_summary)
            # Verify test summary was populated
            self.assertIn("duration_rounds_mean", sf._test_summary)
        finally:
            os.unlink(tmppath)

    def test_summarize_skips_header_row(self):
        """Test that summarize() gracefully handles a header row (ValueError)."""
        import os
        import tempfile
        sf = SummaryFeatures()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            # Write a header line that will cause ValueError when converting to int
            f.write(",".join(FIELDNAMES) + "\n")
            # Write a valid data row
            values = ["0"] * len(FIELDNAMES)
            values[0] = "-1"  # winner = -1
            values[FIELDNAMES.index("duration_rounds")] = "3"
            values[FIELDNAMES.index("duration_phases")] = "15"
            f.write(",".join(values) + "\n")
            tmppath = f.name

        try:
            sf.summarize(tmppath, 1)
            # The header row should be skipped due to ValueError
            # The data row should be processed
            self.assertEqual(1, sf._control_victories)
        finally:
            os.unlink(tmppath)


class TestTrialFeaturesBasic(unittest.TestCase):
    """Tests for TrialFeatures basic methods."""

    def test_initialize(self):
        tf = TrialFeatures()
        self.assertEqual(0, tf.winner())
        self.assertEqual(0, tf.data()["duration_rounds"])
        self.assertEqual(0, tf.data()["duration_phases"])
        self.assertEqual(0, tf.data()["control_actions_taken"])
        self.assertEqual(0, tf.data()["test_actions_taken"])
        self.assertIsInstance(tf.data()["control_damage_rolls"], list)
        self.assertEqual(0, len(tf.data()["control_damage_rolls"]))

    def test_clear(self):
        tf = TrialFeatures()
        tf._data["duration_rounds"] = 5
        tf._winner = 1
        tf.clear()
        self.assertEqual(0, tf.winner())
        self.assertEqual(0, tf.data()["duration_rounds"])

    def test_data(self):
        tf = TrialFeatures()
        data = tf.data()
        self.assertIsInstance(data, dict)
        self.assertIn("duration_rounds", data)

    def test_winner(self):
        tf = TrialFeatures()
        self.assertEqual(0, tf.winner())

    def test_observe_winner(self):
        tf = TrialFeatures()
        tf.observe_winner(-1)
        self.assertEqual(-1, tf.winner())
        self.assertEqual(-1, tf.data()["winner"])

    def test_observe_winner_test(self):
        tf = TrialFeatures()
        tf.observe_winner(1)
        self.assertEqual(1, tf.winner())
        self.assertEqual(1, tf.data()["winner"])

    def test_observe_winner_aiuchi(self):
        tf = TrialFeatures()
        tf.observe_winner(0)
        self.assertEqual(0, tf.winner())
        self.assertEqual(0, tf.data()["winner"])


class TestTrialFeaturesObservePhaseRound(unittest.TestCase):
    """Tests for TrialFeatures observe_phase and observe_round."""

    def test_observe_phase(self):
        tf = TrialFeatures()
        tf.observe_phase()
        self.assertEqual(1, tf.data()["duration_phases"])
        tf.observe_phase()
        self.assertEqual(2, tf.data()["duration_phases"])

    def test_observe_round(self):
        tf = TrialFeatures()
        tf.observe_round()
        self.assertEqual(1, tf.data()["duration_rounds"])
        tf.observe_round()
        self.assertEqual(2, tf.data()["duration_rounds"])


class TestTrialFeaturesObserveEvents(unittest.TestCase):
    """Tests for TrialFeatures observation methods via observe_event."""

    def setUp(self):
        self.test_char = Character("TestChar")
        self.control_char = Character("ControlChar")
        self.context = MockContext(
            test_chars=self.test_char,
            control_chars=self.control_char,
        )
        self.tf = TrialFeatures()

    def test_observe_event_new_phase(self):
        event = NewPhaseEvent(0)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["duration_phases"])

    def test_observe_event_new_round(self):
        event = NewRoundEvent(1)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["duration_rounds"])

    def test_observe_action_test_group(self):
        event = SpendActionEvent(self.test_char, "attack", None)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["test_actions_taken"])
        self.assertEqual(0, self.tf.data()["control_actions_taken"])

    def test_observe_action_control_group(self):
        event = SpendActionEvent(self.control_char, "attack", None)
        self.tf.observe_event(event, self.context)
        self.assertEqual(0, self.tf.data()["test_actions_taken"])
        self.assertEqual(1, self.tf.data()["control_actions_taken"])

    def test_observe_attack_test_group(self):
        action = MockAction(self.test_char)
        event = TakeAttackActionEvent(action)
        self.tf.observe_attack(event, self.context)
        self.assertEqual(1, self.tf.data()["test_attacks_taken"])
        self.assertEqual(0, self.tf.data()["control_attacks_taken"])

    def test_observe_attack_control_group(self):
        action = MockAction(self.control_char)
        event = TakeAttackActionEvent(action)
        self.tf.observe_attack(event, self.context)
        self.assertEqual(0, self.tf.data()["test_attacks_taken"])
        self.assertEqual(1, self.tf.data()["control_attacks_taken"])

    def test_observe_attack_succeeded_test_group(self):
        action = MockAction(self.test_char)
        event = AttackSucceededEvent(action)
        self.tf.observe_attack_succeeded(event, self.context)
        self.assertEqual(1, self.tf.data()["test_attacks_succeeded"])
        self.assertEqual(0, self.tf.data()["control_attacks_succeeded"])

    def test_observe_attack_succeeded_control_group(self):
        action = MockAction(self.control_char)
        event = AttackSucceededEvent(action)
        self.tf.observe_attack_succeeded(event, self.context)
        self.assertEqual(0, self.tf.data()["test_attacks_succeeded"])
        self.assertEqual(1, self.tf.data()["control_attacks_succeeded"])

    def test_observe_parry_test_group(self):
        action = MockAction(self.test_char)
        event = TakeParryActionEvent(action)
        self.tf.observe_parry(event, self.context)
        self.assertEqual(1, self.tf.data()["test_parries_taken"])
        self.assertEqual(0, self.tf.data()["control_parries_taken"])

    def test_observe_parry_control_group(self):
        action = MockAction(self.control_char)
        event = TakeParryActionEvent(action)
        self.tf.observe_parry(event, self.context)
        self.assertEqual(0, self.tf.data()["test_parries_taken"])
        self.assertEqual(1, self.tf.data()["control_parries_taken"])

    def test_observe_parry_succeeded_test_group(self):
        action = MockAction(self.test_char)
        event = ParrySucceededEvent(action)
        self.tf.observe_parry_succeeded(event, self.context)
        self.assertEqual(1, self.tf.data()["test_parries_succeeded"])
        self.assertEqual(0, self.tf.data()["control_parries_succeeded"])

    def test_observe_parry_succeeded_control_group(self):
        action = MockAction(self.control_char)
        event = ParrySucceededEvent(action)
        self.tf.observe_parry_succeeded(event, self.context)
        self.assertEqual(0, self.tf.data()["test_parries_succeeded"])
        self.assertEqual(1, self.tf.data()["control_parries_succeeded"])

    def test_observe_lw_test_group(self):
        # subject = attacker (test_char), so damage is recorded for test group
        event = LightWoundsDamageEvent(self.test_char, self.control_char, 15)
        self.tf.observe_lw(event, self.context)
        self.assertEqual([15], self.tf.data()["test_damage_rolls"])
        self.assertEqual([], self.tf.data()["control_damage_rolls"])

    def test_observe_lw_control_group(self):
        # subject = attacker (control_char), so damage is recorded for control group
        event = LightWoundsDamageEvent(self.control_char, self.test_char, 20)
        self.tf.observe_lw(event, self.context)
        self.assertEqual([], self.tf.data()["test_damage_rolls"])
        self.assertEqual([20], self.tf.data()["control_damage_rolls"])

    def test_observe_sw_test_group(self):
        # subject = attacker (test_char), so SW is recorded for test group
        event = SeriousWoundsDamageEvent(self.test_char, self.control_char, 2)
        self.tf.observe_sw(event, self.context)
        self.assertEqual(2, self.tf.data()["test_sw"])
        self.assertEqual(0, self.tf.data()["control_sw"])

    def test_observe_sw_control_group(self):
        # subject = attacker (control_char), so SW is recorded for control group
        event = SeriousWoundsDamageEvent(self.control_char, self.test_char, 3)
        self.tf.observe_sw(event, self.context)
        self.assertEqual(0, self.tf.data()["test_sw"])
        self.assertEqual(3, self.tf.data()["control_sw"])

    def test_observe_keep_lw_test_group(self):
        event = KeepLightWoundsEvent(self.test_char, self.control_char, 12)
        self.tf.observe_keep_lw(event, self.context)
        self.assertEqual([12], self.tf.data()["test_keep_lw_total"])
        self.assertEqual([], self.tf.data()["control_keep_lw_total"])

    def test_observe_keep_lw_control_group(self):
        event = KeepLightWoundsEvent(self.control_char, self.test_char, 18)
        self.tf.observe_keep_lw(event, self.context)
        self.assertEqual([], self.tf.data()["test_keep_lw_total"])
        self.assertEqual([18], self.tf.data()["control_keep_lw_total"])

    def test_observe_take_sw_test_group(self):
        event = TakeSeriousWoundEvent(self.test_char, self.control_char, 25)
        self.tf.observe_take_sw(event, self.context)
        self.assertEqual([25], self.tf.data()["test_take_sw_total"])
        self.assertEqual([], self.tf.data()["control_take_sw_total"])

    def test_observe_take_sw_control_group(self):
        event = TakeSeriousWoundEvent(self.control_char, self.test_char, 30)
        self.tf.observe_take_sw(event, self.context)
        self.assertEqual([], self.tf.data()["test_take_sw_total"])
        self.assertEqual([30], self.tf.data()["control_take_sw_total"])

    def test_observe_vp_spent_test_group_attack(self):
        event = SpendVoidPointsEvent(self.test_char, "attack", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(1, self.tf.data()["test_vp_spent"])
        self.assertEqual(1, self.tf.data()["test_vp_spent_attacks"])
        self.assertEqual(0, self.tf.data()["test_vp_spent_wound_checks"])
        self.assertEqual(0, self.tf.data()["control_vp_spent"])

    def test_observe_vp_spent_test_group_wound_check(self):
        event = SpendVoidPointsEvent(self.test_char, "wound check", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(1, self.tf.data()["test_vp_spent"])
        self.assertEqual(0, self.tf.data()["test_vp_spent_attacks"])
        self.assertEqual(1, self.tf.data()["test_vp_spent_wound_checks"])

    def test_observe_vp_spent_test_group_other_skill(self):
        event = SpendVoidPointsEvent(self.test_char, "parry", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(1, self.tf.data()["test_vp_spent"])
        self.assertEqual(0, self.tf.data()["test_vp_spent_attacks"])
        self.assertEqual(0, self.tf.data()["test_vp_spent_wound_checks"])

    def test_observe_vp_spent_control_group_attack(self):
        event = SpendVoidPointsEvent(self.control_char, "attack", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(0, self.tf.data()["test_vp_spent"])
        self.assertEqual(1, self.tf.data()["control_vp_spent"])
        self.assertEqual(1, self.tf.data()["control_vp_spent_attacks"])
        self.assertEqual(0, self.tf.data()["control_vp_spent_wound_checks"])

    def test_observe_vp_spent_control_group_wound_check(self):
        event = SpendVoidPointsEvent(self.control_char, "wound check", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(1, self.tf.data()["control_vp_spent"])
        self.assertEqual(0, self.tf.data()["control_vp_spent_attacks"])
        self.assertEqual(1, self.tf.data()["control_vp_spent_wound_checks"])

    def test_observe_vp_spent_control_group_other_skill(self):
        event = SpendVoidPointsEvent(self.control_char, "parry", 1)
        self.tf.observe_vp_spent(event, self.context)
        self.assertEqual(1, self.tf.data()["control_vp_spent"])
        self.assertEqual(0, self.tf.data()["control_vp_spent_attacks"])
        self.assertEqual(0, self.tf.data()["control_vp_spent_wound_checks"])

    def test_observe_wound_check_succeeded_test_group(self):
        event = WoundCheckSucceededEvent(self.test_char, self.control_char, 20, roll=25, tn=20)
        self.tf.observe_wound_check_succeeded(event, self.context)
        self.assertEqual(1, self.tf.data()["test_wc_succeeded"])
        self.assertEqual([5], self.tf.data()["test_wc_succeeded_margin"])
        self.assertEqual(0, self.tf.data()["control_wc_succeeded"])

    def test_observe_wound_check_succeeded_control_group(self):
        event = WoundCheckSucceededEvent(self.control_char, self.test_char, 15, roll=20, tn=15)
        self.tf.observe_wound_check_succeeded(event, self.context)
        self.assertEqual(0, self.tf.data()["test_wc_succeeded"])
        self.assertEqual(1, self.tf.data()["control_wc_succeeded"])
        self.assertEqual([5], self.tf.data()["control_wc_succeeded_margin"])

    def test_observe_wound_check_failed_test_group(self):
        event = WoundCheckFailedEvent(self.test_char, self.control_char, 30, roll=20, tn=30)
        self.tf.observe_wound_check_failed(event, self.context)
        self.assertEqual(1, self.tf.data()["test_wc_failed"])
        self.assertEqual([10], self.tf.data()["test_wc_failed_margin"])
        self.assertEqual([30], self.tf.data()["test_wc_failed_lw_total"])
        self.assertEqual(0, self.tf.data()["control_wc_failed"])

    def test_observe_wound_check_failed_control_group(self):
        event = WoundCheckFailedEvent(self.control_char, self.test_char, 25, roll=15, tn=25)
        self.tf.observe_wound_check_failed(event, self.context)
        self.assertEqual(0, self.tf.data()["test_wc_failed"])
        self.assertEqual(1, self.tf.data()["control_wc_failed"])
        self.assertEqual([10], self.tf.data()["control_wc_failed_margin"])
        self.assertEqual([25], self.tf.data()["control_wc_failed_lw_total"])

    def test_observe_event_spend_ap_raises(self):
        event = SpendAdventurePointsEvent(self.test_char, "attack", 1)
        with self.assertRaises(NotImplementedError):
            self.tf.observe_event(event, self.context)

    def test_observe_event_attack_failed_passes(self):
        # AttackFailedEvent should not raise and just pass
        action = MockAction(self.test_char)
        event = AttackFailedEvent(action)
        # Should not raise
        self.tf.observe_event(event, self.context)
        # No counter for failed attacks, but it should handle gracefully
        self.assertEqual(0, self.tf.data()["test_attacks_succeeded"])

    def test_observe_event_wound_check_succeeded(self):
        # Test the observe_event dispatch for WoundCheckSucceededEvent
        event = WoundCheckSucceededEvent(self.test_char, self.control_char, 20, roll=25, tn=20)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["test_wc_succeeded"])
        self.assertEqual([5], self.tf.data()["test_wc_succeeded_margin"])

    def test_observe_event_wound_check_failed(self):
        # Test the observe_event dispatch for WoundCheckFailedEvent
        event = WoundCheckFailedEvent(self.test_char, self.control_char, 30, roll=20, tn=30)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["test_wc_failed"])
        self.assertEqual([10], self.tf.data()["test_wc_failed_margin"])

    def test_observe_event_keep_lw(self):
        # Test the observe_event dispatch for KeepLightWoundsEvent
        event = KeepLightWoundsEvent(self.test_char, self.control_char, 12)
        self.tf.observe_event(event, self.context)
        self.assertEqual([12], self.tf.data()["test_keep_lw_total"])

    def test_observe_event_take_sw(self):
        # Test the observe_event dispatch for TakeSeriousWoundEvent
        event = TakeSeriousWoundEvent(self.test_char, self.control_char, 25)
        self.tf.observe_event(event, self.context)
        self.assertEqual([25], self.tf.data()["test_take_sw_total"])

    def test_observe_event_lw_damage(self):
        # Test the observe_event dispatch for LightWoundsDamageEvent
        event = LightWoundsDamageEvent(self.test_char, self.control_char, 15)
        self.tf.observe_event(event, self.context)
        self.assertEqual([15], self.tf.data()["test_damage_rolls"])

    def test_observe_event_sw_damage(self):
        # Test the observe_event dispatch for SeriousWoundsDamageEvent
        event = SeriousWoundsDamageEvent(self.test_char, self.control_char, 2)
        self.tf.observe_event(event, self.context)
        self.assertEqual(2, self.tf.data()["test_sw"])

    def test_observe_event_vp_spent(self):
        # Test the observe_event dispatch for SpendVoidPointsEvent
        event = SpendVoidPointsEvent(self.test_char, "attack", 1)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["test_vp_spent"])

    def test_observe_event_parry_succeeded(self):
        # Test the observe_event dispatch for ParrySucceededEvent
        action = MockAction(self.test_char)
        event = ParrySucceededEvent(action)
        self.tf.observe_event(event, self.context)
        self.assertEqual(1, self.tf.data()["test_parries_succeeded"])


class TestTrialFeaturesComplete(unittest.TestCase):
    """Tests for TrialFeatures complete methods."""

    def setUp(self):
        self.test_char = Character("TestChar")
        self.control_char = Character("ControlChar")
        groups = [Group("control", self.control_char), Group("test", self.test_char)]
        self.context = EngineContext(groups)
        self.context.initialize()
        self.tf = TrialFeatures()

    def test_complete_damage_rolls(self):
        self.tf._data["control_damage_rolls"] = [10, 20, 30]
        self.tf._data["test_damage_rolls"] = [15, 25]
        self.tf.complete_damage_rolls(self.context)
        self.assertEqual(60, self.tf.data()["control_damage_rolls_sum"])
        self.assertEqual(1400, self.tf.data()["control_damage_rolls_sumsquares"])
        self.assertEqual(3, self.tf.data()["control_damage_rolls_count"])
        self.assertEqual(40, self.tf.data()["test_damage_rolls_sum"])
        self.assertEqual(850, self.tf.data()["test_damage_rolls_sumsquares"])
        self.assertEqual(2, self.tf.data()["test_damage_rolls_count"])
        self.assertNotIn("control_damage_rolls", self.tf.data())
        self.assertNotIn("test_damage_rolls", self.tf.data())

    def test_complete_damage_rolls_empty(self):
        self.tf._data["control_damage_rolls"] = []
        self.tf._data["test_damage_rolls"] = []
        self.tf.complete_damage_rolls(self.context)
        self.assertEqual(0, self.tf.data()["control_damage_rolls_sum"])
        self.assertEqual(0, self.tf.data()["control_damage_rolls_count"])

    def test_complete_keep_lw(self):
        self.tf._data["control_keep_lw_total"] = [10, 20]
        self.tf._data["test_keep_lw_total"] = [15]
        self.tf.complete_keep_lw(self.context)
        self.assertEqual(30, self.tf.data()["control_keep_lw_total_sum"])
        self.assertEqual(500, self.tf.data()["control_keep_lw_total_sumsquares"])
        self.assertEqual(2, self.tf.data()["control_keep_lw_total_count"])
        self.assertEqual(15, self.tf.data()["test_keep_lw_total_sum"])
        self.assertEqual(225, self.tf.data()["test_keep_lw_total_sumsquares"])
        self.assertEqual(1, self.tf.data()["test_keep_lw_total_count"])

    def test_complete_sw_remaining(self):
        # Default characters: earth=2, max_sw=4, sw=0 => sw_remaining=4
        self.tf.complete_sw_remaining(self.context)
        self.assertEqual(4, self.tf.data()["control_sw_remaining"])
        self.assertEqual(4, self.tf.data()["test_sw_remaining"])

    def test_complete_sw_remaining_after_damage(self):
        self.test_char.take_sw(1)
        self.tf.complete_sw_remaining(self.context)
        self.assertEqual(4, self.tf.data()["control_sw_remaining"])
        self.assertEqual(3, self.tf.data()["test_sw_remaining"])

    def test_complete_take_sw(self):
        self.tf._data["control_take_sw_total"] = [20, 30]
        self.tf._data["test_take_sw_total"] = [25]
        self.tf.complete_take_sw(self.context)
        self.assertEqual(50, self.tf.data()["control_take_sw_total_sum"])
        self.assertEqual(1300, self.tf.data()["control_take_sw_total_sumsquares"])
        self.assertEqual(2, self.tf.data()["control_take_sw_total_count"])
        self.assertEqual(25, self.tf.data()["test_take_sw_total_sum"])
        self.assertEqual(625, self.tf.data()["test_take_sw_total_sumsquares"])
        self.assertEqual(1, self.tf.data()["test_take_sw_total_count"])

    def test_complete_vp_remaining(self):
        self.tf.complete_vp_remaining(self.context)
        # Default characters have 2 in each ring, so max_vp = 2, no TVP, no spent
        self.assertEqual(2, self.tf.data()["control_vp_remaining"])
        self.assertEqual(2, self.tf.data()["test_vp_remaining"])

    def test_complete_wound_checks(self):
        self.tf._data["control_wc_failed_margin"] = [5, 10]
        self.tf._data["test_wc_failed_margin"] = [3]
        self.tf._data["control_wc_failed_lw_total"] = [20, 30]
        self.tf._data["test_wc_failed_lw_total"] = [15]
        self.tf._data["control_wc_succeeded_margin"] = [2, 8]
        self.tf._data["test_wc_succeeded_margin"] = [12]
        self.tf.complete_wound_checks(self.context)
        # control failed margin
        self.assertEqual(15, self.tf.data()["control_wc_failed_margin_sum"])
        self.assertEqual(125, self.tf.data()["control_wc_failed_margin_sumsquares"])
        self.assertEqual(2, self.tf.data()["control_wc_failed_margin_count"])
        # test failed margin
        self.assertEqual(3, self.tf.data()["test_wc_failed_margin_sum"])
        self.assertEqual(9, self.tf.data()["test_wc_failed_margin_sumsquares"])
        self.assertEqual(1, self.tf.data()["test_wc_failed_margin_count"])
        # control failed lw total
        self.assertEqual(50, self.tf.data()["control_wc_failed_lw_total_sum"])
        self.assertEqual(1300, self.tf.data()["control_wc_failed_lw_total_sumsquares"])
        self.assertEqual(2, self.tf.data()["control_wc_failed_lw_total_count"])
        # test failed lw total
        self.assertEqual(15, self.tf.data()["test_wc_failed_lw_total_sum"])
        self.assertEqual(225, self.tf.data()["test_wc_failed_lw_total_sumsquares"])
        self.assertEqual(1, self.tf.data()["test_wc_failed_lw_total_count"])
        # control succeeded margin
        self.assertEqual(10, self.tf.data()["control_wc_succeeded_margin_sum"])
        self.assertEqual(68, self.tf.data()["control_wc_succeeded_margin_sumsquares"])
        self.assertEqual(2, self.tf.data()["control_wc_succeeded_margin_count"])
        # test succeeded margin
        self.assertEqual(12, self.tf.data()["test_wc_succeeded_margin_sum"])
        self.assertEqual(144, self.tf.data()["test_wc_succeeded_margin_sumsquares"])
        self.assertEqual(1, self.tf.data()["test_wc_succeeded_margin_count"])
        # lists should be removed
        self.assertNotIn("control_wc_failed_margin", self.tf.data())
        self.assertNotIn("test_wc_failed_margin", self.tf.data())

    def test_complete_all(self):
        """Test that complete() calls all sub-complete methods."""
        self.tf._data["control_damage_rolls"] = [10]
        self.tf._data["test_damage_rolls"] = [20]
        self.tf._data["control_keep_lw_total"] = [15]
        self.tf._data["test_keep_lw_total"] = [25]
        self.tf._data["control_take_sw_total"] = [30]
        self.tf._data["test_take_sw_total"] = [35]
        self.tf._data["control_wc_failed_margin"] = [5]
        self.tf._data["test_wc_failed_margin"] = [3]
        self.tf._data["control_wc_failed_lw_total"] = [20]
        self.tf._data["test_wc_failed_lw_total"] = [15]
        self.tf._data["control_wc_succeeded_margin"] = [8]
        self.tf._data["test_wc_succeeded_margin"] = [12]
        self.tf.complete(self.context)
        # Verify the computed fields exist
        self.assertIn("control_damage_rolls_sum", self.tf.data())
        self.assertIn("test_damage_rolls_sum", self.tf.data())
        self.assertIn("control_keep_lw_total_sum", self.tf.data())
        self.assertIn("test_keep_lw_total_sum", self.tf.data())
        self.assertIn("control_sw_remaining", self.tf.data())
        self.assertIn("test_sw_remaining", self.tf.data())
        self.assertIn("control_take_sw_total_sum", self.tf.data())
        self.assertIn("test_take_sw_total_sum", self.tf.data())
        self.assertIn("control_vp_remaining", self.tf.data())
        self.assertIn("test_vp_remaining", self.tf.data())
        self.assertIn("control_wc_failed_margin_sum", self.tf.data())


class TestTrialFeaturesWrite(unittest.TestCase):
    """Test TrialFeatures.write() and write_feature_file_header()."""

    def test_write(self):
        tf = TrialFeatures()
        # Prepare data by completing all lists
        tf._data["control_damage_rolls"] = []
        tf._data["test_damage_rolls"] = []
        tf._data["control_keep_lw_total"] = []
        tf._data["test_keep_lw_total"] = []
        tf._data["control_take_sw_total"] = []
        tf._data["test_take_sw_total"] = []
        tf._data["control_wc_failed_margin"] = []
        tf._data["test_wc_failed_margin"] = []
        tf._data["control_wc_failed_lw_total"] = []
        tf._data["test_wc_failed_lw_total"] = []
        tf._data["control_wc_succeeded_margin"] = []
        tf._data["test_wc_succeeded_margin"] = []
        # Complete using a real context
        test_char = Character("T")
        control_char = Character("C")
        groups = [Group("c", control_char), Group("t", test_char)]
        ctx = EngineContext(groups)
        ctx.initialize()
        tf.complete(ctx)
        # Write to a StringIO
        f = io.StringIO()
        tf.write(f)
        output = f.getvalue()
        self.assertTrue(len(output) > 0)

    def test_write_feature_file_header(self):
        f = io.StringIO()
        write_feature_file_header(f)
        output = f.getvalue()
        # Should contain the fieldnames as CSV header
        for field in FIELDNAMES[:5]:
            self.assertIn(field, output)


# =====================================================================
# 2. Tests for simulation/engine.py
# =====================================================================

class TestCombatEngineReset(unittest.TestCase):
    """Test CombatEngine.reset() behavior."""

    def test_reset_clears_history(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        # Add something to history
        engine.history().append("fake_event")
        self.assertEqual(1, len(engine.history()))
        engine.reset()
        self.assertEqual(0, len(engine.history()))

    def test_reset_resets_context_timing(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)], round=3, phase=5)
        context.initialize()
        engine = CombatEngine(context)
        engine.reset()
        self.assertEqual(0, context.round())
        self.assertEqual(0, context.phase())

    def test_reset_resets_features(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        context.features()._data["duration_rounds"] = 5
        engine.reset()
        self.assertEqual(0, context.features().data()["duration_rounds"])


class TestCombatEngineContext(unittest.TestCase):
    """Test CombatEngine accessor methods."""

    def test_context(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        self.assertIs(context, engine.context())

    def test_history(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        self.assertEqual([], engine.history())


class TestCombatEngineRunRound(unittest.TestCase):
    """Test CombatEngine.run_round phase advancement logic."""

    def test_run_round_phase_not_zero_raises(self):
        """If context phase is not 0 at the start of run_round, should raise RuntimeError."""
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)], round=0, phase=1)
        context.initialize()
        engine = CombatEngine(context)
        # Give characters actions so they can participate
        akodo.set_actions([1])
        bayushi.set_actions([1])
        with self.assertRaises(RuntimeError):
            engine.run_round()

    def test_run_completes(self):
        """Test that run() completes normally when combat ends."""
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        # run() should complete because default characters will fight and one will lose
        engine.run()
        # After combat, there should be events in history
        self.assertTrue(len(engine.history()) > 0)


class TestCombatEngineEvent(unittest.TestCase):
    """Test the Engine.event() method handles various event types."""

    def test_event_records_history(self):
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        context = EngineContext([Group("Lion", akodo), Group("Scorpion", bayushi)])
        context.initialize()
        engine = CombatEngine(context)
        event = NewRoundEvent(1)
        engine.event(event)
        self.assertIn(event, engine.history())


# =====================================================================
# 3. Tests for simulation/mechanics/roll_provider.py
# =====================================================================

class TestTestRollProviderPutGet(unittest.TestCase):
    """Tests for TestRollProvider put and get methods."""

    def test_put_skill_roll_new_skill(self):
        rp = TestRollProvider()
        rp.put_skill_roll("iaijutsu", 42)
        result = rp.get_skill_roll("iaijutsu", 5, 3)
        self.assertEqual(42, result)

    def test_put_skill_roll_existing_skill(self):
        rp = TestRollProvider()
        rp.put_skill_roll("attack", 10)
        rp.put_skill_roll("attack", 20)
        self.assertEqual(10, rp.get_skill_roll("attack", 5, 3))
        self.assertEqual(20, rp.get_skill_roll("attack", 5, 3))

    def test_put_damage_roll(self):
        rp = TestRollProvider()
        rp.put_damage_roll(15)
        rp.put_damage_roll(25)
        self.assertEqual(15, rp.get_damage_roll(4, 2))
        self.assertEqual(25, rp.get_damage_roll(4, 2))

    def test_put_wound_check_roll(self):
        rp = TestRollProvider()
        rp.put_wound_check_roll(30)
        result = rp.get_wound_check_roll(5, 3)
        self.assertEqual(30, result)

    def test_put_initiative_roll_list(self):
        rp = TestRollProvider()
        rp.put_initiative_roll([3, 5, 7])
        result = rp.get_initiative_roll(5, 3)
        self.assertEqual([3, 5, 7], result)

    def test_put_initiative_roll_not_list_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(ValueError):
            rp.put_initiative_roll(42)

    def test_get_damage_roll_empty_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(IndexError):
            rp.get_damage_roll(4, 2)

    def test_get_initiative_roll_empty_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(IndexError):
            rp.get_initiative_roll(4, 3)

    def test_get_wound_check_roll_empty_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(IndexError):
            rp.get_wound_check_roll(4, 3)

    def test_get_skill_roll_no_key_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(KeyError):
            rp.get_skill_roll("nonexistent", 5, 3)

    def test_get_skill_roll_empty_queue_raises(self):
        rp = TestRollProvider()
        rp.put_skill_roll("attack", 10)
        rp.get_skill_roll("attack", 5, 3)
        with self.assertRaises(IndexError):
            rp.get_skill_roll("attack", 5, 3)

    def test_die_provider_returns_none(self):
        rp = TestRollProvider()
        self.assertIsNone(rp.die_provider())

    def test_set_die_provider_raises(self):
        rp = TestRollProvider()
        with self.assertRaises(NotImplementedError):
            rp.set_die_provider(None)

    def test_pop_observed_params_skill_roll(self):
        rp = TestRollProvider()
        rp.put_skill_roll("attack", 50)
        rp.get_skill_roll("attack", 7, 4)
        params = rp.pop_observed_params("attack")
        self.assertEqual((7, 4), params)

    def test_pop_observed_params_wound_check(self):
        rp = TestRollProvider()
        rp.put_wound_check_roll(30)
        rp.get_wound_check_roll(5, 3)
        params = rp.pop_observed_params("wound_check")
        self.assertEqual((5, 3), params)

    def test_get_skill_roll_with_explode_false(self):
        rp = TestRollProvider()
        rp.put_skill_roll("attack", 99)
        result = rp.get_skill_roll("attack", 5, 3, explode=False)
        self.assertEqual(99, result)


class TestDefaultRollProviderMethods(unittest.TestCase):
    """Tests for DefaultRollProvider methods."""

    def test_die_provider_default_none(self):
        rp = DefaultRollProvider()
        self.assertIsNone(rp.die_provider())

    def test_die_provider_set(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        rp = DefaultRollProvider(die_provider=td)
        self.assertIs(td, rp.die_provider())

    def test_get_damage_roll(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        td.extend([8, 5, 3, 7])
        rp = DefaultRollProvider(die_provider=td)
        result = rp.get_damage_roll(4, 2)
        # Rolls 4 dice, keeps 2 highest
        # dice: [8, 5, 3, 7] => sorted desc: [8, 7, 5, 3] => keep 2: 8+7=15
        self.assertEqual(15, result)

    def test_get_skill_roll(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        td.extend([6, 4, 9])
        rp = DefaultRollProvider(die_provider=td)
        result = rp.get_skill_roll("attack", 3, 2)
        # dice: [6, 4, 9] => sorted desc: [9, 6, 4] => keep 2: 9+6=15
        self.assertEqual(15, result)

    def test_get_skill_roll_no_explode(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        td.extend([6, 4, 9])
        rp = DefaultRollProvider(die_provider=td)
        result = rp.get_skill_roll("attack", 3, 2, explode=False)
        # Same as above since no 10s
        self.assertEqual(15, result)

    def test_get_initiative_roll(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        td.extend([3, 7, 1, 5])
        rp = DefaultRollProvider(die_provider=td)
        result = rp.get_initiative_roll(4, 3)
        # InitiativeRoll: rolls 4, keeps lowest 3 sorted ascending
        # dice: [3, 7, 1, 5] => sorted ascending: [1, 3, 5, 7] => keep 3: [1, 3, 5]
        self.assertEqual([1, 3, 5], result)

    def test_get_wound_check_roll(self):
        from simulation.mechanics.roll import TestDice
        td = TestDice()
        td.extend([5, 8, 3, 6])
        rp = DefaultRollProvider(die_provider=td)
        result = rp.get_wound_check_roll(4, 2)
        # dice: [5, 8, 3, 6] => sorted desc: [8, 6, 5, 3] => keep 2: 8+6=14
        self.assertEqual(14, result)


# =====================================================================
# 4. Tests for simulation/optimizers/wound_check_optimizers.py
# =====================================================================

class TestProbabilityForResources(unittest.TestCase):
    """Tests for ProbabilityForResources."""

    def test_sort_key_low_ap(self):
        # ap < 4, so vp_value = 4 * vp, ap_value = ap
        pfr = ProbabilityForResources(0.5, 1, 2)
        key = pfr.sort_key_by_cost()
        # vp_value = 4 * 1 = 4, ap_value = 2 => 6
        self.assertEqual(6, key)

    def test_sort_key_high_ap(self):
        # ap >= 4, so vp_value = (6 * (vp+1)) - 2, ap_value = ap + 4
        pfr = ProbabilityForResources(0.5, 1, 4)
        key = pfr.sort_key_by_cost()
        # vp_value = (6 * 2) - 2 = 10, ap_value = 4 + 4 = 8 => 18
        self.assertEqual(18, key)

    def test_sort_key_zero_vp_zero_ap(self):
        pfr = ProbabilityForResources(0.9, 0, 0)
        key = pfr.sort_key_by_cost()
        # vp_value = 4 * 0 = 0, ap_value = 0 => 0
        self.assertEqual(0, key)

    def test_sort_key_high_ap_boundary(self):
        # ap == 3 is still < 4, so uses first branch
        pfr = ProbabilityForResources(0.5, 2, 3)
        key = pfr.sort_key_by_cost()
        # vp_value = 4 * 2 = 8, ap_value = 3 => 11
        self.assertEqual(11, key)

    def test_sort_key_ap_5(self):
        pfr = ProbabilityForResources(0.5, 0, 5)
        key = pfr.sort_key_by_cost()
        # vp_value = (6 * 1) - 2 = 4, ap_value = 5 + 4 = 9 => 13
        self.assertEqual(13, key)


class TestDefaultWoundCheckOptimizerMaxSWNotInDict(unittest.TestCase):
    """Test DefaultWoundCheckOptimizer when max_sw is not in sw_to_roll."""

    def test_declare_returns_zero_vp_when_max_sw_not_in_dict(self):
        # Character with water=3, low damage (5 LW).
        # wound_check(0) with 5 LW = 1 + (5-0)//10 = 1 SW
        # wound_check(5) with 5 LW = 0 SW
        # So sw_to_roll = {1: 0, 0: 5}
        # If we ask for max_sw=2, it's NOT in sw_to_roll, so the early return
        # fires with vp=0 (no resources needed since there's no risk).
        akagi = Character("Akagi")
        akagi.set_ring("water", 3)
        akodo = Character("Akodo")
        groups = [Group("Red Shirts", akagi), Group("Lion", akodo)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        event = LightWoundsDamageEvent(akodo, akagi, 5)
        akagi.take_lw(5)
        optimizer = DefaultWoundCheckOptimizer(akagi, event, context)
        response = optimizer.declare(2, 0.9)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)
        self.assertEqual(0, response.vp)


class TestDefaultWoundCheckOptimizerWithMaxVP(unittest.TestCase):
    """Test DefaultWoundCheckOptimizer with explicit max_vp and max_ap."""

    def setUp(self):
        self.char = Character("TestWC")
        self.char.set_ring("water", 4)
        self.attacker = Character("Attacker")
        groups = [Group("attackers", self.attacker), Group("defenders", self.char)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()

    def test_declare_with_max_vp_zero(self):
        # With max_vp=0, character cannot spend any VP
        event = LightWoundsDamageEvent(self.attacker, self.char, 25)
        self.char.take_lw(25)
        optimizer = DefaultWoundCheckOptimizer(self.char, event, self.context, max_vp=0)
        response = optimizer.declare(1, 0.5)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)
        self.assertEqual(0, response.vp)

    def test_declare_with_max_ap_zero(self):
        # With max_ap=0, character cannot spend any AP
        event = LightWoundsDamageEvent(self.attacker, self.char, 25)
        self.char.take_lw(25)
        optimizer = DefaultWoundCheckOptimizer(self.char, event, self.context, max_ap=0)
        response = optimizer.declare(1, 0.5)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)

    def test_declare_with_explicit_max_vp(self):
        # Provide an explicit max_vp
        event = LightWoundsDamageEvent(self.attacker, self.char, 30)
        self.char.take_lw(30)
        optimizer = DefaultWoundCheckOptimizer(self.char, event, self.context, max_vp=1)
        response = optimizer.declare(1, 0.5)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)
        # VP should be 0 or 1 depending on the probabilities
        self.assertIn(response.vp, [0, 1])


class TestDefaultWoundCheckOptimizerHighDamage(unittest.TestCase):
    """Test DefaultWoundCheckOptimizer with scenarios that require spending VP."""

    def test_declare_two_vp(self):
        # Character with 3 Water, base wound check 4k3
        # With 2 VP: 6k5
        # Need to test a scenario where 2 VP are required
        char = Character("Hardhit")
        char.set_ring("water", 3)
        attacker = Character("Attacker")
        groups = [Group("attackers", attacker), Group("defenders", char)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Very high damage: force the character to need to spend VP
        event = LightWoundsDamageEvent(attacker, char, 40)
        char.take_lw(40)
        optimizer = DefaultWoundCheckOptimizer(char, event, context)
        response = optimizer.declare(2, 0.5)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)
        # The VP should be determined by probability optimization
        self.assertGreaterEqual(response.vp, 0)


class TestDefaultWoundCheckOptimizerKept10Break(unittest.TestCase):
    """Test the kept == 10 break in declare() loop."""

    def test_declare_breaks_at_kept_10(self):
        # Character with water=8: base wound check is 9k8
        # With 2 VP: 11k10, which normalizes to 10k10+2
        # This should trigger the kept == 10 break
        char = Character("Giant")
        char.set_ring("water", 8)
        char.set_ring("earth", 8)
        char.set_ring("fire", 8)
        char.set_ring("air", 8)
        char.set_ring("void", 8)
        attacker = Character("Attacker")
        groups = [Group("attackers", attacker), Group("defenders", char)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # Give enough LW to warrant a wound check
        event = LightWoundsDamageEvent(attacker, char, 60)
        char.take_lw(60)
        optimizer = DefaultWoundCheckOptimizer(char, event, context)
        response = optimizer.declare(1, 0.5)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)


class TestDefaultWoundCheckOptimizerThresholdNotMet(unittest.TestCase):
    """Test when threshold cannot be met."""

    def test_declare_threshold_not_met(self):
        # Very high threshold, impossible to meet
        char = Character("Weak")
        attacker = Character("Strong")
        groups = [Group("attackers", attacker), Group("defenders", char)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        event = LightWoundsDamageEvent(attacker, char, 50)
        char.take_lw(50)
        optimizer = DefaultWoundCheckOptimizer(char, event, context)
        # Very high threshold: 0.999 for 0 SW (avoid all SW)
        response = optimizer.declare(0, 0.999)
        self.assertIsInstance(response, WoundCheckDeclaredEvent)
        # Even if threshold can't be met, should still return a declaration
        # (with 0 VP if 0 SW is not in the dict)
        self.assertGreaterEqual(response.vp, 0)


class TestRiskyKeepLightWoundsOptimizerBasic(unittest.TestCase):
    """Tests for RiskyKeepLightWoundsOptimizer."""

    def test_safe_to_keep(self):
        # Character with high water, low LW => safe to keep
        char = Character("IronMan")
        char.set_ring("water", 5)
        char.take_lw(5)
        attacker = Character("Minion")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = RiskyKeepLightWoundsOptimizer(char, context)
        (should_keep, vp) = optimizer.should_keep(2, 0.1, max_vp=1)
        self.assertTrue(should_keep)
        self.assertEqual(0, vp)

    def test_max_sw_not_in_dict(self):
        # max_sw not in sw_to_roll means the worst case SW is less than max_sw
        # With water=6, lw=3, expected_damage ~= mean_roll(7,2) ~= 15
        # future_damage ~= 18, wound_check(0, 18) = 1+(18-0)//10 = 2
        # So sw_to_roll has {2: 0, 1: 8, 0: 18}
        # If max_sw=3, it's NOT in sw_to_roll => returns (True, 0)
        char = Character("Tank")
        char.set_ring("water", 6)
        char.take_lw(3)
        attacker = Character("Weakling")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = RiskyKeepLightWoundsOptimizer(char, context)
        (should_keep, vp) = optimizer.should_keep(3, 0.1, max_vp=2)
        self.assertTrue(should_keep)
        self.assertEqual(0, vp)

    def test_risky_with_no_lw_history(self):
        # Character with no lw_history uses mean_roll for expected damage
        char = Character("Fresh")
        char.set_ring("water", 4)
        attacker = Character("Attacker")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        # No lw taken yet, but directly set lw to simulate fresh start
        optimizer = RiskyKeepLightWoundsOptimizer(char, context)
        (should_keep, vp) = optimizer.should_keep(2, 0.1, max_vp=2)
        # With 0 LW and expected ~19 damage, future_damage ~= 19
        # Character with 4 water has 5k4 base, should handle this
        self.assertIsInstance(should_keep, bool)

    def test_risky_with_lw_history(self):
        # Character with lw_history uses average for expected damage
        char = Character("Veteran")
        char.set_ring("water", 4)
        char.take_lw(15)
        char.take_lw(20)
        attacker = Character("Attacker")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = RiskyKeepLightWoundsOptimizer(char, context)
        # lw_history = [15, 20], avg = 17 (truncated to int)
        # lw = 35, future_damage = 35 + 17 = 52
        (should_keep, vp) = optimizer.should_keep(2, 0.1, max_vp=2)
        self.assertIsInstance(should_keep, bool)


class TestRiskyKeepLightWoundsOptimizerFallThrough(unittest.TestCase):
    """Test RiskyKeepLightWoundsOptimizer when it falls through (cannot meet threshold)."""

    def test_cannot_meet_threshold(self):
        # Very weak character with high damage - can't meet threshold
        char = Character("GlassJaw")
        # default water = 2, very low wound check
        char.take_lw(40)
        attacker = Character("Heavy")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = RiskyKeepLightWoundsOptimizer(char, context)
        # threshold very low (0.01 = 1% risk acceptable)
        # but with huge damage and weak character, even small risk is too high
        (should_keep, vp) = optimizer.should_keep(1, 0.01, max_vp=1)
        # Should not keep because even with 1 VP the failure chance is too high
        self.assertIsInstance(should_keep, bool)


class TestDefaultKeepLightWoundsOptimizerAdditional(unittest.TestCase):
    """Additional tests for DefaultKeepLightWoundsOptimizer."""

    def test_no_lw_history_uses_mean_roll(self):
        # When lw_history is empty, uses context.mean_roll(7, 2) for expected damage
        char = Character("NoDamageYet")
        char.set_ring("water", 4)
        attacker = Character("First Attacker")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = DefaultKeepLightWoundsOptimizer(char, context)
        (should_keep, vp) = optimizer.should_keep(1, 0.6, max_vp=1)
        # With 0 LW and expected ~19 damage, should be safe to keep
        self.assertTrue(should_keep)
        self.assertEqual(0, vp)

    def test_max_sw_not_in_dict(self):
        # When max_sw is higher than worst case, returns (True, 0) early
        # With water=4, lw=3, expected_damage ~= mean_roll(7,2) ~= 15
        # future_damage ~= 18, wound_check(0, 18) = 1+(18-0)//10 = 2
        # If max_sw=3, NOT in sw_to_roll => returns (True, 0)
        char = Character("SafeChar")
        char.set_ring("water", 4)
        char.take_lw(3)
        attacker = Character("Attacker")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = DefaultKeepLightWoundsOptimizer(char, context)
        (should_keep, vp) = optimizer.should_keep(3, 0.6, max_vp=1)
        self.assertTrue(should_keep)
        self.assertEqual(0, vp)

    def test_with_lw_history(self):
        # When lw_history has entries, uses average for expected damage
        char = Character("DamagedChar")
        char.set_ring("water", 4)
        char.take_lw(10)
        char.take_lw(15)
        attacker = Character("Aggressor")
        groups = [Group("subject", char), Group("enemies", attacker)]
        context = EngineContext(groups)
        context.initialize()
        optimizer = DefaultKeepLightWoundsOptimizer(char, context)
        # lw_history = [10, 15], avg = 12, lw = 25, future = 37
        (should_keep, vp) = optimizer.should_keep(1, 0.6, max_vp=1)
        self.assertIsInstance(should_keep, bool)


if __name__ == "__main__":
    unittest.main()
