import time
from typing import Dict


class CircuitOpenException(Exception):
    def __init__(self, service_name: str, retry_after_sec: int):
        self.service_name = service_name
        self.retry_after_sec = retry_after_sec
        super().__init__(f"Circuit breaker for {service_name} is OPEN. Try again in {retry_after_sec}s.")


class CircuitBreaker:
    """In-memory stateful circuit breaker implementing Closed, Open, and Half-Open states."""
    def __init__(self, failure_threshold: int = 3, recovery_time_sec: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.consecutive_failures = 0
        self.last_failure_time = 0.0

    def before_call(self, service_name: str):
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.recovery_time_sec:
                self.state = "HALF-OPEN"
            else:
                remaining = int(self.recovery_time_sec - (now - self.last_failure_time))
                raise CircuitOpenException(service_name, max(1, remaining))

    def record_success(self):
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"


# Global registry for service circuit breakers
_circuit_registry: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    if service_name not in _circuit_registry:
        _circuit_registry[service_name] = CircuitBreaker()
    return _circuit_registry[service_name]
