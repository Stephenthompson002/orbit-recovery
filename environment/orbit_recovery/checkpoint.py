"""Versioned checkpoint persistence."""

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from .simulation import OrbitSimulation
from .history import DerivativeHistory

CHECKPOINT_VERSION = 1


class CheckpointError(ValueError):
    pass


def save_checkpoint(simulation: OrbitSimulation, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": "orbit-recovery-checkpoint",
        "version": CHECKPOINT_VERSION,
        "mu": simulation.mu,
        "dt": simulation.dt,
        "time": simulation.time,
        "step_index": simulation.step_index,
        "state": list(simulation.state),
        "history_slots": [
            list(item) if item is not None else None
            for item in simulation.history.slots
        ],
        "history_count": simulation.history.count,
    }
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=target.parent, delete=False
        ) as handle:
            temporary_path = handle.name
            json.dump(payload, handle, allow_nan=False, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CheckpointError(f"checkpoint field {field!r} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CheckpointError(f"checkpoint field {field!r} must be finite")
    return result


def load_checkpoint(path: str | Path) -> OrbitSimulation:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"could not read checkpoint: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("format") != "orbit-recovery-checkpoint":
        raise CheckpointError("unrecognized checkpoint format")
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != CHECKPOINT_VERSION:
        raise CheckpointError(f"unsupported checkpoint version: {version!r}")

    try:
        state = tuple(_number(value, "state") for value in payload["state"])
        if len(state) != 6:
            raise CheckpointError("checkpoint state must have six components")
        raw_slots = payload["history_slots"]
        if not isinstance(raw_slots, list):
            raise CheckpointError("checkpoint history_slots must be a list")
        slots = [
            None
            if item is None
            else tuple(_number(value, "history_slots") for value in item)
            for item in raw_slots
        ]
        if any(item is not None and len(item) != 6 for item in slots):
            raise CheckpointError("each occupied history slot must have six components")
        history_count = payload["history_count"]
        if isinstance(history_count, bool) or not isinstance(history_count, int):
            raise CheckpointError("checkpoint history_count must be an integer")
        history = DerivativeHistory.from_slots(slots, history_count)
        time = _number(payload["time"], "time")
        step_index = payload["step_index"]
        if isinstance(step_index, bool) or not isinstance(step_index, int):
            raise CheckpointError("checkpoint step_index must be an integer")
        return OrbitSimulation(
            mu=_number(payload["mu"], "mu"),
            dt=_number(payload["dt"], "dt"),
            position=state[:3],
            velocity=state[3:],
            time=time,
            step_index=step_index,
            history=history,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, CheckpointError):
            raise
        raise CheckpointError(f"invalid checkpoint: {exc}") from exc
