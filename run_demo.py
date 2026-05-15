"""
run_demo.py
===========
Master Demo Runner — ties all 4 phases together.
Runs each fault scenario and prints a full intelligent situation report
the way an operator would see it on the HMI.

Usage:
    python run_demo.py
"""

import time
from simulator import PackagingSimulator, FaultScenario
from alarm_engine import AlarmEngine
from priority_engine import PriorityEngine, PRIORITY_LABELS
from rootcause_engine import RootCauseEngine


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

SEP  = "═" * 70
SEP2 = "─" * 70

ACTION_ICONS = {
    "STOP":    "🛑",
    "INSPECT": "🔍",
    "CLEAR":   "🧹",
    "CHECK":   "✔️",
    "RESTART": "🔄",
    "REDUCE":  "⬇️",
    "MONITOR": "👁️",
    "LOG":     "📋",
    "VERIFY":  "✅",
    "COOL":    "❄️",
    "CLEAN":   "🧼",
    "ALIGN":   "🎯",
    "TEST":    "🧪",
}

def icon(action_type: str) -> str:
    return ACTION_ICONS.get(action_type, "▶")

def severity_badge(s: str) -> str:
    return {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}.get(s, "⚪")


def print_situation_report(scenario_label: str, state, alarms, visible_alarms, report):
    print(f"\n{SEP}")
    print(f"  🏭 INTELLIGENT HMI — SITUATION REPORT")
    print(f"  Scenario : {scenario_label}")
    print(f"  Time     : {state.timestamp}")
    print(SEP)

    # ── Live Signals ─────────────────────────────────────────────
    print(f"\n  📡 LIVE SIGNALS")
    print(f"  {SEP2}")
    print(f"  Conveyor Speed   : {state.conveyor_speed:6.1f}%   {'⚠ JAMMED' if state.conveyor_jammed else '✓ OK'}")
    print(f"  Motor Temp       : {state.motor_temp:6.1f}°C  {'⚠ HOT' if state.motor_temp > 75 else '✓ OK'}")
    print(f"  Motor Current    : {state.motor_current:6.1f} A  {'⚠ HIGH' if state.motor_current > 9 else '✓ OK'}")
    print(f"  Vision Detected  : {'✓ YES' if state.vision_detected else '✗ NO  ⚠ ALERT'}")
    print(f"  Robot Status     : {state.robot_status}")
    print(f"  Throughput       : {state.packages_per_min:5.1f} ppm")

    # ── Alarm Summary ────────────────────────────────────────────
    print(f"\n  🚨 ALARMS ({len(alarms)} total | {len(visible_alarms)} shown | {len(alarms)-len(visible_alarms)} suppressed)")
    print(f"  {SEP2}")
    if visible_alarms:
        for pa in visible_alarms:
            print(f"  {severity_badge(pa.alarm.severity)} [{pa.priority}] {pa.alarm.name}")
            print(f"      → {pa.alarm.message}")
    else:
        print("  ✅ No alarms — all systems nominal")

    # ── Root Cause ───────────────────────────────────────────────
    print(f"\n  🧠 INTELLIGENT DIAGNOSIS")
    print(f"  {SEP2}")
    if report.is_healthy():
        print(f"  ✅ {report.root_cause}")
    else:
        print(f"  ROOT CAUSE [{report.confidence} confidence]:")
        print(f"  ❗ {report.root_cause}")
        print(f"  Estimated Downtime: {report.estimated_downtime}")

        if report.causal_chain:
            print(f"\n  CAUSAL CHAIN:")
            for i, step in enumerate(report.causal_chain):
                connector = "┌" if i == 0 else ("└" if i == len(report.causal_chain)-1 else "├")
                print(f"   {connector}─ [{step.component}]")
                print(f"   {'│' if i < len(report.causal_chain)-1 else ' '}    {step.description}")

        if report.secondary_alarms:
            names = ", ".join(a.name for a in report.secondary_alarms)
            print(f"\n  ℹ️  Secondary effects (suppressed): {names}")

    # ── Recommended Actions ──────────────────────────────────────
    if report.recommended_actions:
        print(f"\n  🔧 RECOMMENDED ACTIONS")
        print(f"  {SEP2}")
        for action in report.recommended_actions:
            print(f"  {icon(action.action_type)} {action.step}: [{action.action_type}] {action.description}")

    print(f"\n{SEP}\n")


# ─────────────────────────────────────────────
# MAIN DEMO
# ─────────────────────────────────────────────

def run_demo():
    sim    = PackagingSimulator()
    a_eng  = AlarmEngine()
    p_eng  = PriorityEngine()
    rc_eng = RootCauseEngine()

    demo_scenarios = [
        (FaultScenario.NONE,           "✅ Normal Operation"),
        (FaultScenario.CONVEYOR_JAM,   "🔴 Conveyor Jam Cascade"),
        (FaultScenario.MOTOR_OVERHEAT, "🟠 Motor Overheat"),
        (FaultScenario.VISION_FAILURE, "🟡 Vision Sensor Failure"),
    ]

    print(f"\n{'═'*70}")
    print("  🚀 INTELLIGENT CONTEXT-AWARE HMI — FULL SYSTEM DEMO")
    print("  Cobot Packaging Line | POC v1.0")
    print(f"{'═'*70}")
    print("\n  Phases active:")
    print("  ✅ Phase 1 — Digital Twin Simulator")
    print("  ✅ Phase 2 — Alarm Engine")
    print("  ✅ Phase 3 — Priority Engine")
    print("  ✅ Phase 4 — Root Cause Engine")

    input("\n  Press ENTER to start demo...\n")

    for scenario, label in demo_scenarios:
        sim.set_scenario(scenario)

        # Advance to a mature state
        for _ in range(12):
            state = sim.tick()

        alarms      = a_eng.evaluate(state)
        prioritized = p_eng.process(alarms)
        visible     = p_eng.active_only(prioritized)
        report      = rc_eng.analyze(alarms)

        print_situation_report(label, state, alarms, visible, report)
        input("  Press ENTER for next scenario...\n")

    print("  🏁 Demo complete.\n")


if __name__ == "__main__":
    run_demo()
