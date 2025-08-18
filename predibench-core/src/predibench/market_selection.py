from datetime import date, datetime, timedelta
from pathlib import Path


from predibench.polymarket_api import (
    Event,
    EventsRequestParameters,
)
from predibench.logger_config import get_logger
from predibench.polymarket_data import save_events_to_file

logger = get_logger(__name__)


def _remove_markets_without_prices_in_events(events: list[Event]) -> list[Event]:
    """Remove markets that have no prices"""
    filtered_events = []
    for event in events:
        market_filtered = [
            market
            for market in event.markets
            if market.prices is not None and len(market.prices) >= 1
        ]
        event.markets = market_filtered
        if len(market_filtered) > 0:
            filtered_events.append(event)
    return filtered_events


def _filter_crypto_events(events: list[Event]) -> list[Event]:
    """Filter out events related to crypto by checking if 'bitcoin' or 'ethereum' is in the slug."""
    crypto_keywords = ["bitcoin", "ethereum", "xrp", "solana", "eth", "btc"]
    filtered_events = []

    for event in events:
        slug_lower = event.slug.lower() if event.slug else ""
        is_crypto = any(keyword in slug_lower for keyword in crypto_keywords)

        if not is_crypto:
            filtered_events.append(event)
        else:
            logger.info(
                f"Filtered out crypto event: {event.title} (slug: {event.slug})"
            )

    return filtered_events


def _filter_events_by_volume_and_markets(
    events: list[Event], min_volume: float = 1000, backward_mode: bool = False
) -> list[Event]:
    """Filter events based on volume threshold and presence of markets."""
    filtered_events = []
    for event in events:
        if event.markets and len(event.markets) > 0:
            if backward_mode:
                # In backward mode, we can't rely on volume24hr as it may not be available for historical events
                # Just ensure events have markets
                filtered_events.append(event)
            elif (
                event.volume24hr and event.volume24hr > min_volume
            ):  # Minimum volume threshold
                filtered_events.append(event)
    return filtered_events


def _select_markets_for_events(
    events: list[Event], base_date: date, backward_mode: bool = False
) -> list[Event]:
    """Select the market with highest volume1wk that has outcomes[0] price between 0.05 and 0.95."""

    if backward_mode:
        # In backward mode: filter events by end_date > base_date (if end_date exists) and select markets by volume
        events_with_selected_markets = []
        for event in events:
            # Filter events where end_date is after base_date, or keep if end_date doesn't exist
            if event.end_date is None or event.end_date.date() > base_date:
                if event.selected_market_id is not None:
                    raise ValueError(
                        f"Event '{event.title}' already has a selected market"
                    )

                # Select market with highest volume1wk (no price constraints in backward mode)
                eligible_markets = [
                    market
                    for market in event.markets
                    if market.end_date is None or market.end_date.date() > base_date
                ]

                if eligible_markets:
                    best_market = max(eligible_markets, key=lambda m: m.volumeNum)
                    event.selected_market_id = best_market.id
                    events_with_selected_markets.append(event)

                    end_date_str = (
                        event.end_date.date() if event.end_date else "no end date"
                    )
                    logger.info(
                        f"Backward mode: Selected event '{event.title}' ending {end_date_str}"
                    )

        return events_with_selected_markets

    events_with_selected_markets = []
    for event in events:
        if event.selected_market_id is not None:
            raise ValueError(f"Event '{event.title}' already has a selected market")

        eligible_markets = []
        for market in event.markets:
            if (
                market.volume1wk is not None
                and market.outcomes
                and len(market.outcomes) > 0
                and 0.05 < market.outcomes[0].price < 0.95
            ):
                eligible_markets.append(market)

        if eligible_markets:
            best_market = max(eligible_markets, key=lambda m: m.volume1wk)
            event.selected_market_id = best_market.id
            events_with_selected_markets.append(event)

    return events_with_selected_markets


def choose_events(
    today_date: datetime,
    event_selection_window: timedelta,
    n_events: int,
    min_volume: float = 1000,
    backward_mode: bool = False,
    filter_crypto_events: bool = True,
    save_path: Path | None = None,
) -> list[Event]:
    """Pick top events by volume for investment for the current week

    backward_mode: if True, then events ending around this date will be selected, but those events are probably closed, we can't use the volume24hr to filter out the events that are open.
    """
    end_date = today_date + event_selection_window
    request_parameters = EventsRequestParameters(
        limit=500,
        order="volume1wk" if not backward_mode else "volume",
        ascending=False,
        end_date_min=today_date if backward_mode else None,
        end_date_max=end_date,
    )
    events = request_parameters.get_events()

    if filter_crypto_events:
        events = _filter_crypto_events(events)

    filtered_events = _filter_events_by_volume_and_markets(
        events=events, min_volume=min_volume, backward_mode=backward_mode
    )
    filtered_events = filtered_events[:n_events]

    for event in filtered_events:
        for market in event.markets:
            if backward_mode:
                market.fill_prices(end_time=end_date)
            else:
                market.fill_prices()

    filtered_events = _remove_markets_without_prices_in_events(filtered_events)

    events_with_selected_markets = _select_markets_for_events(
        events=filtered_events, base_date=today_date, backward_mode=backward_mode
    )

    save_events_to_file(
        events=events_with_selected_markets,
        file_path=save_path
    )

    return events_with_selected_markets
