"""Kakita Bushi Comprehensive Study.

Reframes the VP Allocation Study data around the question "what is the optimal
overall strategy?" rather than "offense vs defense VP allocation." Uses the
exact same matchup structure (same build_variants, strategy_dimensions,
extra_variables, opponents, xp_tiers, xp_deltas) so that results from the
VP study can be reused without re-running simulations.

Dimensions (same as VP study):
  - build: 4 variants (baseline, swap_earth_water, rush_dan4, delay_dan4)
  - attack_style: 6 options (flattened: 2 interrupt x 3 attack VP levels)
  - action_hold: 2 options (hold vs immediate)
  - wound_check_vp: 2 options (never vs threshold 0.5)

Extra variables (decoded from extra_tags):
  - interrupt: on/off
  - attack_vp: never, threshold_05, threshold_07

Total profiles: 4 x 6 x 2 x 2 = 96
Matchups: 96 x 4 opponents x ~19 XP combos ~ 7,296
"""

from web.analysis.definitions.kakita_vp_study import KAKITA_VP_STUDY_CONFIG
from web.analysis.models import AnalysisDefinition
from web.analysis.study import SchoolStudyConfig, build_study_analysis

# ── Findings with per-opponent analysis ──────────────────────────────

_FINDINGS = {
    "attack_vp": (
        "**Spend your Void Points on attack rolls -- it's the single biggest "
        "decision in the study.** A Kakita who spends VP on attacks wins "
        "roughly 5.5 percentage points more often than one who hoards them.\n\n"
        "The way it works: before making an attack roll, estimate whether "
        "spending a Void Point would meaningfully improve your odds of "
        "hitting (and of landing a devastating blow). The best approach is "
        "to **only spend when a VP gives you at least a 70% chance of "
        "hitting your target number** -- this concentrates your limited VP "
        "on attacks that are likely to connect, rather than wasting them on "
        "long-shot swings. A more aggressive 50% threshold wastes VP on "
        "marginal attacks where even with the bonus you'll likely miss.\n\n"
        "**Per-opponent:** This holds true against the Akodo (+5.1%), "
        "Bayushi (+4.7%), and Wave Man (+8.5%). The one exception is the "
        "Shiba, where the more aggressive 50% threshold is slightly better "
        "by about 0.3% -- the Shiba's strong defense means you need to "
        "press harder -- but the difference is tiny."
    ),
    "wound_check_vp": (
        "**When you're hit and rolling a wound check, spend a Void Point "
        "if it has at least a 50% chance of saving you from taking an "
        "extra Serious Wound.** This is the most consistent finding in "
        "the entire study -- it's the right call against every opponent "
        "at every XP tier.\n\n"
        "In practice this means: when you take Light Wounds and are "
        "rolling to see how many Serious Wounds you suffer, look at your "
        "wound check TN. If spending a VP would give you a coin-flip-or-"
        "better chance of avoiding an additional Serious Wound, spend it. "
        "This costs about +1.4% win rate overall -- less dramatic than "
        "attack VP, but perfectly consistent.\n\n"
        "**Per-opponent:** The defensive spend matters most against the "
        "Shiba (+1.9%), who forces close fights where surviving one more "
        "wound makes the difference. Against the Akodo (+1.4%), Bayushi "
        "(+1.3%), and Wave Man (+1.2%) the benefit is similar.\n\n"
        "**Bottom line:** Your VP are best spent on attacks, but don't "
        "neglect defense entirely. When a wound check is close, spending "
        "a VP to stay in the fight is well worth it."
    ),
    "action_hold": (
        "**Attack immediately whenever you have an action available -- "
        "don't hold actions in reserve.** This is worth about +4 "
        "percentage points in win rate, making it the single strongest "
        "tactical choice.\n\n"
        "The Kakita fighting style rewards aggression. Your iaijutsu "
        "strikes are most effective when you act early and keep the "
        "pressure on. Holding an action in reserve (waiting to react "
        "to your opponent) sounds cautious and smart, but in practice "
        "the Kakita gains nothing from it -- your iaijutsu technique "
        "doesn't benefit from saved actions, so you're just giving up "
        "tempo for no return.\n\n"
        "**Per-opponent:** Always attacking immediately wins against the "
        "Akodo (+3.7%), Bayushi (+5.9%), and Wave Man (+6.8%). The one "
        "exception is the Shiba, where holding one action is marginally "
        "better (+0.5%). The Shiba's reactive defensive style may punish "
        "reckless aggression slightly, but even there the advantage of "
        "holding is small enough to ignore in general play."
    ),
    "interrupt": (
        "**Interrupt attacks don't matter much.** The Kakita can spend "
        "2 future action dice to make an out-of-turn iaijutsu strike "
        "when they've already used their current action. In theory this "
        "lets you press the attack when you're out of actions for the "
        "current phase. In practice, **the extra damage potential is "
        "almost exactly offset by losing those 2 future actions**, "
        "resulting in less than 0.4% difference either way.\n\n"
        "**Per-opponent:** Consistent non-effect across all matchups. "
        "No opponent makes interrupt significantly better or worse. "
        "You can enable or disable interrupt attacks without worrying "
        "about it -- focus your attention on VP spending and action "
        "timing instead."
    ),
    "build": (
        "**How you spend your XP matters less than how you fight.** "
        "The default Kakita advancement order (skills first, then rings) "
        "is fine. Rushing to Dan 4 skills before raising rank-3 rings "
        "is equally good. The only build to clearly avoid is delaying "
        "Dan 4 skills until after all rank-3 rings are raised -- that "
        "costs about 4 percentage points in win rate, probably because "
        "the Dan 4 combat skills (Double Attack, Iaijutsu 4, Lunge) are "
        "too valuable to postpone.\n\n"
        "**Per-opponent:** No meaningful variation. Your stat progression "
        "affects raw capability equally against all opponents, so just "
        "pick a sensible advancement order and focus on tactics."
    ),
    "attack_style": (
        "**This combined view (interrupt mode + attack VP level) is "
        "almost entirely driven by VP spending.** The top options all "
        "use the 0.7 VP threshold at ~54.6% win rate; the worst options "
        "never spend VP on attacks at ~49%. Whether interrupt is on or "
        "off within each VP level changes the win rate by only ~0.3%.\n\n"
        "**In plain terms:** the question of *whether to spend VP on "
        "attacks* is far more important than *whether to use interrupt "
        "iaijutsu*. Get your VP spending right and the rest is details."
    ),
}

# ── Study configuration ──────────────────────────────────────────────

# Reuse the exact same structure from the VP study to ensure matchup ID
# compatibility. Only analysis_id, title, question, description, and
# findings differ.
KAKITA_COMPREHENSIVE_CONFIG = SchoolStudyConfig(
    school_key=KAKITA_VP_STUDY_CONFIG.school_key,
    school_name=KAKITA_VP_STUDY_CONFIG.school_name,
    analysis_id="kakita_comprehensive",
    title="Kakita Bushi Comprehensive Study",
    question=(
        "What is the optimal overall strategy for a Kakita Bushi, and "
        "does it change by opponent?"
    ),
    description=(
        "Simulates thousands of duels to answer: how should a Kakita Bushi "
        "spend Void Points, when should they attack, and does the answer "
        "change depending on the opponent? Tests every combination of VP "
        "spending strategy, action timing, interrupt attacks, and character "
        "build across 4 opponents (Akodo, Bayushi, Shiba, Wave Man) at 7 "
        "experience levels. Each 'win rate' is the percentage of simulated "
        "duels won by the Kakita."
    ),
    build_variants=list(KAKITA_VP_STUDY_CONFIG.build_variants),
    strategy_dimensions=list(KAKITA_VP_STUDY_CONFIG.strategy_dimensions),
    extra_variables=list(KAKITA_VP_STUDY_CONFIG.extra_variables),
    opponents=list(KAKITA_VP_STUDY_CONFIG.opponents),
    xp_tiers=list(KAKITA_VP_STUDY_CONFIG.xp_tiers),
    xp_deltas=list(KAKITA_VP_STUDY_CONFIG.xp_deltas),
    findings=_FINDINGS,
)


def build_kakita_comprehensive_analysis(
    num_trials: int = 100,
) -> AnalysisDefinition:
    """Build the Kakita Bushi Comprehensive Study analysis definition."""
    return build_study_analysis(
        KAKITA_COMPREHENSIVE_CONFIG, num_trials=num_trials,
    )
