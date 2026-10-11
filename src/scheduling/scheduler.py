"""
OS-inspired Real-Time Process Scheduling for Traffic Signals.

Maps traffic intersection management to Operating System concepts:
- Approaches / Directions == Ready Processes / Threads
- Traffic Light Green Time == CPU Execution Quantum
- Queue Length == Process Priority / Workload Size
- Cumulative Waiting Time == Starvation Prevention & Process Aging
- Preemption & Context Switch == Signal Phase Transitions with Yellow Overhead
"""

from typing import Dict, Any, Tuple
from src.simulation.signal_controller import PHASE_NS_GREEN, PHASE_EW_GREEN


class TrafficProcess:
    """Represents a directional traffic flow as an OS Process."""

    def __init__(self, name: str, phase_id: int):
        self.name = name
        self.phase_id = phase_id
        self.queue_length = 0
        self.total_waiting_time = 0.0
        self.time_starved = 0.0  # seconds spent waiting without receiving CPU/Green light
        self.serving_time = 0.0

    def reset(self):
        self.queue_length = 0
        self.total_waiting_time = 0.0
        self.time_starved = 0.0
        self.serving_time = 0.0


class TrafficScheduler:
    """
    OS-inspired Real-Time Traffic Scheduler.

    Implements:
    - Dynamic Priority Scheduling with Aging:
      Priority = (Queue Weight * Queue Length) + (Aging Factor * Time Starved)
    - Anti-Starvation / Bounded Waiting: Guarantees every approach receives green light within Max Starvation window.
    - Context Switch Cost: Yellow transition overhead accounted for to prevent thrashing.
    """

    def __init__(
        self,
        queue_weight: float = 1.0,
        aging_factor: float = 0.25,
        max_starvation_time: float = 60.0
    ):
        self.queue_weight = queue_weight
        self.aging_factor = aging_factor
        self.max_starvation_time = max_starvation_time

        self.processes = {
            "NS": TrafficProcess("NS", PHASE_NS_GREEN),
            "EW": TrafficProcess("EW", PHASE_EW_GREEN)
        }
        self.active_phase = PHASE_NS_GREEN

    def update_metrics(self, queues: Dict[str, int], waiting_times: Dict[str, float], active_green_phase: int):
        """
        Updates workload and aging timers for each directional process.
        """
        # North + South grouped into NS process
        self.processes["NS"].queue_length = queues.get("N", 0) + queues.get("S", 0)
        self.processes["NS"].total_waiting_time = waiting_times.get("N", 0.0) + waiting_times.get("S", 0.0)

        # East + West grouped into EW process
        self.processes["EW"].queue_length = queues.get("E", 0) + queues.get("W", 0)
        self.processes["EW"].total_waiting_time = waiting_times.get("E", 0.0) + waiting_times.get("W", 0.0)

        self.active_phase = active_green_phase

        # Update starvation and serving counters
        if active_green_phase == PHASE_NS_GREEN:
            self.processes["NS"].serving_time += 1.0
            self.processes["NS"].time_starved = 0.0
            self.processes["EW"].time_starved += 1.0
            self.processes["EW"].serving_time = 0.0
        elif active_green_phase == PHASE_EW_GREEN:
            self.processes["EW"].serving_time += 1.0
            self.processes["EW"].time_starved = 0.0
            self.processes["NS"].time_starved += 1.0
            self.processes["NS"].serving_time = 0.0

    def calculate_priority(self, proc_key: str) -> float:
        """
        Calculates effective priority using OS Priority Scheduling with Aging:
        Effective Priority = (queue_weight * queue_length) + (aging_factor * time_starved)
        """
        proc = self.processes[proc_key]
        priority = (self.queue_weight * proc.queue_length) + (self.aging_factor * proc.time_starved)
        return round(priority, 3)

    def select_next_phase(self) -> Tuple[int, str]:
        """
        Selects the next green phase based on OS scheduling principles:
        1. Starvation prevention override (Hard real-time deadline).
        2. Priority comparison (Queue length + Aging).
        """
        ns_proc = self.processes["NS"]
        ew_proc = self.processes["EW"]

        # Check anti-starvation condition (guaranteed turnaround time)
        if ns_proc.time_starved >= self.max_starvation_time and ns_proc.queue_length > 0:
            return PHASE_NS_GREEN, "aging_starvation_override_NS"
        if ew_proc.time_starved >= self.max_starvation_time and ew_proc.queue_length > 0:
            return PHASE_EW_GREEN, "aging_starvation_override_EW"

        ns_priority = self.calculate_priority("NS")
        ew_priority = self.calculate_priority("EW")

        if ns_priority >= ew_priority:
            return PHASE_NS_GREEN, f"priority_scheduled_NS (NS:{ns_priority} >= EW:{ew_priority})"
        else:
            return PHASE_EW_GREEN, f"priority_scheduled_EW (EW:{ew_priority} > NS:{ns_priority})"

    def arbitrate(self, ai_proposed_phase: int) -> Tuple[int, str]:
        """
        Valid action arbitration between RL Agent and OS Scheduler.
        Prevents starvation if the RL agent develops a biased policy.
        """
        ns_proc = self.processes["NS"]
        ew_proc = self.processes["EW"]

        # If a direction is starved beyond max threshold, OS Scheduler vetoes RL proposal
        if ai_proposed_phase == PHASE_EW_GREEN and ns_proc.time_starved >= self.max_starvation_time and ns_proc.queue_length > 0:
            return PHASE_NS_GREEN, "os_arbitration_veto_NS_starved"

        if ai_proposed_phase == PHASE_NS_GREEN and ew_proc.time_starved >= self.max_starvation_time and ew_proc.queue_length > 0:
            return PHASE_EW_GREEN, "os_arbitration_veto_EW_starved"

        # Otherwise accept AI recommendation
        return ai_proposed_phase, "ai_action_accepted"
