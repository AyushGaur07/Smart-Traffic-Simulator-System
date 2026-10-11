"""
Defines safe signal phases, transitions, and legal movement enforcement for the 4-way intersection.
Ensures green lights are never granted to conflicting movements.
"""

from typing import Tuple, Dict, List

# Phase mappings for intersection C:
# 16 signal links:
# S_C: 0 (turn left), 1 (straight), 2 (turn right), 3 (u-turn)
# E_C: 4 (turn left), 5 (straight), 6 (turn right), 7 (u-turn)
# N_C: 8 (turn left), 9 (straight), 10 (turn right), 11 (u-turn)
# W_C: 12 (turn left), 13 (straight), 14 (turn right), 15 (u-turn)

# Legal phases:
# Phase 0: NS Green (Links 0,1,2,3 and 8,9,10,11 green: "GGggrrrrGGggrrrr")
# Phase 1: NS Yellow ("yyyyrrrryyyyrrrr")
# Phase 2: EW Green (Links 4,5,6,7 and 12,13,14,15 green: "rrrrGGggrrrrGGgg")
# Phase 3: EW Yellow ("rrrryyyyrrrryyyy")

PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN = 2
PHASE_EW_YELLOW = 3

GREEN_PHASES = [PHASE_NS_GREEN, PHASE_EW_GREEN]
YELLOW_PHASES = [PHASE_NS_YELLOW, PHASE_EW_YELLOW]

PHASE_STATE_STRINGS: Dict[int, str] = {
    PHASE_NS_GREEN: "GGggrrrrGGggrrrr",
    PHASE_NS_YELLOW: "yyyyrrrryyyyrrrr",
    PHASE_EW_GREEN: "rrrrGGggrrrrGGgg",
    PHASE_EW_YELLOW: "rrrryyyyrrrryyyy",
}

DEFAULT_MIN_GREEN = 10.0  # seconds
DEFAULT_MAX_GREEN = 60.0  # seconds
YELLOW_DURATION = 3.0     # seconds


class SignalController:
    """
    Guarantees safe signal phase transitions.
    Enforces minimum green time, maximum green time, and yellow clearance.
    Prevents any controller (adaptive or RL) from bypassing safety intervals.
    """

    def __init__(self, min_green: float = DEFAULT_MIN_GREEN, max_green: float = DEFAULT_MAX_GREEN, yellow_time: float = YELLOW_DURATION):
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_time = yellow_time

        self.current_phase = PHASE_NS_GREEN
        self.time_in_phase = 0.0
        self.transition_target_phase: int = -1

    def reset(self, initial_phase: int = PHASE_NS_GREEN):
        """Resets the signal state."""
        self.current_phase = initial_phase
        self.time_in_phase = 0.0
        self.transition_target_phase = -1

    def step(self) -> int:
        """Advances internal timer by 1 second and handles automatic yellow completion."""
        self.time_in_phase += 1.0

        # If currently in yellow clearance, check if yellow interval completed
        if self.current_phase in YELLOW_PHASES:
            if self.time_in_phase >= self.yellow_time:
                # Transition to the targeted green phase
                self.current_phase = self.transition_target_phase
                self.time_in_phase = 0.0
                self.transition_target_phase = -1

        return self.current_phase

    def request_phase(self, desired_green_phase: int) -> Tuple[int, str]:
        """
        Processes a request to switch to or maintain a green phase.
        Returns: (phase_to_set_in_sumo, status_reason)
        """
        if desired_green_phase not in GREEN_PHASES:
            raise ValueError(f"Invalid green phase requested: {desired_green_phase}. Must be in {GREEN_PHASES}")

        # If currently in yellow transition, ignore requests until yellow finishes
        if self.current_phase in YELLOW_PHASES:
            return self.current_phase, "transitioning_yellow"

        # If requesting the same green phase currently active
        if desired_green_phase == self.current_phase:
            if self.time_in_phase >= self.max_green:
                # Force switch to opposite direction due to max green limit
                other_green = PHASE_EW_GREEN if self.current_phase == PHASE_NS_GREEN else PHASE_NS_GREEN
                yellow_phase = PHASE_NS_YELLOW if self.current_phase == PHASE_NS_GREEN else PHASE_EW_YELLOW
                self.current_phase = yellow_phase
                self.time_in_phase = 0.0
                self.transition_target_phase = other_green
                return self.current_phase, "forced_max_green_switch"
            return self.current_phase, "hold_current_green"

        # Requesting a different green phase
        if self.time_in_phase < self.min_green:
            # Cannot switch yet: minimum green time must be respected
            return self.current_phase, "min_green_not_met"

        # Min green satisfied: trigger yellow transition
        yellow_phase = PHASE_NS_YELLOW if self.current_phase == PHASE_NS_GREEN else PHASE_EW_YELLOW
        self.current_phase = yellow_phase
        self.time_in_phase = 0.0
        self.transition_target_phase = desired_green_phase
        return self.current_phase, "initiating_yellow_transition"

    def is_in_transition(self) -> bool:
        """Returns True if the controller is currently serving yellow clearance."""
        return self.current_phase in YELLOW_PHASES
