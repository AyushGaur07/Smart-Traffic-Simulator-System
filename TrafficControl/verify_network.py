from pathlib import Path
import traci

HERE = Path(__file__).resolve().parent
SUMO = Path(r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe")
NET = HERE / "network.net.xml"
ROUTES = HERE / "routes.rou.xml"

for path in (SUMO, NET, ROUTES):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

traci.start([str(SUMO), "-n", str(NET), "-r", str(ROUTES), "--end", "5", "--no-step-log", "true"])
try:
    traci.simulationStep()
    print("Traffic-light IDs:", traci.trafficlight.getIDList())
    print("All junction IDs:", traci.junction.getIDList())
    for tls_id in traci.trafficlight.getIDList():
        print(f"\nTraffic light: {tls_id}")
        print("State:", traci.trafficlight.getRedYellowGreenState(tls_id))
        for program in traci.trafficlight.getAllProgramLogics(tls_id):
            print("Program:", program.programID, "| phases:", len(program.phases))
            for i, phase in enumerate(program.phases):
                print(f"  phase {i}: {phase.duration}s, {phase.state}")
finally:
    traci.close()
