import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from predibench.logger_config import get_logger
from predibench.polymarket_api import Event, Market, MarketOutcome
from predibench.storage_utils import read_from_storage, write_to_storage

logger = get_logger(__name__)


def market_to_dict(market: Market) -> dict[str, Any]:
    """Convert a Market object to a dictionary for JSON serialization."""
    market_dict = market.model_dump()

    # Handle datetime serialization
    if market_dict.get("end_datetime"):
        market_dict["end_datetime"] = market_dict["end_datetime"].isoformat()
    market_dict["creation_datetime"] = market_dict["creation_datetime"].isoformat()

    # Serialize pandas Series to JSON-compatible format
    if market_dict.get("prices") is not None and isinstance(
        market_dict["prices"], pd.Series
    ):
        series = market_dict["prices"]
        # Convert index to datetime first to ensure consistent serialization
        if not isinstance(series.index, pd.DatetimeIndex):
            series = series.copy()
            series.index = pd.to_datetime(series.index)

        market_dict["prices"] = {
            "values": series.values.tolist(),
            "index": [idx.isoformat() for idx in series.index],
            "name": series.name,
        }

    return market_dict


def market_from_dict(market_data: dict[str, Any]) -> Market:
    """Convert a dictionary back to a Market object."""
    # Handle datetime deserialization
    if market_data.get("end_datetime"):
        market_data["end_datetime"] = datetime.fromisoformat(
            market_data["end_datetime"]
        )
    market_data["creation_datetime"] = datetime.fromisoformat(
        market_data["creation_datetime"]
    )

    # Convert outcomes
    outcomes = []
    for outcome_data in market_data.get("outcomes", []):
        outcomes.append(MarketOutcome(**outcome_data))
    market_data["outcomes"] = outcomes

    # Deserialize pandas Series from JSON-compatible format
    if market_data.get("prices") is not None and isinstance(
        market_data["prices"], dict
    ):
        prices_data = market_data["prices"]
        # Always deserialize as DatetimeIndex for consistency
        index = pd.to_datetime(prices_data["index"])
        market_data["prices"] = pd.Series(
            data=prices_data["values"], index=index, name=prices_data.get("name")
        )
    elif market_data.get("prices") is None:
        market_data["prices"] = None

    return Market(**market_data)


def event_to_dict(event: Event) -> dict[str, Any]:
    """Convert an Event object to a dictionary for JSON serialization."""
    event_dict = event.model_dump()

    # Handle datetime serialization
    if event_dict.get("start_datetime"):
        event_dict["start_datetime"] = event_dict["start_datetime"].isoformat()
    if event_dict.get("end_datetime"):
        event_dict["end_datetime"] = event_dict["end_datetime"].isoformat()
    event_dict["creation_datetime"] = event_dict["creation_datetime"].isoformat()

    # Handle markets using the market_to_dict function
    event_dict["markets"] = [market_to_dict(market) for market in event.markets]

    return event_dict


def event_from_dict(event_data: dict[str, Any]) -> Event:
    """Convert a dictionary back to an Event object."""
    # Handle datetime deserialization
    if event_data.get("start_datetime"):
        event_data["start_datetime"] = datetime.fromisoformat(
            event_data["start_datetime"]
        )
    if event_data.get("end_datetime"):
        event_data["end_datetime"] = datetime.fromisoformat(event_data["end_datetime"])
    event_data["creation_datetime"] = datetime.fromisoformat(
        event_data["creation_datetime"]
    )

    # Handle markets using the market_from_dict function
    markets = []
    for market_data in event_data.get("markets", []):
        markets.append(market_from_dict(market_data))
    event_data["markets"] = markets

    return Event(**event_data)


def save_events_to_file(events: list[Event], file_path: Path) -> None:
    """Save a list of Event objects to a JSON file."""

    # Use the event_to_dict function for each event
    events_data = [event_to_dict(event) for event in events]

    content = json.dumps(events_data, indent=2)
    write_to_storage(file_path, content)

    logger.info(f"Saved {len(events)} events to cache: {file_path}")


def load_events_from_file(file_path: Path) -> list[Event]:
    """Load a list of Event objects from a JSON file."""

    content = read_from_storage(file_path)
    events_data = json.loads(content)

    # Use the event_from_dict function for each event
    events = [event_from_dict(event_data) for event_data in events_data]

    logger.info(f"Loaded {len(events)} events from cache: {file_path}")
    return events
