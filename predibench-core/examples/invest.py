from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from predibench.agent import launch_agent_investments, launch_agent_event_investments
from predibench.pnl import compute_pnls, get_historical_returns
from predibench.common import OUTPUT_PATH
from predibench.utils import collect_investment_choices
from predibench.market_selection import choose_markets, choose_events
from predibench.polymarket_data import save_events_to_file, load_events_from_file
from predibench.logging import get_logger

load_dotenv()

logger = get_logger(__name__)


def run_event_based_investment(time_until_ending: timedelta, max_n_events: int, model_names: list[str], investment_dates: list[date], cache_file: Path | None = None) -> None:
    """Run event-based investment simulation with multiple AI models."""
    
    today_date=datetime.now(timezone.utc)
    logger.info("Using event-based investment approach")
    
    if cache_file is not None and cache_file.exists():
        logger.info("Loading events from cache")
        selected_events = load_events_from_file(cache_file)
    else:
        logger.info("Fetching events from API")
        selected_events = choose_events(
            today_date=today_date,
            time_until_ending=time_until_ending,
            n_events=max_n_events
        )
        save_events_to_file(selected_events, cache_file)
    
    logger.info(f"Selected {len(selected_events)} events for analysis")
    for event in selected_events:
        logger.info(f"- {event.title} (Volume: ${event.volume:,.0f})")
    
    # now you have to do the investment agent for each event, think about the database and compute the pnl
    # you must also implement a mechanism to have more datapoints (backward compatiblities)
    # then frontend backend and deployment
    launch_agent_event_investments(
        list_models=model_names,
        investment_dates=investment_dates,
        events=selected_events
    )
    
    logger.info("Event-based investment analysis complete!")
    # TODO: Implement PnL calculation for event-based investments


def run_market_based_investment(end_date: date, n_events: int, model_names: list[str], investment_dates: list[date]) -> None:
    """Run legacy market-based investment simulation with multiple AI models."""
    logger.info("Using legacy market-based investment approach") 
    
    selected_markets = choose_markets(
        today_date=end_date, 
        n_markets=n_events  # Use n_events for backward compatibility
    )
    returns_df, prices_data = get_historical_returns(markets=selected_markets)

    launch_agent_investments(
        list_models=model_names,
        investment_dates=investment_dates,
        prices_df=prices_data,
        markets=selected_markets,
    )

    positions_data = collect_investment_choices(output_path=OUTPUT_PATH)
    final_pnl_results, cumulative_pnl_results, visualization_figures = compute_pnls(
        investment_dates=investment_dates, positions_df=positions_data
    )

    logger.info("Final PnL per agent:")
    logger.info(final_pnl_results)




if __name__ == "__main__":
    run_market_based_investment(end_date=date(2025, 8, 1), n_events=3, model_names=["test_random"], investment_dates=[date(2025, 7, 25), date(2025, 8, 1)])
    run_event_based_investment(time_until_ending=timedelta(days=21), max_n_events=3, model_names=["test_random"], investment_dates=[date(2025, 7, 25), date(2025, 8, 1)])
