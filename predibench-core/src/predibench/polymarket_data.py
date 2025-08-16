import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from predibench.common import OUTPUT_PATH
from predibench.polymarket_api import Event, Market, MarketOutcome
from predibench.logger_config import get_logger

logger = get_logger(__name__)

# Create cache directory if it doesn't exist
CACHE_PATH = OUTPUT_PATH / "cache"
CACHE_PATH.mkdir(parents=True, exist_ok=True)


def market_to_dict(market: Market) -> dict[str, Any]:
    """Convert a Market object to a dictionary for JSON serialization."""
    market_dict = market.model_dump()
    
    # Handle datetime serialization
    if market_dict.get('end_date'):
        market_dict['end_date'] = market_dict['end_date'].isoformat()
    if market_dict.get('createdAt'):
        market_dict['createdAt'] = market_dict['createdAt'].isoformat()
    
    # Serialize pandas Series to JSON-compatible format
    if market_dict.get('prices') is not None and isinstance(market_dict['prices'], pd.Series):
        series = market_dict['prices']
        # Convert index to datetime first to ensure consistent serialization
        if not isinstance(series.index, pd.DatetimeIndex):
            series = series.copy()
            series.index = pd.to_datetime(series.index)
        
        market_dict['prices'] = {
            'values': series.values.tolist(),
            'index': [idx.isoformat() for idx in series.index],
            'name': series.name
        }
    
    return market_dict


def market_from_dict(market_data: dict[str, Any]) -> Market:
    """Convert a dictionary back to a Market object."""
    # Handle datetime deserialization
    if market_data.get('end_date'):
        market_data['end_date'] = datetime.fromisoformat(market_data['end_date'])
    if market_data.get('createdAt'):
        market_data['createdAt'] = datetime.fromisoformat(market_data['createdAt'])
    
    # Convert outcomes
    outcomes = []
    for outcome_data in market_data.get('outcomes', []):
        outcomes.append(MarketOutcome(**outcome_data))
    market_data['outcomes'] = outcomes
    
    # Deserialize pandas Series from JSON-compatible format
    if market_data.get('prices') is not None and isinstance(market_data['prices'], dict):
        prices_data = market_data['prices']
        # Always deserialize as DatetimeIndex for consistency
        index = pd.to_datetime(prices_data['index'])
        market_data['prices'] = pd.Series(
            data=prices_data['values'],
            index=index,
            name=prices_data.get('name')
        )
    elif market_data.get('prices') is None:
        market_data['prices'] = None
    
    return Market(**market_data)


def event_to_dict(event: Event) -> dict[str, Any]:
    """Convert an Event object to a dictionary for JSON serialization."""
    event_dict = event.model_dump()
    
    # Handle datetime serialization
    if event_dict.get('start_date'):
        event_dict['start_date'] = event_dict['start_date'].isoformat()
    if event_dict.get('end_date'):
        event_dict['end_date'] = event_dict['end_date'].isoformat()
    if event_dict.get('createdAt'):
        event_dict['createdAt'] = event_dict['createdAt'].isoformat()
    
    # Handle markets using the market_to_dict function
    event_dict['markets'] = [market_to_dict(market) for market in event.markets]
    
    return event_dict


def event_from_dict(event_data: dict[str, Any]) -> Event:
    """Convert a dictionary back to an Event object."""
    # Handle datetime deserialization
    if event_data.get('start_date'):
        event_data['start_date'] = datetime.fromisoformat(event_data['start_date'])
    if event_data.get('end_date'):
        event_data['end_date'] = datetime.fromisoformat(event_data['end_date'])
    if event_data.get('createdAt'):
        event_data['createdAt'] = datetime.fromisoformat(event_data['createdAt'])
    
    # Handle markets using the market_from_dict function
    markets = []
    for market_data in event_data.get('markets', []):
        markets.append(market_from_dict(market_data))
    event_data['markets'] = markets
    
    return Event(**event_data)


def save_events_to_file(events: list[Event], file_path: Path | None = None) -> None:
    """Save a list of Event objects to a JSON file."""
    if file_path is None:
        file_path = CACHE_PATH / "selected_events.json"
    
    # Use the event_to_dict function for each event
    events_data = [event_to_dict(event) for event in events]
    
    with open(file_path, 'w') as f:
        json.dump(events_data, f, indent=2)
    
    logger.info(f"Saved {len(events)} events to cache: {file_path}")


def load_events_from_file(file_path: Path | None = None) -> list[Event]:
    """Load a list of Event objects from a JSON file."""
    
    if not file_path.exists():
        raise FileNotFoundError(f"Cache file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        events_data = json.load(f)
    
    # Use the event_from_dict function for each event
    events = [event_from_dict(event_data) for event_data in events_data]
    
    logger.info(f"Loaded {len(events)} events from cache: {file_path}")
    return events