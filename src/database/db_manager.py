"""
Database connection and storage module.
Supports MySQL with an automatic SQLite fallback.
Uses parameterized queries and proper transactions.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_PATH = RESULTS_DIR / "traffic_results.sqlite3"

# Read environment variables
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "smart_traffic_db")


class DatabaseManager:
    """
    Manages database connections, schema initialization, and data persistence
    with seamless SQLite fallback when MySQL is unavailable.
    """

    def __init__(self, db_type: Optional[str] = None):
        self.db_type = db_type or DB_TYPE
        self.active_backend = "sqlite"
        self._init_schema()

    def get_connection(self):
        """Returns an active database connection."""
        if self.db_type == "mysql":
            try:
                import pymysql
                conn = pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    autocommit=False,
                    charset="utf8mb4"
                )
                self.active_backend = "mysql"
                return conn
            except Exception as e:
                # Graceful fallback to SQLite
                print(f"[DatabaseManager] Warning: MySQL connection failed ({e}). Falling back to SQLite.")
                self.active_backend = "sqlite"

        # SQLite fallback / default
        self.active_backend = "sqlite"
        conn = sqlite3.connect(DEFAULT_SQLITE_PATH)
        return conn

    def _init_schema(self):
        """Initializes tables for simulation runs, step metrics, scheduler decisions, and RL rewards."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if self.active_backend == "mysql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    run_id VARCHAR(64) PRIMARY KEY,
                    controller VARCHAR(32) NOT NULL,
                    seed INT NOT NULL,
                    simulation_seconds INT NOT NULL,
                    departed_vehicles INT NOT NULL,
                    arrived_vehicles INT NOT NULL,
                    vehicles_remaining INT NOT NULL,
                    max_queue_vehicles INT NOT NULL,
                    mean_queue_vehicles DOUBLE NOT NULL,
                    stopped_vehicle_seconds INT NOT NULL,
                    mean_waiting_seconds_per_vehicle DOUBLE,
                    total_co2_grams DOUBLE NOT NULL,
                    throughput_vehicles_per_hour DOUBLE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS step_metrics (
                    run_id VARCHAR(64) NOT NULL,
                    sim_time INT NOT NULL,
                    active_vehicles INT NOT NULL,
                    halted_vehicles INT NOT NULL,
                    mean_speed_mps DOUBLE NOT NULL,
                    queue_n INT NOT NULL,
                    queue_s INT NOT NULL,
                    queue_e INT NOT NULL,
                    queue_w INT NOT NULL,
                    co2_grams_this_step DOUBLE NOT NULL,
                    PRIMARY KEY (run_id, sim_time),
                    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_decisions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64) NOT NULL,
                    sim_time INT NOT NULL,
                    chosen_phase INT NOT NULL,
                    reason VARCHAR(128) NOT NULL,
                    ns_waiting DOUBLE NOT NULL,
                    ew_waiting DOUBLE NOT NULL,
                    ns_queue INT NOT NULL,
                    ew_queue INT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
            """)
        else:
            # SQLite syntax
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_runs (
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
                    mean_waiting_seconds_per_vehicle REAL,
                    total_co2_grams REAL NOT NULL,
                    throughput_vehicles_per_hour REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
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
                    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    sim_time INTEGER NOT NULL,
                    chosen_phase INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    ns_waiting REAL NOT NULL,
                    ew_waiting REAL NOT NULL,
                    ns_queue INTEGER NOT NULL,
                    ew_queue INTEGER NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
                );
            """)

        conn.commit()
        conn.close()

    def save_run(self, summary: Dict[str, Any], steps: List[Dict[str, Any]], decisions: Optional[List[Dict[str, Any]]] = None):
        """Saves a completed simulation run with step metrics and scheduler decisions transactionally."""
        conn = self.get_connection()
        cursor = conn.cursor()
        ph = "%s" if self.active_backend == "mysql" else "?"

        cols = [
            "run_id", "controller", "seed", "simulation_seconds", "departed_vehicles",
            "arrived_vehicles", "vehicles_remaining", "max_queue_vehicles",
            "mean_queue_vehicles", "stopped_vehicle_seconds",
            "mean_waiting_seconds_per_vehicle", "total_co2_grams",
            "throughput_vehicles_per_hour"
        ]

        try:
            insert_run_sql = f"""
                INSERT OR REPLACE INTO simulation_runs ({','.join(cols)})
                VALUES ({','.join([ph] * len(cols))})
            """ if self.active_backend == "sqlite" else f"""
                INSERT INTO simulation_runs ({','.join(cols)})
                VALUES ({','.join([ph] * len(cols))})
                ON DUPLICATE KEY UPDATE controller=VALUES(controller), arrived_vehicles=VALUES(arrived_vehicles)
            """
            cursor.execute(insert_run_sql, tuple(summary.get(c) for c in cols))

            # Insert steps
            step_cols = [
                "run_id", "sim_time", "active_vehicles", "halted_vehicles",
                "mean_speed_mps", "queue_n", "queue_s", "queue_e", "queue_w",
                "co2_grams_this_step"
            ]
            insert_step_sql = f"""
                INSERT OR REPLACE INTO step_metrics ({','.join(step_cols)})
                VALUES ({','.join([ph] * len(step_cols))})
            """ if self.active_backend == "sqlite" else f"""
                INSERT INTO step_metrics ({','.join(step_cols)})
                VALUES ({','.join([ph] * len(step_cols))})
                ON DUPLICATE KEY UPDATE halted_vehicles=VALUES(halted_vehicles)
            """
            step_values = [
                tuple(
                    summary["run_id"] if c == "run_id" else s.get(c)
                    for c in step_cols
                )
                for s in steps
            ]
            cursor.executemany(insert_step_sql, step_values)

            # Insert decisions if provided
            if decisions:
                dec_cols = ["run_id", "sim_time", "chosen_phase", "reason", "ns_waiting", "ew_waiting", "ns_queue", "ew_queue"]
                insert_dec_sql = f"""
                    INSERT INTO scheduler_decisions ({','.join(dec_cols)})
                    VALUES ({','.join([ph] * len(dec_cols))})
                """
                dec_values = [
                    tuple(
                        summary["run_id"] if c == "run_id" else d.get(c)
                        for c in dec_cols
                    )
                    for d in decisions
                ]
                cursor.executemany(insert_dec_sql, dec_values)

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[DatabaseManager] Transaction rolled back due to error: {e}")
            raise e
        finally:
            conn.close()

    def get_all_runs(self) -> List[Dict[str, Any]]:
        """Retrieves summary metrics for all stored simulation runs."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT controller, COUNT(*), AVG(arrived_vehicles), AVG(max_queue_vehicles),
                   AVG(mean_queue_vehicles), AVG(stopped_vehicle_seconds),
                   AVG(total_co2_grams), AVG(throughput_vehicles_per_hour)
            FROM simulation_runs GROUP BY controller ORDER BY controller
        """)
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "controller": r[0],
                "runs": r[1],
                "avg_arrived": round(float(r[2]), 2) if r[2] is not None else 0.0,
                "avg_max_queue": round(float(r[3]), 2) if r[3] is not None else 0.0,
                "avg_mean_queue": round(float(r[4]), 2) if r[4] is not None else 0.0,
                "avg_stopped_veh_sec": round(float(r[5]), 2) if r[5] is not None else 0.0,
                "avg_co2_grams": round(float(r[6]), 2) if r[6] is not None else 0.0,
                "avg_throughput_vph": round(float(r[7]), 2) if r[7] is not None else 0.0,
            })
        return results
