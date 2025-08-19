from datetime import datetime, timedelta

from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    EventsRequestParameters,
    MarketsRequestParameters,
    OrderBook,
    _HistoricalTimeSeriesRequestParameters,
    _split_date_range,
)


def test_get_open_markets():
    """Test basic market retrieval."""
    request_parameters = MarketsRequestParameters(limit=10)
    markets = request_parameters.get_markets()
    for market in markets:
        assert len(market.outcomes) >= 2
    # why not 500 ? Some markets are missing keys clobTokenIds or outcomes
    assert len(markets) == 10
    for market in markets:
        assert len(market.id) > 0
        assert len(market.question) > 0
        assert market.liquidity is None or market.liquidity >= 0


def test_polymarket_api_integration():
    """Test the complete Polymarket API workflow with live data."""
    # Fetch active markets
    market_request = MarketsRequestParameters(
        limit=5,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        liquidity_num_min=1000,
    )
    all_markets = market_request.get_markets()

    # Verify we got markets and find an open one
    assert len(all_markets) > 0, "Should find some active markets"

    open_market = None
    for market in all_markets:
        print(
            f"Checking market: {market.question[:50]}... (created: {market.creation_datetime.year})"
        )
        if market.volume24hr > 0:
            open_market = market
            break

    assert open_market is not None, "No open market found"

    # Verify market properties
    assert len(open_market.id) > 0
    assert len(open_market.question) > 0
    assert len(open_market.outcomes) >= 2

    print(f"\nUsing market: {open_market.question}")
    print(f"Created: {open_market.creation_datetime}")

    # Test order book functionality
    token_id = open_market.outcomes[0].clob_token_id
    print(f"\nGetting order book for token: {token_id}")

    order_book = OrderBook.get_order_book(token_id)

    # Verify order book structure
    assert len(order_book.market) > 0
    assert len(order_book.asset_id) > 0
    assert len(order_book.timestamp) > 0
    assert isinstance(order_book.bids, list)
    assert isinstance(order_book.asks, list)

    print(f"Order book timestamp: {order_book.timestamp}")
    print(f"Best bid: {order_book.bids[0].price if order_book.bids else 'None'}")
    print(f"Best ask: {order_book.asks[0].price if order_book.asks else 'None'}")
    print(f"Tick size: {order_book.tick_size}")

    # Test timeseries functionality
    timeseries_request_parameters = _HistoricalTimeSeriesRequestParameters(
        market_id=token_id,
        start_datetime=datetime.now() - timedelta(days=10),
        end_datetime=datetime.now(),
        interval="1d",
    )
    timeseries = timeseries_request_parameters.get_token_daily_timeseries()

    # Verify timeseries data
    assert len(timeseries) > 0, "Should have some timeseries data"
    assert all(0 <= price <= 1 for price in timeseries.values), (
        "Prices should be between 0 and 1"
    )

    print(f"Found {len(timeseries)} data points")
    for date, price in timeseries.iloc[-5:].items():  # Print last 5 points
        print(f"  {date}: ${price:.4f}")


def test_get_market_events():
    """Test basic market event retrieval."""
    request_first = EventsRequestParameters(limit=5)
    events = request_first.get_events()
    assert len(events) == 5

    for event in events:
        # Basic validation of event properties
        assert len(event.id) > 0
        assert len(event.slug) > 0
        assert len(event.title) > 0
        assert event.liquidity is None or event.liquidity >= 0
        assert event.volume is None or event.volume >= 0
        assert event.start_datetime is None or isinstance(
            event.start_datetime, datetime
        )
        assert event.end_datetime is None or isinstance(event.end_datetime, datetime)
        assert isinstance(event.creation_datetime, datetime)
        assert isinstance(event.markets, list)

        # Validate markets structure
        for market in event.markets:
            assert len(market.id) > 0
            assert len(market.question) > 0
            assert len(market.outcomes) >= 2
            assert isinstance(market.outcomes, list)
            # Validate market outcomes
            for outcome in market.outcomes:
                assert len(outcome.name) > 0
                assert len(outcome.clob_token_id) > 0
                assert 0 <= outcome.price <= 1

    assert len(events) >= 1  # Should get at least some events

    # Test offset
    request_second = EventsRequestParameters(limit=5, offset=5)
    events_second = request_second.get_events()
    assert len(events_second) == 5

    first_ids = {event.id for event in events}
    second_ids = {event.id for event in events_second}
    # Events should be different (though not necessarily disjoint due to API behavior)
    assert len(first_ids.union(second_ids)) > len(first_ids)


def test_split_date_range_small():
    """Test that small date ranges don't get split."""
    start_datetime = datetime(2024, 1, 1)
    end_datetime = datetime(2024, 1, 10)

    chunks = _split_date_range(start_datetime, end_datetime)

    assert len(chunks) == 1
    assert chunks[0] == (start_datetime, end_datetime)


def test_split_date_range_large():
    """Test that large date ranges get split into multiple chunks."""
    start_datetime = datetime(2024, 1, 1)
    end_datetime = datetime(2024, 1, 31)  # 30 days, should be split

    chunks = _split_date_range(start_datetime, end_datetime)

    assert len(chunks) > 1

    # Check that chunks cover the entire range without gaps
    assert chunks[0][0] == start_datetime
    assert chunks[-1][1] == end_datetime

    # Check that each chunk is within the limit
    for chunk_start, chunk_end in chunks:
        assert chunk_end - chunk_start <= MAX_INTERVAL_TIMESERIES

    # Check that chunks don't overlap (except by 1 hour)
    for i in range(len(chunks) - 1):
        current_end = chunks[i][1]
        next_start = chunks[i + 1][0]
        assert next_start == current_end + timedelta(hours=1)


def test_split_date_range_very_large():
    """Test splitting a very large date range (60 days)."""
    start_datetime = datetime(2024, 1, 1)
    end_datetime = datetime(2024, 3, 1)  # ~60 days

    chunks = _split_date_range(start_datetime, end_datetime)

    # Should split into at least 4 chunks (60 days / 14 days ≈ 4.3)
    assert len(chunks) >= 4

    # Verify continuity
    reconstructed_range = chunks[-1][1] - chunks[0][0]
    original_range = end_datetime - start_datetime
    # Allow for small differences due to the 1-hour gaps between chunks
    assert (
        abs((reconstructed_range - original_range).total_seconds())
        <= (len(chunks) - 1) * 3600
    )


def test_split_date_range_multi_split_precise():
    """Test precise multi-split behavior with known intervals."""
    # Create a range that should split into exactly 3 chunks
    start_datetime = datetime(2024, 1, 1, 0, 0, 0)
    # Add 2 * MAX_INTERVAL_TIMESERIES + some extra time to force 3 chunks
    end_datetime = start_datetime + (2 * MAX_INTERVAL_TIMESERIES) + timedelta(days=5)

    chunks = _split_date_range(start_datetime, end_datetime)

    # Should have exactly 3 chunks
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"

    # First chunk should start at start_datetime
    assert chunks[0][0] == start_datetime

    # Last chunk should end at end_datetime
    assert chunks[-1][1] == end_datetime

    # Check that segment starts are correctly spaced by MAX_INTERVAL_TIMESERIES
    expected_second_start = start_datetime + MAX_INTERVAL_TIMESERIES
    expected_third_start = start_datetime + (2 * MAX_INTERVAL_TIMESERIES)

    assert chunks[1][0] == expected_second_start
    assert chunks[2][0] == expected_third_start

    # Check that chunk ends are properly offset by 1 hour from next start
    assert chunks[0][1] == expected_second_start - timedelta(hours=1)
    assert chunks[1][1] == expected_third_start - timedelta(hours=1)

    # Verify no chunk exceeds MAX_INTERVAL_TIMESERIES
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        duration = chunk_end - chunk_start
        assert duration <= MAX_INTERVAL_TIMESERIES, (
            f"Chunk {i} duration {duration} exceeds limit"
        )

    print(
        f"Successfully split {end_datetime - start_datetime} into {len(chunks)} chunks:"
    )
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        duration = chunk_end - chunk_start
        print(f"  Chunk {i + 1}: {chunk_start} to {chunk_end} (duration: {duration})")


if __name__ == "__main__":
    test_get_market_events()
