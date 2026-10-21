The orbital run in this workspace gives a noticeably different trajectory after periodic checkpoint recovery than it does when run continuously. Investigate the simulation and its diagnostics, identify the cause, and repair the checkpoint/recovery behavior without weakening the numerical behavior or validation.

The project is under `/workspace/orbit_recovery/`. It models a Newtonian two-body relative orbit with configurable gravitational parameter, initial position and velocity, and fixed time step. The reproducible example is `/workspace/examples/eccentric_orbit.json`; run the diagnostic with:

```sh
python -m orbit_recovery.cli
```

Keep the package API and checkpoint error handling usable. Checkpoints with unsupported versions and invalid inputs must fail explicitly. Validate the fix with the supplied diagnostic and by comparing resumed and uninterrupted runs at different checkpoint phases. The task verifier also exercises distinct orbital parameters and long-run physical invariants.

You have 3600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
