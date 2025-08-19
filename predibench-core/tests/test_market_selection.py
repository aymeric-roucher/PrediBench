"""
End-to-end tests for market selection functionality.

This test suite covers:
1. Event caching functionality (save/load cycle)
2. Backward compatibility testing for choose_events()
3. API integration and data integrity verification
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger
from predibench.market_selection import choose_events
from predibench.polymarket_api import Event, Market, MarketOutcome
from predibench.polymarket_data import load_events_from_file, save_events_to_file

logger = get_logger(__name__)


def create_mock_events() -> list[Event]:
    """Create mock events for testing to avoid API rate limits."""
    mock_events = []
    # Use today's date to ensure events fit within the test date range
    today = date.today()
    base_time = datetime.combine(today, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    for i in range(10):
        # Create mock outcomes with prices in valid range (0.05 < price < 0.95)
        price_base = 0.2 + (i * 0.05)  # Prices between 0.2 and 0.65
        outcomes = [
            MarketOutcome(
                clob_token_id=f"token_{i}_0",
                name="Yes",
                price=price_base,  # Valid price range
            ),
            MarketOutcome(
                clob_token_id=f"token_{i}_1",
                name="No",
                price=1.0 - price_base,  # Complement price
            ),
        ]

        # Create mock market with proper volume1wk and end_datetime within test range
        market = Market(
            id=f"market_{i}",
            question=f"Will event {i} happen?",
            slug=f"event-{i}-market",
            description=f"Mock market for event {i}",
            end_datetime=base_time + timedelta(days=i + 1),  # Within 21-day window
            creation_datetime=base_time - timedelta(days=30),
            volumeNum=10000.0 + (i * 1000),  # Volume between 10k-19k
            volume24hr=2000.0 + (i * 200),  # 24hr volume between 2k-3.8k
            volume1wk=5000.0 + (i * 500),  # 1wk volume between 5k-9.5k (REQUIRED!)
            volume1mo=20000.0 + (i * 1000),  # 1mo volume between 20k-29k
            volume1yr=100000.0 + (i * 5000),  # 1yr volume between 100k-145k
            liquidity=50000.0 + (i * 2000),  # Liquidity between 50k-68k
            outcomes=outcomes,
            prices=pd.Series(
                name="price",
                index=pd.date_range(
                    start=base_time, end=base_time + timedelta(days=9), freq="D"
                ),
                data=[0.5 + 0.1 * (i % 5) for i in range(10)],
            ),
            price_outcome_name="Yes",
        )

        # Create mock event with volume24hr > 1000 and end_datetime within test range
        event = Event(
            id=f"event_{i}",
            slug=f"mock-event-{i}",
            title=f"Mock Event {i}",
            description=f"This is a mock event for testing purposes - Event {i}",
            start_datetime=base_time + timedelta(hours=i),
            end_datetime=base_time + timedelta(days=i + 1),  # Within 21-day window
            creation_datetime=base_time - timedelta(days=30),
            volume=50000.0 + (i * 5000),  # Volume between 50k-95k
            volume24hr=5000.0
            + (i * 500),  # 24hr volume between 5k-9.5k (> 1000 REQUIRED!)
            volume1wk=15000.0 + (i * 1000),  # 1wk volume between 15k-24k
            volume1mo=60000.0 + (i * 3000),  # 1mo volume between 60k-87k
            volume1yr=300000.0 + (i * 10000),  # 1yr volume between 300k-390k
            liquidity=100000.0 + (i * 5000),  # Liquidity between 100k-145k
            markets=[market],
            selected_market_id=None,
        )

        mock_events.append(event)

    return mock_events


@patch("predibench.polymarket_api.Market.fill_prices")
@patch("predibench.market_selection.EventsRequestParameters.get_events")
def test_choose_events_event_caching_e2e(mock_get_events, mock_fill_prices):
    """End-to-end test for event save/load functionality."""
    # Mock the API call to avoid rate limits
    mock_get_events.return_value = create_mock_events()

    # Create a proper wrapper function that can handle both positional and keyword args
    def fill_prices_wrapper(*args, **kwargs):
        pass

    mock_fill_prices.side_effect = fill_prices_wrapper

    # Test parameters (same as used in invest.py)
    today_date = date.today()
    event_selection_window = timedelta(days=21)
    max_n_events = 3

    # Step 1: Fetch events from API
    selected_events = choose_events(
        target_date=today_date,
        time_until_ending=event_selection_window,
        n_events=max_n_events,
    )

    # checking events
    nb_markets_with_prices = 0
    nb_markets_without_prices = 0
    assert len(selected_events) == max_n_events, (
        f"Expected {max_n_events} events, got {len(selected_events)}"
    )
    for event in selected_events:
        assert len(event.markets) > 0, f"Event {event.title} has no markets"
        assert event.volume24hr is not None, f"Event {event.title} has no volume24hr"
        assert event.volume24hr > 0, f"Event {event.title} has no volume24hr"
        assert event.end_datetime.date() <= today_date + event_selection_window, (
            f"Event {event.title} has end_date {event.end_datetime} which is after {today_date + event_selection_window}"
        )

        for market in event.markets:
            assert len(market.outcomes) == 2, (
                f"Market {market.question} has {len(market.outcomes)} outcomes, expected 2"
            )
            if market.prices is not None and len(market.prices) >= 1:
                nb_markets_with_prices += 1
            else:
                nb_markets_without_prices += 1
    assert nb_markets_with_prices > 0
    assert nb_markets_without_prices == 0

    # Step 2: Save events to file
    cache_file = DATA_PATH / "test_events_cache.json"
    save_events_to_file(selected_events, cache_file)

    # Verify file was created
    assert cache_file.exists(), f"Cache file was not created: {cache_file}"

    # Step 3: Load events from file
    loaded_events = load_events_from_file(cache_file)

    # Step 4: Verify data integrity
    # Check basic counts
    assert len(selected_events) == len(loaded_events), (
        f"Event count mismatch: original={len(selected_events)}, loaded={len(loaded_events)}"
    )

    # Check each event
    for i, (original, loaded) in enumerate(zip(selected_events, loaded_events)):
        # Check basic event properties
        assert original.id == loaded.id, f"Event ID mismatch for event {i}"
        assert original.title == loaded.title, f"Event title mismatch for event {i}"
        assert original.slug == loaded.slug, f"Event slug mismatch for event {i}"
        assert original.description == loaded.description, (
            f"Event description mismatch for event {i}"
        )

        # Check numeric fields
        assert original.volume == loaded.volume, f"Event volume mismatch for event {i}"
        assert original.volume24hr == loaded.volume24hr, (
            f"Event volume24hr mismatch for event {i}"
        )
        assert original.liquidity == loaded.liquidity, (
            f"Event liquidity mismatch for event {i}"
        )

        # Check markets count
        assert len(original.markets) == len(loaded.markets), (
            f"Markets count mismatch for event {i}: original={len(original.markets)}, loaded={len(loaded.markets)}"
        )

        # Check first market details (if exists)
        if original.markets and loaded.markets:
            orig_market = original.markets[0]
            loaded_market = loaded.markets[0]

            assert orig_market.id == loaded_market.id, (
                f"Market ID mismatch for event {i}"
            )
            assert orig_market.question == loaded_market.question, (
                f"Market question mismatch for event {i}"
            )
            assert len(orig_market.outcomes) == len(loaded_market.outcomes), (
                f"Market outcomes count mismatch for event {i}"
            )

            # Check pandas Series prices preservation
            if orig_market.prices is not None:
                assert loaded_market.prices is not None, (
                    f"Prices Series lost during serialization for market {orig_market.id}"
                )
                assert isinstance(loaded_market.prices, pd.Series), (
                    f"Prices should be a pandas Series for market {orig_market.id}"
                )
                assert orig_market.prices.name == loaded_market.prices.name, (
                    f"Series name mismatch for market {orig_market.id}"
                )
                assert len(orig_market.prices) == len(loaded_market.prices), (
                    f"Series length mismatch for market {orig_market.id}"
                )

                # Check that values are preserved (index may be converted to DatetimeIndex)
                assert list(orig_market.prices.values) == list(
                    loaded_market.prices.values
                ), f"Values mismatch for market {orig_market.id}"
                assert len(orig_market.prices) == len(loaded_market.prices), (
                    f"Length mismatch for market {orig_market.id}"
                )
                # Convert both to DatetimeIndex for comparison
                orig_dt_index = pd.to_datetime(orig_market.prices.index)
                loaded_dt_index = pd.to_datetime(loaded_market.prices.index)
                assert list(orig_dt_index) == list(loaded_dt_index), (
                    f"Index mismatch for market {orig_market.id}"
                )
            else:
                assert loaded_market.prices is None, (
                    f"Prices should be None for market {orig_market.id}"
                )

    # Step 5: Cleanup
    if cache_file.exists():
        cache_file.unlink()


@patch("predibench.polymarket_api.Market.fill_prices")
@patch("predibench.market_selection.EventsRequestParameters.get_events")
def test_choose_events_backward(mock_get_events, mock_fill_prices):
    """Test choose_events function for backward mode."""
    # Mock the API call to avoid rate limits
    mock_get_events.return_value = create_mock_events()

    # Mock fill_prices to avoid API calls and provide mock price data
    def create_mock_prices(market_instance, start_datetime, end_datetime):
        # Create mock price data as a pandas Series
        dates = pd.date_range(start=start_datetime, end=end_datetime, freq="D")
        prices = [
            0.5 + 0.1 * (i % 5) for i in range(len(dates))
        ]  # Mock price fluctuation
        market_instance.prices = pd.Series(prices, index=dates, name="price")
        market_instance.price_outcome_name = "Yes"

    # Create a proper wrapper function that can handle both positional and keyword args
    def fill_prices_wrapper(*args, **kwargs):
        # Extract the market instance (self)
        if len(args) > 0:
            market_instance = args[0]
            start_dt = args[1] if len(args) > 1 else kwargs.get("start_datetime")
            end_dt = args[2] if len(args) > 2 else kwargs.get("end_datetime")
        else:
            # This shouldn't happen, but just in case
            return
        create_mock_prices(market_instance, start_dt, end_dt)

    mock_fill_prices.side_effect = fill_prices_wrapper

    # Test parameters
    base_datetime = datetime(2025, 8, 15, tzinfo=timezone.utc)  # Fixed date for testing
    event_selection_window = timedelta(days=7)
    max_n_events = 3

    # Test 1: Normal mode (backward_mode=False)
    selected_events = choose_events(
        target_date=base_datetime.date(),
        time_until_ending=event_selection_window,
        n_events=max_n_events,
    )

    # checking events
    nb_markets_with_prices = 0
    nb_markets_without_prices = 0
    assert len(selected_events) > 0, (
        f"Expected {max_n_events} events, got {len(selected_events)}"
    )
    for event in selected_events:
        assert len(event.markets) > 0, f"Event {event.title} has no markets"
        assert event.end_datetime <= base_datetime + event_selection_window, (
            f"Event {event.title} has end_date {event.end_datetime} which is after {base_datetime + event_selection_window}"
        )

        for market in event.markets:
            assert len(market.outcomes) == 2, (
                f"Market {market.question} has {len(market.outcomes)} outcomes, expected 2"
            )
            if market.prices is not None and len(market.prices) >= 1:
                nb_markets_with_prices += 1
            else:
                nb_markets_without_prices += 1
    assert nb_markets_with_prices > 0


def main():
    # Note: When running main() directly, we need to handle mocking differently
    # For pytest, the decorators will work automatically
    def create_mock_prices(market_instance, start_datetime, end_datetime):
        dates = pd.date_range(start=start_datetime, end=end_datetime, freq="D")
        prices = [0.5 + 0.1 * (i % 5) for i in range(len(dates))]
        market_instance.prices = pd.Series(prices, index=dates, name="price")
        market_instance.price_outcome_name = "Yes"

    with (
        patch(
            "predibench.market_selection.EventsRequestParameters.get_events"
        ) as mock_get_events,
        patch("predibench.polymarket_api.Market.fill_prices") as mock_fill_prices,
    ):
        mock_get_events.return_value = create_mock_events()
        mock_fill_prices.side_effect = (
            lambda self, start_datetime, end_datetime: create_mock_prices(
                self, start_datetime, end_datetime
            )
        )
        test_choose_events_event_caching_e2e()
        test_choose_events_backward()


if __name__ == "__main__":
    main()
