"""
Simulation clock with shift tracking and event scheduling.
"""

from datetime import datetime, timedelta, timezone

from simulator.config import Shift, SHIFT_DURATION


class SimulationClock:
    """Monotonic simulation clock with 1-second resolution."""

    def __init__(self, start_time: datetime | None = None):
        self.start_time = start_time or datetime(2025, 6, 15, 6, 0, 0,
                                                  tzinfo=timezone.utc)
        self.tick: int = 0
        self._current_time = self.start_time

    def advance(self) -> None:
        """Advance the clock by one tick (1 second)."""
        self.tick += 1
        self._current_time = self.start_time + timedelta(seconds=self.tick)

    @property
    def current_time(self) -> datetime:
        return self._current_time

    @property
    def timestamp(self) -> str:
        return self._current_time.isoformat()

    @property
    def elapsed_seconds(self) -> int:
        return self.tick

    @property
    def current_shift(self) -> Shift:
        """Determine current shift based on hour of day."""
        hour = self._current_time.hour
        if 6 <= hour < 18:
            return Shift.DAY
        return Shift.NIGHT

    @property
    def shift_elapsed(self) -> int:
        """Seconds elapsed in current shift."""
        hour = self._current_time.hour
        minute = self._current_time.minute
        second = self._current_time.second
        if hour >= 18:
            return (hour - 18) * 3600 + minute * 60 + second
        elif hour >= 6:
            return (hour - 6) * 3600 + minute * 60 + second
        else:
            return (hour + 6) * 3600 + minute * 60 + second

    def is_shift_change(self) -> bool:
        """Returns True if we're at a shift boundary."""
        hour = self._current_time.hour
        minute = self._current_time.minute
        second = self._current_time.second
        return (hour in (6, 18)) and minute == 0 and second == 0

    @property
    def time_of_day_factor(self) -> float:
        """Returns 0.0 at midnight, 1.0 at noon for diurnal effects."""
        hour = self._current_time.hour + self._current_time.minute / 60.0
        import math
        return 0.5 + 0.5 * math.sin(math.pi * (hour - 6) / 12.0)
