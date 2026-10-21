"""Fixed-step Adams-Bashforth-Moulton predictor-corrector integrator."""

from .physics import PhaseVector, derivative
from .history import DerivativeHistory


def _add_scaled(state: PhaseVector, step: float, terms: tuple[tuple[float, PhaseVector], ...]) -> PhaseVector:
    values = [
        state[index] + step * sum(weight * term[index] for weight, term in terms)
        for index in range(6)
    ]
    return values[0], values[1], values[2], values[3], values[4], values[5]


def _rk4_step(state: PhaseVector, dt: float, mu: float) -> PhaseVector:
    first = derivative(state, mu)
    second = derivative(_add_scaled(state, dt / 2, ((1.0, first),)), mu)
    third = derivative(_add_scaled(state, dt / 2, ((1.0, second),)), mu)
    fourth = derivative(_add_scaled(state, dt, ((1.0, third),)), mu)
    return _add_scaled(
        state,
        dt,
        ((1 / 6, first), (1 / 3, second), (1 / 3, third), (1 / 6, fourth)),
    )


def advance(
    state: PhaseVector,
    history: DerivativeHistory,
    dt: float,
    mu: float,
) -> tuple[PhaseVector, tuple[PhaseVector, ...]]:
    """Advance one step and retain up to four derivatives in oldest-first order."""
    if len(history) < 4:
        next_state = _rk4_step(state, dt, mu)
    else:
        oldest, older, recent, newest = history.ordered()
        predicted = _add_scaled(
            state,
            dt / 24,
            ((-9, oldest), (37, older), (-59, recent), (55, newest)),
        )
        predicted_derivative = derivative(predicted, mu)
        next_state = _add_scaled(
            state,
            dt / 24,
            ((1, older), (-5, recent), (19, newest), (9, predicted_derivative)),
        )

    history.append(derivative(next_state, mu))
    return next_state, history
