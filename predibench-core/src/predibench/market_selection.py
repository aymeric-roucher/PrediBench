import json
import textwrap
from datetime import date, datetime, timedelta

from smolagents import ChatMessage, LiteLLMModel

from predibench.common import OUTPUT_PATH
from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    Market,
    Event,
    MarketsRequestParameters,
    EventsRequestParameters,
)
from predibench.logger_config import get_logger

logger = get_logger(__name__)


def _remove_markets_without_prices_in_events(events: list[Event]) -> list[Event]:
    """Remove markets that have no prices"""
    filtered_events = []
    for event in events:
        market_filtered = [market for market in event.markets if market.prices is not None and len(market.prices) >= 1]
        event.markets = market_filtered
        if len(market_filtered) > 0:
            filtered_events.append(event)
    return filtered_events

def _filter_crypto_events(events: list[Event]) -> list[Event]:
    """Filter out events related to crypto by checking if 'bitcoin' or 'ethereum' is in the slug."""
    crypto_keywords = ["bitcoin", "ethereum"]
    filtered_events = []
    
    for event in events:
        slug_lower = event.slug.lower() if event.slug else ""
        is_crypto = any(keyword in slug_lower for keyword in crypto_keywords)
        
        if not is_crypto:
            filtered_events.append(event)
        else:
            logger.info(f"Filtered out crypto event: {event.title} (slug: {event.slug})")
    
    return filtered_events

def _filter_events_by_volume_and_markets(events: list[Event], min_volume: float = 1000, backward_mode: bool = False) -> list[Event]:
    """Filter events based on volume threshold and presence of markets."""
    filtered_events = []
    for event in events:
        if event.markets and len(event.markets) > 0:
            if backward_mode:
                # In backward mode, we can't rely on volume24hr as it may not be available for historical events
                # Just ensure events have markets
                filtered_events.append(event)
            elif event.volume24hr and event.volume24hr > min_volume:  # Minimum volume threshold
                filtered_events.append(event)
    return filtered_events

# TODO: add tenacity retry for the requests
# TODO: all of the parameters here should be threated as hyper parameters
def choose_events(today_date: datetime, time_until_ending: timedelta, n_events: int, key_for_filtering: str = "volume", min_volume: float = 1000, backward_mode: bool = False, filter_crypto_events: bool = True) -> list[Event]:
    """Pick top events by volume for investment for the current week
    
    backward_mode: if True, then events ending around this date will be selected, but those events are probably closed, we can't use the volume24hr to filter out the events that are open.
    """
    end_date = today_date + time_until_ending
    request_parameters = EventsRequestParameters(
        limit=500,
        order=key_for_filtering,
        ascending=False,
        end_date_min=today_date,
        end_date_max=end_date,
    )
    events = request_parameters.get_events()
    
    if filter_crypto_events:
        events = _filter_crypto_events(events)
    
    filtered_events = _filter_events_by_volume_and_markets(events=events, min_volume=min_volume, backward_mode=backward_mode)
    filtered_events = filtered_events[:n_events]
    
    
    for event in filtered_events:
        for market in event.markets:
            if backward_mode:
                market.fill_prices(
                    end_time=end_date
                )
            else:
                market.fill_prices()
    
    filtered_events = _remove_markets_without_prices_in_events(filtered_events)
    return filtered_events
