"""
Reinforcement Learning Environment wrapper for SUMO intersection.
Calculates rewards balancing throughput, stopped vehicles, delay, and smoothness.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
import traci

from src.simulation.signal_controller import (
    SignalController,
    PHASE_NS_GREEN,
    PHASE_EW_GREEN,
    PHASE_STATE_STRINGS
)

SUMO_HOME = Path(r"C:\Program Files (x86)\Eclipse\Sumo")
SUMO_BIN = SUMO_HOME / "bin" / "sumo.exe"
SUMO_GUI_BIN = SUMO_HOME / "bin" / "sumo-gui.exe"

APPROACH_EDGES = {"N": "N_C", "S": "S_C", "E": "E_C", "W": "W_C"}


class SumoTrafficEnv:
    """
    OpenAI Gym-style environment wrapper around TraCI.
    Coordinates signal changes via the SignalController to guarantee safety.
    """

    def __init__(
        self,
        net_file: Path,
        route_file: Path,
        sim_seconds: int = 300,
        seed: int = 42,
        use_gui: bool = False,
        min_green: float = 10.0,
        max_green: float = 60.0
    ):
        self.net_file = net_file
        self.route_file = route_file
        self.sim_seconds = sim_seconds
        self.seed = seed
        self.use_gui = use_gui

        self.signal_controller = SignalController(min_green=min_green, max_green=max_green)
        self.tls_id = "C"

        self.sim_time = 0
        self.accumulated_arrived = 0
        self.accumulated_departed = 0
        self.is_running = False

    def reset(self) -> np.ndarray:
        """Starts or restarts the SUMO simulation and returns the initial state."""
        self.close()

        executable = SUMO_GUI_BIN if self.use_gui else SUMO_BIN
        cmd = [
            str(executable),
            "-n", str(self.net_file),
            "-r", str(self.route_file),
            "--seed", str(self.seed),
            "--end", str(self.sim_seconds),
            "--step-length", "1",
            "--no-step-log", "true",
            "--duration-log.disable", "true"
        ]

        if self.use_gui:
            viewsettings_path = self.net_file.parent / "viewsettings.xml"
            if viewsettings_path.exists():
                cmd.extend(["--gui-settings-file", str(viewsettings_path)])
            cmd.extend(["--start", "true", "--delay", "120"])

        traci.start(cmd)
        self.is_running = True
        self.sim_time = 0
        self.accumulated_arrived = 0
        self.accumulated_departed = 0
        self.signal_controller.reset(initial_phase=PHASE_NS_GREEN)

        # Set initial signal state in SUMO
        traci.trafficlight.setRedYellowGreenState(self.tls_id, PHASE_STATE_STRINGS[PHASE_NS_GREEN])

        return self.get_state()

    def get_state(self) -> np.ndarray:
        """
        State representation:
        [Queue_N, Queue_S, Queue_E, Queue_W, Wait_NS/100, Wait_EW/100, Active_Phase_Flag]
        """
        queues, waiting_times = self.get_approach_metrics()

        wait_ns = (waiting_times["N"] + waiting_times["S"]) / 100.0
        wait_ew = (waiting_times["E"] + waiting_times["W"]) / 100.0
        current_phase_flag = 1.0 if self.signal_controller.current_phase == PHASE_NS_GREEN else 0.0

        state = np.array([
            float(queues["N"]),
            float(queues["S"]),
            float(queues["E"]),
            float(queues["W"]),
            wait_ns,
            wait_ew,
            current_phase_flag
        ], dtype=np.float32)

        return state

    def get_approach_metrics(self) -> Tuple[Dict[str, int], Dict[str, float]]:
        """Returns queues (halted vehicles) and waiting times by direction."""
        queues = {}
        waiting = {}

        for direction, edge_id in APPROACH_EDGES.items():
            halted_on_edge = 0
            waiting_time_on_edge = 0.0
            try:
                num_lanes = traci.edge.getLaneNumber(edge_id)
                for lane_idx in range(num_lanes):
                    lane_id = f"{edge_id}_{lane_idx}"
                    halted_on_edge += traci.lane.getLastStepHaltingNumber(lane_id)
                for vid in traci.edge.getLastStepVehicleIDs(edge_id):
                    waiting_time_on_edge += traci.vehicle.getWaitingTime(vid)
            except traci.TraCIException:
                pass
            queues[direction] = int(halted_on_edge)
            waiting[direction] = float(waiting_time_on_edge)

        return queues, waiting

    def step(self, desired_green_phase: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Executes one 1-second simulation step.
        Passes action through signal safety controller.
        Returns: (next_state, reward, done, info)
        """
        # Request phase transition through safety layer
        applied_phase, status = self.signal_controller.request_phase(desired_green_phase)

        # Advance internal controller clock
        current_phase = self.signal_controller.step()

        # Set physical signal state in SUMO
        traci.trafficlight.setRedYellowGreenState(self.tls_id, PHASE_STATE_STRINGS[current_phase])

        # Step SUMO forward
        traci.simulationStep()
        self.sim_time += 1

        arrived_this_step = traci.simulation.getArrivedNumber()
        departed_this_step = traci.simulation.getDepartedNumber()
        self.accumulated_arrived += arrived_this_step
        self.accumulated_departed += departed_this_step

        queues, waiting = self.get_approach_metrics()
        total_halted = sum(queues.values())
        total_waiting = sum(waiting.values())

        # Speed and emissions
        vehicle_ids = traci.vehicle.getIDList()
        speeds = [traci.vehicle.getSpeed(v) for v in vehicle_ids]
        mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
        co2_step = sum(max(0.0, traci.vehicle.getCO2Emission(v)) / 1000.0 for v in vehicle_ids)

        # Reward function:
        # + bonus per arrived vehicle
        # - penalty for stopped vehicles (queue pressure)
        # - penalty for excessive waiting time
        # - small penalty if changing phase (transition overhead / yellow clearance)
        is_yellow = self.signal_controller.is_in_transition()
        transition_penalty = 1.0 if is_yellow else 0.0

        reward = (
            (arrived_this_step * 10.0)
            - (total_halted * 0.5)
            - (total_waiting * 0.05)
            - transition_penalty
        )

        next_state = self.get_state()
        done = self.sim_time >= self.sim_seconds

        info = {
            "sim_time": self.sim_time,
            "active_vehicles": len(vehicle_ids),
            "halted_vehicles": total_halted,
            "mean_speed_mps": round(mean_speed, 4),
            "queue_n": queues["N"],
            "queue_s": queues["S"],
            "queue_e": queues["E"],
            "queue_w": queues["W"],
            "queues": queues,
            "waiting": waiting,
            "co2_grams_this_step": round(co2_step, 6),
            "arrived_this_step": arrived_this_step,
            "total_arrived": self.accumulated_arrived,
            "total_departed": self.accumulated_departed,
            "phase": current_phase,
            "phase_status": status
        }

        return next_state, reward, done, info

    def close(self):
        """Closes SUMO TraCI connection safely."""
        if self.is_running:
            try:
                traci.close()
            except Exception:
                pass
            self.is_running = False
