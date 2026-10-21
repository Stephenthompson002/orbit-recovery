"""Small command-line runner for reproducible orbit diagnostics."""

import argparse
import json
import tempfile
from pathlib import Path

from .simulation import OrbitSimulation


def _create_simulation(config: dict) -> OrbitSimulation:
    return OrbitSimulation(
        mu=config["mu"],
        dt=config["dt"],
        position=tuple(config["position"]),
        velocity=tuple(config["velocity"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent.parent / "examples" / "eccentric_orbit.json")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--checkpoint-every", type=int, default=None)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    steps = args.steps if args.steps is not None else config["steps"]
    interval = (
        args.checkpoint_every
        if args.checkpoint_every is not None
        else config["checkpoint_every"]
    )
    if steps < 0 or interval <= 0:
        parser.error("steps must be nonnegative and checkpoint interval must be positive")

    uninterrupted = _create_simulation(config).run_steps(steps)
    with tempfile.TemporaryDirectory() as directory:
        checkpoint_path = Path(directory) / "orbit.json"
        resumed = _create_simulation(config)
        completed = 0
        while completed < steps:
            count = min(interval, steps - completed)
            resumed.run_steps(count)
            completed += count
            if completed < steps:
                resumed.save_checkpoint(checkpoint_path)
                resumed = OrbitSimulation.load_checkpoint(checkpoint_path)

    error = max(abs(a - b) for a, b in zip(uninterrupted.state, resumed.state, strict=True))
    print(f"steps={steps} checkpoint_every={interval}")
    print(f"uninterrupted energy={uninterrupted.energy:.12g}")
    print(f"resumed energy={resumed.energy:.12g}")
    print(f"maximum endpoint component difference={error:.12g}")


if __name__ == "__main__":
    main()
