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
from predibench.polymarket_api import Event
from predibench.polymarket_data import load_events_from_file, save_events_to_file
from predibench.retry_models import InferenceClientModelWithRetry
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


def upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentResult], base_date: date, dataset_name: str = "m-ric/predibench-agent-choices", split: str = "train"
) -> None:
    """Upload investment results to the Hugging Face dataset."""
    # Load the existing dataset
    ds = load_dataset(dataset_name)

    # Prepare new data rows
    new_rows = []
    current_timestamp = datetime.now()

    for model_result in results_per_model:
        for event_result in model_result.event_results:
            # Map decision to choice value
            choice_mapping = {"BUY": 1, "SELL": 0, "NOTHING": -1}
            choice = choice_mapping.get(event_result.market_decision.decision, -1)

            row = {
                "agent_name": model_result.model_id,
                "date": base_date,
                "question": event_result.market_decision.market_question,
                "choice": choice,
                "choice_raw": event_result.market_decision.decision.lower(),
                "market_id": event_result.market_decision.market_id,
                "messages_count": 0,  # This would need to be tracked during agent execution
                "has_reasoning": event_result.market_decision.rationale is not None,
                "timestamp_uploaded": current_timestamp,
                "rationale": event_result.market_decision.rationale or "",
            }
            new_rows.append(row)

    if new_rows:
        # Create a new dataset with the new rows
        new_dataset = Dataset.from_list(new_rows)
        # Concatenate with existing dataset using datasets.concatenate_datasets

        # Check if split exists, if not use empty dataset
        try:
            existing_data = ds[split]
        except KeyError:
            existing_data = Dataset.from_list([])
        
        combined_dataset = concatenate_datasets([existing_data, new_dataset])

        # Push back to hub as a pull request (safer approach)
        combined_dataset.push_to_hub(
            dataset_name,
            split=split,
            token=os.getenv(ENV_VAR_HF_TOKEN),
        )

        logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")
    else:
        logger.warning("No data to upload to HF dataset")


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

    if backward_date is None:
        base_date = datetime.now(timezone.utc).date()
        backward_mode = False
    else:
        base_date = backward_date
        backward_mode = True

    logger.info("Using event-based investment approach")
    logger.info(f"Base date: {base_date}")
    logger.info(f"Backward mode: {backward_mode}")

    # Create output directory structure: output_path/date
    date_output_path = output_path / base_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    # Define cache file path within the date-specific output directory
    timestamp = get_timestamp_string()
    cache_file = date_output_path / f"events_cache_{timestamp}.json"

    if cache_file.exists() and load_from_cache:
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(file_path=cache_file)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            today_date=base_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events,
            backward_mode=backward_mode,
            filter_crypto_events=filter_crypto_events,
        )
        save_events_to_file(events=selected_events, file_path=cache_file)

    logger.info(f"Selected {len(selected_events)} events for analysis")
    for event in selected_events:
        logger.info(f"- {event.title} (Volume: ${event.volume:,.0f})")

    results_per_model = launch_agent_investments(
        models=models,
        events=selected_events,
        target_date=base_date,
        backward_mode=backward_mode,
        date_output_path=date_output_path,
    )

    # Upload results to Hugging Face dataset
    upload_results_to_hf_dataset(
        results_per_model=results_per_model, base_date=base_date, dataset_name=dataset_name, split=split
    )

    logger.info("Event-based investment analysis complete!")
    return results_per_model


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
