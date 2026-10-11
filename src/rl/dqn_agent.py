"""
Deep Q-Network (DQN) controller for traffic light control.
Uses PyTorch for neural network function approximation.
Includes Experience Replay, Target Network, and Epsilon-Greedy Exploration.
"""

import random
from collections import deque
from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from src.simulation.signal_controller import PHASE_NS_GREEN, PHASE_EW_GREEN


class QNetwork(nn.Module):
    """Deep Q-Network with fully connected layers."""

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 64):
        super(QNetwork, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ReplayBuffer:
    """Experience replay buffer for off-policy DQN training."""

    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, done = zip(*batch)
        return (
            np.array(state, dtype=np.float32),
            np.array(action, dtype=np.int64),
            np.array(reward, dtype=np.float32),
            np.array(next_state, dtype=np.float32),
            np.array(done, dtype=np.float32)
        )

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    Reinforcement learning agent controlling traffic signal phases.
    State: [Queue_N, Queue_S, Queue_E, Queue_W, Wait_NS, Wait_EW, Current_Phase]
    Actions: 0 -> NS Green (phase 0), 1 -> EW Green (phase 2)
    """

    ACTION_TO_PHASE = [PHASE_NS_GREEN, PHASE_EW_GREEN]

    def __init__(
        self,
        state_dim: int = 7,
        action_dim: int = 2,
        lr: float = 1e-3,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        buffer_capacity: int = 10000,
        batch_size: int = 32,
        target_update_freq: int = 50
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.policy_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.memory = ReplayBuffer(buffer_capacity)
        self.train_step_count = 0

    def select_action(self, state: np.ndarray, evaluate: bool = False) -> int:
        """Epsilon-greedy action selection. In evaluation mode, acts greedily."""
        if not evaluate and random.random() < self.epsilon:
            action_idx = random.randint(0, self.action_dim - 1)
        else:
            state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
                action_idx = int(torch.argmax(q_values, dim=1).item())
        return self.ACTION_TO_PHASE[action_idx]

    def train_step(self) -> Optional[float]:
        """Samples a mini-batch from experience buffer and performs gradient descent."""
        if len(self.memory) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)

        # Convert actions from phase ids (0, 2) to action indices (0, 1)
        action_indices = np.array([0 if a == PHASE_NS_GREEN else 1 for a in actions], dtype=np.int64)

        states_t = torch.tensor(states, dtype=torch.float32, device=self.device)
        actions_t = torch.tensor(action_indices, dtype=torch.int64, device=self.device).unsqueeze(1)
        rewards_t = torch.tensor(rewards, dtype=torch.float32, device=self.device).unsqueeze(1)
        next_states_t = torch.tensor(next_states, dtype=torch.float32, device=self.device)
        dones_t = torch.tensor(dones, dtype=torch.float32, device=self.device).unsqueeze(1)

        # Q(s, a)
        q_vals = self.policy_net(states_t).gather(1, actions_t)

        # Target Q = r + gamma * max_a' Q_target(s', a') * (1 - done)
        with torch.no_grad():
            next_q_vals = self.target_net(next_states_t).max(1, keepdim=True)[0]
            target_q = rewards_t + (1 - dones_t) * self.gamma * next_q_vals

        loss = self.loss_fn(q_vals, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.train_step_count += 1
        if self.train_step_count % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return float(loss.item())

    def save(self, filepath: Path):
        """Saves policy network weights."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.policy_net.state_dict(), filepath)

    def load(self, filepath: Path):
        """Loads policy network weights."""
        if filepath.exists():
            self.policy_net.load_state_dict(torch.load(filepath, map_location=self.device))
            self.target_net.load_state_dict(self.policy_net.state_dict())
            self.epsilon = self.epsilon_min
            print(f"[DQNAgent] Model loaded successfully from {filepath}")
        else:
            print(f"[DQNAgent] Warning: Checkpoint not found at {filepath}")
