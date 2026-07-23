import pytest

from py_generic_host.resilience.retry import default_retry


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    @default_retry(exc_types=(ValueError,), attempts=3)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("retry me")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3