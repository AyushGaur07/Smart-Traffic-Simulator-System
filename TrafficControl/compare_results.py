import sqlite3
from database import DB_PATH

def main():
    if not DB_PATH.exists():
        print("No database yet. Run at least one experiment first.")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT controller, COUNT(*), AVG(arrived_vehicles), AVG(max_queue_vehicles),
                   AVG(mean_queue_vehicles), AVG(stopped_vehicle_seconds),
                   AVG(co2_grams), AVG(throughput_vehicles_per_hour)
            FROM experiments GROUP BY controller ORDER BY controller
        """).fetchall()
    finally:
        conn.close()
    print("Compare runs only when network, demand, duration and seed are matched.")
    print("controller | runs | avg arrived | avg max halted | avg mean halted | "
          "avg stopped vehicle-seconds | avg CO2 grams | avg throughput/hour")
    for row in rows:
        print(" | ".join(str(round(x, 3) if isinstance(x, float) else x) for x in row))

if __name__ == "__main__":
    main()
