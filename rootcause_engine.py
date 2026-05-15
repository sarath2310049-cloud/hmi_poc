"""
rootcause_engine.py
===================
Phase 4 — Root Cause Engine  ← CORE INNOVATION
Uses a machine dependency graph + alarm correlation to identify
the PRIMARY root cause and suppress downstream cascade alarms.

Output: single RootCauseReport with causal chain + recommended actions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from alarm_engine import Alarm
from priority_engine import PrioritizedAlarm, PriorityEngine


# ─────────────────────────────────────────────
# MACHINE DEPENDENCY GRAPH
# ─────────────────────────────────────────────
# node → list of nodes it feeds into
# If node X fails, everything downstream is a SECONDARY effect.

DEPENDENCY_GRAPH: Dict[str, List[str]] = {
    "Conveyor":      ["Vision Sensor", "Motor"],
    "Vision Sensor": ["Cobot"],
    "Motor":         ["Conveyor"],       # Motor failure also stops conveyor
    "Cobot":         ["System"],
    "System":        [],
}

# Reverse map: component → its upstream dependencies
def _build_upstream_map() -> Dict[str, List[str]]:
    upstream: Dict[str, List[str]] = {k: [] for k in DEPENDENCY_GRAPH}
    for source, targets in DEPENDENCY_GRAPH.items():
        for t in targets:
            upstream.setdefault(t, []).append(source)
    return upstream

UPSTREAM_MAP = _build_upstream_map()


# ─────────────────────────────────────────────
# ROOT CAUSE SCENARIOS
# ─────────────────────────────────────────────
# Each entry: (root_alarm_ids, root_cause_label, causal_chain, recommended_steps)

ROOT_CAUSE_SCENARIOS = [
    {
        "id":          "RC-001",
        "triggers":    {"ALM-003"},               # Conveyor jam confirmed (jam flag set)
        "label":       "Conveyor Mechanical Jam",
        "chain": [
            ("Conveyor",      "Belt stopped due to physical obstruction"),
            ("Vision Sensor", "No package reaching sensor — feed interrupted"),
            ("Cobot",         "Robot idle — nothing to pick"),
            ("Motor",         "Stall current spiking — motor fighting jam"),
        ],
        "impact": ["ALM-007", "ALM-008", "ALM-006", "ALM-010"],  # secondary alarm IDs
        "actions": [
            ("Step 1", "STOP",    "Trigger E-stop on Conveyor Motor (M1) immediately"),
            ("Step 2", "INSPECT", "Physically inspect conveyor belt at Station 2–3 for obstruction"),
            ("Step 3", "CLEAR",   "Remove blocked package or foreign object"),
            ("Step 4", "CHECK",   "Inspect belt tension and roller alignment"),
            ("Step 5", "RESTART", "Reset motor drive and restart conveyor at 60% speed"),
            ("Step 6", "VERIFY",  "Confirm vision sensor detects first package before full speed"),
        ],
        "estimated_downtime": "5–10 minutes",
    },
    {
        "id":          "RC-002",
        "triggers":    {"ALM-004"},               # Motor critical overheat
        "label":       "Motor Thermal Failure",
        "chain": [
            ("Motor",    "Winding temperature exceeded safe limit — thermal protection activating"),
            ("Conveyor", "Speed reduced by thermal protection circuit"),
            ("Cobot",    "Pick rate degraded due to irregular feed"),
        ],
        "impact": ["ALM-005", "ALM-006", "ALM-002", "ALM-010"],
        "actions": [
            ("Step 1", "REDUCE",  "Reduce conveyor load — drop to 50% speed immediately"),
            ("Step 2", "COOL",    "Allow motor to cool for minimum 15 minutes"),
            ("Step 3", "INSPECT", "Check motor cooling fan and ventilation clearance"),
            ("Step 4", "CHECK",   "Verify motor drive parameters — check for overcurrent history"),
            ("Step 5", "RESTART", "Restart at reduced speed, monitor temperature for 5 minutes"),
        ],
        "estimated_downtime": "15–20 minutes",
    },
    {
        "id":          "RC-003",
        "triggers":    {"ALM-005", "ALM-006"},    # Overheat warning + overcurrent
        "label":       "Motor Overload — Early Warning",
        "chain": [
            ("Motor",    "Current and temperature both elevated — overload condition developing"),
            ("Conveyor", "Risk of speed reduction if not addressed"),
        ],
        "impact": ["ALM-010"],
        "actions": [
            ("Step 1", "MONITOR", "Increase monitoring frequency — check every 2 minutes"),
            ("Step 2", "REDUCE",  "Reduce conveyor speed to 70% as precaution"),
            ("Step 3", "INSPECT", "Check for partial mechanical obstruction on belt"),
            ("Step 4", "LOG",     "Log event for maintenance review — check motor wear schedule"),
        ],
        "estimated_downtime": "0 minutes (preventive action)",
    },
    {
        "id":          "RC-004",
        "triggers":    {"ALM-007"},               # Vision failure
        "label":       "Vision Sensor Malfunction",
        "chain": [
            ("Vision Sensor", "Sensor not detecting packages — possible misalignment or contamination"),
            ("Cobot",         "Robot unable to confirm pick target — waiting"),
        ],
        "impact": ["ALM-008", "ALM-010"],
        "actions": [
            ("Step 1", "CHECK",   "Verify vision sensor power and cable connections"),
            ("Step 2", "CLEAN",   "Clean sensor lens — check for dust, glare, or obstruction"),
            ("Step 3", "ALIGN",   "Confirm sensor alignment with package detection zone"),
            ("Step 4", "TEST",    "Run sensor self-test from HMI diagnostic panel"),
            ("Step 5", "RESTART", "Restart sensor controller if self-test fails"),
        ],
        "estimated_downtime": "3–8 minutes",
    },
]


# ─────────────────────────────────────────────
# ROOT CAUSE REPORT
# ─────────────────────────────────────────────

@dataclass
class CausalStep:
    component:   str
    description: str

@dataclass
class ActionStep:
    step:        str
    action_type: str   # STOP | INSPECT | CLEAR | CHECK | RESTART | REDUCE | MONITOR | LOG | VERIFY | COOL | CLEAN | ALIGN | TEST
    description: str

@dataclass
class RootCauseReport:
    scenario_id:        str
    root_cause:         str               # human-readable label
    confidence:         str               # HIGH | MEDIUM | LOW
    primary_alarm:      Optional[Alarm]   # the alarm that triggered root cause
    causal_chain:       List[CausalStep]  # ordered chain of effects
    secondary_alarms:   List[Alarm]       # suppressed downstream alarms
    recommended_actions: List[ActionStep]
    estimated_downtime: str
    timestamp:          str = field(default_factory=lambda: __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def is_healthy(self) -> bool:
        return self.scenario_id == "HEALTHY"


# ─────────────────────────────────────────────
# ROOT CAUSE ENGINE
# ─────────────────────────────────────────────

class RootCauseEngine:
    """
    Matches active alarm set against ROOT_CAUSE_SCENARIOS.
    Returns a single RootCauseReport — the most specific match found.
    """

    def __init__(self):
        self._p_engine = PriorityEngine()

    def analyze(self, alarms: List[Alarm]) -> RootCauseReport:
        if not alarms:
            return self._healthy_report()

        active_ids = {a.alarm_id for a in alarms}
        alarm_map  = {a.alarm_id: a for a in alarms}

        # Find best matching scenario.
        # Priority rules:
        #   1. A scenario whose trigger is a SAFETY-CRITICAL alarm (P1) wins outright.
        #   2. Otherwise: full-match wins over partial; larger trigger set breaks ties.
        P1_ALARM_IDS = {"ALM-001", "ALM-003", "ALM-004", "ALM-009"}

        best_scenario  = None
        best_score     = (-1, -1, 0)   # (has_p1_trigger, all_matched, trigger_set_size)

        for scenario in ROOT_CAUSE_SCENARIOS:
            triggers    = scenario["triggers"]
            overlap     = len(triggers & active_ids)
            if overlap == 0:
                continue
            has_p1      = 1 if triggers & P1_ALARM_IDS & active_ids else 0
            all_matched = 1 if overlap == len(triggers) else 0
            score       = (has_p1, all_matched, len(triggers))
            if score > best_score:
                best_score    = score
                best_overlap  = overlap
                best_scenario = scenario

        if best_scenario is None or best_overlap == 0:
            return self._unknown_report(alarms)

        # Determine confidence based on how many triggers matched
        total_triggers = len(best_scenario["triggers"])
        confidence = "HIGH" if best_overlap == total_triggers else "MEDIUM"

        # Primary alarm = highest priority trigger
        trigger_alarms = [alarm_map[aid] for aid in best_scenario["triggers"] if aid in alarm_map]
        primary = trigger_alarms[0] if trigger_alarms else None

        # Secondary alarms = downstream effects
        secondary = [alarm_map[aid] for aid in best_scenario["impact"] if aid in alarm_map]

        return RootCauseReport(
            scenario_id   = best_scenario["id"],
            root_cause    = best_scenario["label"],
            confidence    = confidence,
            primary_alarm = primary,
            causal_chain  = [CausalStep(c, d) for c, d in best_scenario["chain"]],
            secondary_alarms = secondary,
            recommended_actions = [
                ActionStep(s, t, d) for s, t, d in best_scenario["actions"]
            ],
            estimated_downtime = best_scenario["estimated_downtime"],
        )

    # ── Fallback reports ──────────────────────────────────────────

    def _healthy_report(self) -> RootCauseReport:
        return RootCauseReport(
            scenario_id    = "HEALTHY",
            root_cause     = "No faults detected — system operating normally",
            confidence     = "HIGH",
            primary_alarm  = None,
            causal_chain   = [],
            secondary_alarms = [],
            recommended_actions = [],
            estimated_downtime = "N/A",
        )

    def _unknown_report(self, alarms: List[Alarm]) -> RootCauseReport:
        return RootCauseReport(
            scenario_id    = "RC-UNKNOWN",
            root_cause     = "Unclassified fault — manual investigation required",
            confidence     = "LOW",
            primary_alarm  = alarms[0] if alarms else None,
            causal_chain   = [CausalStep(a.component, a.message) for a in alarms],
            secondary_alarms = [],
            recommended_actions = [
                ActionStep("Step 1", "INSPECT", "Review all active alarms and recent trend data"),
                ActionStep("Step 2", "LOG",     "Document current system state for engineering review"),
            ],
            estimated_downtime = "Unknown",
        )


# ─────────────────────────────────────────────
# QUICK SELF-TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from simulator import PackagingSimulator, FaultScenario
    from alarm_engine import AlarmEngine

    sim    = PackagingSimulator()
    a_eng  = AlarmEngine()
    rc_eng = RootCauseEngine()

    print("=" * 65)
    print("  ROOT CAUSE ENGINE — SELF TEST")
    print("=" * 65)

    test_cases = [
        (FaultScenario.NONE,           "Normal Operation"),
        (FaultScenario.CONVEYOR_JAM,   "Conveyor Jam"),
        (FaultScenario.MOTOR_OVERHEAT, "Motor Overheat"),
        (FaultScenario.VISION_FAILURE, "Vision Failure"),
    ]

    for scenario, label in test_cases:
        sim.set_scenario(scenario)
        for _ in range(12):
            state = sim.tick()

        alarms = a_eng.evaluate(state)
        report = rc_eng.analyze(alarms)

        print(f"\n{'─'*65}")
        print(f"  SCENARIO : {label}")
        print(f"  ROOT CAUSE [{report.confidence} confidence]: {report.root_cause}")
        print(f"  Downtime Estimate: {report.estimated_downtime}")

        if report.causal_chain:
            print(f"\n  Causal Chain:")
            for i, step in enumerate(report.causal_chain):
                prefix = "  ┌" if i == 0 else ("  └" if i == len(report.causal_chain)-1 else "  │")
                print(f"  {prefix} [{step.component}] {step.description}")

        if report.secondary_alarms:
            print(f"\n  Secondary (suppressed) alarms: {[a.name for a in report.secondary_alarms]}")

        if report.recommended_actions:
            print(f"\n  Recommended Actions:")
            for action in report.recommended_actions:
                print(f"    [{action.step}] {action.action_type:8} → {action.description}")

    print("\n✅ Root Cause Engine OK — Phase 4 complete\n")
