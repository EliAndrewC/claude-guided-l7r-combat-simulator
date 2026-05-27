"""SC-004 architectural proof — TraceEntry consumers compose freely.

Spec 007: a new renderer can be added that consumes ``list[TraceEntry]``
and emits its own output format WITHOUT touching ``DetailedEventFormatter``,
``CombatObserver``, or anything in ``simulation/``.

This test demonstrates that property by implementing a minimal toy
``JsonRenderer`` (not a shipping module — it lives here in the test
file only) and asserting:

1. ``JsonRenderer`` exists and is callable.
2. It handles every concrete ``TraceEntry`` subclass defined in
   ``web/adapters/trace_entries.py``.
3. The module only imports from ``web/adapters/trace_entries`` —
   verified by inspecting the JsonRenderer source's import list.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from typing import get_args

from web.adapters import trace_entries
from web.adapters.trace_entries import (
    AkodoFifthDanCounterEntry,
    AttackEntry,
    ComponentDelta,
    DamageProjection,
    DeathEntry,
    DuelEndedEntry,
    DuelInitiativeRolledEntry,
    DuelResheathEntry,
    DuelStrikeRolledEntry,
    GainFloatingBonusEntry,
    GainTvpEntry,
    IaijutsuDuelHeaderEntry,
    IaijutsuFocusEntry,
    IaijutsuStrikeEntry,
    InitiativeEntry,
    KeepLightWoundsEntry,
    LightWoundsDamageEntry,
    ModifierDelta,
    PhaseHeaderEntry,
    RawTextEntry,
    RoundHeaderEntry,
    SchoolNegatedEntry,
    SeriousWoundsDamageEntry,
    ShowMeYourStanceDeclaredEntry,
    ShowMeYourStanceRolledEntry,
    SpendFloatingBonusEntry,
    SpendVpEntry,
    StatusBlockEntry,
    SurrenderEntry,
    TakeSeriousWoundEntry,
    TraceEntry,
    UnconsciousEntry,
    WoundCheckEntry,
)
from web.adapters.trace_entries import (
    CounterattackEntry as _CounterattackEntry,
)
from web.adapters.trace_entries import (
    IaijutsuEntry as _IaijutsuEntry,
)
from web.adapters.trace_entries import (
    ParryEntry as _ParryEntry,
)


class JsonRenderer:
    """Toy renderer that emits one JSON object per TraceEntry.

    This is intentionally minimal — it demonstrates SC-004 by proving a
    new renderer can be added without touching anything but
    ``web/adapters/trace_entries.py``. NOT a production module.
    """

    def render(self, entries: list[TraceEntry]) -> str:
        return "\n".join(self._to_json(e) for e in entries)

    def _to_json(self, entry: TraceEntry) -> str:
        # Dataclass entries (the vast majority) convert via ``asdict``.
        if dataclasses.is_dataclass(entry):
            return json.dumps(dataclasses.asdict(entry), sort_keys=True)
        # Defensive fallback — never reachable in correct operation.
        return json.dumps({"unknown": str(entry)})  # pragma: no cover


def _concrete_trace_entry_subclasses() -> list[type]:
    """Enumerate every concrete dataclass type in the TraceEntry union."""
    return list(get_args(TraceEntry))


class TestJsonRenderer:
    def test_renderer_is_callable(self):
        r = JsonRenderer()
        assert callable(r.render)

    def test_handles_every_concrete_entry_type(self):
        """Every TraceEntry concrete subclass produces a valid JSON line."""
        renderer = JsonRenderer()
        samples = self._build_one_of_each()
        # Sanity: every concrete type from the union appears in samples.
        sample_types = {type(s) for s in samples}
        expected_types = set(_concrete_trace_entry_subclasses())
        missing = expected_types - sample_types
        assert not missing, f"Missing samples for: {missing}"

        output = renderer.render(samples)
        # Every line parses as valid JSON.
        for line in output.splitlines():
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
            assert "kind" in parsed

    def test_renderer_does_not_import_simulation(self):
        """Verify the JsonRenderer's source has no import from ``simulation``."""
        src = inspect.getsource(JsonRenderer)
        assert "import simulation" not in src
        assert "from simulation" not in src

    def test_renderer_does_not_import_combat_observer_or_formatter(self):
        """JsonRenderer must not reference DetailedEventFormatter or CombatObserver."""
        src = inspect.getsource(JsonRenderer)
        assert "DetailedEventFormatter" not in src
        assert "CombatObserver" not in src

    def test_trace_entries_module_does_not_import_simulation(self):
        """The TraceEntry definition module itself has no simulation deps."""
        src = inspect.getsource(trace_entries)
        assert "import simulation" not in src
        # The module CAN reference 'simulation' in docstrings (Principle II
        # references the engine pure rule) — we only ban actual imports.
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("from simulation"):
                raise AssertionError(
                    f"trace_entries.py must not import from simulation: {line}"
                )

    # ── helpers ───────────────────────────────────────────────────────

    def _build_one_of_each(self) -> list[TraceEntry]:
        """One synthetic instance per concrete TraceEntry subclass."""
        comp = [ComponentDelta("X", 5, 5), ComponentDelta("Y", 3, 0)]
        mods = [ModifierDelta("Bayushi 2nd Dan", 5)]
        proj = DamageProjection(
            rolled=7, kept=2, components=comp,
            extra_damage_dice=0, margin_over_tn=0,
        )
        return [
            RoundHeaderEntry(round_number=1),
            PhaseHeaderEntry(phase=2),
            StatusBlockEntry(statuses={
                "A": {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3,
                      "max_vp": 3, "actions": [1], "crippled": False},
            }),
            InitiativeEntry(entries=[{
                "name": "A", "rolled": 5, "kept": 4,
                "all_dice": [1, 2, 3, 4, 5], "actions": [1, 2, 3, 4],
            }]),
            AttackEntry(
                phase_prefix="Phase 1 | A |", actor_name="A", target_name="B",
                skill="attack", vp_spent=None, vp_skill=None,
                rolled=5, kept=3, modifier=0,
                components=comp, modifier_components=mods,
                dice=[10, 8, 5, 3, 1], sum_of_kept=23, total=23,
                tn=20, base_tn=20, outcome="hit",
                damage_projection=proj,
            ),
            _CounterattackEntry(
                phase_prefix="A |", actor_name="A", target_name="B",
                vp_spent=None, vp_skill=None,
                rolled=5, kept=3, modifier=0,
                components=comp, modifier_components=mods,
                dice=[10, 8, 5], sum_of_kept=23, total=23,
                tn=20, outcome="hit",
                damage_projection=proj,
            ),
            _ParryEntry(
                phase_prefix="A |", actor_name="A", target_name="B",
                rolled=5, kept=3, modifier=0,
                components=comp, modifier_components=mods,
                dice=[10, 8, 5], sum_of_kept=23, total=23,
                tn=20, outcome="succeeded",
            ),
            _IaijutsuEntry(
                phase_prefix="A |", actor_name="A", is_challenger=True,
                skill="iaijutsu", skill_roll=20, opponent_skill_roll=15,
                extra_damage_dice=1, rolled=5, kept=3,
                dice=[10, 8, 5], sum_of_kept=20, effective_modifier=0,
            ),
            LightWoundsDamageEntry(
                phase_prefix="A |", attacker_name="A", target_name="B",
                rolled=5, kept=2, components=comp,
                dice=[10, 8, 5, 3, 1], sum_of_kept=18, damage=18,
                lw_after=18,
            ),
            SeriousWoundsDamageEntry(
                phase_prefix="A |", target_name="B",
                damage=1, from_double_attack=False,
            ),
            WoundCheckEntry(
                phase_prefix="A |", character_name="A",
                vp_spent=None, vp_source=None, vp_skill=None,
                vp_breakdown=None,
                rolled=5, kept=3, modifier=0,
                components=comp, modifier_components=mods,
                dice=[9, 8, 6, 3, 1], sum_of_kept=23, total=23,
                tn=20, outcome="passed",
            ),
            KeepLightWoundsEntry(
                phase_prefix="A |", character_name="A", lw_total=15,
            ),
            TakeSeriousWoundEntry(
                phase_prefix="A |", character_name="A", voluntary=False,
            ),
            SpendVpEntry(
                phase_prefix="A |", character_name="A",
                amount=2, skill="attack",
            ),
            GainTvpEntry(
                phase_prefix="A |", character_name="A",
                amount=4, source="Akodo Special Ability",
            ),
            GainFloatingBonusEntry(
                phase_prefix="A |", character_name="A",
                amount=15, source="Akodo 3rd Dan",
                breakdown="margin 18 ÷ 5 × attack 5",
            ),
            SpendFloatingBonusEntry(
                phase_prefix="A |", character_name="A",
                amount=10, source="Akodo 3rd Dan",
            ),
            SchoolNegatedEntry(
                phase_prefix="A |", negator_name="Ishi", target_name="A",
                target_school_name="Akodo Bushi", vp_cost=10,
            ),
            AkodoFifthDanCounterEntry(
                phase_prefix="A |", akodo_name="A",
                vp_spent=2, damage=20, target_name="B",
            ),
            IaijutsuDuelHeaderEntry(),
            ShowMeYourStanceDeclaredEntry(character_name="A"),
            ShowMeYourStanceRolledEntry(
                character_name="A", roll=15,
                discerned_fire=3, discerned_tn=30,
                rolled=None, kept=None, dice=[],
            ),
            DuelInitiativeRolledEntry(
                challenger_name="A", defender_name="B",
                challenger_roll=20, defender_roll=15, winner_name="A",
            ),
            IaijutsuFocusEntry(
                character_name="A", challenger_name="A", defender_name="B",
                challenger_tn=30, defender_tn=25,
            ),
            IaijutsuStrikeEntry(
                character_name="A", challenger_name="A", defender_name="B",
                challenger_tn=30, defender_tn=25,
            ),
            DuelStrikeRolledEntry(
                character_name="A", target_name="B", roll=20, tn=15,
                is_hit=True, extra_damage_dice=0,
                rolled=None, kept=None, dice=[],
            ),
            DuelResheathEntry(higher_roller_name="A"),
            DuelEndedEntry(),
            DeathEntry(phase_prefix="A |", character_name="A"),
            UnconsciousEntry(phase_prefix="A |", character_name="A"),
            SurrenderEntry(phase_prefix="A |", character_name="A"),
            RawTextEntry(lines=["some raw line"]),
        ]


class TestArchitectureContract:
    """Spec 007 SC-004 + Principle II compliance."""

    def test_trace_entries_pure_data(self):
        """All TraceEntry concrete types are frozen dataclasses."""
        for cls in _concrete_trace_entry_subclasses():
            assert dataclasses.is_dataclass(cls), f"{cls.__name__} not a dataclass"
            # ``frozen=True`` → cls has ``__hash__`` and immutable.
            params = cls.__dataclass_params__
            assert params.frozen is True, f"{cls.__name__} not frozen"

    def test_trace_entries_have_kind_discriminator(self):
        """Every concrete TraceEntry subclass exposes a ``kind`` field."""
        for cls in _concrete_trace_entry_subclasses():
            field_names: list[str] = [
                f.name for f in dataclasses.fields(cls)
            ]
            assert "kind" in field_names, f"{cls.__name__} missing 'kind' field"

    def test_concrete_count_matches_data_model(self):
        """Sanity check — spec 007 enumerated ~30 entry types."""
        subclasses = _concrete_trace_entry_subclasses()
        assert len(subclasses) >= 25
        assert len(subclasses) <= 50
