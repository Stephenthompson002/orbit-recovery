"""Fixed-capacity derivative history used by the multistep integrator."""

from dataclasses import dataclass, field

from .physics import PhaseVector

HISTORY_CAPACITY = 4


@dataclass
class DerivativeHistory:
    slots: list[PhaseVector | None] = field(
        default_factory=lambda: [None] * HISTORY_CAPACITY
    )
    count: int = 0
    start: int = 0

    @classmethod
    def from_ordered(cls, values: tuple[PhaseVector, ...]) -> "DerivativeHistory":
        if not 1 <= len(values) <= HISTORY_CAPACITY:
            raise ValueError("derivative history must contain between one and four entries")
        history = cls()
        for value in values:
            history.append(value)
        return history

    @classmethod
    def from_slots(
        cls,
        slots: list[PhaseVector | None],
        count: int,
        start: int = 0,
    ) -> "DerivativeHistory":
        if len(slots) != HISTORY_CAPACITY:
            raise ValueError("derivative history buffer must contain four slots")
        if not 1 <= count <= HISTORY_CAPACITY:
            raise ValueError("derivative history count must be between one and four")
        if not 0 <= start < HISTORY_CAPACITY:
            raise ValueError("derivative history start is out of range")
        history = cls(list(slots), count, start)
        history.ordered()
        return history

    def __len__(self) -> int:
        return self.count

    def ordered(self) -> tuple[PhaseVector, ...]:
        values: list[PhaseVector] = []
        for index in range(self.count):
            value = self.slots[(self.start + index) % HISTORY_CAPACITY]
            if value is None:
                raise ValueError("derivative history has an empty active slot")
            values.append(value)
        return tuple(values)

    def append(self, value: PhaseVector) -> None:
        if self.count < HISTORY_CAPACITY:
            index = (self.start + self.count) % HISTORY_CAPACITY
            self.slots[index] = value
            self.count += 1
        else:
            self.slots[self.start] = value
            self.start = (self.start + 1) % HISTORY_CAPACITY
