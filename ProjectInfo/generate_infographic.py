"""
Script to generate a high-resolution, presentation-ready PNG image
of the Architecture, OS/DBMS Mapping, and Project Structure for ProjectInfo.
"""

from pathlib import Path
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "ProjectInfo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_FILE = OUTPUT_DIR / "SmartTraffic_Architecture_and_Modules.png"


def generate_infographic():
    fig = plt.figure(figsize=(16, 20), facecolor="#f8fafc")
    ax = fig.add_subplot(111)
    ax.axis('off')

    # Header Box
    ax.text(0.5, 0.97, "Smart Traffic Management System",
            fontsize=24, fontweight='bold', ha='center', va='top', color='#0f172a')
    ax.text(0.5, 0.945, "7-Level Architecture, OS & DBMS Module Mapping, and Viva Guide\nTeam StructMinds (Ayush Gaur, Vedansh Manwal, Anmol Pujari)",
            fontsize=12, ha='center', va='top', color='#475569')

    # Draw divider
    ax.plot([0.05, 0.95], [0.92, 0.92], color="#0f766e", lw=3)

    # 1. 7-Level Pipeline Section
    ax.text(0.05, 0.895, "1. 7-LEVEL PIPELINE IMPLEMENTATION (100% MATCH)",
            fontsize=14, fontweight='bold', color="#0f766e")

    levels = [
        ("Level 1", "Simulation Environment", "TrafficControl/network.net.xml & routes.rou.xml", "SUMO 4-way left-hand intersection network & routes."),
        ("Level 2", "Main Controller", "src/simulation/sumo_env.py & main.py / gui_app.py", "TraCI interface collecting vehicle speeds, queues, delay."),
        ("Level 3A", "AI Core Module (DQN)", "src/rl/dqn_agent.py & src/rl/train_dqn.py", "Deep Q-Network observing states and picking green phases."),
        ("Level 3B", "OS Layer (Scheduler)", "src/scheduling/scheduler.py", "Dynamic Priority scheduling with Aging & starvation counters."),
        ("Level 4", "Decision & Safety Layer", "src/simulation/signal_controller.py & scheduler.py", "Enforces 10s min green, 60s max green, 3s yellow clearance & OS veto."),
        ("Level 5", "Action Implementation", "src/simulation/sumo_env.py", "Applies safe phase commands to SUMO traffic light via TraCI."),
        ("Level 6", "Data Persistence (DBMS)", "src/database/db_manager.py", "Stores runs, step metrics, and decisions in MySQL / SQLite."),
        ("Level 7", "Analysis & Metrics", "src/evaluation/evaluator.py & plot_results.py", "Aggregates delay, throughput, CO2 & plots comparison charts.")
    ]

    y_pos = 0.865
    for lvl, name, file_path, desc in levels:
        # Box background
        bbox_props = dict(boxstyle="round,pad=0.5", fc="#ffffff", ec="#cbd5e1", lw=1.2)
        ax.text(0.06, y_pos, f"{lvl}: {name}", fontsize=11, fontweight='bold', color="#1e293b", bbox=bbox_props)
        ax.text(0.35, y_pos, f"File: {file_path}", fontsize=10, fontweight='bold', color="#0f766e")
        ax.text(0.35, y_pos - 0.02, f"Role: {desc}", fontsize=9.5, color="#64748b")
        y_pos -= 0.045

    # 2. OS Concepts Section
    ax.plot([0.05, 0.95], [0.495, 0.495], color="#cbd5e1", lw=1.5)
    ax.text(0.05, 0.47, "2. OPERATING SYSTEMS (OS) MODULE MAPPING",
            fontsize=14, fontweight='bold', color="#0f766e")
    ax.text(0.05, 0.448, "Primary Code File: src/scheduling/scheduler.py",
            fontsize=11, fontweight='bold', color="#334155")

    os_points = [
        ("• Ready Processes / Threads", "Each directional approach (NS & EW) is modeled as a TrafficProcess tracking workload and queue."),
        ("• CPU Time Slice / Quantum", "Traffic light green time is treated as CPU execution time, bounded by 10s min green and 60s max green."),
        ("• Dynamic Priority Scheduling", "Priority = (Queue Length * w_q) + (Starvation Time * w_a). High queues gain immediate priority."),
        ("• Process Aging", "Time spent waiting increments time_starved every second, boosting priority to guarantee bounded waiting."),
        ("• Context Switch Overhead", "Mandatory 3-second yellow clearance interval acts as a context-switch penalty preventing thrashing."),
        ("• OS Kernel Arbiter / Veto", "arbitrate() checks AI actions: if an approach is starved > 45s, the OS scheduler vetoes the AI to prevent starvation.")
    ]

    y_pos_os = 0.42
    for title, desc in os_points:
        ax.text(0.06, y_pos_os, title, fontsize=10.5, fontweight='bold', color="#1e293b")
        ax.text(0.35, y_pos_os, desc, fontsize=10, color="#475569")
        y_pos_os -= 0.026

    # 3. DBMS Concepts Section
    ax.plot([0.05, 0.95], [0.25, 0.25], color="#cbd5e1", lw=1.5)
    ax.text(0.05, 0.225, "3. DATABASE MANAGEMENT (DBMS) MODULE MAPPING",
            fontsize=14, fontweight='bold', color="#0f766e")
    ax.text(0.05, 0.203, "Primary Code File: src/database/db_manager.py  |  Storage: results/traffic_results.sqlite3",
            fontsize=11, fontweight='bold', color="#334155")

    db_points = [
        ("• Relational Database Schema", "3 normalized tables: simulation_runs (summary PK), step_metrics (FK run_id), scheduler_decisions (FK)."),
        ("• ACID Transactions", "All insertions wrapped in atomic transactions with commit() and rollback() to prevent partial writes."),
        ("• Parameterized SQL Queries", "Uses SQL parameter placeholders ('?' for SQLite, '%s' for MySQL) to prevent syntax injection."),
        ("• MySQL + SQLite Fallback", "Configured for local MySQL; automatically falls back to SQLite without crashing if MySQL is offline.")
    ]

    y_pos_db = 0.175
    for title, desc in db_points:
        ax.text(0.06, y_pos_db, title, fontsize=10.5, fontweight='bold', color="#1e293b")
        ax.text(0.35, y_pos_db, desc, fontsize=10, color="#475569")
        y_pos_db -= 0.026

    # 4. Folder Structure Section
    ax.plot([0.05, 0.95], [0.06, 0.06], color="#cbd5e1", lw=1.5)
    ax.text(0.05, 0.038, "Folder Structure: D:\\SmartTrafficSimulator\\  |  TrafficControl/  |  src/ (simulation, scheduling, rl, database, evaluation)",
            fontsize=10.5, fontweight='bold', color="#0f766e")

    plt.tight_layout()
    plt.savefig(IMG_FILE, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Image Generator] Successfully created Infographic at {IMG_FILE}")


if __name__ == "__main__":
    generate_infographic()
