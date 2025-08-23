from typing import Generator, Type, TypeVar

from smolagents import ChatMessage, ChatMessageStreamDelta, Tool
from smolagents.models import ApiModel, InferenceClientModel, LiteLLMModel, OpenAIModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
    after_log,
)

from predibench.logger_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=ApiModel)


def add_retry_logic(base_class: Type[T]) -> Type[T]:
    """Factory function to add retry logic to any ApiModel class."""

    class ModelWithRetry(base_class):
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_fixed(61),
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
            before_sleep=before_sleep_log(logger, "INFO"),
            after=after_log(logger, "INFO"),
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
            retry=retry_if_exception_type((Exception,)),
            reraise=True,
            before_sleep=before_sleep_log(logger, "INFO"),
            after=after_log(logger, "INFO"),
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
