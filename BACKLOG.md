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
  2026-05-26. (5th-Dan negation refactor: `specs/004-…` not
  formalized; merged 2026-05-26 as commit `89dc0bb`.)

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

- [ ] **Akodo Bushi School** (`simulation/schools/akodo_school.py`).
  Canonical "generic" bushi; also one of the two playability
  baselines in Principle IX. **Critical to audit early** — every
  other school's win-feasibility check assumes Akodo behaves
  correctly.
- [ ] **Hida Bushi School** (`simulation/schools/hida_school.py`).
  The other Principle IX baseline. Currently has 3 TODO markers —
  likely the least-complete bushi skeleton. **Critical to audit
  early.**
- [ ] **Matsu Bushi School** (`simulation/schools/matsu_school.py`).
  Berserker/Lion-clan offensive bushi.
- [ ] **Bayushi Bushi School**
  (`simulation/schools/bayushi_school.py`). Scorpion-clan deception
  bushi (feint-heavy).
- [ ] **Kakita Duelist School**
  (`simulation/schools/kakita_school.py`, 610 lines — largest
  skeleton). Iaijutsu duelist; iaijutsu-duel engine already exists
  per commit `5d67a78`. Note: factory registration name is "Kakita
  Bushi School" but upstream rules-text title is "Kakita Duelist
  School" — verify which is authoritative before audit.
- [ ] **Otaku Bushi School** (`simulation/schools/otaku_school.py`).
  Unicorn-clan mounted bushi (mount mechanics may be out of scope
  for combat sim).
- [ ] **Shiba Bushi School** (`simulation/schools/shiba_school.py`).
  Phoenix-clan defender of shugenja (defensive bushi).
- [ ] **Shinjo Bushi School**
  (`simulation/schools/shinjo_school.py`). Unicorn-clan scout/bushi
  hybrid.
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
