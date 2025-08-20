import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from smolagents.models import ApiModel

from predibench.agent.runner import ModelInvestmentResult, run_agent_investments
from predibench.common import DATA_PATH, ENV_VAR_HF_TOKEN
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_data import load_events_from_file
from predibench.retry_models import InferenceClientModelWithRetry
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


def run_investments_for_specific_date(
    models: list[ApiModel | str],
    max_n_events: int,
    output_path: Path,
    time_until_ending: timedelta,
    target_date: date,
    cache_file_path: Path | None = None,
    load_from_cache: bool = False,
    filter_crypto_events: bool = True,
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "test",
) -> list[ModelInvestmentResult]:
    """Run event-based investment simulation with multiple AI models."""
    logger.info(f"Running investment analysis for {target_date}")

    date_output_path = output_path / target_date.strftime("%Y-%m-%d")
    date_output_path.mkdir(parents=True, exist_ok=True)

    cache_file_path = (
        cache_file_path
        or date_output_path / f"events_cache_{get_timestamp_string()}.json"
    )

    if cache_file_path.exists() and load_from_cache:
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(cache_file_path)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            target_date=target_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events,
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
        target_date=target_date,
        date_output_path=date_output_path,
        dataset_name=dataset_name,
        split=split,
        hf_token_for_dataset=hf_token,
        timestamp_for_saving=timestamp,
    )

    logger.info("Investment analysis complete!")

    return results


if __name__ == "__main__":
    # Test with random model to verify new output format
    models = [
        InferenceClientModelWithRetry(model_id="openai/gpt-oss-120b"),
    ]

    results = run_investments_for_specific_date(
        time_until_ending=timedelta(days=7 * 6),
        max_n_events=2,  # Smaller number for testing
        models=models,
        output_path=DATA_PATH,
        target_date=date(2025, 8, 19),
    )
    
    # Print sample output to verify format
    if results:
        sample_result = results[0]
        print(f"\nSample output for model: {sample_result.model_id}")
        if sample_result.event_results:
            sample_event = sample_result.event_results[0]
            print(f"Event: {sample_event.event_title}")
            print(f"Number of market decisions: {len(sample_event.market_decisions)}")
            if sample_event.market_decisions:
                sample_market = sample_event.market_decisions[0]
                print(f"Sample market decision:")
                print(f"  Market: {sample_market.market_question}")
                print(f"  Probability assessment: {sample_market.probability_assessment}")
                print(f"  Market odds: {sample_market.market_odds}")
                print(f"  Confidence: {sample_market.confidence_in_assessment}")
                print(f"  Betting decision: {sample_market.betting_decision.direction}")
                print(f"  Amount: {sample_market.betting_decision.amount}")
                print(f"  Reasoning: {sample_market.betting_decision.reasoning}")
