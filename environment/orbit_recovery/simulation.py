"""Simulation state and stepping API."""

import math

from .integrator import advance
from .history import DerivativeHistory
from .physics import PhaseVector, derivative, specific_angular_momentum, specific_energy


class OrbitSimulation:
    def __init__(
        self,
        mu: float,
        dt: float,
        position: tuple[float, float, float],
        velocity: tuple[float, float, float],
        *,
        time: float = 0.0,
        step_index: int = 0,
        history: DerivativeHistory | None = None,
    ) -> None:
        self.mu = self._finite_positive(mu, "mu")
        self.dt = self._finite_positive(dt, "dt")
        if len(position) != 3 or len(velocity) != 3:
            raise ValueError("position and velocity must each contain three components")
        if not all(math.isfinite(value) for value in (*position, *velocity)):
            raise ValueError("position and velocity components must be finite")
        self.state: PhaseVector = (*position, *velocity)
        if sum(value * value for value in self.state[:3]) == 0.0:
            raise ValueError("initial separation must be nonzero")
        if not math.isfinite(time):
            raise ValueError("time must be finite")
        if isinstance(step_index, bool) or not isinstance(step_index, int) or step_index < 0:
            raise ValueError("step_index must be a nonnegative integer")
        self.time = float(time)
        self.step_index = step_index
        self.history = (
            history
            if history is not None
            else DerivativeHistory.from_ordered((derivative(self.state, self.mu),))
        )
        self._validate_history()

    @staticmethod
    def _finite_positive(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a finite positive number")
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite positive number")
        return value

    def _validate_history(self) -> None:
        for item in self.history.ordered():
            if len(item) != 6 or not all(math.isfinite(value) for value in item):
                raise ValueError("derivative history contains an invalid phase vector")

    def step(self) -> None:
        self.state, self.history = advance(self.state, self.history, self.dt, self.mu)
        self.time += self.dt
        self.step_index += 1

    def run_steps(self, steps: int) -> "OrbitSimulation":
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError("steps must be a nonnegative integer")
        for _ in range(steps):
            self.step()
        return self

    @property
    def energy(self) -> float:
        return specific_energy(self.state, self.mu)

    @property
    def angular_momentum(self) -> tuple[float, float, float]:
        return specific_angular_momentum(self.state)

    def save_checkpoint(self, path: str) -> None:
        from .checkpoint import save_checkpoint

        save_checkpoint(self, path)

    @classmethod
    def load_checkpoint(cls, path: str) -> "OrbitSimulation":
        from .checkpoint import load_checkpoint

        return load_checkpoint(path)
