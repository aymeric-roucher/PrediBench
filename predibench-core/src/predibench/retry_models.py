import logging
from typing import Generator, Type, TypeVar

from smolagents import ChatMessage, ChatMessageStreamDelta, Tool
from smolagents.models import ApiModel, InferenceClientModel, LiteLLMModel, OpenAIModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
    after_log,
)

from predibench.logger_config import get_logger

import openai
import litellm


def is_rate_limit_error(exception: Exception) -> bool:
    """Check if an exception is a rate limit error from any provider."""
    # Check specific rate limit errors
    if isinstance(exception, (openai.RateLimitError, litellm.RateLimitError)):
        return True
    
    # Check for common rate limit messages in exception strings
    error_message = str(exception).lower()
    rate_limit_indicators = [
        'rate limit', 'rate_limit', 'too many requests', 
        'quota exceeded', 'throttled', '429'
    ]
    
    return any(indicator in error_message for indicator in rate_limit_indicators)

logger = get_logger(__name__)

T = TypeVar("T", bound=ApiModel)


def add_retry_logic(base_class: Type[T]) -> Type[T]:
    """Factory function to add retry logic to any ApiModel class."""

    class ModelWithRetry(base_class):
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_fixed(61),
            retry=is_rate_limit_error,
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.INFO),
            after=after_log(logger, logging.INFO),
        )
        def generate(
            self,
            messages: list[ChatMessage | dict],
            stop_sequences: list[str] | None = None,
            response_format: dict[str, str] | None = None,
            tools_to_call_from: list[Tool] | None = None,
            **kwargs,
        ) -> ChatMessage:
            return super().generate(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_fixed(61),
            retry=is_rate_limit_error,
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.INFO),
            after=after_log(logger, logging.INFO),
        )
        def generate_stream(
            self,
            messages: list[ChatMessage | dict],
            stop_sequences: list[str] | None = None,
            response_format: dict[str, str] | None = None,
            tools_to_call_from: list[Tool] | None = None,
            **kwargs,
        ) -> Generator[ChatMessageStreamDelta, None, None]:
            return super().generate_stream(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )

    ModelWithRetry.__name__ = f"{base_class.__name__}WithRetry"
    ModelWithRetry.__doc__ = (
        f"{base_class.__name__} with tenacity retry logic for rate limiting."
    )

    return ModelWithRetry


InferenceClientModelWithRetry = add_retry_logic(InferenceClientModel)
OpenAIModelWithRetry = add_retry_logic(OpenAIModel)
LiteLLMModelWithRetry = add_retry_logic(LiteLLMModel)
