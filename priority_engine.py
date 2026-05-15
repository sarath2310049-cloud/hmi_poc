"""
priority_engine.py
==================
Phase 3 — Priority Engine
Classifies alarms into P1–P4 and produces an operator-ready sorted alarm list.
Also suppresses redundant alarms that are clearly secondary to a higher-priority event.
"""

from dataclasses import dataclass
from typing import List, Dict
from alarm_engine import Alarm


# ─────────────────────────────────────────────
# PRIORITY MAP
# ─────────────────────────────────────────────
# Maps alarm_id → priority level P1 (most urgent) → P4 (informational)

PRIORITY_MAP: Dict[str, str] = {
    "ALM-001": "P1",   # Conveyor Stopped
    "ALM-003": "P1",   # Conveyor Jam Detected
    "ALM-004": "P1",   # Motor Critical Overheat
    "ALM-009": "P1",   # Robot Fault

    "ALM-002": "P2",   # Conveyor Speed Low
    "ALM-005": "P2",   # Motor Overheat Warning
    "ALM-006": "P2",   # Motor Overcurrent

    "ALM-007": "P3",   # No Package Detected
    "ALM-008": "P3",   # Robot Idle

    "ALM-010": "P4",   # Low Throughput
}

PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}

PRIORITY_LABELS = {
    "P1": "🔴 CRITICAL — Immediate action required",
    "P2": "🟠 HIGH     — Respond within 5 minutes",
    "P3": "🟡 MEDIUM   — Monitor and prepare response",
    "P4": "🔵 LOW      — Informational",
}


# ─────────────────────────────────────────────
# SUPPRESSION RULES
# ─────────────────────────────────────────────
# If a root/primary alarm is present, suppress these secondary alarm_ids.
# This reduces noise — operators don't need to act on downstream effects separately.

SUPPRESSION_RULES: Dict[str, List[str]] = {
    "ALM-001": ["ALM-007", "ALM-008", "ALM-010"],   # Conveyor stop → suppress vision/robot/throughput
    "ALM-003": ["ALM-007", "ALM-008", "ALM-010"],   # Conveyor jam → same
    "ALM-004": ["ALM-006", "ALM-002"],               # Critical overheat → suppress overcurrent + speed low
}


# ─────────────────────────────────────────────
# PRIORITIZED ALARM DATACLASS
# ─────────────────────────────────────────────

@dataclass
class PrioritizedAlarm:
    alarm:      Alarm
    priority:   str    # P1–P4
    suppressed: bool   # True = secondary alarm, hidden from main view
    rank:       int    # sort key


# ─────────────────────────────────────────────
# PRIORITY ENGINE
# ─────────────────────────────────────────────

class PriorityEngine:
    """
    Takes raw alarm list → assigns priority → suppresses secondary alarms
    → returns sorted PrioritizedAlarm list ready for display.
    """

    def process(self, alarms: List[Alarm]) -> List[PrioritizedAlarm]:
        if not alarms:
            return []

        # Step 1: Assign priority to every alarm
        prioritized = []
        for alarm in alarms:
            priority = PRIORITY_MAP.get(alarm.alarm_id, "P4")
            prioritized.append(PrioritizedAlarm(
                alarm      = alarm,
                priority   = priority,
                suppressed = False,
                rank       = PRIORITY_ORDER[priority],
            ))

        # Step 2: Determine which alarms to suppress
        active_ids = {pa.alarm.alarm_id for pa in prioritized}
        suppressed_ids = set()
        for trigger_id, suppress_list in SUPPRESSION_RULES.items():
            if trigger_id in active_ids:
                for sid in suppress_list:
                    suppressed_ids.add(sid)

        for pa in prioritized:
            if pa.alarm.alarm_id in suppressed_ids:
                pa.suppressed = True

        # Step 3: Sort by priority (P1 first), then by alarm_id for stability
        prioritized.sort(key=lambda pa: (pa.rank, pa.alarm.alarm_id))

        return prioritized

    def active_only(self, prioritized: List[PrioritizedAlarm]) -> List[PrioritizedAlarm]:
        """Returns only unsuppressed alarms — what operators actually see."""
        return [pa for pa in prioritized if not pa.suppressed]

    def summary(self, prioritized: List[PrioritizedAlarm]) -> Dict:
        """Returns count breakdown by priority for dashboard widgets."""
        counts = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "suppressed": 0}
        for pa in prioritized:
            if pa.suppressed:
                counts["suppressed"] += 1
            else:
                counts[pa.priority] += 1
        return counts


# ─────────────────────────────────────────────
# QUICK SELF-TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from simulator import PackagingSimulator, FaultScenario
    from alarm_engine import AlarmEngine

    sim     = PackagingSimulator()
    a_eng   = AlarmEngine()
    p_eng   = PriorityEngine()

    print("=" * 65)
    print("  PRIORITY ENGINE — SELF TEST")
    print("=" * 65)

    test_cases = [
        (FaultScenario.NONE,           "Normal Operation"),
        (FaultScenario.CONVEYOR_JAM,   "Conveyor Jam Cascade"),
        (FaultScenario.MOTOR_OVERHEAT, "Motor Overheat"),
        (FaultScenario.VISION_FAILURE, "Vision Sensor Failure"),
    ]

    for scenario, label in test_cases:
        sim.set_scenario(scenario)
        for _ in range(10):
            state = sim.tick()

        raw_alarms  = a_eng.evaluate(state)
        prioritized = p_eng.process(raw_alarms)
        visible     = p_eng.active_only(prioritized)
        counts      = p_eng.summary(prioritized)

        print(f"\n── {label} ─────────────────────────────────")
        print(f"   Total alarms: {len(raw_alarms)} | Visible: {len(visible)} | Suppressed: {counts['suppressed']}")

        for pa in prioritized:
            tag = "  [SUPPRESSED]" if pa.suppressed else ""
            print(f"  {pa.priority} | {pa.alarm.alarm_id} | {pa.alarm.name}{tag}")

        print(f"\n  Operator sees ({len(visible)} alarm(s)):")
        for pa in visible:
            print(f"    {PRIORITY_LABELS[pa.priority]}")
            print(f"    → {pa.alarm.message}")

    print("\n✅ Priority Engine OK — Phase 3 complete\n")
