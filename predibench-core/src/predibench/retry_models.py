from smolagents.models import ApiModel, InferenceClientModel, OpenAIModel, LiteLLMModel
from smolagents import ChatMessage, ChatMessageStreamDelta, Tool
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from typing import Generator
from predibench.logger_config import get_logger

logger = get_logger(__name__)


class InferenceClientModelWithRetry(InferenceClientModel):
    """InferenceClientModel with tenacity retry logic for rate limiting."""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> ChatMessage:
        try:
            return super().generate(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"Model generate failed: {e}. Retrying in 60 seconds...")
            raise e
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate_stream(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> Generator[ChatMessageStreamDelta]:
        try:
            return super().generate_stream(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"Model generate_stream failed: {e}. Retrying in 60 seconds...")
            raise e


class OpenAIModelWithRetry(OpenAIModel):
    """OpenAIModel with tenacity retry logic for rate limiting."""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> ChatMessage:
        try:
            return super().generate(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"OpenAI model generate failed: {e}. Retrying in 60 seconds...")
            raise e
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate_stream(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> Generator[ChatMessageStreamDelta]:
        try:
            return super().generate_stream(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"OpenAI model generate_stream failed: {e}. Retrying in 60 seconds...")
            raise e


class LiteLLMModelWithRetry(LiteLLMModel):
    """LiteLLMModel with tenacity retry logic for rate limiting."""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> ChatMessage:
        try:
            return super().generate(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"LiteLLM model generate failed: {e}. Retrying in 60 seconds...")
            raise e
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(61),
        retry=retry_if_exception_type((Exception,)),
    )
    def generate_stream(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        **kwargs,
    ) -> Generator[ChatMessageStreamDelta]:
        try:
            return super().generate_stream(
                messages=messages,
                stop_sequences=stop_sequences,
                response_format=response_format,
                tools_to_call_from=tools_to_call_from,
                **kwargs,
            )
        except Exception as e:
            logger.warning(f"LiteLLM model generate_stream failed: {e}. Retrying in 60 seconds...")
            raise e