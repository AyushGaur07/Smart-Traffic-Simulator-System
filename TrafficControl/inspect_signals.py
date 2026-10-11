
from pathlib import Path
import traci

PROJECT = Path(__file__).resolve().parent
SUMO = Path(r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe")
NETWORK = PROJECT / "network.net.xml"
ROUTES = PROJECT / "routes.rou.xml"

command = [
    str(SUMO),
    "-n", str(NETWORK),
    "-r", str(ROUTES),
    "--end", "10",
    "--no-step-log", "true"
]

print("Inspecting the traffic-light program...")
traci.start(command)

try:
    for tls_id in traci.trafficlight.getIDList():
        print(f"\nTraffic light: {tls_id}")

        programs = traci.trafficlight.getAllProgramLogics(tls_id)

        for program in programs:
            print(f"\nProgram ID: {program.programID}")
            print(f"Number of phases: {len(program.phases)}")

            for i, phase in enumerate(program.phases):
                print(
                    f"Phase {i}: "
                    f"duration={phase.duration} seconds, "
                    f"state={phase.state}"
                )

                if phase.next:
                    print(f"  Next phase indices: {phase.next}")

    print("\nSignal inspection complete.")

finally:
    traci.close()
