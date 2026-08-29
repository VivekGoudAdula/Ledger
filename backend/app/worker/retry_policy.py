"""Retry Policy Engine.

Defines bounded retry policy with exponential backoff and error classification (RETRYABLE vs NON_RETRYABLE).
"""

from typing import Type
import math


class RetryPolicy:
    """Bounded retry policy governing worker task re-execution."""

    NON_RETRYABLE_EXCEPTIONS: tuple[Type[BaseException], ...] = (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        IndexError,
    )

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 10.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        if base_delay_seconds < 0.0 or max_delay_seconds < 0.0:
            raise ValueError("Retry delays cannot be negative.")

        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    def is_retryable(self, exception: Exception) -> bool:
        """Classify exception as RETRYABLE or NON_RETRYABLE."""
        if isinstance(exception, self.NON_RETRYABLE_EXCEPTIONS):
            return False
        return True

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if task execution should be retried for attempt count."""
        if attempt >= self.max_attempts:
            return False
        return self.is_retryable(exception)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay in seconds for current attempt."""
        if attempt < 1:
            return self.base_delay_seconds
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(self.max_delay_seconds, float(delay))
