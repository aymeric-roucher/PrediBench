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
from predibench.polymarket_api import EventsRequestParameters
from predibench.polymarket_data import load_events_from_file
from predibench.retry_models import InferenceClientModelWithRetry
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


def run_investments_for_specific_events(
    models: list[ApiModel | str],
    event_ids: list[str],
    selected_market_ids: dict[str, str],
    output_path: Path,
    target_date: date | None = None,
    backward_mode: bool = False,
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "test",
) -> list[ModelInvestmentResult]:
    """Run event-based investment simulation for specific events by fetching fresh data.
    
    Args:
        models: List of AI models to use for investment decisions
        event_ids: List of specific event IDs to analyze
        selected_market_ids: Dictionary mapping event_id -> market_id for pre-selected markets
        output_path: Directory to save results
        target_date: Date for the analysis (defaults to today)
        backward_mode: Whether to run in backward mode for historical analysis
        dataset_name: HuggingFace dataset name for agent choices
        split: Dataset split to use
        
    Returns:
        List of investment results for each model
    """
    base_date = target_date or datetime.now(timezone.utc).date()
    
    logger.info(
        f"Running investment analysis for specific events on {base_date} (backward_mode: {backward_mode})"
    )
    logger.info(f"Event IDs: {event_ids}")
    
    date_output_path = output_path / base_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    # Fetch fresh event data from API
    selected_events = []
    for event_id in event_ids:
        try:
            # Fetch event data using EventsRequestParameters
            event_request = EventsRequestParameters(id=int(event_id))
            events = event_request.get_events()
            
            if not events:
                logger.warning(f"No event found for ID: {event_id}")
                continue
                
            event = events[0]  # Should only be one event for specific ID
            
            # Set the selected market ID if provided
            if event_id in selected_market_ids:
                event.selected_market_id = selected_market_ids[event_id]
            else:
                # If no market specified, select the first available market
                if event.markets:
                    event.selected_market_id = event.markets[0].id
                    logger.info(f"Auto-selected market {event.markets[0].id} for event {event_id}")
                else:
                    logger.warning(f"No markets available for event {event_id}")
                    continue
            
            # Fill prices for all markets in the event
            for market in event.markets:
                if backward_mode:
                    # For backward mode, fetch prices up to the target date
                    end_time = datetime.combine(base_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                    market.fill_prices(end_time=end_time)
                else:
                    # For forward mode, fetch current prices
                    market.fill_prices()
            
            # Only include events that have markets with prices
            markets_with_prices = [
                market for market in event.markets 
                if market.prices is not None and len(market.prices) >= 1
            ]
            
            if markets_with_prices:
                event.markets = markets_with_prices
                selected_events.append(event)
                logger.info(f"Successfully loaded event: {event.title} (Volume: ${event.volume:,.0f})")
            else:
                logger.warning(f"No markets with prices found for event {event_id}: {event.title}")
                
        except Exception as e:
            logger.error(f"Failed to fetch data for event {event_id}: {str(e)}")
            continue

    if not selected_events:
        logger.error("No valid events with market data found")
        return []

    logger.info(f"Successfully loaded {len(selected_events)} events with market data")

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


def run_investments_for_today(
    models: list[ApiModel | str],
    max_n_events: int,
    output_path: Path,
    event_selection_window: timedelta,
    backward_date: date | None = None,
    cache_file_path: Path | None = None,
    load_from_cache: bool = False,
    filter_crypto_events: bool = True,
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "test",
) -> list[ModelInvestmentResult]:
    """Run event-based investment simulation with multiple AI models."""
    base_date = backward_date or datetime.now(timezone.utc).date()
    backward_mode = backward_date is not None

    logger.info(
        f"Running investment analysis for {base_date} (backward_mode: {backward_mode})"
    )

    date_output_path = output_path / base_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    cache_file_path = cache_file_path or date_output_path / f"events_cache_{get_timestamp_string()}.json"

    if cache_file_path.exists() and load_from_cache:
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(cache_file_path)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            today_date=base_date,
            event_selection_window=event_selection_window,
            n_events=max_n_events,
            backward_mode=backward_mode,
            filter_crypto_events=filter_crypto_events,
            save_path=cache_file_path,
        )

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
    ]

    # Example usage of run_investments_for_today
    run_investments_for_today(
        event_selection_window=timedelta(days=7 * 6),
        max_n_events=5,
        models=models,
        output_path=DATA_PATH,
    )
    
    # Example usage of run_investments_for_specific_events
    # Uncomment and modify the lines below to test specific events:
    # event_ids = ["123456", "789012"]  # Replace with actual event IDs
    # selected_market_ids = {"123456": "market_id_1", "789012": "market_id_2"}  # Optional: specify market IDs
    # run_investments_for_specific_events(
    #     models=models,
    #     event_ids=event_ids,
    #     selected_market_ids=selected_market_ids,
    #     output_path=DATA_PATH,
    #     target_date=date.today(),
    #     backward_mode=False,
    # )
