from datetime import timedelta
import os
import typer
from predibench.invest import run_investments_for_today
from predibench.retry_models import InferenceClientModelWithRetry, OpenAIModelWithRetry
from predibench.common import DATA_PATH, ENV_VAR_HF_TOKEN
from predibench.logger_config import get_logger

logger = get_logger(__name__)

app = typer.Typer()

MODEL_MAP = {
    "openai/gpt-5": OpenAIModelWithRetry(model_id="gpt-5"),
    "openai/gpt-5-mini": OpenAIModelWithRetry(model_id="gpt-5-mini"),
    "huggingface/openai/gpt-oss-120b": InferenceClientModelWithRetry(
        model_id="openai/gpt-oss-120b", token=os.getenv(ENV_VAR_HF_TOKEN)
    ),
    "huggingface/openai/gpt-oss-20b": InferenceClientModelWithRetry(
        model_id="openai/gpt-oss-20b", token=os.getenv(ENV_VAR_HF_TOKEN)
    ),
    "huggingface/Qwen/Qwen3-235B-A22B-Thinking-2507": InferenceClientModelWithRetry(
        model_id="Qwen/Qwen3-235B-A22B-Thinking-2507", token=os.getenv(ENV_VAR_HF_TOKEN)
    ),
    "huggingface/deepseek-ai/DeepSeek-R1-0528": InferenceClientModelWithRetry(
        model_id="deepseek-ai/DeepSeek-R1-0528", token=os.getenv(ENV_VAR_HF_TOKEN)
    ),
}


@app.command()
def main(
    model_name: str = typer.Argument(..., help="Name of the model to run"),
    max_events: int = typer.Option(10, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7*6, help="Days until event ending"),
):
    """Main script to run investment analysis with a single model."""

    if model_name == "all":
        models = list(MODEL_MAP.values())
    elif model_name == "huggingface":
        models = [
            model
            for model_name, model in MODEL_MAP.items()
            if model_name.startswith("huggingface")
        ]
    elif model_name == "openai":
        models = [
            model
            for model_name_key, model in MODEL_MAP.items()
            if model_name_key.startswith("openai")
        ]
    elif model_name in MODEL_MAP:
        models = [MODEL_MAP[model_name]]
    else:
        available_models = ", ".join(
            list(MODEL_MAP.keys()) + ["all", "huggingface", "openai"]
        )
        typer.echo(
            f"Error: Model '{model_name}' not found. Available models: {available_models}"
        )
        raise typer.Exit(1)

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
