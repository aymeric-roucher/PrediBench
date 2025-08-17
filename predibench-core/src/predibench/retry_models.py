"""Retry-enabled model wrappers for smolagents."""

from typing import Any, Dict, List, Optional
from smolagents.models import ApiModel, InferenceClientModel, OpenAIModel, LiteLLMModel
from smolagents import ChatMessage
from predibench.retry_config import llm_retry
from predibench.logger_config import get_logger

logger = get_logger(__name__)


class RetryApiModel(ApiModel):
    """Wrapper for ApiModel with retry logic."""
    
    def __init__(self, wrapped_model: ApiModel):
        """Initialize with a wrapped model instance."""
        self.wrapped_model = wrapped_model
        # Copy attributes from wrapped model
        for attr_name in dir(wrapped_model):
            if not attr_name.startswith('_') and not callable(getattr(wrapped_model, attr_name)):
                setattr(self, attr_name, getattr(wrapped_model, attr_name))
    
    @property
    def model_id(self) -> str:
        """Return the model ID from the wrapped model."""
        return self.wrapped_model.model_id
    
    @llm_retry
    def __call__(
        self,
        messages: List[ChatMessage],
        stop_sequences: Optional[List[str]] = None,
        grammar: Optional[str] = None,
        **kwargs
    ) -> str:
        """Call the wrapped model with retry logic."""
        logger.debug(f"Calling model {self.model_id} with retry logic")
        return self.wrapped_model(messages, stop_sequences, grammar, **kwargs)


class RetryInferenceClientModel(RetryApiModel):
    """Retry-enabled wrapper for InferenceClientModel."""
    
    def __init__(self, model_id: str, **kwargs):
        """Initialize InferenceClientModel with retry logic."""
        wrapped_model = InferenceClientModel(model_id=model_id, **kwargs)
        super().__init__(wrapped_model)


class RetryOpenAIModel(RetryApiModel):
    """Retry-enabled wrapper for OpenAIModel."""
    
    def __init__(self, model_id: str, **kwargs):
        """Initialize OpenAIModel with retry logic."""
        wrapped_model = OpenAIModel(model_id=model_id, **kwargs)
        super().__init__(wrapped_model)


class RetryLiteLLMModel(RetryApiModel):
    """Retry-enabled wrapper for LiteLLMModel."""
    
    def __init__(self, model_id: str, **kwargs):
        """Initialize LiteLLMModel with retry logic."""
        wrapped_model = LiteLLMModel(model_id=model_id, **kwargs)
        super().__init__(wrapped_model)


def wrap_model_with_retry(model: ApiModel | str) -> ApiModel | str:
    """Wrap a model with retry logic if it's an ApiModel instance."""
    if isinstance(model, str):
        return model  # String models like "test_random" are handled differently
    elif isinstance(model, ApiModel):
        return RetryApiModel(model)
    else:
        logger.warning(f"Unknown model type: {type(model)}")
        return model