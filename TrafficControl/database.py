from pathlib import Path
import sqlite3
import csv

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DB_PATH = RESULTS_DIR / "traffic_results.sqlite3"

def connect():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            run_id TEXT PRIMARY KEY,
            controller TEXT NOT NULL,
            seed INTEGER NOT NULL,
            simulation_seconds INTEGER NOT NULL,
            departed_vehicles INTEGER NOT NULL,
            arrived_vehicles INTEGER NOT NULL,
            vehicles_remaining INTEGER NOT NULL,
            max_queue_vehicles INTEGER NOT NULL,
            mean_queue_vehicles REAL NOT NULL,
            stopped_vehicle_seconds INTEGER NOT NULL,
            mean_waiting_seconds_per_departed_vehicle REAL,
            co2_grams REAL NOT NULL,
            throughput_vehicles_per_hour REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS step_metrics (
            run_id TEXT NOT NULL,
            sim_time INTEGER NOT NULL,
            active_vehicles INTEGER NOT NULL,
            halted_vehicles INTEGER NOT NULL,
            mean_speed_mps REAL NOT NULL,
            queue_n INTEGER NOT NULL,
            queue_s INTEGER NOT NULL,
            queue_e INTEGER NOT NULL,
            queue_w INTEGER NOT NULL,
            co2_grams_this_step REAL NOT NULL,
            PRIMARY KEY (run_id, sim_time),
            FOREIGN KEY (run_id) REFERENCES experiments(run_id)
        )
    """)
    conn.commit()
    return conn

def save_experiment(conn, summary, steps):
    cols = [
        "run_id", "controller", "seed", "simulation_seconds", "departed_vehicles",
        "arrived_vehicles", "vehicles_remaining", "max_queue_vehicles",
        "mean_queue_vehicles", "stopped_vehicle_seconds",
        "mean_waiting_seconds_per_departed_vehicle", "co2_grams",
        "throughput_vehicles_per_hour"
    ]
    conn.execute(
        f"INSERT OR REPLACE INTO experiments ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
        tuple(summary.get(c) for c in cols)
    )
    conn.executemany("""
        INSERT OR REPLACE INTO step_metrics
        (run_id, sim_time, active_vehicles, halted_vehicles, mean_speed_mps,
         queue_n, queue_s, queue_e, queue_w, co2_grams_this_step)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (summary["run_id"], s["sim_time"], s["active_vehicles"], s["halted_vehicles"],
         s["mean_speed_mps"], s["queue_n"], s["queue_s"], s["queue_e"], s["queue_w"],
         s["co2_grams_this_step"]) for s in steps
    ])
    conn.commit()

def export_csv(summary, steps):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = RESULTS_DIR / "experiments.csv"
    steps_file = RESULTS_DIR / f"steps_{summary['run_id']}.csv"
    write_header = not summary_file.exists()
    with summary_file.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(summary)
    if steps:
        with steps_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(steps[0].keys()))
            writer.writeheader()
            writer.writerows(steps)
    return summary_file, steps_file
