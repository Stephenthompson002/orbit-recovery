import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import pwd
except ImportError:
    pwd = None

TASK_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = Path("/workspace")
if not (PACKAGE_PARENT / "orbit_recovery").is_dir():
    PACKAGE_PARENT = TASK_ROOT / "environment"

WORKER = r"""
import json
import sys
import tempfile
from pathlib import Path

request = json.load(sys.stdin)
sys.path.insert(0, request["package_parent"])
try:
    from orbit_recovery import OrbitSimulation

    def create(config):
        return OrbitSimulation(
            mu=config["mu"],
            dt=config["dt"],
            position=tuple(config["position"]),
            velocity=tuple(config["velocity"]),
        )

    def snapshot(simulation):
        return {
            "state": list(simulation.state),
            "time": simulation.time,
            "energy": simulation.energy,
            "angular_momentum": list(simulation.angular_momentum),
            "mu": simulation.mu,
            "dt": simulation.dt,
            "step_index": simulation.step_index,
            "history_slots": [
                list(item) if item is not None else None
                for item in simulation.history.slots
            ],
            "history_count": simulation.history.count,
            "history_start": simulation.history.start,
        }

    operation = request["operation"]
    if operation == "run":
        result = snapshot(create(request["config"]).run_steps(request["steps"]))
    elif operation == "resume":
        simulation = create(request["config"]).run_steps(request["cut"])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "orbit.json"
            simulation.save_checkpoint(checkpoint)
            simulation = OrbitSimulation.load_checkpoint(checkpoint)
            simulation.run_steps(request["steps"] - request["cut"])
        result = snapshot(simulation)
    elif operation == "repeat_resume":
        simulation = create(request["config"])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "orbit.json"
            completed = 0
            while completed < request["steps"]:
                count = min(request["interval"], request["steps"] - completed)
                simulation.run_steps(count)
                completed += count
                if completed < request["steps"]:
                    simulation.save_checkpoint(checkpoint)
                    simulation = OrbitSimulation.load_checkpoint(checkpoint)
        result = snapshot(simulation)
    elif operation == "roundtrip":
        simulation = create(request["config"]).run_steps(request["steps"])
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "orbit.json"
            simulation.save_checkpoint(checkpoint)
            simulation = OrbitSimulation.load_checkpoint(checkpoint)
        result = snapshot(simulation)
    elif operation in ("legacy_resume", "load_payload"):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "orbit.json"
            checkpoint.write_text(
                json.dumps(request["payload"]), encoding="utf-8"
            )
            simulation = OrbitSimulation.load_checkpoint(checkpoint)
            if operation == "legacy_resume":
                simulation.run_steps(request["steps"])
            result = snapshot(simulation)
    elif operation == "read_file":
        result = {"contents": Path(request["path"]).read_text(encoding="utf-8")}
    else:
        result = snapshot(create(request["config"]))
except Exception as error:
    result = {"error_type": type(error).__name__, "error": str(error)}

print(json.dumps(result, allow_nan=False))
"""


def query(operation: str, **parameters: object) -> dict:
    request = {
        "operation": operation,
        "package_parent": str(PACKAGE_PARENT),
        **parameters,
    }
    preexec_fn = None
    if os.name == "posix" and os.geteuid() == 0 and pwd is not None:
        account = pwd.getpwnam("orbitrunner")

        def drop_privileges() -> None:
            os.setgid(account.pw_gid)
            os.setuid(account.pw_uid)

        preexec_fn = drop_privileges

    process = subprocess.run(
        [sys.executable, "-I", "-c", WORKER],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
        cwd=tempfile.gettempdir(),
        env={
            "HOME": tempfile.gettempdir(),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        preexec_fn=preexec_fn,
    )
    if process.returncode != 0:
        raise AssertionError(
            f"candidate process exited {process.returncode}: {process.stderr[-4000:]}"
        )
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(
            f"candidate process did not return JSON: {process.stdout[-4000:]}"
        ) from error


def orbit_config(mu: float, semi_major_axis: float, eccentricity: float, dt: float) -> dict:
    periapsis = semi_major_axis * (1 - eccentricity)
    speed = math.sqrt(mu * (1 + eccentricity) / periapsis)
    return {
        "mu": mu,
        "dt": dt,
        "position": [periapsis, 0.0, 0.0],
        "velocity": [0.0, speed, 0.0],
    }


def analytic_orbit_position(
    mu: float, semi_major_axis: float, eccentricity: float, time: float
) -> tuple[float, float]:
    mean_motion = math.sqrt(mu / semi_major_axis**3)
    mean_anomaly = (mean_motion * time) % (2 * math.pi)
    eccentric_anomaly = mean_anomaly
    for _ in range(20):
        correction = (
            eccentric_anomaly
            - eccentricity * math.sin(eccentric_anomaly)
            - mean_anomaly
        ) / (1 - eccentricity * math.cos(eccentric_anomaly))
        eccentric_anomaly -= correction
        if abs(correction) < 1e-14:
            break
    return (
        semi_major_axis * (math.cos(eccentric_anomaly) - eccentricity),
        semi_major_axis * math.sqrt(1 - eccentricity**2) * math.sin(eccentric_anomaly),
    )


class OrbitRecoveryTests(unittest.TestCase):
    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0,
        "verifier privilege boundary is enforced in the Linux Docker image",
    )
    def test_candidate_process_cannot_read_verifier_tests(self) -> None:
        result = query("read_file", path="/tests/test_orbit_recovery.py")
        self.assertEqual(result["error_type"], "PermissionError")

    def test_analytic_orbits_match_independent_solution_and_conserve_invariants(self) -> None:
        cases = (
            (1.0, 1.0, 0.0, 0.01, 20),
            (0.8, 1.3, 0.6, 0.003, 12),
            (4.7, 2.2, 0.35, 0.01, 18),
        )
        for mu, axis, eccentricity, dt, orbits in cases:
            with self.subTest(mu=mu, axis=axis, eccentricity=eccentricity):
                config = orbit_config(mu, axis, eccentricity, dt)
                initial = query("run", config=config, steps=0)
                period = 2 * math.pi * math.sqrt(axis**3 / mu)
                result = query(
                    "run",
                    config=config,
                    steps=round(orbits * period / dt),
                )
                expected_x, expected_y = analytic_orbit_position(
                    mu, axis, eccentricity, result["time"]
                )
                position_error = math.hypot(
                    result["state"][0] - expected_x,
                    result["state"][1] - expected_y,
                )
                self.assertLess(position_error, 2e-5)
                self.assertLess(
                    abs(result["energy"] - initial["energy"])
                    / abs(initial["energy"]),
                    1e-6,
                )
                for current, starting in zip(
                    result["angular_momentum"],
                    initial["angular_momentum"],
                    strict=True,
                ):
                    self.assertLess(abs(current - starting), 1e-7)

    def test_checkpoint_resume_matches_uninterrupted_run_at_varied_cuts(self) -> None:
        config = orbit_config(1.0, 1.0, 0.4, 0.01)
        steps = 6000
        uninterrupted = query("run", config=config, steps=steps)
        for cut in (6, 7, 8, 9, 31, 997, 4001):
            with self.subTest(cut=cut):
                resumed = query(
                    "resume", config=config, steps=steps, cut=cut
                )
                for actual, expected in zip(
                    resumed["state"], uninterrupted["state"], strict=True
                ):
                    self.assertAlmostEqual(actual, expected, delta=1e-11)
                self.assertAlmostEqual(
                    resumed["time"], uninterrupted["time"], delta=1e-12
                )

    def test_repeated_checkpoint_recovery_preserves_the_trajectory(self) -> None:
        config = orbit_config(1.0, 1.0, 0.4, 0.02)
        steps = 10_000
        uninterrupted = query("run", config=config, steps=steps)
        resumed = query(
            "repeat_resume", config=config, steps=steps, interval=250
        )
        for actual, expected in zip(
            resumed["state"], uninterrupted["state"], strict=True
        ):
            self.assertAlmostEqual(actual, expected, delta=1e-11)

    def test_checkpoint_roundtrip_preserves_solver_configuration(self) -> None:
        config = orbit_config(3.25, 1.7, 0.25, 0.007)
        result = query("roundtrip", config=config, steps=18)
        self.assertEqual(result["mu"], config["mu"])
        self.assertEqual(result["dt"], config["dt"])
        self.assertEqual(result["step_index"], 18)
        self.assertEqual(result["history_start"], 3)

    def test_legacy_checkpoint_recovers_its_ring_phase(self) -> None:
        fixture = Path(__file__).parent / "data" / "legacy_v1_checkpoint.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        expected = query(
            "run",
            config=orbit_config(0.75, 1.2, 0.3, 0.002),
            steps=155,
        )
        restored = query(
            "legacy_resume",
            payload=payload,
            steps=137,
        )
        for actual, reference in zip(
            restored["state"], expected["state"], strict=True
        ):
            self.assertAlmostEqual(actual, reference, delta=1e-11)

    def test_ambiguous_legacy_checkpoint_is_rejected(self) -> None:
        fixture = Path(__file__).parent / "data" / "legacy_v1_checkpoint.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        payload["history_slots"][0] = payload["history_slots"][2]
        result = query("load_payload", payload=payload)
        self.assertEqual(result["error_type"], "CheckpointError")

    def test_unsupported_checkpoint_versions_are_rejected(self) -> None:
        for version in (0, 999, True):
            payload = {
                "format": "orbit-recovery-checkpoint",
                "version": version,
            }
            with self.subTest(version=version):
                result = query("load_payload", payload=payload)
                self.assertEqual(result["error_type"], "CheckpointError")

    def test_corrupt_checkpoint_is_rejected(self) -> None:
        result = query("load_payload", payload={"format": "wrong", "version": 2})
        self.assertEqual(result["error_type"], "CheckpointError")

    def test_invalid_physical_inputs_are_rejected(self) -> None:
        cases = (
            (0.0, 0.01, [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
            (1.0, 0.0, [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
            (1.0, 0.01, [0.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
            (1.0, 0.01, [1.0, 0.0, 0.0], [0.0, float("nan"), 0.0]),
        )
        for mu, dt, position, velocity in cases:
            config = {
                "mu": mu,
                "dt": dt,
                "position": position,
                "velocity": velocity,
            }
            with self.subTest(config=config):
                result = query("run", config=config, steps=0)
                self.assertEqual(result["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
