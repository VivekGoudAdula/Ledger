"""Unit Tests for RetryPolicy.

Validates error classification (RETRYABLE vs NON_RETRYABLE), attempt limits, and exponential backoff.
"""

import pytest

from app.worker.retry_policy import RetryPolicy


def test_retry_policy_error_classification():
    policy = RetryPolicy(max_attempts=3)

    # Non-retryable errors
    assert policy.is_retryable(ValueError("Invalid format")) is False
    assert policy.is_retryable(TypeError("Type mismatch")) is False
    assert policy.is_retryable(KeyError("Missing key")) is False

    # Retryable errors
    assert policy.is_retryable(TimeoutError("Connection timed out")) is True
    assert policy.is_retryable(ConnectionError("Network disconnected")) is True


def test_retry_policy_should_retry():
    policy = RetryPolicy(max_attempts=3)
    err = TimeoutError("Transient failure")

    assert policy.should_retry(err, attempt=1) is True
    assert policy.should_retry(err, attempt=2) is True
    assert policy.should_retry(err, attempt=3) is False  # Max attempts reached!


def test_retry_policy_exponential_backoff_calculation():
    policy = RetryPolicy(base_delay_seconds=1.0, max_delay_seconds=5.0)

    assert policy.calculate_delay(attempt=1) == 1.0
    assert policy.calculate_delay(attempt=2) == 2.0
    assert policy.calculate_delay(attempt=3) == 4.0
    assert policy.calculate_delay(attempt=4) == 5.0  # Capped at max_delay_seconds (5.0)!
