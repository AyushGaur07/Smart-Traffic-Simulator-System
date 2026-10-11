
from pathlib import Path
import traci

PROJECT = Path(__file__).resolve().parent
SUMO = Path(r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe")
NETWORK = PROJECT / "network.net.xml"
ROUTES = PROJECT / "routes.rou.xml"

SIMULATION_SECONDS = 300

command = [
    str(SUMO),
    "-n", str(NETWORK),
    "-r", str(ROUTES),
    "--end", str(SIMULATION_SECONDS),
    "--no-step-log", "true"
]

print("Running fixed-time baseline...")
traci.start(command)

total_stopped_vehicle_seconds = 0
max_stopped = 0
stopped_vehicle_samples = 0
total_vehicle_samples = 0

try:
    total_arrived = 0
    total_departed = 0
    for second in range(SIMULATION_SECONDS):
        traci.simulationStep()
        total_arrived += traci.simulation.getArrivedNumber()
        total_departed += traci.simulation.getDepartedNumber()

        vehicle_ids = traci.vehicle.getIDList()
        stopped_now = sum(
            traci.vehicle.getSpeed(vid) <= 0.1
            for vid in vehicle_ids
        )

        # Count stopped vehicle-seconds across the whole run
        total_stopped_vehicle_seconds += stopped_now
        max_stopped = max(max_stopped, stopped_now)
        total_vehicle_samples += len(vehicle_ids)
        stopped_vehicle_samples += stopped_now

        if (second + 1) % 60 == 0:
            print(
                f"Time: {second + 1:3d}s | "
                f"Present: {len(vehicle_ids):3d} | "
                f"Stopped: {stopped_now:3d} | "
                f"Arrived: {total_arrived:3d}"
            )

    print("\n--- FIXED-TIME BASELINE RESULTS ---")
    print(f"Simulation duration: {SIMULATION_SECONDS} seconds")
    print(f"Maximum stopped vehicles at once: {max_stopped}")
    print(f"Total stopped vehicle-seconds: {total_stopped_vehicle_seconds}")
    print(f"Total vehicle observations: {total_vehicle_samples}")
    print(f"Total stopped vehicle observations: {stopped_vehicle_samples}")
    print(f"Vehicles still present: {len(traci.vehicle.getIDList())}")
    print(f"Vehicles departed: {total_departed}")
    print(f"Vehicles arrived: {total_arrived}")
    print(f"Vehicles waiting to depart: {traci.simulation.getDepartDelay() if hasattr(traci.simulation, 'getDepartDelay') else 'Not measured'}")

finally:
    traci.close()

print("\nBaseline run completed.")
