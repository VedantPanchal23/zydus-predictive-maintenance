import pytest

from common.reliability import retry_call


def test_retry_call_retries_until_success():
    attempts = {"count": 0}

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("transient failure")
        return "ok"

    result = retry_call(
        flaky_operation,
        retries=3,
        initial_delay=0.01,
        retry_exceptions=(ValueError,),
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_call_raises_after_final_attempt():
    def always_fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        retry_call(
            always_fail,
            retries=2,
            initial_delay=0.01,
            retry_exceptions=(RuntimeError,),
        )
