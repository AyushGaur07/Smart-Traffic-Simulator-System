"""
DQN Training Pipeline for Smart Traffic Management.
Trains the Q-network with experience replay and saves checkpoint models.
"""

from pathlib import Path
import argparse
import numpy as np

from src.simulation.sumo_env import SumoTrafficEnv
from src.rl.dqn_agent import DQNAgent

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NET_FILE = PROJECT_ROOT / "TrafficControl" / "network.net.xml"
ROUTES_FILE = PROJECT_ROOT / "TrafficControl" / "routes.rou.xml"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
MODEL_PATH = CHECKPOINT_DIR / "dqn_traffic_model.pth"


def train_dqn(episodes: int = 5, sim_seconds: int = 300, seed: int = 42):
    """
    Trains the DQN agent over a specified number of simulation episodes.
    Logs episode rewards and loss.
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    agent = DQNAgent(
        state_dim=7,
        action_dim=2,
        lr=1e-3,
        gamma=0.95,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.99,
        buffer_capacity=10000,
        batch_size=32,
        target_update_freq=50
    )

    env = SumoTrafficEnv(
        net_file=NET_FILE,
        route_file=ROUTES_FILE,
        sim_seconds=sim_seconds,
        seed=seed,
        use_gui=False,
        min_green=10.0,
        max_green=60.0
    )

    print(f"\n==========================================")
    print(f"Starting DQN Training: {episodes} episodes, {sim_seconds}s per episode")
    print(f"Checkpoint target: {MODEL_PATH}")
    print(f"==========================================\n")

    for ep in range(1, episodes + 1):
        state = env.reset()
        total_reward = 0.0
        losses = []

        for step in range(sim_seconds):
            # Epsilon-greedy action
            action = agent.select_action(state, evaluate=False)

            # Step environment
            next_state, reward, done, info = env.step(action)
            total_reward += reward

            # Push to replay buffer
            agent.memory.push(state, action, reward, next_state, done)
            state = next_state

            # Perform Q-network gradient update
            loss = agent.train_step()
            if loss is not None:
                losses.append(loss)

            if done:
                break

        env.close()

        avg_loss = np.mean(losses) if losses else 0.0
        print(f"Episode {ep}/{episodes} | Total Reward: {total_reward:8.1f} | "
              f"Departed: {info['total_departed']:3d} | Arrived: {info['total_arrived']:3d} | "
              f"Epsilon: {agent.epsilon:.3f} | Avg Loss: {avg_loss:.4f}")

    # Save trained checkpoint
    agent.save(MODEL_PATH)
    print(f"\n[Training Complete] Model saved successfully to {MODEL_PATH}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DQN Traffic Controller")
    parser.add_argument("--episodes", type=int, default=5, help="Number of training episodes")
    parser.add_argument("--seconds", type=int, default=300, help="Simulation duration per episode")
    parser.add_argument("--seed", type=int, default=42, help="SUMO random seed")
    args = parser.parse_args()

    train_dqn(episodes=args.episodes, sim_seconds=args.seconds, seed=args.seed)
