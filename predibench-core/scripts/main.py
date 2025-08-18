from datetime import timedelta

import typer
from predibench.invest import run_investments_for_today
from predibench.retry_models import InferenceClientModelWithRetry, OpenAIModelWithRetry
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger

logger = get_logger(__name__)

app = typer.Typer()

MODEL_MAP = {
    "huggingface/openai/gpt-oss-120b": InferenceClientModelWithRetry(model_id="openai/gpt-oss-120b"),
    "huggingface/openai/gpt-oss-20b": InferenceClientModelWithRetry(model_id="openai/gpt-oss-20b"),
    "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507": InferenceClientModelWithRetry(model_id="Qwen/Qwen3-30B-A3B-Instruct-2507"),
    "huggingface/deepseek-ai/DeepSeek-R1-0528": InferenceClientModelWithRetry(model_id="deepseek-ai/DeepSeek-R1-0528"),
    "huggingface/Qwen/Qwen3-4B-Thinking-2507": InferenceClientModelWithRetry(model_id="Qwen/Qwen3-4B-Thinking-2507"),
    "gpt-4.1": OpenAIModelWithRetry(model_id="gpt-4.1"),
    "gpt-4o": OpenAIModelWithRetry(model_id="gpt-4o"),
    "gpt-4.1-mini": OpenAIModelWithRetry(model_id="gpt-4.1-mini"),
    "o4-mini": OpenAIModelWithRetry(model_id="o4-mini"),
    "gpt-5": OpenAIModelWithRetry(model_id="gpt-5"),
    "gpt-5-mini": OpenAIModelWithRetry(model_id="gpt-5-mini"),
    "o3-deep-research": OpenAIModelWithRetry(model_id="o3-deep-research"),
    "test_random": "test_random",
}

@app.command()
def main(
    model_name: str = typer.Argument(..., help="Name of the model to run"),
    max_events: int = typer.Option(5, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(21, help="Days until event ending"),
):
    """Main script to run investment analysis with a single model."""
    
    if model_name not in MODEL_MAP:
        available_models = ", ".join(MODEL_MAP.keys())
        typer.echo(f"Error: Model '{model_name}' not found. Available models: {available_models}")
        raise typer.Exit(1)
    
    model = MODEL_MAP[model_name]
    models = [model]
    
    logger.info(f"Starting investment analysis with model: {model_name}")
    
    results = run_investments_for_today(
        time_until_ending=timedelta(days=days_ahead), 
        max_n_events=max_events, 
        models=models, 
        output_path=DATA_PATH,
    )
    
    logger.info(f"Analysis completed. Results: {results}")

if __name__ == "__main__":
    app()