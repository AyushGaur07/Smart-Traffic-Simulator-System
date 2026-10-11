"""
Unified CLI Entry Point and Interactive Demonstration Runner
for Smart Traffic Management System.

Allows selecting control strategy, configuring parameters, launching SUMO GUI,
and viewing real-time / post-simulation metrics.
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evaluator import run_single_simulation, run_benchmark_suite
from src.rl.train_dqn import train_dqn
from src.evaluation.plot_results import plot_benchmark_comparison
from src.database.db_manager import DatabaseManager


def interactive_menu():
    print("\n" + "=" * 65)
    print("   SMART TRAFFIC MANAGEMENT SYSTEM (StructMinds PBL Phase-II)")
    print("   OS-Based Real-Time Process Scheduling & Deep Q-Learning")
    print("=" * 65)
    print(" 1. Run Fixed-Time Baseline Simulation")
    print(" 2. Run OS-Adaptive Priority Scheduling Simulation")
    print(" 3. Run DQN Reinforcement Learning Simulation")
    print(" 4. Run DQN + OS Scheduling & Safety Arbitration Simulation")
    print(" 5. Run Full 4-Controller Comparative Benchmark")
    print(" 6. Train Deep Q-Network (DQN) Model")
    print(" 7. View Stored Database Records")
    print(" 8. Generate & Update Benchmark Charts")
    print(" 9. Exit")
    print("=" * 65)

    choice = input("Select an option (1-9) [Default: 5]: ").strip() or "5"

    gui_choice = input("Launch with SUMO graphical GUI? (y/N): ").strip().lower() == "y"
    duration = input("Simulation duration in seconds [Default: 300]: ").strip()
    sim_seconds = int(duration) if duration.isdigit() else 300

    if choice == "1":
        run_single_simulation("fixed", sim_seconds=sim_seconds, use_gui=gui_choice)
    elif choice == "2":
        run_single_simulation("adaptive", sim_seconds=sim_seconds, use_gui=gui_choice)
    elif choice == "3":
        run_single_simulation("dqn", sim_seconds=sim_seconds, use_gui=gui_choice)
    elif choice == "4":
        run_single_simulation("dqn_os", sim_seconds=sim_seconds, use_gui=gui_choice)
    elif choice == "5":
        results = run_benchmark_suite(sim_seconds=sim_seconds)
        plot_benchmark_comparison()
    elif choice == "6":
        episodes_input = input("Number of training episodes [Default: 5]: ").strip()
        episodes = int(episodes_input) if episodes_input.isdigit() else 5
        train_dqn(episodes=episodes, sim_seconds=sim_seconds)
    elif choice == "7":
        db = DatabaseManager()
        runs = db.get_all_runs()
        print(f"\n--- Stored Database Records ({db.active_backend.upper()}) ---")
        for r in runs:
            print(f"Controller: {r['controller']:<10} | Runs: {r['runs']:<2} | "
                  f"Avg Arrived: {r['avg_arrived']} | Avg Stopped Veh-s: {r['avg_stopped_veh_sec']}")
    elif choice == "8":
        plot_benchmark_comparison()
    elif choice == "9":
        print("Exiting.")
        return
    else:
        print("Invalid choice.")


def main():
    parser = argparse.ArgumentParser(description="Smart Traffic Management System CLI")
    parser.add_argument("--mode", choices=["interactive", "benchmark", "train", "run", "plot", "db"], default="interactive")
    parser.add_argument("--controller", choices=["fixed", "adaptive", "dqn", "dqn_os"], default="dqn_os")
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--gui", action="store_true")

    args = parser.parse_args()

    if args.mode == "interactive":
        interactive_menu()
    elif args.mode == "benchmark":
        run_benchmark_suite(sim_seconds=args.seconds, seed=args.seed)
        plot_benchmark_comparison()
    elif args.mode == "train":
        train_dqn(episodes=args.episodes, sim_seconds=args.seconds, seed=args.seed)
    elif args.mode == "run":
        run_single_simulation(args.controller, sim_seconds=args.seconds, seed=args.seed, use_gui=args.gui)
    elif args.mode == "plot":
        plot_benchmark_comparison()
    elif args.mode == "db":
        db = DatabaseManager()
        for r in db.get_all_runs():
            print(r)


if __name__ == "__main__":
    main()
