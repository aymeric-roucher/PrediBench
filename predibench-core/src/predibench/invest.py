import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from datasets import Dataset, concatenate_datasets, load_dataset
from dotenv import load_dotenv
from smolagents.models import ApiModel

from predibench.agent import ModelInvestmentResult, launch_agent_investments
from predibench.common import DATA_PATH, ENV_VAR_HF_TOKEN
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file, save_events_to_file
from predibench.retry_models import InferenceClientModelWithRetry
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


def upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentResult], 
    base_date: date, 
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "train"
) -> None:
    """Upload investment results to the Hugging Face dataset."""
    choice_mapping = {"BUY": 1, "SELL": 0, "NOTHING": -1}
    timestamp = datetime.now()
    
    new_rows = [
        {
            "agent_name": model_result.model_id,
            "date": base_date,
            "question": event_result.market_decision.market_question,
            "choice": choice_mapping.get(event_result.market_decision.decision, -1),
            "choice_raw": event_result.market_decision.decision.lower(),
            "market_id": event_result.market_decision.market_id,
            "messages_count": 0,
            "has_reasoning": event_result.market_decision.rationale is not None,
            "timestamp_uploaded": timestamp,
            "rationale": event_result.market_decision.rationale or "",
        }
        for model_result in results_per_model
        for event_result in model_result.event_results
    ]
    
    if not new_rows:
        logger.warning("No data to upload to HF dataset")
        return
        
    ds = load_dataset(dataset_name)
    existing_data = ds.get(split, Dataset.from_list([]))
    
    combined_dataset = concatenate_datasets([existing_data, Dataset.from_list(new_rows)])
    combined_dataset.push_to_hub(dataset_name, split=split, token=os.getenv(ENV_VAR_HF_TOKEN))
    
    logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")


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
    
    logger.info(f"Running investment analysis for {base_date} (backward_mode: {backward_mode})")
    
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
    
    results = launch_agent_investments(
        models=models,
        events=selected_events,
        target_date=base_date,
        backward_mode=backward_mode,
        date_output_path=date_output_path,
    )
    
    upload_results_to_hf_dataset(results, base_date, dataset_name, split)
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
