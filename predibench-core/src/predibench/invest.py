import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from datasets import Dataset, concatenate_datasets, load_dataset
from dotenv import load_dotenv
from smolagents.models import ApiModel

from predibench.agent.runner import ModelInvestmentResult, run_agent_investments
from predibench.common import DATA_PATH, ENV_VAR_HF_TOKEN
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file, save_events_to_file
from predibench.retry_models import InferenceClientModelWithRetry
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


def run_investments_for_today(
    time_until_ending: timedelta,
    max_n_events: int,
    models: list[ApiModel | str],
    output_path: Path,
    backward_date: date | None = None,
    load_from_cache: bool = False,
    filter_crypto_events: bool = True,
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "train",
) -> list[ModelInvestmentResult]:
    """Run event-based investment simulation with multiple AI models."""
    base_date = backward_date or datetime.now(timezone.utc).date()
    backward_mode = backward_date is not None

    logger.info(
        f"Running investment analysis for {base_date} (backward_mode: {backward_mode})"
    )

    date_output_path = output_path / base_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    cache_file = date_output_path / f"events_cache_{get_timestamp_string()}.json"

    if cache_file.exists() and load_from_cache:
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(cache_file)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            today_date=base_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events,
            backward_mode=backward_mode,
            filter_crypto_events=filter_crypto_events,
        )
        save_events_to_file(selected_events, cache_file)

    logger.info(f"Selected {len(selected_events)} events:")
    for event in selected_events:
        logger.info(f"  - {event.title} (Volume: ${event.volume:,.0f})")

    timestamp = get_timestamp_string()
    hf_token = os.getenv(ENV_VAR_HF_TOKEN)
    
    results = run_agent_investments(
        models=models,
        events=selected_events,
        target_date=base_date,
        backward_mode=backward_mode,
        date_output_path=date_output_path,
        dataset_name=dataset_name,
        split=split,
        hf_token_for_dataset=hf_token,
        timestamp_for_saving=timestamp,
    )

    logger.info("Investment analysis complete!")

    return results


if __name__ == "__main__":
    models = [
        InferenceClientModelWithRetry(model_id="openai/gpt-oss-120b"),
        "o3-deep-research",
    ]

    run_investments_for_today(
        time_until_ending=timedelta(days=7 * 6),
        max_n_events=20,
        models=models,
        output_path=DATA_PATH,
    )
