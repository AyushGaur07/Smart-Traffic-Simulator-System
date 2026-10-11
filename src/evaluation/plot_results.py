"""
Chart generation utility for evaluation comparison.
Generates publication-quality comparison bar charts using Matplotlib.
"""

from pathlib import Path
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def plot_benchmark_comparison(results_data=None):
    """Generates comparison charts for Throughput, Stopped Vehicle-Seconds, and Max Queue."""
    if not results_data:
        # Default to latest verified measurements if none passed
        results_data = [
            {"controller": "Fixed-Time", "arrived": 77, "stopped_sec": 1608, "max_queue": 15, "throughput": 924.0},
            {"controller": "OS-Adaptive", "arrived": 82, "stopped_sec": 575, "max_queue": 8, "throughput": 984.0},
            {"controller": "DQN", "arrived": 82, "stopped_sec": 808, "max_queue": 8, "throughput": 984.0},
            {"controller": "DQN + OS", "arrived": 85, "stopped_sec": 724, "max_queue": 7, "throughput": 1020.0},
        ]

    controllers = [r["controller"] for r in results_data]
    stopped_sec = [r["stopped_sec"] for r in results_data]
    throughput = [r["throughput"] for r in results_data]
    max_queue = [r["max_queue"] for r in results_data]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    colors = ["#e74c3c", "#3498db", "#f39c12", "#2ecc71"]

    # 1. Total Stopped Vehicle-Seconds (Lower is better)
    axes[0].bar(controllers, stopped_sec, color=colors)
    axes[0].set_title("Total Stopped Vehicle-Seconds (Lower is Better)")
    axes[0].set_ylabel("Stopped Seconds")
    for i, v in enumerate(stopped_sec):
        axes[0].text(i, v + 25, str(v), ha="center", fontweight="bold")

    # 2. Throughput (Higher is better)
    axes[1].bar(controllers, throughput, color=colors)
    axes[1].set_title("Throughput in Vehicles/Hour (Higher is Better)")
    axes[1].set_ylabel("Vehicles / Hour")
    for i, v in enumerate(throughput):
        axes[1].text(i, v + 15, str(v), ha="center", fontweight="bold")

    # 3. Maximum Queue Length (Lower is better)
    axes[2].bar(controllers, max_queue, color=colors)
    axes[2].set_title("Max Halted Queue Length (Lower is Better)")
    axes[2].set_ylabel("Vehicles")
    for i, v in enumerate(max_queue):
        axes[2].text(i, v + 0.3, str(v), ha="center", fontweight="bold")

    plt.tight_layout()
    chart_path = RESULTS_DIR / "benchmark_comparison.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()
    print(f"[Plotter] Comparison chart saved successfully to {chart_path}")
    return chart_path


if __name__ == "__main__":
    plot_benchmark_comparison()
