# Schools backlog

This file enumerates every school defined in upstream
`rules/04-schools.md` and tracks its implementation status in this
simulator. The list is the canonical queue when picking the next
school to implement.

When the user (or a future session) says "implement the next school",
read this file, pick the topmost entry under **Skeleton present —
needs full audit + completion**, and run the workflow in
[CLAUDE.md § New school implementation workflow](CLAUDE.md).

When a school graduates (passes the full speckit workflow + 4-agent
review), move its entry to **Validated via speckit workflow** with
the merge commit reference.

## Validated via speckit workflow

These schools have been through `/speckit-specify → clarify → plan
→ tasks → implement` with `school-progression-designer`,
`school-strategy-designer`, `school-implementer`, `rules-auditor`,
and `combat-simulator` review. Principles VII/VIII/IX verified.

- **Mirumoto Bushi School** — `specs/001-mirumoto-bushi-school/`,
  merged 2026-05-25.
- **Isawa Ishi School** — `specs/002-isawa-ishi-school/`, merged
  2026-05-26. (5th-Dan negation refactor not formalized as a separate
  spec; merged 2026-05-26 as commit `89dc0bb`.)
- **Akodo Bushi School** — `specs/004-akodo-bushi-school/`, merged
  2026-05-27. Identity-driven AKODO_PRIORITIES + new
  `AkodoAttackStrategy` (kill-shot / feint-first / plain-attack
  fallback with `TVP_SATURATION_CAP = 4` for mirror non-degeneracy)
  + 4th Dan off-by-one fix + 35 new tests (2919 → 2954). One of the
  two Principle IX playability baselines.
- **Hida Bushi School** — `specs/010-hida-bushi-school/`, merged
  2026-05-28 as commit `b52dc08`. Identity-driven HIDA_PRIORITIES
  (lunge → double-attack rules-fidelity fix) + new
  `HidaAttackStrategy` (kill-shot / pressure / reserve with the
  combat-simulator P5 gate `len(actions) >= 2`) + 3rd Dan reroll
  provider + 4th Dan SW-for-LW trade + 5th Dan counterattack-excess
  WC bonus and post-damage interrupt slot + 933 new tests
  (2954 → 3887). The OOM-trigger containment pattern
  (`_CappedCombatEngine` in playability tests) was added here and
  should be applied to future playability tests.
  Two deferrals documented in OPEN_QUESTIONS.md and structurally
  enforced via `@unittest.skip`: US3 win-feasibility (Akodo-side
  structural gap) and Principle IX 2(a) clean mirror termination
  (Hida defensive stack absorbs damage indefinitely). Both require
  a follow-up branch with broader scope than the school itself.
- **Matsu Bushi School** — `specs/011-matsu-bushi-school/`, merged
  2026-05-28 as commit `69cd640`. Identity-driven MATSU_PRIORITIES
  (parry capped at 3, fire promoted, void at Dan 4) + revised
  default strategy bindings (`WoundCheckStrategy04` +
  `DefaultInterruptStrategy`) + Special Ability strict 10-dice
  initiative (Q1) + 3rd Dan source-attributed
  `WoundCheckFloatingBonus` + 4th Dan rules-fidelity fixes
  (clean-hit extra-dice bug + strict `<` boundary) + 5th Dan
  listener relocated from `wound_check_failed` to `sw_damage` slot
  (eliminates double-SW emission + LW race vs defender's default
  listener) + ~50 new tests (3887 → 3925). One US3 sub-test
  (vs Wave-Man baseline) honestly skipped — cross-school evidence
  shows NO validated school meets the 35% floor vs Wave-Man at
  450 XP, indicating the Wave-Man template at 450 XP is
  structurally over-tuned (rules-balance question for a follow-up
  branch). Matsu vs Akodo 40% PASSES (clear contrast to Hida's 0%).
- **Bayushi Bushi School** — `specs/012-bayushi-bushi-school/`,
  merged 2026-05-28 as commit `e36c7d3`. **Audit-and-tighten run**
  on the most polished bushi skeleton (263 lines, 9 existing tests).
  Rules-fidelity: PASSED (with 1 MINOR dead-code fix in
  `BayushiAttackStrategy._count_bayushi_4th_dan_bonuses` — `source`
  is a method, not an attribute). Principle VII fixes: added
  `bayushi_5th_dan_halved_lw_actual` field to `WoundCheckEntry` so
  the 5th Dan half-LW WC surfaces with explicit attribution
  ("Bayushi 5th Dan: SW vs halved LW (N → N//2)") in both renderers;
  relabeled "VP on attack" → "Bayushi Special Ability VP on attack"
  in damage breakdown. Win-feasibility vs Akodo at 450 XP: ~80%
  (combat-simulator measurement) — Bayushi's Special Ability damage
  is so strong it dominates. + 24 new tests (3925 → 3949).
  Two deferrals documented in OPEN_QUESTIONS.md:
  (1) `BayushiAttackStrategy` (feint-first ladder) PROVIDED in
  source + unit-tested but NOT installed — the engine default
  `UniversalAttackStrategy` gates its feint branch on `vp() == 0`,
  so under defaults the 3rd/4th Dan feint engines are functionally
  unreachable (combat-simulator confirmed: 0/78 feints across 20
  seeds). Installation shifts the seed=1234 calibration combat used
  by ~10 trace tests; deferred to a follow-up branch.
  (2) `BAYUSHI_PRIORITIES` revision (school-progression-designer's
  identity-aligned version) also documented but not applied for the
  same calibration-combat reason.
- **Shinjo Bushi School** — `specs/017-shinjo-bushi-school/`,
  merged 2026-05-29. **Audit-and-completion run** on a 152-line
  skeleton with 13 existing tests; combat-simulator's pre-fix
  baseline showed 0/10 wins vs 450-XP Akodo and 0/13 round-robin
  wins — the school was structurally broken.
  Rules-fidelity (3 BLOCKING fixes):
  - **Q1**: ``extra_rolled()`` returned ``["double attack",
    "initiative", "parry"]`` instead of the rules-text
    ``["initiative", "parry", "wound check"]`` — missing wound
    check + included a knack not in the 1st Dan clause.
  - **Q4 BLOCKING IDENTITY**: ``ShinjoSpendActionListener``
    computed ``2 * hold_phases`` and wrote it to
    ``character._shinjo_hold_bonus`` — but NOTHING in the codebase
    read that attribute. The +2X-per-phase-held Special Ability
    was structurally DEAD. Fixed by emitting an ``AddModifierEvent``
    with ``Modifier(character, None, ATTACK_SKILLS, +2X)`` paired
    with ``ExpireAfterNextAttackByCharacterListener`` +
    ``ExpireAtEndOfRoundListener`` (Daidoji precedent).
  - **NEW BLOCKING bug surfaced by combat-simulator**: 4th Dan
    "highest die set to 1" failed on TIES — ``actions.index(max
    (actions))`` only reduced the first occurrence, so
    ``[2,3,5,5]`` initial → ``[1,2,3,5]`` instead of
    ``[1,1,2,3]``. Fixed by reducing ALL dice tied at the max.
  Q2 (4th Dan double-roll-initiative) and Q5 (hold-phases math)
  pre-resolved in OPEN_QUESTIONS were both REFUTED by
  rules-auditor: ``_set_school_listener`` REPLACES the
  ``new_round`` slot (so the engine default doesn't fire), and
  ``InitiativeAction.phase()`` returns the original die value for
  non-interrupt actions (the engine constructs them with
  ``InitiativeAction([die], die)``).
  Principle VIII identity bindings: ``HoldOneActionStrategy``
  (Special Ability rewards held dice), ``AlwaysParryStrategy``
  (2nd/3rd/5th Dan all trigger on parry), ``WoundCheckStrategy04``
  (1st Dan +1 WC die + 5th Dan margin-bonus = above-average WC
  pool).
  Q3 refactor: ``ShinjoFifthDanParryListener`` now subclasses
  ``ShinjoParryListener`` and delegates the 3rd Dan
  action-die decrease via ``super()`` instead of duplicating the
  loop inline.
  Tests: 14 new tests (4018 → 4032), 100% coverage on
  ``shinjo_school.py``. Both playability tests pass (mirror at
  300 XP terminates; hold-bonus modifier fires empirically vs
  Akodo).
  Deferrals documented:
  1. ``SHINJO_PRIORITIES`` revision (parry-first / attack-second /
     air-3 at Dan 3 / earth removed) — same calibration-combat
     cascade as Bayushi/Kakita/Otaku/Shiba.
  2. Trace renderer surfacing for the Special Ability hold-bonus
     modifier — tagged via ``_shinjo_special_ability_hold_phases``
     attribute on the modifier but the existing modifier-breakdown
     renderer doesn't yet read school-specific source attribution
     for transient modifiers (broader trace-infrastructure work).
  3. 3rd Dan action-die decrease + 4th Dan highest-to-1 trace
     surfacing — currently silent state mutations.
- **Shiba Bushi School** — `specs/016-shiba-bushi-school/`,
  merged 2026-05-29. **Audit-and-completion run** on a 139-line
  skeleton with 6 existing tests.
  **HIGH-severity dead-code bug surfaced by rules-auditor**:
  ``ShibaParryAction.roll_parry`` was the wrong method name —
  the engine calls ``roll_skill`` (see ``actions.py:327``), so the
  Special Ability "parry attacks directed at other characters with
  no penalty" never fired in real combat (the base
  ``ParryAction.roll_skill`` always applied the
  ``5 * attacker.skill("attack")`` parry-other penalty). The
  existing ``test_no_parry_other_penalty`` masked the bug by
  calling ``roll_parry()`` directly. Fixed by renaming to
  ``roll_skill`` with the matching base signature (ring kwarg
  preserved).
  Rules-fidelity (3 BLOCKING):
  - **T-A1** (above): ``roll_parry`` → ``roll_skill`` rename.
  - **Q3** (3rd Dan normalization): ``ShibaTakeParryEvent._roll_damage``
    bypassed ``normalize_roll_params``; for attack≥6 (rolled=12)
    the buggy code rolled raw 12k1 instead of the engine-convention
    normalized 10k3. Fixed via explicit pass through
    ``normalize_roll_params``.
  - **Q2** (lowest die): rules say "spending your **lowest** 1
    action die" but standard ``BaseAttackStrategy.choose_action`` /
    ``BaseParryStrategy._choose_action`` interrupt branch picks
    ``max``. New ``ShibaInterruptParryStrategy._choose_action``
    picks ``min(actions())``.
  Principle VIII identity bug (Q1 partially refuted): ``parry`` is
  already in the engine default ``_interrupt_skills``, so the spec's
  initial ``add_interrupt_skill`` framing was unnecessary — but the
  engine default ``DefaultInterruptStrategy`` delegates to
  ``ReluctantParryStrategy`` which damage-gates parries (suppresses
  the 3rd Dan damage engine which is supposed to fire on EVERY parry
  attempt). New ``ShibaInterruptParryStrategy`` fires eagerly on
  ``AttackRolledEvent`` against Shiba or adjacent allies with the
  lowest-die selection + SW-saturation gate. Also installed
  ``WoundCheckStrategy04`` (1st Dan WC die + 4th Dan +3k1 WC =
  +4k1 WC, extreme tank profile).
  Tests: 23 new tests (3995 → 4018), 100% coverage on
  ``shiba_school.py``. Both playability tests pass (mirror at
  300 XP terminates within 18 rounds; interrupt-parry fires
  empirically against Akodo across a 10-seed sweep).
  Deferrals documented:
  1. ``SHIBA_PRIORITIES`` revision (parry-first / attack-second /
     counterattack capped at 3 / air-3 at Dan 3 / water-3 at Dan 3 /
     earth demoted) — same Bayushi/Kakita/Otaku-precedent
     calibration-combat cascade pattern.
  2. **5th Dan ``AddModifierEvent`` rendering** — trace-auditor +
     trace-reader both flagged this as P0 (modifier invisible in
     both renderers). Tag ``_shiba_5th_dan_margin`` added to the
     event for downstream wiring, but no ``AddModifierEvent``
     handler exists in the trace adapters at all (broader trace-
     infrastructure work beyond Shiba-specific scope).
  3. **3rd Dan parry damage attribution** in the LW-damage entry —
     same trace-infrastructure scope; the damage line currently
     reads as ordinary attack damage.
  4. **combat-simulator stream timeout** — Phase 2 dispatch had an
     API connection error; playability tests provide local
     validation but no full round-robin baseline.
- **Otaku Bushi School** — `specs/014-otaku-bushi-school/`,
  merged 2026-05-29. **Audit-and-completion run** on a 192-line
  skeleton with 27 existing tests. Rules-fidelity: 4 BLOCKING fixes —
  (Q2) 3rd Dan listener was modifying ALL of target's action dice
  instead of "next X" where X = Otaku's attack skill; (Q3) 5th Dan
  "may" was unconditional — added strategic threshold (`raw_rolled
  >= 20`) so the dice-trade fires on overflow rolls only rather
  than every hit ≥ 12 rolled; (Q4) 5th Dan dice math left negative
  `extra_rolled` components leaking into the user-visible trace as
  "-Nk-M reconciliation" — algebra preserved + min-2 floor made
  explicit; (Q1) **HIGH-severity Principle VIII identity bug** —
  `add_interrupt_skill("lunge")` was wired but no strategy fired
  the interrupt; combat-simulator measured 0 interrupt-lunges
  across 23 combats pre-fix. Added new `OtakuInterruptLungeStrategy`
  (fires on `AttackSucceededEvent`/`AttackFailedEvent` via a new
  `OtakuAttackResolvedListener` since the engine's default listener
  wiring doesn't dispatch interrupt_strategy on resolution events)
  with mirror-recursion gate (decline against incoming interrupt-
  lunge) + SW-saturation gate (decline at sw_remaining ≤ 1) +
  WoundCheckStrategy04 install (1st Dan WC die + 2nd Dan WC free
  raise = aggressive WC posture, matches Hida/Matsu/Bayushi).
  Principle VII trace fix: `_from_otaku_5th_dan` flag on the SW
  event surfaces "Otaku 5th Dan: traded 10 rolled damage dice for
  1 SW" attribution in both renderers. + 25 new tests (3974 → 3995).
  Deferrals documented: (1) `OTAKU_PRIORITIES` revision (school-
  progression-designer produced lunge-first / attack-second / fire-3
  at Dan 3 / water-3 at Dan 4 / parry-capped-at-3 revision) NOT
  applied — same Bayushi/Kakita-precedent calibration-combat shift
  pattern. (2) Trace observability for 3rd Dan target-action-die
  shift, 4th Dan parry-still-+1, and Special Ability interrupt-
  lunge label — tags present on the action events but renderer
  surfacing limited to the 5th Dan SW (the highest-impact gap per
  trace-auditor P0 ranking). (3) Base `LungeAction.calculate_extra_
  damage_dice` returning `super() + 1` on parry makes the Otaku
  4th Dan override structurally redundant for output — flagged by
  rules-auditor as a separate rules-fidelity question (other lunge
  users shouldn't get +1 on parry).
- **Kakita Duelist School** — `specs/013-kakita-duelist-school/`,
  merged 2026-05-29 as commit `c768b30`. **Audit-and-tighten run**
  on the largest bushi skeleton (610 lines, 16 existing tests, 24
  classes / functions, iaijutsu-duel engine already exists per
  `5d67a78`). Rules-fidelity: PASS with 1 MINOR (5th Dan extra free
  raise encoded as -5 on opponent instead of +5 on Kakita —
  mechanically equivalent). **HIGH-severity Constitution Principle
  VIII identity fix**: the default attack strategy was
  `KakitaAttackStrategy` (doesn't check `has_interrupt_action`)
  even though `apply_special_ability` calls `add_interrupt_skill
  ("iaijutsu")` — the Special Ability's interrupt-iaijutsu clause
  was structurally dead. Swapped to `KakitaInterruptAttackStrategy`.
  Principle VII fixes: 3rd Dan tempo bonus now surfaces with
  "Kakita 3rd Dan tempo bonus (attack X × Y phases): +N" attribution
  (was a bare unsourced +N with broken "(see preceding line)"
  cross-reference); 2nd Dan iaijutsu free raise also attributed.
  Refactored 3 duplicated `skill_roll_params` blocks into a single
  `_kakita_tempo_bonus` helper. Win-feasibility vs 450-XP Akodo:
  ~90% (combat-simulator). + 17 new tests (3951 → 3968).
  Four deferrals documented: (1) Q1 name discrepancy ("Kakita Bushi
  School" vs upstream "Kakita Duelist School") — needs an atomic
  rename branch; (2) `KAKITA_PRIORITIES` revision — cascades into
  19 failing study tests (`web/analysis/definitions/kakita_*.py`
  encode the OLD priorities); (3) 4th Dan iaijutsu damage free
  raise trace observability — requires a damage-modifier breakdown
  system that doesn't exist; (4) 5th Dan "reconciliation" label on
  contested damage — requires plumbing through `normalize_roll_params`.

## Partial work (no full audit yet)

- **Ide Diplomat School** — `school_choices` Pattern B
  (configurable `school_ring`) was added during the
  `003-school-choices` feature, but the school has never been
  through a full Mirumoto/Ishi-style audit. Treat as a skeleton
  school for queue purposes; the choice infrastructure stays.

## Skeleton present — needs full audit + completion

Listed in suggested implementation order, grouped by archetype so
adjacent runs share rules-text patterns and review heuristics.

### Bushi schools (direct combat — closest in shape to Mirumoto)

- [ ] **Daidoji Yojimbo School**
  (`simulation/schools/daidoji_school.py`). Crane-clan bodyguard;
  has interrupt-cost mutation that the 5th Dan negation refactor
  flagged as not yet tracked. Treat as a candidate to extend
  `BaseSchool` mutation-tracking helpers.

### Specialty schools (non-bushi combat)

- [ ] **Hiruma Scout School**
  (`simulation/schools/hiruma_school.py`). Crab-clan
  scout/skirmisher.
- [ ] **Kuni Witch Hunter School**
  (`simulation/schools/kuni_school.py`). Has known engine gap —
  `NotImplementedError: spend_ap` per prior notes. Audit may
  surface engine work.
- [ ] **Yogo Warden School**
  (`simulation/schools/yogo_school.py`). Scorpion-clan ward-caster
  (some abilities likely shugenja-adjacent — verify whether they
  fall under the Shugenja School out-of-scope clause or are purely
  combat-relevant).
- [ ] **Isawa Duelist School**
  (`simulation/schools/isawa_school.py`). Phoenix-clan duelist (NOT
  the same as Isawa Ishi). Has the water-damage skill_ring mutation
  flagged by the negation refactor.

### Mystic / monk schools

- [ ] **Brotherhood of Shinsei Monk School**
  (`simulation/schools/monk_school.py`). Unarmed monk.
- [ ] **Togashi Ise Zumi School**
  (`simulation/schools/ise_zumi_school.py`). Dragon-clan tattooed
  monk.
- [ ] **Priest School** (`simulation/schools/priest_school.py`).
  Has 5 TODO markers — likely a near-empty skeleton.

### Court / social schools (combat presence is indirect)

These schools' identities are largely social, but per Constitution
Principle VIII their combat defaults must still be playable. Audit
will need careful Principle IX analysis (what does "identity engine
fires" look like for a school whose identity is social maneuvering?).

- [ ] **Courtier School**
  (`simulation/schools/courtier_school.py`).
- [ ] **Doji Artisan School**
  (`simulation/schools/doji_artisan_school.py`). Has ad-hoc
  `_doji_artisan_*` attributes flagged by the negation refactor.
- [ ] **Ikoma Bard School**
  (`simulation/schools/ikoma_bard_school.py`).
- [ ] **Shosuro Actor School**
  (`simulation/schools/shosuro_actor_school.py`).
- [ ] **Kitsuki Magistrate School**
  (`simulation/schools/kitsuki_school.py`). Investigator/courtier
  hybrid.
- [ ] **Ide Diplomat School** — see "Partial work" above; restart
  from full audit when picked up.

### Trade school

- [ ] **Merchant School**
  (`simulation/schools/merchant_school.py`). Combat presence is
  unclear; audit may determine this is largely a non-combat school.

## Out of scope

These remain unimplemented and are excluded from the queue. Do not
draft specs for them in the current project phase.

- **Shugenja School** — the generalized spell-using shugenja class
  in `rules/04-schools.md`. Deferred per Constitution Principle III
  (this phase of the project does not model the spell subsystem).
  Note: **Isawa Ishi** is implemented because its Special Ability
  is Void-point mysticism, not spellcasting; it does not depend on
  the Shugenja spell engine.
- **Between Place rules / Spirit Encounter rules** — permanently
  out of scope per Constitution Principle III.

## Notes on classification

The "Skeleton present" status only means the file exists in
`simulation/schools/` and is registered in `factory.py`. Every
audited school so far (Mirumoto, Ishi) has surfaced substantive
bugs during `rules-auditor` review even when the skeleton looked
complete. Do not treat a high line-count or absence of TODO
markers as evidence of correctness.
