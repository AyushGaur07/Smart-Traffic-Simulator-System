"""
Unit and integration tests for the Smart Traffic Management System.
Tests:
1. Network file existence and structure.
2. SignalController safety invariants (min/max green, yellow clearance).
3. OS Scheduler priority calculation, aging, and anti-starvation.
4. Database schema and transactional insertion (SQLite fallback).
5. DQN agent forward pass and replay buffer mechanics.
"""

import unittest
from pathlib import Path
import numpy as np

from src.simulation.signal_controller import (
    SignalController,
    PHASE_NS_GREEN,
    PHASE_NS_YELLOW,
    PHASE_EW_GREEN,
    PHASE_EW_YELLOW
)
from src.scheduling.scheduler import TrafficScheduler
from src.rl.dqn_agent import DQNAgent, ReplayBuffer
from src.database.db_manager import DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestNetworkFiles(unittest.TestCase):
    """Verifies that all required SUMO network and definition files exist."""

    def test_network_files_exist(self):
        net_file = PROJECT_ROOT / "TrafficControl" / "network.net.xml"
        routes_file = PROJECT_ROOT / "TrafficControl" / "routes.rou.xml"
        nodes_file = PROJECT_ROOT / "TrafficControl" / "nodes.nod.xml"
        edges_file = PROJECT_ROOT / "TrafficControl" / "edges.edg.xml"

        self.assertTrue(net_file.exists(), "network.net.xml missing")
        self.assertTrue(routes_file.exists(), "routes.rou.xml missing")
        self.assertTrue(nodes_file.exists(), "nodes.nod.xml missing")
        self.assertTrue(edges_file.exists(), "edges.edg.xml missing")


class TestSignalController(unittest.TestCase):
    """Verifies safety rules, transitions, and intervals."""

    def setUp(self):
        self.sc = SignalController(min_green=10.0, max_green=30.0, yellow_time=3.0)
        self.sc.reset(initial_phase=PHASE_NS_GREEN)

    def test_min_green_enforcement(self):
        # At t=0, requesting switch to EW should be rejected due to min green
        phase, status = self.sc.request_phase(PHASE_EW_GREEN)
        self.assertEqual(status, "min_green_not_met")
        self.assertEqual(self.sc.current_phase, PHASE_NS_GREEN)

    def test_safe_transition_to_yellow(self):
        # Advance time by 10 seconds to satisfy min green
        for _ in range(10):
            self.sc.step()

        phase, status = self.sc.request_phase(PHASE_EW_GREEN)
        self.assertEqual(status, "initiating_yellow_transition")
        self.assertEqual(self.sc.current_phase, PHASE_NS_YELLOW)
        self.assertTrue(self.sc.is_in_transition())

        # Advance through 3 seconds of yellow clearance
        self.sc.step()  # t=1 of yellow
        self.sc.step()  # t=2 of yellow
        current_phase = self.sc.step()  # t=3 of yellow -> switches to EW green

        self.assertEqual(current_phase, PHASE_EW_GREEN)
        self.assertFalse(self.sc.is_in_transition())

    def test_max_green_enforcement(self):
        # Advance to max green limit (30 seconds)
        for _ in range(30):
            self.sc.step()

        # Requesting same green after max green should force a yellow switch
        phase, status = self.sc.request_phase(PHASE_NS_GREEN)
        self.assertEqual(status, "forced_max_green_switch")
        self.assertEqual(self.sc.current_phase, PHASE_NS_YELLOW)


class TestTrafficScheduler(unittest.TestCase):
    """Tests OS-inspired priority scheduling, aging, and anti-starvation arbitration."""

    def setUp(self):
        self.scheduler = TrafficScheduler(queue_weight=1.0, aging_factor=0.5, max_starvation_time=20.0)

    def test_priority_calculation_with_aging(self):
        queues = {"N": 5, "S": 5, "E": 2, "W": 2}
        waiting = {"N": 10.0, "S": 10.0, "E": 5.0, "W": 5.0}

        # NS is currently serving
        self.scheduler.update_metrics(queues, waiting, active_green_phase=PHASE_NS_GREEN)

        # NS priority: 1.0 * (5+5) + 0.5 * 0 = 10.0
        # EW priority: 1.0 * (2+2) + 0.5 * 1 = 4.5
        self.assertEqual(self.scheduler.calculate_priority("NS"), 10.0)
        self.assertEqual(self.scheduler.calculate_priority("EW"), 4.5)

    def test_anti_starvation_override(self):
        queues = {"N": 1, "S": 0, "E": 20, "W": 20}
        waiting = {"N": 5.0, "S": 0.0, "E": 50.0, "W": 50.0}

        # Simulate NS waiting for 25 seconds while EW has massive traffic
        self.scheduler.processes["NS"].time_starved = 25.0
        self.scheduler.processes["NS"].queue_length = 1
        self.scheduler.processes["EW"].queue_length = 40

        next_phase, reason = self.scheduler.select_next_phase()
        self.assertEqual(next_phase, PHASE_NS_GREEN)
        self.assertIn("aging_starvation_override_NS", reason)

    def test_ai_arbitration_veto(self):
        # If AI proposes EW green but NS has been starved past max starvation limit
        self.scheduler.processes["NS"].time_starved = 25.0
        self.scheduler.processes["NS"].queue_length = 2

        action, reason = self.scheduler.arbitrate(ai_proposed_phase=PHASE_EW_GREEN)
        self.assertEqual(action, PHASE_NS_GREEN)
        self.assertEqual(reason, "os_arbitration_veto_NS_starved")


class TestDatabaseManager(unittest.TestCase):
    """Tests database initialization and record insertion."""

    def test_schema_and_save_run(self):
        db = DatabaseManager()
        summary = {
            "run_id": "test_run_001",
            "controller": "unit_test",
            "seed": 999,
            "simulation_seconds": 10,
            "departed_vehicles": 5,
            "arrived_vehicles": 4,
            "vehicles_remaining": 1,
            "max_queue_vehicles": 2,
            "mean_queue_vehicles": 1.5,
            "stopped_vehicle_seconds": 15,
            "mean_waiting_seconds_per_vehicle": 3.0,
            "total_co2_grams": 12.5,
            "throughput_vehicles_per_hour": 1440.0
        }
        steps = [{
            "run_id": "test_run_001",
            "sim_time": 1,
            "active_vehicles": 3,
            "halted_vehicles": 1,
            "mean_speed_mps": 11.2,
            "queue_n": 1,
            "queue_s": 0,
            "queue_e": 0,
            "queue_w": 0,
            "co2_grams_this_step": 1.25
        }]
        # Should execute cleanly without error
        db.save_run(summary, steps)
        runs = db.get_all_runs()
        self.assertTrue(any(r["controller"] == "unit_test" for r in runs))


class TestDQNAgent(unittest.TestCase):
    """Tests DQN neural network output dimensions and experience replay."""

    def test_dqn_action_selection(self):
        agent = DQNAgent(state_dim=7, action_dim=2)
        state = np.array([5.0, 4.0, 2.0, 1.0, 0.5, 0.2, 1.0], dtype=np.float32)
        action = agent.select_action(state, evaluate=True)
        self.assertIn(action, [PHASE_NS_GREEN, PHASE_EW_GREEN])

    def test_replay_buffer(self):
        buf = ReplayBuffer(capacity=100)
        s = np.zeros(7, dtype=np.float32)
        buf.push(s, PHASE_NS_GREEN, 1.0, s, False)
        self.assertEqual(len(buf), 1)


if __name__ == "__main__":
    unittest.main()
