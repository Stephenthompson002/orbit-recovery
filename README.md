# orbit-recovery

An evaluation task in the Science category (Physics) about a two-body orbit simulation whose periodic checkpoint recovery corrupts the trajectory.

## Task summary

The agent investigates a multi-file Python simulation, reproduces the restart-dependent numerical error, and repairs checkpoint state handling. The simulation integrates Newtonian relative motion with an Adams-Bashforth-Moulton predictor-corrector. Independent tests cover analytic orbital positions, conservation of energy and angular momentum, restart equivalence at varied checkpoint phases, invalid inputs, and unsupported checkpoint versions.

The starter checkpoint omits state needed to reconstruct the derivative ring buffer's chronological position. The oracle writes a versioned format and migrates unambiguous version-1 checkpoints; ambiguous history and unsupported versions fail explicitly. The diagnosis is supported by the provided repeatable log and simulation source; the verifier is separate from the agent environment.

## Layout

- `task.toml`: Task metadata and artifact paths.
- `instruction.md`: agent-facing problem statement.
- `environment/`: pinned Python Docker environment, simulation package, configurable example and diagnostic output.
- `solution/`: isolated oracle patch and `solve.sh`.
- `tests/`: independent deterministic verifier and Docker setup.

## Local setup and validation

The runtime has no third-party Python dependencies or network requirement.

From this directory, build and run the agent environment:

```powershell
docker build -t orbit-recovery-env -f environment/Dockerfile environment
docker run --rm orbit-recovery-env
```

Run the verifier locally with the current starter source mounted into its test container:

```powershell
docker build -t orbit-recovery-verifier -f tests/Dockerfile tests
$source = (Resolve-Path environment\orbit_recovery).Path
$patch = (Resolve-Path solution\checkpoint.py).Path
docker run --rm --network none `
  --mount "type=bind,source=$source,target=/workspace/orbit_recovery,readonly" `
  --mount "type=bind,source=$patch,target=/workspace/orbit_recovery/checkpoint.py,readonly" `
  orbit-recovery-verifier bash /tests/test.sh
```

The command overlays only the oracle checkpoint module on the starter package and should finish with all verifier tests passing. Remove the second mount to see the starter fail the recovery and legacy-checkpoint checks. The verifier runs candidate code as an unprivileged user; `/tests` and `/logs` remain root-only.

Harbor oracle and NOP trials can be run from this directory with the installed Harbor CLI:

```powershell
harbor run --path . --agent oracle --quiet --yes
harbor run --path . --agent nop --quiet --yes
```

## Submission archive

The submission ZIP is built from the contents of this directory so `task.toml`, `instruction.md`, `environment/`, `solution/`, and `tests/` are at its root.
