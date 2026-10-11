from pathlib import Path
import argparse
import uuid
import statistics
import traci
from database import connect, save_experiment, export_csv

HERE = Path(__file__).resolve().parent
SUMO_HOME = Path(r"C:\Program Files (x86)\Eclipse\Sumo")
SUMO = SUMO_HOME / "bin" / "sumo.exe"
NET = HERE / "network.net.xml"
ROUTES = HERE / "routes.rou.xml"
GREEN_PHASES = (0, 2)
MIN_GREEN = 15.0
MAX_GREEN = 60.0
APPROACH_EDGES = {"N": "N_C", "S": "S_C", "E": "E_C", "W": "W_C"}

def lane_queue(edge_id):
    total = 0
    try:
        num_lanes = traci.edge.getLaneNumber(edge_id)
        for lane_idx in range(num_lanes):
            lane_id = f"{edge_id}_{lane_idx}"
            total += traci.lane.getLastStepHaltingNumber(lane_id)
    except traci.TraCIException:
        pass
    return int(total)

def observe():
    queues = {direction: lane_queue(edge) for direction, edge in APPROACH_EDGES.items()}
    vehicle_ids = traci.vehicle.getIDList()
    speeds = [traci.vehicle.getSpeed(v) for v in vehicle_ids]
    halted = sum(speed <= 0.1 for speed in speeds)
    mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
    co2_grams_step = 0.0
    for vid in vehicle_ids:
        try:
            # SUMO TraCI reports CO2 emission rate in mg/s; simulation step is 1 second.
            co2_grams_step += max(0.0, traci.vehicle.getCO2Emission(vid)) / 1000.0
        except traci.TraCIException:
            pass
    return queues, len(vehicle_ids), halted, mean_speed, co2_grams_step

def maybe_adapt(tls_id, phase, queues, sim_time, last_change):
    # The generated signal program has green phases 0 and 2 and yellow phases 1 and 3.
    # Do not overwrite signal states or bypass yellow transitions.
    if phase not in GREEN_PHASES or sim_time - last_change < 5:
        return last_change
    remaining = traci.trafficlight.getNextSwitch(tls_id) - sim_time
    if remaining > 2:
        return last_change
    ns = queues["N"] + queues["S"]
    ew = queues["E"] + queues["W"]
    pressure_current = ns if phase == 0 else ew
    pressure_other = ew if phase == 0 else ns
    duration = traci.trafficlight.getPhaseDuration(tls_id)
    if pressure_current > pressure_other and duration < MAX_GREEN:
        traci.trafficlight.setPhaseDuration(tls_id, min(MAX_GREEN, duration + 5))
        return sim_time
    if pressure_current < pressure_other and duration > MIN_GREEN:
        traci.trafficlight.setPhaseDuration(tls_id, max(MIN_GREEN, duration - 5))
        return sim_time
    return last_change

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", choices=("fixed", "adaptive"), default="fixed")
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    executable = SUMO_HOME / "bin" / ("sumo-gui.exe" if args.gui else "sumo.exe")
    for path in (executable, NET, ROUTES):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}. Check SUMO_HOME or generate the network.")
    run_id = f"{args.controller}_{args.seed}_{uuid.uuid4().hex[:8]}"
    command = [str(executable), "-n", str(NET), "-r", str(ROUTES),
               "--seed", str(args.seed), "--end", str(args.seconds),
               "--step-length", "1", "--no-step-log", "true", "--duration-log.disable", "true"]

    print(f"Starting {args.controller} controller for {args.seconds}s (seed {args.seed})")
    traci.start(command)
    tls_ids = traci.trafficlight.getIDList()
    if not tls_ids:
        traci.close()
        raise RuntimeError("No traffic-light-controlled junction found.")
    tls_id = tls_ids[0]

    steps = []
    halted_samples = []
    stopped_vehicle_seconds = 0
    total_co2_grams = 0.0
    waiting_active_at_end = 0.0
    last_change = -999
    total_arrived = 0
    total_departed = 0

    try:
        for sim_time in range(args.seconds):
            traci.simulationStep()
            total_arrived += traci.simulation.getArrivedNumber()
            total_departed += traci.simulation.getDepartedNumber()
            queues, active, halted, mean_speed, co2_g = observe()
            if args.controller == "adaptive":
                last_change = maybe_adapt(tls_id, traci.trafficlight.getPhase(tls_id),
                                          queues, sim_time, last_change)
            stopped_vehicle_seconds += halted
            halted_samples.append(halted)
            total_co2_grams += co2_g
            waiting_active_at_end = 0.0
            for vid in traci.vehicle.getIDList():
                try:
                    waiting_active_at_end += traci.vehicle.getAccumulatedWaitingTime(vid)
                except traci.TraCIException:
                    pass
            steps.append({
                "sim_time": sim_time + 1, "active_vehicles": active,
                "halted_vehicles": halted, "mean_speed_mps": round(mean_speed, 4),
                "queue_n": queues["N"], "queue_s": queues["S"],
                "queue_e": queues["E"], "queue_w": queues["W"],
                "co2_grams_this_step": round(co2_g, 6)
            })
            if (sim_time + 1) % 60 == 0:
                print(f"t={sim_time+1:4d}s | active={active:3d} | halted={halted:3d} | "
                      f"queues N/S/E/W={queues['N']}/{queues['S']}/{queues['E']}/{queues['W']}")

        arrived = int(total_arrived)
        departed = int(total_departed)
        remaining = len(traci.vehicle.getIDList())
        summary = {
            "run_id": run_id, "controller": args.controller, "seed": args.seed,
            "simulation_seconds": args.seconds, "departed_vehicles": departed,
            "arrived_vehicles": arrived, "vehicles_remaining": int(remaining),
            "max_queue_vehicles": int(max(halted_samples) if halted_samples else 0),
            "mean_queue_vehicles": round(statistics.mean(halted_samples) if halted_samples else 0.0, 4),
            "stopped_vehicle_seconds": int(stopped_vehicle_seconds),
            "mean_waiting_seconds_per_departed_vehicle":
                round(waiting_active_at_end / departed, 4) if departed else None,
            "co2_grams": round(total_co2_grams, 4),
            "throughput_vehicles_per_hour": round(arrived / (args.seconds / 3600), 4)
        }
    finally:
        traci.close()

    conn = connect()
    try:
        save_experiment(conn, summary, steps)
    finally:
        conn.close()
    summary_csv, step_csv = export_csv(summary, steps)

    print("\n--- EXPERIMENT SUMMARY ---")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nSQLite database: {HERE / 'results' / 'traffic_results.sqlite3'}")
    print(f"Summary CSV: {summary_csv}")
    print(f"Step metrics CSV: {step_csv}")

if __name__ == "__main__":
    main()
