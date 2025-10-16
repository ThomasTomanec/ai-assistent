# src/infrastructure/adapters/ai/models/circuit_state.py

"""Circuit Breaker State Model"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics"""
    state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    total_trips: int = 0

    def to_dict(self) -> dict:
        """Export as dict"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_trips': self.total_trips,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None
        }
