"""
Repeatable evaluation runner for:
1. fixed - Baseline Fixed-Time Control
2. adaptive - Non-AI OS-inspired Priority Scheduling with Aging
3. dqn - Pure Deep Q-Network Controller
4. dqn_os - DQN with OS-inspired Safety & Anti-Starvation Arbitration Layer

Ensures identical network, route demand, duration, and random seeds across all tests.
"""

from pathlib import Path
import argparse
import uuid
import statistics
import traci

from src.simulation.sumo_env import SumoTrafficEnv
from src.simulation.signal_controller import PHASE_NS_GREEN, PHASE_EW_GREEN
from src.scheduling.scheduler import TrafficScheduler
from src.rl.dqn_agent import DQNAgent
from src.database.db_manager import DatabaseManager, RESULTS_DIR

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NET_FILE = PROJECT_ROOT / "TrafficControl" / "network.net.xml"
ROUTES_FILE = PROJECT_ROOT / "TrafficControl" / "routes.rou.xml"
MODEL_PATH = PROJECT_ROOT / "checkpoints" / "dqn_traffic_model.pth"


def run_single_simulation(
    controller_type: str,
    sim_seconds: int = 300,
    seed: int = 42,
    use_gui: bool = False,
    save_to_db: bool = True
):
    """
    Runs a single simulation under specified control strategy and collects standard metrics.
    """
    env = SumoTrafficEnv(
        net_file=NET_FILE,
        route_file=ROUTES_FILE,
        sim_seconds=sim_seconds,
        seed=seed,
        use_gui=use_gui,
        min_green=10.0,
        max_green=60.0
    )

    scheduler = TrafficScheduler(queue_weight=1.0, aging_factor=0.3, max_starvation_time=45.0)
    agent = None

    if "dqn" in controller_type:
        agent = DQNAgent()
        if MODEL_PATH.exists():
            agent.load(MODEL_PATH)
        else:
            print(f"[Warning] Trained model not found at {MODEL_PATH}. Using untrained policy for evaluation.")

    state = env.reset()
    run_id = f"{controller_type}_{seed}_{uuid.uuid4().hex[:8]}"

    steps_data = []
    decisions_data = []
    halted_samples = []
    total_stopped_veh_seconds = 0
    total_co2_grams = 0.0

    print(f"\n>>> Running [{controller_type.upper()}] control for {sim_seconds}s (seed {seed})...")

    # Fixed time parameters: alternating 42s green, 3s yellow
    fixed_phase = PHASE_NS_GREEN
    fixed_timer = 0
    fixed_green_duration = 42

    for t in range(sim_seconds):
        queues, waiting = env.get_approach_metrics()
        current_green = env.signal_controller.current_phase
        if current_green not in [PHASE_NS_GREEN, PHASE_EW_GREEN]:
            # If in yellow, consider target or previous green
            current_green = env.signal_controller.transition_target_phase

        scheduler.update_metrics(queues, waiting, current_green)

        # Decide green phase based on controller type
        desired_phase = PHASE_NS_GREEN
        decision_reason = "default"

        if controller_type == "fixed":
            fixed_timer += 1
            if fixed_timer >= fixed_green_duration:
                fixed_phase = PHASE_EW_GREEN if fixed_phase == PHASE_NS_GREEN else PHASE_NS_GREEN
                fixed_timer = 0
            desired_phase = fixed_phase
            decision_reason = f"fixed_timer_phase_{fixed_phase}"

        elif controller_type == "adaptive":
            desired_phase, decision_reason = scheduler.select_next_phase()

        elif controller_type == "dqn":
            desired_phase = agent.select_action(state, evaluate=True)
            decision_reason = "dqn_greedy_policy"

        elif controller_type == "dqn_os":
            dqn_action = agent.select_action(state, evaluate=True)
            desired_phase, decision_reason = scheduler.arbitrate(dqn_action)

        # Step the environment
        next_state, reward, done, info = env.step(desired_phase)
        state = next_state

        halted = info["halted_vehicles"]
        halted_samples.append(halted)
        total_stopped_veh_seconds += halted
        total_co2_grams += info["co2_grams_this_step"]

        steps_data.append({
            "run_id": run_id,
            "sim_time": t + 1,
            "active_vehicles": info["active_vehicles"],
            "halted_vehicles": halted,
            "mean_speed_mps": info["mean_speed_mps"],
            "queue_n": info["queue_n"],
            "queue_s": info["queue_s"],
            "queue_e": info["queue_e"],
            "queue_w": info["queue_w"],
            "co2_grams_this_step": info["co2_grams_this_step"]
        })

        if t % 5 == 0:  # record periodic scheduler logs
            decisions_data.append({
                "run_id": run_id,
                "sim_time": t + 1,
                "chosen_phase": desired_phase,
                "reason": decision_reason,
                "ns_waiting": waiting["N"] + waiting["S"],
                "ew_waiting": waiting["E"] + waiting["W"],
                "ns_queue": queues["N"] + queues["S"],
                "ew_queue": queues["E"] + queues["W"]
            })

        if (t + 1) % 60 == 0 or (t + 1) == sim_seconds:
            progress_pct = int(((t + 1) / sim_seconds) * 100)
            bar_len = 15
            filled = int(bar_len * (t + 1) // sim_seconds)
            progress_bar = "=" * filled + "-" * (bar_len - filled)
            
            # Format decision reason for human readability
            clean_reason = decision_reason
            if "priority_scheduled" in decision_reason:
                clean_reason = "OS Priority Shift"
            elif "starvation_override" in decision_reason:
                clean_reason = "[!] Anti-Starvation Preemption"
            elif "ai_action_accepted" in decision_reason:
                clean_reason = "AI Green Decision"
            elif "fixed_timer" in decision_reason:
                clean_reason = "Fixed Clock Switch"
            
            print(f"[{progress_bar}] {progress_pct:3d}% | Time: {t+1:3d}s/{sim_seconds}s | "
                  f"Active Cars: {info['active_vehicles']:2d} | Waiting at Red: {halted:2d} | "
                  f"Cleared: {info['total_arrived']:2d} | Status: {clean_reason}")

        if done:
            break

    # Calculate end-of-run accumulated waiting time across active vehicles
    waiting_active_at_end = 0.0
    for vid in traci.vehicle.getIDList():
        try:
            waiting_active_at_end += traci.vehicle.getAccumulatedWaitingTime(vid)
        except Exception:
            pass

    arrived = env.accumulated_arrived
    departed = env.accumulated_departed
    remaining = len(traci.vehicle.getIDList())

    env.close()

    summary = {
        "run_id": run_id,
        "controller": controller_type,
        "seed": seed,
        "simulation_seconds": sim_seconds,
        "departed_vehicles": departed,
        "arrived_vehicles": arrived,
        "vehicles_remaining": remaining,
        "max_queue_vehicles": int(max(halted_samples) if halted_samples else 0),
        "mean_queue_vehicles": round(statistics.mean(halted_samples) if halted_samples else 0.0, 2),
        "stopped_vehicle_seconds": int(total_stopped_veh_seconds),
        "mean_waiting_seconds_per_vehicle": round(waiting_active_at_end / departed, 2) if departed > 0 else 0.0,
        "total_co2_grams": round(total_co2_grams, 1),
        "throughput_vehicles_per_hour": round(arrived / (sim_seconds / 3600.0), 1)
    }

    if save_to_db:
        db = DatabaseManager()
        db.save_run(summary, steps_data, decisions_data)

    print("\n" + "=" * 60)
    print(f"               SIMULATION RESULT: {controller_type.upper()}")
    print("=" * 60)
    print(f"  * Vehicles Cleared (Arrived)   : {summary['arrived_vehicles']} out of {summary['departed_vehicles']} cars")
    print(f"  * Cars Still on Road           : {summary['vehicles_remaining']} cars")
    print(f"  * Total Waiting Delay          : {summary['stopped_vehicle_seconds']} vehicle-seconds")
    print(f"  * Worst Traffic Jam (Peak)     : {summary['max_queue_vehicles']} cars halted")
    print(f"  * Average Queue Length         : {summary['mean_queue_vehicles']} cars")
    print(f"  * Hourly Capacity (Throughput) : {summary['throughput_vehicles_per_hour']} vehicles / hour")
    print(f"  * Total Carbon Emissions (CO2) : {summary['total_co2_grams']} grams (~{round(summary['total_co2_grams']/1000, 2)} kg)")
    print("=" * 60 + "\n")

    return summary


def run_benchmark_suite(sim_seconds: int = 300, seed: int = 42):
    """
    Runs all 4 controllers under identical conditions and outputs an ASCII comparison table.
    """
    controllers = ["fixed", "adaptive", "dqn", "dqn_os"]
    results = []

    print("\n" + "=" * 70)
    print("STARTING COMPREHENSIVE 4-CONTROLLER BENCHMARK EVALUATION")
    print("=" * 70)

    for c in controllers:
        res = run_single_simulation(controller_type=c, sim_seconds=sim_seconds, seed=seed)
        results.append(res)

    print("\n" + "=" * 90)
    print("BENCHMARK COMPARISON TABLE")
    print("=" * 90)
    header = f"{'Controller':<12} | {'Arrived':<8} | {'Departed':<9} | {'Max Queue':<10} | {'Mean Queue':<11} | {'Stopped Veh-s':<14} | {'CO2 (g)':<9} | {'Throughput (veh/h)':<18}"
    print(header)
    print("-" * len(header))
    for r in results:
        row = f"{r['controller']:<12} | {r['arrived_vehicles']:<8} | {r['departed_vehicles']:<9} | {r['max_queue_vehicles']:<10} | {r['mean_queue_vehicles']:<11} | {r['stopped_vehicle_seconds']:<14} | {r['total_co2_grams']:<9} | {r['throughput_vehicles_per_hour']:<18}"
        print(row)
    print("=" * 90)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run traffic simulation benchmark.")
    parser.add_argument("--controller", choices=["fixed", "adaptive", "dqn", "dqn_os", "all"], default="all")
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if args.controller == "all":
        run_benchmark_suite(sim_seconds=args.seconds, seed=args.seed)
    else:
        run_single_simulation(controller_type=args.controller, sim_seconds=args.seconds, seed=args.seed, use_gui=args.gui)
