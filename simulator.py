"""
simulator.py
============
Digital Twin Simulator — Cobot Packaging System
Simulates live industrial signals for conveyor, motor, vision sensor, and robot.
Supports normal operation + controlled fault injection for demo scenarios.
"""

import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────
# FAULT SCENARIO DEFINITIONS
# ─────────────────────────────────────────────

class FaultScenario(Enum):
    NONE            = "none"
    CONVEYOR_JAM    = "conveyor_jam"
    MOTOR_OVERHEAT  = "motor_overheat"
    VISION_FAILURE  = "vision_failure"


# ─────────────────────────────────────────────
# SYSTEM STATE
# ─────────────────────────────────────────────

@dataclass
class SystemState:
    timestamp: str           = ""

    # Conveyor
    conveyor_speed: float    = 100.0   # % of rated speed (0–100)
    conveyor_jammed: bool    = False

    # Motor
    motor_current: float     = 5.0     # Amperes
    motor_temp: float        = 45.0    # °C

    # Vision sensor
    vision_detected: bool    = True    # True = package present

    # Robot
    robot_status: str        = "IDLE"  # IDLE | PICKING | WAITING | FAULT

    # Packaging throughput
    packages_per_min: float  = 12.0

    # Metadata
    active_scenario: str     = FaultScenario.NONE.value


# ─────────────────────────────────────────────
# SIMULATOR CLASS
# ─────────────────────────────────────────────

class PackagingSimulator:
    """
    Generates realistic industrial sensor readings.
    In NORMAL mode: values fluctuate naturally around healthy baselines.
    In FAULT mode: values degrade according to the fault scenario.
    """

    # ── Healthy baselines ──────────────────────────────────────────
    NORMAL = {
        "conveyor_speed":    (95.0, 105.0),   # min, max
        "motor_current":     (4.5,  5.5),
        "motor_temp":        (40.0, 55.0),
        "packages_per_min":  (11.0, 13.0),
    }

    def __init__(self):
        self._scenario = FaultScenario.NONE
        self._fault_progress = 0.0   # 0.0 → 1.0 (how far fault has developed)
        self._state = SystemState()

    # ── Public API ─────────────────────────────────────────────────

    def set_scenario(self, scenario: FaultScenario):
        """Inject a fault scenario. Call with NONE to reset to normal."""
        self._scenario = scenario
        self._fault_progress = 0.0
        print(f"[Simulator] Scenario set → {scenario.value}")

    def tick(self) -> SystemState:
        """Advance simulation by one time step and return current state."""
        self._fault_progress = min(1.0, self._fault_progress + 0.08)
        state = self._build_state()
        self._state = state
        return state

    def current_state(self) -> SystemState:
        return self._state

    # ── Internal builders ──────────────────────────────────────────

    def _build_state(self) -> SystemState:
        s = SystemState()
        s.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s.active_scenario = self._scenario.value

        if self._scenario == FaultScenario.NONE:
            self._apply_normal(s)

        elif self._scenario == FaultScenario.CONVEYOR_JAM:
            self._apply_conveyor_jam(s)

        elif self._scenario == FaultScenario.MOTOR_OVERHEAT:
            self._apply_motor_overheat(s)

        elif self._scenario == FaultScenario.VISION_FAILURE:
            self._apply_vision_failure(s)

        return s

    def _apply_normal(self, s: SystemState):
        s.conveyor_speed   = self._rand(*self.NORMAL["conveyor_speed"])
        s.conveyor_jammed  = False
        s.motor_current    = self._rand(*self.NORMAL["motor_current"])
        s.motor_temp       = self._rand(*self.NORMAL["motor_temp"])
        s.vision_detected  = True
        s.robot_status     = "PICKING"
        s.packages_per_min = self._rand(*self.NORMAL["packages_per_min"])

    def _apply_conveyor_jam(self, s: SystemState):
        """
        Cascade:
          conveyor slows → stops → vision loses package → robot waits → motor heats
        """
        p = self._fault_progress

        # Conveyor degrades then stops
        s.conveyor_speed  = max(0.0, 100.0 - p * 100.0) + self._noise(3)
        s.conveyor_jammed = p > 0.6

        # Motor current spikes as it fights the jam
        s.motor_current   = 5.0 + p * 6.0 + self._noise(0.3)
        # Motor heats up due to stall current
        s.motor_temp      = 45.0 + p * 40.0 + self._noise(2)

        # Vision loses package once conveyor stops
        s.vision_detected  = p < 0.5
        # Robot waits because nothing arrives
        s.robot_status     = "WAITING" if p > 0.5 else "PICKING"

        s.packages_per_min = max(0.0, 12.0 - p * 12.0)

    def _apply_motor_overheat(self, s: SystemState):
        """
        Motor temperature climbs gradually → conveyor slows as protection kicks in.
        """
        p = self._fault_progress

        s.motor_temp      = 55.0 + p * 50.0 + self._noise(2)   # peaks ~105°C
        s.motor_current   = 5.0 + p * 3.0 + self._noise(0.2)

        # Thermal protection slows the conveyor
        s.conveyor_speed  = 100.0 - p * 30.0 + self._noise(4)
        s.conveyor_jammed = False

        s.vision_detected  = True
        s.robot_status     = "PICKING" if p < 0.7 else "WAITING"
        s.packages_per_min = 12.0 - p * 4.0

    def _apply_vision_failure(self, s: SystemState):
        """
        Vision sensor intermittently fails → robot can't confirm packages → throughput drops.
        """
        p = self._fault_progress

        s.conveyor_speed   = self._rand(*self.NORMAL["conveyor_speed"])
        s.conveyor_jammed  = False
        s.motor_current    = self._rand(*self.NORMAL["motor_current"])
        s.motor_temp       = self._rand(*self.NORMAL["motor_temp"])

        # Flickers then goes dark
        s.vision_detected  = random.random() > p
        s.robot_status     = "WAITING" if not s.vision_detected else "PICKING"
        s.packages_per_min = 12.0 - p * 7.0

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _rand(lo: float, hi: float) -> float:
        return round(random.uniform(lo, hi), 2)

    @staticmethod
    def _noise(scale: float) -> float:
        return round(random.gauss(0, scale), 2)


# ─────────────────────────────────────────────
# QUICK SELF-TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sim = PackagingSimulator()

    print("=" * 55)
    print("  DIGITAL TWIN — SELF TEST")
    print("=" * 55)

    scenarios = [
        (FaultScenario.NONE,           "Normal Operation",  3),
        (FaultScenario.CONVEYOR_JAM,   "Conveyor Jam",      5),
        (FaultScenario.MOTOR_OVERHEAT, "Motor Overheat",    5),
        (FaultScenario.VISION_FAILURE, "Vision Failure",    5),
    ]

    for scenario, label, ticks in scenarios:
        sim.set_scenario(scenario)
        print(f"\n── {label} ──────────────────────────")
        for _ in range(ticks):
            state = sim.tick()
            print(
                f"  [{state.timestamp}] "
                f"Conv:{state.conveyor_speed:6.1f}%  "
                f"Temp:{state.motor_temp:5.1f}°C  "
                f"Vision:{str(state.vision_detected):5}  "
                f"Robot:{state.robot_status:8}  "
                f"Jammed:{state.conveyor_jammed}"
            )
            time.sleep(0.1)

    print("\n✅ Simulator OK — Phase 1 complete\n")
