"""
alarm_engine.py
===============
Phase 2 — Alarm Engine
Converts raw simulator signals into structured industrial alarms.
Each alarm carries: id, name, severity, timestamp, affected component, raw value.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from simulator import SystemState


# ─────────────────────────────────────────────
# ALARM DEFINITION
# ─────────────────────────────────────────────

@dataclass
class Alarm:
    alarm_id:   str    # unique short code  e.g. "ALM-001"
    name:       str    # human label        e.g. "Conveyor Jam"
    severity:   str    # CRITICAL | HIGH | MEDIUM | LOW
    component:  str    # which subsystem    e.g. "Conveyor"
    message:    str    # detail message
    value:      float  # the raw value that triggered it
    threshold:  float  # the threshold that was breached
    timestamp:  str    = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    active:     bool   = True


# ─────────────────────────────────────────────
# THRESHOLDS  (single source of truth)
# ─────────────────────────────────────────────

THRESHOLDS = {
    "conveyor_speed_low":      20.0,   # % — below this → jam likely
    "conveyor_speed_zero":      2.0,   # % — essentially stopped
    "motor_temp_warning":      75.0,   # °C
    "motor_temp_critical":     90.0,   # °C
    "motor_current_high":       9.0,   # A
    "packages_per_min_low":     5.0,   # ppm
}


# ─────────────────────────────────────────────
# ALARM ENGINE
# ─────────────────────────────────────────────

class AlarmEngine:
    """
    Evaluates each SystemState snapshot against threshold rules.
    Returns a list of active Alarm objects.
    """

    def evaluate(self, state: SystemState) -> List[Alarm]:
        alarms: List[Alarm] = []
        self._check_conveyor(state, alarms)
        self._check_motor(state, alarms)
        self._check_vision(state, alarms)
        self._check_robot(state, alarms)
        self._check_throughput(state, alarms)
        return alarms

    # ── Subsystem checks ──────────────────────────────────────────

    def _check_conveyor(self, s: SystemState, alarms: List[Alarm]):
        if s.conveyor_speed <= THRESHOLDS["conveyor_speed_zero"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-001",
                name      = "Conveyor Stopped",
                severity  = "CRITICAL",
                component = "Conveyor",
                message   = f"Conveyor speed dropped to {s.conveyor_speed:.1f}% — possible jam or E-stop.",
                value     = s.conveyor_speed,
                threshold = THRESHOLDS["conveyor_speed_zero"],
                timestamp = s.timestamp,
            ))
        elif s.conveyor_speed <= THRESHOLDS["conveyor_speed_low"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-002",
                name      = "Conveyor Speed Low",
                severity  = "HIGH",
                component = "Conveyor",
                message   = f"Conveyor running at {s.conveyor_speed:.1f}% — below safe operating threshold.",
                value     = s.conveyor_speed,
                threshold = THRESHOLDS["conveyor_speed_low"],
                timestamp = s.timestamp,
            ))

        if s.conveyor_jammed:
            alarms.append(Alarm(
                alarm_id  = "ALM-003",
                name      = "Conveyor Jam Detected",
                severity  = "CRITICAL",
                component = "Conveyor",
                message   = "Physical jam detected on conveyor belt. Immediate inspection required.",
                value     = 1.0,
                threshold = 0.0,
                timestamp = s.timestamp,
            ))

    def _check_motor(self, s: SystemState, alarms: List[Alarm]):
        if s.motor_temp >= THRESHOLDS["motor_temp_critical"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-004",
                name      = "Motor Critical Overheat",
                severity  = "CRITICAL",
                component = "Motor",
                message   = f"Motor temperature at {s.motor_temp:.1f}°C — critical limit exceeded. Shutdown risk.",
                value     = s.motor_temp,
                threshold = THRESHOLDS["motor_temp_critical"],
                timestamp = s.timestamp,
            ))
        elif s.motor_temp >= THRESHOLDS["motor_temp_warning"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-005",
                name      = "Motor Overheat Warning",
                severity  = "HIGH",
                component = "Motor",
                message   = f"Motor temperature at {s.motor_temp:.1f}°C — approaching critical limit.",
                value     = s.motor_temp,
                threshold = THRESHOLDS["motor_temp_warning"],
                timestamp = s.timestamp,
            ))

        if s.motor_current >= THRESHOLDS["motor_current_high"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-006",
                name      = "Motor Overcurrent",
                severity  = "HIGH",
                component = "Motor",
                message   = f"Motor drawing {s.motor_current:.1f}A — possible mechanical resistance or stall.",
                value     = s.motor_current,
                threshold = THRESHOLDS["motor_current_high"],
                timestamp = s.timestamp,
            ))

    def _check_vision(self, s: SystemState, alarms: List[Alarm]):
        if not s.vision_detected:
            alarms.append(Alarm(
                alarm_id  = "ALM-007",
                name      = "No Package Detected",
                severity  = "MEDIUM",
                component = "Vision Sensor",
                message   = "Vision sensor reports no package at pickup zone. Feed or sensor issue.",
                value     = 0.0,
                threshold = 1.0,
                timestamp = s.timestamp,
            ))

    def _check_robot(self, s: SystemState, alarms: List[Alarm]):
        if s.robot_status == "WAITING":
            alarms.append(Alarm(
                alarm_id  = "ALM-008",
                name      = "Robot Idle — Waiting for Feed",
                severity  = "MEDIUM",
                component = "Cobot",
                message   = "Robot is idle — no package to pick. Upstream feed disruption.",
                value     = 0.0,
                threshold = 0.0,
                timestamp = s.timestamp,
            ))
        elif s.robot_status == "FAULT":
            alarms.append(Alarm(
                alarm_id  = "ALM-009",
                name      = "Robot Fault",
                severity  = "CRITICAL",
                component = "Cobot",
                message   = "Robot controller reports FAULT state. Manual reset required.",
                value     = 0.0,
                threshold = 0.0,
                timestamp = s.timestamp,
            ))

    def _check_throughput(self, s: SystemState, alarms: List[Alarm]):
        if s.packages_per_min < THRESHOLDS["packages_per_min_low"]:
            alarms.append(Alarm(
                alarm_id  = "ALM-010",
                name      = "Low Throughput",
                severity  = "LOW",
                component = "System",
                message   = f"Packaging rate dropped to {s.packages_per_min:.1f} ppm — below acceptable minimum.",
                value     = s.packages_per_min,
                threshold = THRESHOLDS["packages_per_min_low"],
                timestamp = s.timestamp,
            ))


# ─────────────────────────────────────────────
# QUICK SELF-TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from simulator import PackagingSimulator, FaultScenario

    sim    = PackagingSimulator()
    engine = AlarmEngine()

    print("=" * 60)
    print("  ALARM ENGINE — SELF TEST")
    print("=" * 60)

    test_cases = [
        (FaultScenario.NONE,           "Normal Operation"),
        (FaultScenario.CONVEYOR_JAM,   "Conveyor Jam (mature)"),
        (FaultScenario.MOTOR_OVERHEAT, "Motor Overheat (mature)"),
        (FaultScenario.VISION_FAILURE, "Vision Failure (mature)"),
    ]

    for scenario, label in test_cases:
        sim.set_scenario(scenario)
        # Advance to a mature fault state
        for _ in range(10):
            state = sim.tick()

        alarms = engine.evaluate(state)
        print(f"\n── {label} → {len(alarms)} alarm(s) ─────────────────")
        if alarms:
            for a in alarms:
                print(f"  [{a.severity:8}] {a.alarm_id} | {a.name}")
                print(f"            → {a.message}")
        else:
            print("  ✅ No alarms — system healthy")

    print("\n✅ Alarm Engine OK — Phase 2 complete\n")
