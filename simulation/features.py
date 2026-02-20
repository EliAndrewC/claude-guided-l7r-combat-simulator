#!/usr/bin/env python3

#
# features.py
#
#
# Observe and analyze features of an L7R simulation run.
#

import csv

from simulation import events
from simulation.skills import ATTACK_SKILLS

FIELDNAMES = [
  'winner',
  'control_sw_remaining',
  'control_vp_remaining',
  'test_sw_remaining',
  'test_vp_remaining',
  'duration_rounds',
  'duration_phases',
  'control_actions_taken',
  'control_attacks_taken',
  'control_parries_taken',
  'control_attacks_succeeded',
  'control_parries_succeeded',
  'control_ap_remaining',
  'control_ap_spent',
  'control_ap_spent_wound_checks',
  'control_damage_rolls_count',
  'control_damage_rolls_sum',
  'control_damage_rolls_sumsquares',
  'control_keep_lw_total_count',
  'control_keep_lw_total_sum',
  'control_keep_lw_total_sumsquares',
  'control_sw',
  'control_take_sw_total_count',
  'control_take_sw_total_sum',
  'control_take_sw_total_sumsquares',
  'control_vp_spent',
  'control_vp_spent_attacks',
  'control_vp_spent_wound_checks',
  'control_wc_failed',
  'control_wc_failed_lw_total_count',
  'control_wc_failed_lw_total_sum',
  'control_wc_failed_lw_total_sumsquares',
  'control_wc_failed_margin_count',
  'control_wc_failed_margin_sum',
  'control_wc_failed_margin_sumsquares',
  'control_wc_succeeded',
  'control_wc_succeeded_margin_count',
  'control_wc_succeeded_margin_sum',
  'control_wc_succeeded_margin_sumsquares',
  'control_keep_lw_total_count',
  'test_actions_taken',
  'test_attacks_taken',
  'test_parries_taken',
  'test_attacks_succeeded',
  'test_parries_succeeded',
  'test_ap_remaining',
  'test_ap_spent',
  'test_ap_spent_wound_checks',
  'test_damage_rolls_count',
  'test_damage_rolls_sum',
  'test_damage_rolls_sumsquares',
  'test_keep_lw_total_count',
  'test_keep_lw_total_sum',
  'test_keep_lw_total_sumsquares',
  'test_sw',
  'test_take_sw_total_count',
  'test_take_sw_total_sum',
  'test_take_sw_total_sumsquares',
  'test_vp_spent',
  'test_vp_spent_attacks',
  'test_vp_spent_wound_checks',
  'test_wc_failed',
  'test_wc_failed_lw_total_count',
  'test_wc_failed_lw_total_sum',
  'test_wc_failed_lw_total_sumsquares',
  'test_wc_failed_margin_count',
  'test_wc_failed_margin_sum',
  'test_wc_failed_margin_sumsquares',
  'test_wc_succeeded',
  'test_wc_succeeded_margin_count',
  'test_wc_succeeded_margin_sum',
  'test_wc_succeeded_margin_sumsquares'
]


class SummaryFeatures(object):
  '''
  Summary of many simulation runs.

  Questions we might ask after a simulation:
  * Duration in rounds
  * Duration in phases
  * AP remaining
  * AP spent
  * VP remaining
  * VP spent
  * VP spent on attacks
  * VP spent on wound checks
  * Winner's normal initiative actions per round compared to loser
  * Winner's total SW compared to loser (at beginning of combat)
  * SW remaining (winner only)
  * Actions taken
  * Attacks taken
  * Parries taken
  * Interrupt actions taken
  * Interrupt attacks taken
  * Interrupt parries taken
  * Average damage per attack
  '''
  def __init__(self):
    self._control_victories = 0
    self._test_victories = 0
    # summary statistics
    self._summary = {}
    # common results
    self._data = {}
    # results given control group victory
    self._control_data = {}
    self._control_summary = {}
    # results given test group victory
    self._test_data = {}
    self._test_summary = {}
    self.initialize()

  def initialize(self):
    for field in FIELDNAMES:
      self._data[field] = 0
      self._control_data[field] = 0
      self._test_data[field] = 0

  def observe(self, trial_features):
    if trial_features.get_winner() == -1:
      self._control_victories += 1
    else:
      self._test_victories += 1

  def mean(self, total, n):
    if n == 0:
      return 0
    else:
      return total / n

  def stdev(self, sumsquares, n, mean):
    if n == 0:
      return 0
    else:
      return (sumsquares / n) - (mean * mean)

  def summarize(self, feature_fpath, ntrials):
    # load data
    with open(feature_fpath, 'r') as f:
      reader = csv.DictReader(f, fieldnames=FIELDNAMES)
      for row in reader:
        # add to data
        try:
          for k,v in row.items():
            self._data[k] += int(v)
        except ValueError:
          continue
        # determine winner and add to data for that winner's victories
        winner = int(row['winner'])
        if winner == -1:
          self._control_victories += 1
          for k,v in row.items():
            self._control_data[k] += int(v)
        elif winner == 1:
          self._test_victories += 1
          for k,v in row.items():
            self._test_data[k] += int(v)
    # calculate summary metrics
    self.summarize_duration(self._data, self._summary, ntrials)
    self.summarize_duration(self._control_data, self._control_summary, self._control_victories)
    self.summarize_duration(self._test_data, self._test_summary, self._test_victories)
    self.summarize_actions(self._data, self._summary, ntrials)
    self.summarize_actions(self._control_data, self._control_summary, self._control_victories)
    self.summarize_actions(self._test_data, self._test_summary, self._test_victories)
    self.summarize_damage(self._data, self._summary, ntrials)
    self.summarize_damage(self._control_data, self._control_summary, self._control_victories)
    self.summarize_damage(self._test_data, self._test_summary, self._test_victories)
    self.summarize_keep_lw(self._data, self._summary, ntrials)
    self.summarize_keep_lw(self._control_data, self._control_summary, self._control_victories)
    self.summarize_keep_lw(self._test_data, self._test_summary, self._test_victories)
    self.summarize_sw_remaining(self._data, self._summary, ntrials)
    self.summarize_sw_remaining(self._control_data, self._control_summary, self._control_victories)
    self.summarize_sw_remaining(self._test_data, self._test_summary, self._test_victories)
    self.summarize_take_sw(self._data, self._summary, ntrials)
    self.summarize_take_sw(self._control_data, self._control_summary, self._control_victories)
    self.summarize_take_sw(self._test_data, self._test_summary, self._test_victories)
    # TODO: summarize AP
    self.summarize_vp(self._data, self._summary, ntrials)
    self.summarize_vp(self._control_data, self._control_summary, self._control_victories)
    self.summarize_vp(self._test_data, self._test_summary, self._test_victories)
    self.summarize_wound_checks(self._data, self._summary, ntrials)
    self.summarize_wound_checks(self._control_data, self._control_summary, self._control_victories)
    self.summarize_wound_checks(self._test_data, self._test_summary, self._test_victories)

  def summarize_actions(self, datad, summaryd, n):
    #
    # summarize actions taken
    summaryd['control_actions_taken_mean'] = self.mean(datad['control_actions_taken'], n)
    summaryd['test_actions_taken_mean'] = self.mean(datad['test_actions_taken'], n)
    #
    # summarize attacks taken
    summaryd['control_attacks_taken_mean'] = self.mean(datad['control_attacks_taken'], n)
    summaryd['test_attacks_taken_mean'] = self.mean(datad['test_attacks_taken'], n)
    #
    # summarize parries taken
    summaryd['control_parries_taken_mean'] = self.mean(datad['control_parries_taken'], n)
    summaryd['test_parries_taken_mean'] = self.mean(datad['test_parries_taken'], n)
    #
    # summarize attacks succeeded
    summaryd['control_attacks_succeeded_mean'] = self.mean(datad['control_attacks_succeeded'], n)
    summaryd['test_attacks_succeeded_mean'] = self.mean(datad['test_attacks_succeeded'], n)
    #
    # summarize parries succeeded
    summaryd['control_parries_succeeded_mean'] = self.mean(datad['control_parries_succeeded'], n)
    summaryd['test_parries_succeeded_mean'] = self.mean(datad['test_parries_succeeded'], n)
    return

  def summarize_damage(self, datad, summaryd, n):
    #
    # summarize control group damage rolls
    control_damage_mean = self.mean(datad['control_damage_rolls_sum'], datad['control_damage_rolls_count'])
    summaryd['control_damage_mean'] = control_damage_mean
    control_damage_stdev = self.stdev(datad['control_damage_rolls_sumsquares'], datad['control_damage_rolls_count'], control_damage_mean)
    summaryd['control_damage_stdev'] = control_damage_stdev
    #
    # summarize test group damage rolls
    test_damage_mean = self.mean(datad['test_damage_rolls_sum'], datad['test_damage_rolls_count'])
    summaryd['test_damage_mean'] = test_damage_mean
    test_damage_stdev = self.stdev(datad['test_damage_rolls_sumsquares'], datad['test_damage_rolls_count'], test_damage_mean)
    summaryd['test_damage_stdev'] = test_damage_stdev
    #
    # TODO: summarize SW dealt
    #
    return

  def summarize_duration(self, datad, summaryd, n):
    #
    # summarize duration in rounds
    summaryd['duration_rounds_mean'] = self.mean(datad['duration_rounds'], n)
    #
    # summarize duration in phases
    summaryd['duration_phases_mean'] = self.mean(datad['duration_phases'], n)
    return

  def summarize_keep_lw(self, datad, summaryd, n):
    #
    # mean LW kept
    summaryd['control_keep_lw_total_mean'] = self.mean(datad['control_keep_lw_total_sum'], datad['control_keep_lw_total_count'])
    summaryd['test_keep_lw_total_mean'] = self.mean(datad['test_keep_lw_total_sum'], datad['test_keep_lw_total_count'])
    return

  def summarize_sw_remaining(self, datad, summaryd, n): 
    #
    # summarize sw remaining
    summaryd['test_sw_remaining_mean'] = self.mean(datad['test_sw_remaining'], n)
    summaryd['control_sw_remaining_mean'] = self.mean(datad['control_sw_remaining'], n)
    return 

  def summarize_take_sw(self, datad, summaryd, n):
    #
    # mean LW total when taking a SW after successful Wound Check
    summaryd['control_take_sw_total_mean'] = self.mean(datad['control_take_sw_total_sum'], datad['control_take_sw_total_count'])
    summaryd['test_take_sw_total_mean'] = self.mean(datad['test_take_sw_total_sum'], datad['test_take_sw_total_count'])
    return

  def summarize_vp(self, datad, summaryd, n):
    #
    # vp remaining
    summaryd['control_vp_remaining_mean'] = self.mean(datad['control_vp_remaining'], n)
    summaryd['test_vp_remaining_mean'] = self.mean(datad['test_vp_remaining'], n)
    #
    # vp spent
    summaryd['control_vp_spent_mean'] = self.mean(datad['control_vp_spent'], n)
    summaryd['test_vp_spent_mean'] = self.mean(datad['test_vp_spent'], n)
    #
    # vp spent on attack rolls
    summaryd['control_vp_spent_attacks_mean'] = self.mean(datad['control_vp_spent_attacks'], n)
    summaryd['test_vp_spent_attacks_mean'] = self.mean(datad['test_vp_spent_attacks'], n)
    #
    # vp spent on wound checks
    summaryd['control_vp_spent_wound_checks_mean'] = self.mean(datad['control_vp_spent_wound_checks'], n)
    summaryd['test_vp_spent_wound_checks_mean'] = self.mean(datad['test_vp_spent_wound_checks'], n)
    return

  def summarize_wound_checks(self, datad, summaryd, n):
    #
    # wound checks succeeded
    summaryd['control_wc_succeeded_mean'] = self.mean(datad['control_wc_succeeded'], n)
    summaryd['test_wc_succeeded_mean'] = self.mean(datad['test_wc_succeeded'], n)
    #
    # wound checks failed
    summaryd['control_wc_failed_mean'] = self.mean(datad['control_wc_failed'], n)
    summaryd['test_wc_failed_mean'] = self.mean(datad['test_wc_failed'], n)
    #
    # failed wound check margin
    summaryd['control_wc_failed_margin_mean'] = self.mean(datad['control_wc_failed_margin_sum'], datad['control_wc_failed_margin_count'])
    summaryd['test_wc_failed_margin_mean'] = self.mean(datad['test_wc_failed_margin_sum'], datad['test_wc_failed_margin_count'])
    #
    # failed wound check LW total
    summaryd['control_wc_failed_lw_total_mean'] = self.mean(datad['control_wc_failed_lw_total_sum'], datad['control_wc_failed_lw_total_count'])
    summaryd['test_wc_failed_lw_total_mean'] = self.mean(datad['test_wc_failed_lw_total_sum'], datad['test_wc_failed_lw_total_count'])
    #
    # succeeded wound check margin
    summaryd['control_wc_succeeded_margin_mean'] = self.mean(datad['control_wc_succeeded_margin_sum'], datad['control_wc_succeeded_margin_count'])
    summaryd['test_wc_succeeded_margin_mean'] = self.mean(datad['test_wc_succeeded_margin_sum'], datad['test_wc_succeeded_margin_count'])
    return

  def print_report(self):
    # duration summary
    print('Average combat duration in rounds: {:.2f}'.format(self._summary['duration_rounds_mean']))
    print('Average combat duration in phases: {:.2f}'.format(self._summary['duration_phases_mean']))
    print('')
    # test group stats
    print('Test group stats:')
    print('\tSW remaining mean: {:.2f}'.format(self._summary['test_sw_remaining_mean']))
    print('\tDamage roll mean: {:.2f}'.format(self._summary['test_damage_mean']))
    print('\tDamage roll stdev: {:.2f}'.format(self._summary['test_damage_stdev']))
    print('\tVP remaining mean: {:.2f}'.format(self._summary['test_vp_remaining_mean']))
    print('\tVP spent mean: {:.2f}'.format(self._summary['test_vp_spent_mean']))
    print('\tVP spent on attacks mean: {:.2f}'.format(self._summary['test_vp_spent_attacks_mean']))
    print('\tVP spent on wound checks mean: {:.2f}'.format(self._summary['test_vp_spent_wound_checks_mean']))
    print('\tActions taken mean: {:.2f}'.format(self._summary['test_actions_taken_mean']))
    print('\tAttacks taken mean: {:.2f}'.format(self._summary['test_attacks_taken_mean']))
    print('\tParries taken mean: {:.2f}'.format(self._summary['test_parries_taken_mean']))
    print('\tAttacks succeeded mean: {:.2f}'.format(self._summary['test_attacks_succeeded_mean']))
    print('\tParries succeeded mean: {:.2f}'.format(self._summary['test_parries_succeeded_mean']))
    print('\tSuccessful wound check mean margin: {:.2f}'.format(self._summary['test_wc_succeeded_margin_mean']))
    print('\tFailed wound check mean LW: {:.2f}'.format(self._summary['test_wc_failed_lw_total_mean']))
    print('\tFailed wound check mean margin: {:.2f}'.format(self._summary['test_wc_failed_margin_mean']))
    print('\tMean LW kept: {:.2f}'.format(self._summary['test_keep_lw_total_mean']))
    print('\tMean LW when voluntarily taking SW: {:.2f}'.format(self._summary['test_take_sw_total_mean']))
    print('')
    # control group stats
    print('Control group stats:')
    print('\tSW remaining mean: {:.2f}'.format(self._summary['control_sw_remaining_mean']))
    print('\tDamage roll mean: {:.2f}'.format(self._summary['control_damage_mean']))
    print('\tDamage roll stdev: {:.2f}'.format(self._summary['control_damage_stdev']))
    print('\tVP remaining mean: {:.2f}'.format(self._summary['control_vp_remaining_mean']))
    print('\tVP spent mean: {:.2f}'.format(self._summary['control_vp_spent_mean']))
    print('\tVP spent on attacks mean: {:.2f}'.format(self._summary['control_vp_spent_attacks_mean']))
    print('\tVP spent on wound checks mean: {:.2f}'.format(self._summary['control_vp_spent_wound_checks_mean']))
    print('\tActions taken mean: {:.2f}'.format(self._summary['control_actions_taken_mean']))
    print('\tAttacks taken mean: {:.2f}'.format(self._summary['control_attacks_taken_mean']))
    print('\tParries taken mean: {:.2f}'.format(self._summary['control_parries_taken_mean']))
    print('\tAttacks succeeded mean: {:.2f}'.format(self._summary['control_attacks_succeeded_mean']))
    print('\tParries succeeded mean: {:.2f}'.format(self._summary['control_parries_succeeded_mean']))
    print('\tSuccessful wound check mean margin: {:.2f}'.format(self._summary['control_wc_succeeded_margin_mean']))
    print('\tFailed wound check mean LW: {:.2f}'.format(self._summary['control_wc_failed_lw_total_mean']))
    print('\tFailed wound check mean margin: {:.2f}'.format(self._summary['control_wc_failed_margin_mean']))
    print('\tMean LW kept: {:.2f}'.format(self._summary['control_keep_lw_total_mean']))
    print('\tMean LW when voluntarily taking SW: {:.2f}'.format(self._summary['control_take_sw_total_mean']))
    if self._test_victories > 0:
      # stats given test group victory
      print('')
      print('Features given test group victory:')
      print('\tAverage combat duration in rounds: {:.2f}'.format(self._test_summary['duration_rounds_mean']))
      print('\tAverage combat duration in phases: {:.2f}'.format(self._test_summary['duration_phases_mean']))
      print('\t')
      print('\tTest group stats:')
      print('\t\tSW remaining mean: {:.2f}'.format(self._test_summary['test_sw_remaining_mean']))
      print('\t\tDamage roll mean: {:.2f}'.format(self._test_summary['test_damage_mean']))
      print('\t\tDamage roll stdev: {:.2f}'.format(self._test_summary['test_damage_stdev']))
      print('\t\tVP remaining mean: {:.2f}'.format(self._summary['test_vp_remaining_mean']))
      print('\t\tVP spent mean: {:.2f}'.format(self._test_summary['test_vp_spent_mean']))
      print('\t\tVP spent on attacks mean: {:.2f}'.format(self._test_summary['test_vp_spent_attacks_mean']))
      print('\t\tVP spent on wound checks mean: {:.2f}'.format(self._test_summary['test_vp_spent_wound_checks_mean']))
      print('\t\tActions taken mean: {:.2f}'.format(self._test_summary['test_actions_taken_mean']))
      print('\t\tAttacks taken mean: {:.2f}'.format(self._test_summary['test_attacks_taken_mean']))
      print('\t\tParries taken mean: {:.2f}'.format(self._test_summary['test_parries_taken_mean']))
      print('\t\tAttacks succeeded mean: {:.2f}'.format(self._test_summary['test_attacks_succeeded_mean']))
      print('\t\tParries succeeded mean: {:.2f}'.format(self._test_summary['test_parries_succeeded_mean']))
      print('\t\tSuccessful wound check mean margin: {:.2f}'.format(self._test_summary['test_wc_succeeded_margin_mean']))
      print('\t\tFailed wound check mean LW: {:.2f}'.format(self._test_summary['test_wc_failed_lw_total_mean']))
      print('\t\tFailed wound check mean margin: {:.2f}'.format(self._test_summary['test_wc_failed_margin_mean']))
      print('\t\tMean LW kept: {:.2f}'.format(self._test_summary['test_keep_lw_total_mean']))
      print('\t\tMean LW when voluntarily taking SW: {:.2f}'.format(self._test_summary['test_take_sw_total_mean']))
      print('\t')
      print('\tControl group stats:')
      print('\t\tSW remaining mean: {:.2f}'.format(self._test_summary['control_sw_remaining_mean']))
      print('\t\tDamage roll mean: {:.2f}'.format(self._test_summary['control_damage_mean']))
      print('\t\tDamage roll stdev: {:.2f}'.format(self._test_summary['control_damage_stdev']))
      print('\t\tVP remaining mean: {:.2f}'.format(self._summary['control_vp_remaining_mean']))
      print('\t\tVP spent mean: {:.2f}'.format(self._test_summary['control_vp_spent_mean']))
      print('\t\tVP spent on attacks mean: {:.2f}'.format(self._test_summary['control_vp_spent_attacks_mean']))
      print('\t\tVP spent on wound checks mean: {:.2f}'.format(self._test_summary['control_vp_spent_wound_checks_mean']))
      print('\t\tActions taken mean: {:.2f}'.format(self._test_summary['control_actions_taken_mean']))
      print('\t\tAttacks taken mean: {:.2f}'.format(self._test_summary['control_attacks_taken_mean']))
      print('\t\tParries taken mean: {:.2f}'.format(self._test_summary['control_parries_taken_mean']))
      print('\t\tAttacks succeeded mean: {:.2f}'.format(self._test_summary['control_attacks_succeeded_mean']))
      print('\t\tParries succeeded mean: {:.2f}'.format(self._test_summary['control_parries_succeeded_mean']))
      print('\t\tSuccessful wound check mean margin: {:.2f}'.format(self._test_summary['control_wc_succeeded_margin_mean']))
      print('\t\tFailed wound check mean LW: {:.2f}'.format(self._test_summary['control_wc_failed_lw_total_mean']))
      print('\t\tFailed wound check mean margin: {:.2f}'.format(self._test_summary['control_wc_failed_margin_mean']))
      print('\t\tMean LW kept: {:.2f}'.format(self._test_summary['control_keep_lw_total_mean']))
      print('\t\tMean LW when voluntarily taking SW: {:.2f}'.format(self._test_summary['control_take_sw_total_mean']))
    if self._control_victories > 0:
      # stats given control group victory 
      print('')
      print('Features given control group victory:')
      print('\tAverage combat duration in rounds: {:.2f}'.format(self._control_summary['duration_rounds_mean']))
      print('\tAverage combat duration in phases: {:.2f}'.format(self._control_summary['duration_phases_mean']))
      print('\t')
      print('\tTest group stats:')
      print('\t\tSW remaining mean: {:.2f}'.format(self._control_summary['test_sw_remaining_mean']))
      print('\t\tDamage roll mean: {:.2f}'.format(self._control_summary['test_damage_mean']))
      print('\t\tDamage roll stdev: {:.2f}'.format(self._control_summary['test_damage_stdev']))
      print('\t\tVP remaining mean: {:.2f}'.format(self._summary['test_vp_remaining_mean']))
      print('\t\tVP spent mean: {:.2f}'.format(self._control_summary['test_vp_spent_mean']))
      print('\t\tVP spent on attacks mean: {:.2f}'.format(self._control_summary['test_vp_spent_attacks_mean']))
      print('\t\tVP spent on wound checks mean: {:.2f}'.format(self._control_summary['test_vp_spent_wound_checks_mean']))
      print('\t\tActions taken mean: {:.2f}'.format(self._control_summary['test_actions_taken_mean']))
      print('\t\tAttacks taken mean: {:.2f}'.format(self._control_summary['test_attacks_taken_mean']))
      print('\t\tParries taken mean: {:.2f}'.format(self._control_summary['test_parries_taken_mean']))
      print('\t\tAttacks succeeded mean: {:.2f}'.format(self._control_summary['test_attacks_succeeded_mean']))
      print('\t\tParries succeeded mean: {:.2f}'.format(self._control_summary['test_parries_succeeded_mean']))
      print('\t\tSuccessful wound check mean margin: {:.2f}'.format(self._test_summary['test_wc_succeeded_margin_mean']))
      print('\t\tFailed wound check mean LW: {:.2f}'.format(self._control_summary['test_wc_failed_lw_total_mean']))
      print('\t\tFailed wound check mean margin: {:.2f}'.format(self._control_summary['test_wc_failed_margin_mean']))
      print('\t\tMean LW kept: {:.2f}'.format(self._control_summary['test_keep_lw_total_mean']))
      print('\t\tMean LW when voluntarily taking SW: {:.2f}'.format(self._control_summary['test_take_sw_total_mean']))
      print('\t')
      print('\tControl group stats:')
      print('\t\tSW remaining mean: {:.2f}'.format(self._control_summary['control_sw_remaining_mean']))
      print('\t\tDamage roll mean: {:.2f}'.format(self._control_summary['control_damage_mean']))
      print('\t\tDamage roll stdev: {:.2f}'.format(self._control_summary['control_damage_stdev']))
      print('\t\tVP remaining mean: {:.2f}'.format(self._summary['control_vp_remaining_mean']))
      print('\t\tVP spent mean: {:.2f}'.format(self._control_summary['control_vp_spent_mean']))
      print('\t\tVP spent on attacks mean: {:.2f}'.format(self._control_summary['control_vp_spent_attacks_mean']))
      print('\t\tVP spent on wound checks mean: {:.2f}'.format(self._control_summary['control_vp_spent_wound_checks_mean']))
      print('\t\tActions taken mean: {:.2f}'.format(self._control_summary['control_actions_taken_mean']))
      print('\t\tAttacks taken mean: {:.2f}'.format(self._control_summary['control_attacks_taken_mean']))
      print('\t\tParries taken mean: {:.2f}'.format(self._test_summary['control_parries_taken_mean']))
      print('\t\tAttacks succeeded mean: {:.2f}'.format(self._control_summary['control_attacks_succeeded_mean']))
      print('\t\tParries succeeded mean: {:.2f}'.format(self._control_summary['control_parries_succeeded_mean']))
      print('\t\tSuccessful wound check mean margin: {:.2f}'.format(self._control_summary['control_wc_succeeded_margin_mean']))
      print('\t\tFailed wound check mean LW: {:.2f}'.format(self._control_summary['control_wc_failed_lw_total_mean']))
      print('\t\tFailed wound check mean margin: {:.2f}'.format(self._control_summary['control_wc_failed_margin_mean']))
      print('\t\tMean LW kept: {:.2f}'.format(self._control_summary['control_keep_lw_total_mean']))
      print('\t\tMean LW when voluntarily taking SW: {:.2f}'.format(self._control_summary['control_take_sw_total_mean']))
    return


class TrialFeatures(object):
  '''
  Features of a single run.
  '''
  def __init__(self):
    self._data = {}
    self._winner = 0
    self.initialize()

  def clear(self):
    self.initialize()

  def data(self):
    return self._data

  def winner(self):
    return self._winner

  def initialize(self):
    '''
  Questions we might ask after a simulation:
  * Winner's normal initiative actions per round compared to loser
  * Winner's total SW compared to loser (at beginning of combat)
  * Interrupt actions taken
  * Interrupt attacks taken
  * Interrupt parries taken
  '''
    # winner (-1: control, 0: aiuchi, 1: test)
    self._winner = 0
    # duration of trial
    self._data['duration_rounds'] = 0
    self._data['duration_phases'] = 0
    # control's actions
    self._data['control_actions_taken'] = 0
    self._data['control_attacks_taken'] = 0
    self._data['control_parries_taken'] = 0
    self._data['control_attacks_succeeded'] = 0
    self._data['control_parries_succeeded'] = 0
    # control's AP
    self._data['control_ap_remaining'] = 0
    self._data['control_ap_spent'] = 0
    self._data['control_ap_spent_wound_checks'] = 0
    # control's damage inflicted
    self._data['control_damage_rolls'] = []
    self._data['control_sw'] = 0
    # control's SW remaining
    self._data['control_sw_remaining'] = 0
    # control's wound checks
    self._data['control_keep_lw_total'] = []
    self._data['control_take_sw_total'] = []
    self._data['control_wc_failed'] = 0
    self._data['control_wc_failed_margin'] = []
    self._data['control_wc_failed_lw_total'] = []
    self._data['control_wc_succeeded'] = 0
    self._data['control_wc_succeeded_margin'] = []
    # control's VP
    self._data['control_vp_remaining'] = 0
    self._data['control_vp_spent'] = 0
    self._data['control_vp_spent_attacks'] = 0
    self._data['control_vp_spent_wound_checks'] = 0
    # test's actions
    self._data['test_actions_taken'] = 0
    self._data['test_attacks_taken'] = 0
    self._data['test_parries_taken'] = 0
    self._data['test_attacks_succeeded'] = 0
    self._data['test_parries_succeeded'] = 0
    # test's AP
    self._data['test_ap_remaining'] = 0
    self._data['test_ap_spent'] = 0
    self._data['test_ap_spent_wound_checks'] = 0
    # test's damage inflicted
    self._data['test_damage_rolls'] = []
    self._data['test_sw'] = 0
    # test's SW remaining
    self._data['test_sw_remaining'] = 0
    # test's wound checks
    self._data['test_keep_lw_total'] = []
    self._data['test_take_sw_total'] = []
    self._data['test_wc_failed'] = 0
    self._data['test_wc_failed_margin'] = []
    self._data['test_wc_failed_lw_total'] = []
    self._data['test_wc_succeeded'] = 0
    self._data['test_wc_succeeded_margin'] = []
    # test's VP
    self._data['test_vp_remaining'] = 0
    self._data['test_vp_spent'] = 0
    self._data['test_vp_spent_attacks'] = 0
    self._data['test_vp_spent_wound_checks'] = 0

  def observe_event(self, event, context):
    if isinstance(event, events.NewPhaseEvent):
      self.observe_phase()
    elif isinstance(event, events.NewRoundEvent):
      self.observe_round()
    elif isinstance(event, events.LightWoundsDamageEvent):
      self.observe_lw(event, context)
    elif isinstance(event, events.SeriousWoundsDamageEvent):
      self.observe_sw(event, context)
    elif isinstance(event, events.SpendActionEvent):
      self.observe_action(event, context)
    elif isinstance(event, events.SpendAdventurePointsEvent):
      raise NotImplementedError('Collecting features for spend_ap events is not yet supported')
    elif isinstance(event, events.SpendVoidPointsEvent):
      self.observe_vp_spent(event, context)
    elif isinstance(event, events.TakeAttackActionEvent):
      self.observe_attack(event, context)
    elif isinstance(event, events.TakeParryActionEvent):
      self.observe_parry(event, context)
    elif isinstance(event, events.AttackSucceededEvent):
      self.observe_attack_succeeded(event, context)
    elif isinstance(event, events.AttackFailedEvent):
      # TODO: collect failed attacks
      pass
    elif isinstance(event, events.ParrySucceededEvent):
      self.observe_parry_succeeded(event, context)
    elif isinstance(event, events.WoundCheckSucceededEvent):
      self.observe_wound_check_succeeded(event, context)
    elif isinstance(event, events.WoundCheckFailedEvent):
      self.observe_wound_check_failed(event, context)
    elif isinstance(event, events.KeepLightWoundsEvent):
      self.observe_keep_lw(event, context)
    elif isinstance(event, events.TakeSeriousWoundEvent):
      self.observe_take_sw(event, context)

  def observe_action(self, event, context):
    if event.subject in context.test_group():
      self._data['test_actions_taken'] += 1
    else:
      self._data['control_actions_taken'] += 1

  def observe_attack(self, event, context):
    if event.action.subject() in context.test_group():
      self._data['test_attacks_taken'] += 1
    else:
      self._data['control_attacks_taken'] += 1

  def observe_attack_succeeded(self, event, context):
    if event.action.subject() in context.test_group():
      self._data['test_attacks_succeeded'] += 1
    else:
      self._data['control_attacks_succeeded'] += 1

  def observe_keep_lw(self, event, context):
    if event.subject in context.test_group():
      self._data['test_keep_lw_total'].append(event.damage)
    else:
      self._data['control_keep_lw_total'].append(event.damage)

  def observe_lw(self, event, context):
    if event.subject in context.test_group():
      self._data['test_damage_rolls'].append(event.damage)
    else:
      self._data['control_damage_rolls'].append(event.damage)

  def observe_parry(self, event, context):
    if event.action.subject() in context.test_group():
      self._data['test_parries_taken'] += 1
    else:
      self._data['control_parries_taken'] += 1

  def observe_parry_succeeded(self, event, context):
    if event.action.subject() in context.test_group():
      self._data['test_parries_succeeded'] += 1
    else:
      self._data['control_parries_succeeded'] += 1

  def observe_phase(self):
    self._data['duration_phases'] += 1

  def observe_round(self):
    self._data['duration_rounds'] += 1

  def observe_sw(self, event, context):
    if event.subject in context.test_group():
      self._data['test_sw'] += event.damage
    else:
      self._data['control_sw'] += event.damage

  def observe_take_sw(self, event, context):
    # observes LW total when character takes SW voluntarily
    if event.subject in context.test_group():
      self._data['test_take_sw_total'].append(event.damage)
    else:
      self._data['control_take_sw_total'].append(event.damage)

  def observe_vp_spent(self, event, context):
    if event.subject in context.test_group():
      self._data['test_vp_spent'] += 1
      if event.skill in ATTACK_SKILLS:
        self._data['test_vp_spent_attacks'] += 1
      elif event.skill == 'wound check':
        self._data['test_vp_spent_wound_checks'] += 1
    else:
      self._data['control_vp_spent'] += 1
      if event.skill in ATTACK_SKILLS:
        self._data['control_vp_spent_attacks'] += 1
      elif event.skill == 'wound check':
        self._data['control_vp_spent_wound_checks'] += 1

  def observe_winner(self, result):
    '''
    observe_winner(result)

    Set the winner of this simulation.
    -1 = control group won
    0 = both sides lost
    1 = test group won
    '''
    self._winner = result
    self._data['winner'] = result

  def observe_wound_check_failed(self, event, context):
    if event.subject in context.test_group():
      self._data['test_wc_failed'] += 1
      self._data['test_wc_failed_margin'].append(event.tn - event.roll)
      self._data['test_wc_failed_lw_total'].append(event.damage)
    else:
      self._data['control_wc_failed'] += 1
      self._data['control_wc_failed_margin'].append(event.tn - event.roll)
      self._data['control_wc_failed_lw_total'].append(event.damage)

  def observe_wound_check_succeeded(self, event, context):
    if event.subject in context.test_group():
      self._data['test_wc_succeeded'] += 1
      self._data['test_wc_succeeded_margin'].append(event.roll - event.tn)
    else:
      self._data['control_wc_succeeded'] += 1
      self._data['control_wc_succeeded_margin'].append(event.roll - event.tn)

  def complete(self, context):
    self.complete_damage_rolls(context)
    self.complete_keep_lw(context)
    self.complete_sw_remaining(context)
    self.complete_take_sw(context)
    self.complete_vp_remaining(context)
    self.complete_wound_checks(context)
 
  def complete_damage_rolls(self, context):
    # get count, sum, and sum of squares for control damage rolls
    control_damage = self._data['control_damage_rolls']
    self._data['control_damage_rolls_sum'] = sum(control_damage)
    self._data['control_damage_rolls_sumsquares'] = sum([x * x for x in control_damage])
    self._data['control_damage_rolls_count'] = len(control_damage)
    self._data.pop('control_damage_rolls')
    # get count, sum, and sum of squares for test damage rolls
    test_damage = self._data['test_damage_rolls']
    self._data['test_damage_rolls_sum'] = sum(test_damage)
    self._data['test_damage_rolls_sumsquares'] = sum([x * x for x in test_damage])
    self._data['test_damage_rolls_count'] = len(test_damage)
    self._data.pop('test_damage_rolls')

  def complete_keep_lw(self, context):
    # get count, sum, and sum of squares for LW total when keeping LW
    control_keep_lw_total = self._data['control_keep_lw_total']
    self._data['control_keep_lw_total_sum'] = sum(control_keep_lw_total)
    self._data['control_keep_lw_total_sumsquares'] = sum([x * x for x in control_keep_lw_total])
    self._data['control_keep_lw_total_count'] = len(control_keep_lw_total)
    self._data.pop('control_keep_lw_total')
    # same for test
    test_keep_lw_total = self._data['test_keep_lw_total']
    self._data['test_keep_lw_total_sum'] = sum(test_keep_lw_total)
    self._data['test_keep_lw_total_sumsquares'] = sum([x * x for x in test_keep_lw_total])
    self._data['test_keep_lw_total_count'] = len(test_keep_lw_total)
    self._data.pop('test_keep_lw_total')

  def complete_sw_remaining(self, context):
    control_sw_remaining = sum([character.sw_remaining() for character in context.groups()[0]])
    test_sw_remaining = sum([character.sw_remaining() for character in context.groups()[1]])
    self._data['control_sw_remaining'] = control_sw_remaining
    self._data['test_sw_remaining'] = test_sw_remaining

  def complete_take_sw(self, context):
    # get count, sum, and sum of squares for control LW total
    # when voluntarily taking SW after a successful wound check
    control_take_sw_total = self._data['control_take_sw_total']
    self._data['control_take_sw_total_sum'] = sum(control_take_sw_total)
    self._data['control_take_sw_total_sumsquares'] = sum([x * x for x in control_take_sw_total])
    self._data['control_take_sw_total_count'] = len(control_take_sw_total)
    self._data.pop('control_take_sw_total')
    # same for test group
    test_take_sw_total = self._data['test_take_sw_total']
    self._data['test_take_sw_total_sum'] = sum(test_take_sw_total)
    self._data['test_take_sw_total_sumsquares'] = sum([x * x for x in test_take_sw_total])
    self._data['test_take_sw_total_count'] = len(test_take_sw_total)
    self._data.pop('test_take_sw_total')

  def complete_vp_remaining(self, context):
    control_vp_remaining = sum([character.vp() for character in context.groups()[0]])
    test_vp_remaining = sum([character.vp() for character in context.groups()[1]])
    self._data['control_vp_remaining'] = control_vp_remaining
    self._data['test_vp_remaining'] = test_vp_remaining

  def complete_wound_checks(self, context):
    # get count, sum, and sum of squares for control wound check failed margin
    control_wc_failed_margin = self._data['control_wc_failed_margin']
    self._data['control_wc_failed_margin_sum'] = sum(control_wc_failed_margin)
    self._data['control_wc_failed_margin_sumsquares'] = sum([x * x for x in control_wc_failed_margin])
    self._data['control_wc_failed_margin_count'] = len(control_wc_failed_margin)
    self._data.pop('control_wc_failed_margin')
    # get count, sum, and sum of squares for test wound check failed margin
    test_wc_failed_margin = self._data['test_wc_failed_margin']
    self._data['test_wc_failed_margin_sum'] = sum(test_wc_failed_margin)
    self._data['test_wc_failed_margin_sumsquares'] = sum([x * x for x in test_wc_failed_margin])
    self._data['test_wc_failed_margin_count'] = len(test_wc_failed_margin)
    self._data.pop('test_wc_failed_margin')
    # get count, sum, and sum of squares for control LW total when wound check failed
    control_wc_failed_lw_total = self._data['control_wc_failed_lw_total']
    self._data['control_wc_failed_lw_total_sum'] = sum(control_wc_failed_lw_total)
    self._data['control_wc_failed_lw_total_sumsquares'] = sum([x * x for x in control_wc_failed_lw_total])
    self._data['control_wc_failed_lw_total_count'] = len(control_wc_failed_lw_total)
    self._data.pop('control_wc_failed_lw_total')
    # same for test
    test_wc_failed_lw_total = self._data['test_wc_failed_lw_total']
    self._data['test_wc_failed_lw_total_sum'] = sum(test_wc_failed_lw_total)
    self._data['test_wc_failed_lw_total_sumsquares'] = sum([x * x for x in test_wc_failed_lw_total])
    self._data['test_wc_failed_lw_total_count'] = len(test_wc_failed_lw_total)
    self._data.pop('test_wc_failed_lw_total')
    # get count, sum, and sum of squares for control wound check succeeded margin
    control_wc_succeeded_margin = self._data['control_wc_succeeded_margin']
    self._data['control_wc_succeeded_margin_sum'] = sum(control_wc_succeeded_margin)
    self._data['control_wc_succeeded_margin_sumsquares'] = sum([x * x for x in control_wc_succeeded_margin])
    self._data['control_wc_succeeded_margin_count'] = len(control_wc_succeeded_margin)
    self._data.pop('control_wc_succeeded_margin')
    # get count, sum, and sum of squares for test wound check succeeded margin
    test_wc_succeeded_margin = self._data['test_wc_succeeded_margin']
    self._data['test_wc_succeeded_margin_sum'] = sum(test_wc_succeeded_margin)
    self._data['test_wc_succeeded_margin_sumsquares'] = sum([x * x for x in test_wc_succeeded_margin])
    self._data['test_wc_succeeded_margin_count'] = len(test_wc_succeeded_margin)
    self._data.pop('test_wc_succeeded_margin')

  def write(self, f):
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writerow(self._data)

def write_feature_file_header(f):
  writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
  writer.writeheader()

