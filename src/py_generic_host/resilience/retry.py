import logging

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_cause_type,
    stop_after_attempt,
    wait_exponential_jitter,
)


# 重试这个部分可以再根据场景做得更精细一些
def default_retry(
        exc_types = (Exception, ),
        attempts: int = 5,
):
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=0.2, max=10),
        retry=retry_if_exception_cause_type(exc_types),
        before_sleep=before_sleep_log(logging.getLogger("Retry"), logging.WARNING),
    )

