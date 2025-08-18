from datetime import timedelta, date
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
    max_events: int = typer.Option(10, help="Maximum number of events to analyze"),
    days_ahead: int = typer.Option(7*6, help="Days until event ending"),
    weeks_back: int = typer.Option(4, help="Number of weeks to go back for backward mode"),
):
    """Main script to run investment analysis with all models across past weeks."""

    all_results = []
    
    logger.info("Starting investment analysis with all models across past weeks")
    
    # Generate dates for the past 4 weeks, starting with the oldest
    dates_to_process = []
    for week_offset in range(weeks_back, 0, -1):  # Start from oldest (4 weeks back) to newest (1 week back)
        backward_date = date.today() - timedelta(weeks=week_offset)
        dates_to_process.append(backward_date)
    
    # Add today (no backward mode)
    dates_to_process.append(date.today())
    
    # Run for each date and each model
    for target_date in dates_to_process:
        is_today = target_date == date.today()
        backward_date = None if is_today else target_date
        
        logger.info(f"Processing date: {target_date} ({'today' if is_today else 'backward mode'})")
        
        for model_name, model in MODEL_MAP.items():
            logger.info(f"Running analysis for model: {model_name}")
            
            results = run_investments_for_today(
                time_until_ending=timedelta(days=days_ahead),
                max_n_events=max_events,
                models=[model],  # Run one model at a time
                output_path=DATA_PATH,
                backward_date=backward_date,
                dataset_name="charles-azam/predibench",
                split="test2",
            )
            
            all_results.extend(results)
            logger.info(f"Completed analysis for {model_name} on {target_date}")
            continue

    logger.info(f"All analyses completed. Total results: {len(all_results)}")


if __name__ == "__main__":
    app()