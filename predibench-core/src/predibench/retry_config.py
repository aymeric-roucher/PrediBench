"""Global retry configuration for PrediBench using tenacity."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging
import requests
from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError

# Global retry configuration variables
RETRY_MAX_ATTEMPTS = 5
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 60
RETRY_EXPONENTIAL_MULTIPLIER = 2

# Logger for retry operations
retry_logger = logging.getLogger("predibench.retry")


def create_http_retry_decorator():
    """Create a retry decorator for HTTP requests (Polymarket API, Search APIs)."""
    return retry(
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_EXPONENTIAL_MULTIPLIER,
            min=RETRY_MIN_WAIT_SECONDS,
            max=RETRY_MAX_WAIT_SECONDS
        ),
        retry=retry_if_exception_type((
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        )),
        before_sleep=before_sleep_log(retry_logger, logging.WARNING),
        reraise=True,
    )


def create_llm_retry_decorator():
    """Create a retry decorator for LLM API calls (OpenAI, LiteLLM, etc.)."""
    return retry(
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_EXPONENTIAL_MULTIPLIER,
            min=RETRY_MIN_WAIT_SECONDS,
            max=RETRY_MAX_WAIT_SECONDS
        ),
        retry=retry_if_exception_type((
            RateLimitError,
            APIError,
            APIConnectionError,
            APITimeoutError,
            Exception,  # Catch all exceptions for now, can be more specific later
        )),
        before_sleep=before_sleep_log(retry_logger, logging.WARNING),
        reraise=True,
    )


# Pre-configured decorators for easy use
http_retry = create_http_retry_decorator()
llm_retry = create_llm_retry_decorator()