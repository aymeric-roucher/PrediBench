from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from predibench.agent import launch_agent_investments
from predibench.market_selection import choose_events
from predibench.polymarket_data import save_events_to_file, load_events_from_file
from predibench.logger_config import get_logger
from smolagents.models import ApiModel, InferenceClientModel, OpenAIModel
from predibench.polymarket_api import Event

load_dotenv()

logger = get_logger(__name__)


def select_markets_for_events(events: list[Event]) -> list[Event]:
    """Select the market with highest volume1wk that has outcomes[0] price between 0.05 and 0.95."""
    events_with_selected_markets = []
    for event in events:
        if event.selected_market_id is not None:
            raise ValueError(f"Event '{event.title}' already has a selected market")
        
        eligible_markets = []
        for market in event.markets:
            if (market.volume1wk is not None and 
                market.outcomes and 
                len(market.outcomes) > 0 and
                0.05 < market.outcomes[0].price < 0.95):
                eligible_markets.append(market)
        
        if eligible_markets:
            best_market = max(eligible_markets, key=lambda m: m.volume1wk)
            event.selected_market_id = best_market.id
            events_with_selected_markets.append(event)

    return events_with_selected_markets

def run_investments_for_today(
    time_until_ending: timedelta, 
    max_n_events: int, 
    models: list[ApiModel | str], 
    output_path: Path,
    backward_date: date | None = None,
    load_from_cache: bool = False,
) -> None:
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
    cache_file = date_output_path / "events_cache.json"
    
    if cache_file.exists() and load_from_cache:
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(file_path=cache_file)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            today_date=base_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events,
            backward_mode=backward_mode
        )
        save_events_to_file(events=selected_events, file_path=cache_file)
            
    logger.info(f"Selected {len(selected_events)} events for analysis")
    for event in selected_events:
        logger.info(f"- {event.title} (Volume: ${event.volume:,.0f})")
        
    loaded_events = load_events_from_file(file_path=cache_file)
    
    events_with_selected_markets = select_markets_for_events(selected_events)
    
    results_per_model = launch_agent_investments(
        models=models,
        events=events_with_selected_markets,
        date_output_path=date_output_path
    )
    
    logger.info("Event-based investment analysis complete!")
    # TODO: Implement PnL calculation for event-based investments



def compute_pnl_between_dates_for_model(model_name: str, start_date: date, end_date: date) -> float:
    pass

if __name__ == "__main__":
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]

    run_investments_for_today(
        time_until_ending=timedelta(days=21), 
        max_n_events=3, 
        models=models, 
        output_path=Path("data"),
    )
