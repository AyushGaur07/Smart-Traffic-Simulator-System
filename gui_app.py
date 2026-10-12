"""
Desktop GUI Control Dashboard for Smart Traffic Management System.
Built with Tkinter (Python standard library, no extra install needed).
Allows one-click control, SUMO GUI launching, live status, and benchmark viewing.
"""
import os
import sys
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

RESULTS_IMAGE = PROJECT_ROOT / "results" / "benchmark_comparison.png"


class TrafficDashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Traffic Simulator — StructMinds PBL Phase-II")
        self.geometry("780x640")
        self.minsize(700, 550)

        # Apply a clean native Windows theme
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "winnative" in style.theme_names():
            style.theme_use("winnative")

        self.running_process = None
        self._build_ui()

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#2c3e50", pady=12)
        header.pack(fill="x")

        title_label = tk.Label(
            header,
            text="Smart Traffic Management System",
            font=("Helvetica", 16, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title_label.pack()

        subtitle_label = tk.Label(
            header,
            text="OS-Based Real-Time Process Scheduling & AI Traffic Control (Team StructMinds)",
            font=("Helvetica", 9),
            fg="#bdc3c7",
            bg="#2c3e50"
        )
        subtitle_label.pack()

        # Main controls container
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)

        # Control Configuration Box
        config_frame = ttk.LabelFrame(main_frame, text=" 1. Simulation Setup ", padding="10")
        config_frame.pack(fill="x", pady=5)

        # Row 1: Strategy dropdown
        ttk.Label(config_frame, text="Control Strategy:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.controller_var = tk.StringVar(value="dqn_os")
        strategies = [
            ("DQN + OS Safety Arbiter (Best / Smartest)", "dqn_os"),
            ("OS Adaptive Priority & Aging (OS Concept)", "adaptive"),
            ("Pure DQN Reinforcement Learning", "dqn"),
            ("Fixed-Time Baseline (Old Standard)", "fixed"),
        ]
        self.strat_dropdown = ttk.Combobox(
            config_frame,
            values=[s[0] for s in strategies],
            state="readonly",
            width=42
        )
        self.strat_dropdown.current(0)
        self.strat_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.strategy_map = {s[0]: s[1] for s in strategies}

        # Row 2: Duration, Random Seed & GUI check
        ttk.Label(config_frame, text="Duration (seconds):", font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.duration_var = tk.StringVar(value="300")
        duration_entry = ttk.Entry(config_frame, textvariable=self.duration_var, width=10)
        duration_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(config_frame, text="Traffic Random Seed:", font=("Helvetica", 10)).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.seed_var = tk.StringVar(value="42")
        seed_entry = ttk.Entry(config_frame, textvariable=self.seed_var, width=10)
        seed_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.gui_var = tk.BooleanVar(value=True)
        gui_check = tk.Checkbutton(
            config_frame,
            text="Open 3D/2D Visualizer (SUMO GUI Window so you can see cars moving!)",
            variable=self.gui_var,
            font=("Helvetica", 10),
            activebackground="#f0f0f0",
            selectcolor="#ffffff"
        )
        gui_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Action Buttons Box
        btn_frame = ttk.LabelFrame(main_frame, text=" 2. Actions & Demonstrations ", padding="10")
        btn_frame.pack(fill="x", pady=8)

        self.btn_run = tk.Button(
            btn_frame,
            text="▶ Start Traffic Simulation",
            font=("Helvetica", 11, "bold"),
            bg="#27ae60",
            fg="white",
            padx=12,
            pady=6,
            relief="raised",
            command=self.start_simulation
        )
        self.btn_run.pack(side="left", padx=6)

        self.btn_benchmark = tk.Button(
            btn_frame,
            text="📊 Run All 4 Comparison Benchmark",
            font=("Helvetica", 10, "bold"),
            bg="#2980b9",
            fg="white",
            padx=10,
            pady=6,
            relief="raised",
            command=self.run_benchmark
        )
        self.btn_benchmark.pack(side="left", padx=6)

        self.btn_tests = tk.Button(
            btn_frame,
            text="🧪 Run Unit Tests",
            font=("Helvetica", 10),
            bg="#8e44ad",
            fg="white",
            padx=10,
            pady=6,
            relief="raised",
            command=self.run_tests
        )
        self.btn_tests.pack(side="left", padx=6)

        self.btn_stop = tk.Button(
            btn_frame,
            text="⏹ Stop",
            font=("Helvetica", 10),
            bg="#c0392b",
            fg="white",
            padx=10,
            pady=6,
            state="disabled",
            command=self.stop_process
        )
        self.btn_stop.pack(side="right", padx=6)

        self.btn_clear = tk.Button(
            btn_frame,
            text="🧹 Clear Output",
            font=("Helvetica", 10),
            bg="#555555",
            fg="white",
            padx=10,
            pady=6,
            relief="raised",
            command=self.clear_console
        )
        self.btn_clear.pack(side="right", padx=6)

        # Live Console Output Box
        console_frame = ttk.LabelFrame(main_frame, text=" Live Output & Real-Time Log ", padding="8")
        console_frame.pack(fill="both", expand=True, pady=5)

        self.console = tk.Text(
            console_frame,
            wrap="word",
            bg="#181c24",
            fg="#e2e8f0",
            insertbackground="white",
            font=("Consolas", 10),
            padx=10,
            pady=8
        )
        scrollbar = ttk.Scrollbar(console_frame, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.console.pack(fill="both", expand=True)

        self.log("╔══════════════════════════════════════════════════════════════════╗")
        self.log("║     SMART TRAFFIC SIMULATOR — LIVE DASHBOARD                     ║")
        self.log("╚══════════════════════════════════════════════════════════════════╝")
        self.log(" • Select a strategy above and click '▶ Start Traffic Simulation'.")
        self.log(" • When the SUMO window opens, click the green Play button (▶).")
        self.log(" • Live progress bars and clear summary cards will display below.\n")

    def log(self, text: str):
        self.console.insert("end", text + "\n")
        self.console.see("end")

    def clear_console(self):
        self.console.delete("1.0", "end")
        self.log("Output cleared. Ready for next simulation.\n")

    def run_command_in_thread(self, cmd_args, description):
        def worker():
            self.log(f"\n>>> [STARTING] {description}...")
            self.btn_run.config(state="disabled")
            self.btn_benchmark.config(state="disabled")
            self.btn_tests.config(state="disabled")
            self.btn_stop.config(state="normal")

            env = os.environ.copy()
            env["PYTHONPATH"] = str(PROJECT_ROOT)

            try:
                self.running_process = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    env=env
                )

                for line in self.running_process.stdout:
                    self.console.insert("end", line)
                    self.console.see("end")

                self.running_process.wait()
                code = self.running_process.returncode
                if code == 0:
                    self.log(f">>> [FINISHED] {description} successfully.")
                else:
                    self.log(f">>> [EXIT] {description} exited with code {code}.")
            except Exception as e:
                self.log(f">>> [ERROR] {e}")
            finally:
                self.running_process = None
                self.btn_run.config(state="normal")
                self.btn_benchmark.config(state="normal")
                self.btn_tests.config(state="normal")
                self.btn_stop.config(state="disabled")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def start_simulation(self):
        strat_key = self.strategy_map[self.strat_dropdown.get()]
        dur = self.duration_var.get().strip() or "300"
        seed = self.seed_var.get().strip() or "42"
        use_gui = self.gui_var.get()

        cmd = [
            str(PYTHON_EXE),
            str(PROJECT_ROOT / "main.py"),
            "--mode", "run",
            "--controller", strat_key,
            "--seconds", dur,
            "--seed", seed
        ]
        if use_gui:
            cmd.append("--gui")

        self.run_command_in_thread(cmd, f"Simulation with {strat_key.upper()} (Seed {seed})")

    def run_benchmark(self):
        dur = self.duration_var.get().strip() or "300"
        seed = self.seed_var.get().strip() or "42"
        cmd = [
            str(PYTHON_EXE),
            str(PROJECT_ROOT / "main.py"),
            "--mode", "benchmark",
            "--seconds", dur,
            "--seed", seed
        ]
        self.run_command_in_thread(cmd, f"4-Controller Benchmark Evaluation (Seed {seed})")

    def run_tests(self):
        cmd = [
            str(PYTHON_EXE),
            "-m", "unittest",
            "tests/test_traffic_system.py"
        ]
        self.run_command_in_thread(cmd, "Unit Test Suite")

    def stop_process(self):
        if self.running_process:
            self.running_process.terminate()
            self.log(">>> [STOPPING] Process stopped by user.")


def main():
    app = TrafficDashboardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
