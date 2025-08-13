
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

import plotly.graph_objects as go

from predibench.polymarket_api import (
    MarketsRequestParameters,
    Event,
    convert_polymarket_time_to_datetime,
    _HistoricalTimeSeriesRequestParameters,
    OrderBook,
)


def test_get_open_markets():
    """Test basic market retrieval."""
    request_parameters = MarketsRequestParameters(limit=500)
    markets = request_parameters.get_open_markets()
    for market in markets:
        assert len(market.outcomes) >= 2
    # why not 500 ? Some markets are missing keys clobTokenIds or outcomes
    assert len(markets) >= 490
    for market in markets:
        assert len(market.id) > 0
        assert len(market.question) > 0
        assert market.liquidity is None or market.liquidity >= 0



def test_get_open_markets_limit():
    """Test that limit parameter works correctly."""
    request_small = MarketsRequestParameters(limit=5)
    request_large = MarketsRequestParameters(limit=20)
    markets_small = request_small.get_open_markets()
    markets_large = request_large.get_open_markets()

    assert len(markets_small) == 5
    assert len(markets_large) == 20
    assert len(markets_large) > len(markets_small)


def test_polymarket_api_integration():
    """Test the complete Polymarket API workflow with live data."""
    # Fetch active markets
    market_request = MarketsRequestParameters(
        limit=20,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        liquidity_num_min=1000,
    )
    all_markets = market_request.get_open_markets()
    
    # Verify we got markets and find an open one
    assert len(all_markets) > 0, "Should find some active markets"
    
    open_market = None
    for market in all_markets:
        print(
            f"Checking market: {market.question[:50]}... (created: {market.createdAt.year})"
        )
        if market.volume24hr>0:
            open_market = market
            break
    
    assert open_market is not None, "No open market found"
    
    # Verify market properties
    assert len(open_market.id) > 0
    assert len(open_market.question) > 0
    assert len(open_market.outcomes) >= 2

    print(f"\nUsing market: {open_market.question}")
    print(f"Created: {open_market.createdAt}")

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
        market=token_id,
        start_time=datetime.now() - timedelta(days=10),
        end_time=datetime.now(),
        interval="1d",
    )
    timeseries = timeseries_request_parameters.get_token_daily_timeseries()

    # Verify timeseries data
    assert len(timeseries) > 0, "Should have some timeseries data"
    assert all(0 <= price <= 1 for price in timeseries.values), "Prices should be between 0 and 1"

    print(f"Found {len(timeseries)} data points")
    for date, price in timeseries.iloc[-5:].items():  # Print last 5 points
        print(f"  {date}: ${price:.4f}")

    # Test visualization creation
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timeseries.index, y=timeseries.values, mode="lines+markers", name="Price"
        )
    )
    fig.update_layout(
        title=f"Price History - {open_market.question}",
        xaxis_title="Time",
        yaxis_title="Price",
    )
    
    # Write to temporary file instead of polluting working directory
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        fig.write_image(tmp_file.name)
        # Clean up the temporary file
        Path(tmp_file.name).unlink()
        print(f"Successfully created visualization (temporary file cleaned up)")
    
    # Verify the figure was created correctly
    assert len(fig.data) == 1
    assert fig.data[0].mode == "lines+markers"

def test__get_events():
    """Test basic market event retrieval."""
    events = Event._get_events()
    assert len(events) == 500


def test_get_market_events_offset():
    """Test that offset parameter works correctly."""
    events_first = Event._get_events(limit=5, offset=0)
    events_second = Event._get_events(limit=5, offset=5)

    assert len(events_first) == 5
    assert len(events_second) == 5

    first_ids = {event["id"] for event in events_first}
    second_ids = {event["id"] for event in events_second}
    assert first_ids.isdisjoint(second_ids)
    
def test__get_market_events():
    """Test basic market event retrieval."""
    events = Event._get_events()
    for event in events:
        # ticker is sometimes different from slug
        assert event["ticker"] in event["slug"]

        # those dates are typically the same, but sometimes different
        assert (
            convert_polymarket_time_to_datetime(event["creationDate"]).date()
            >= convert_polymarket_time_to_datetime(event["createdAt"]).date()
        )

        # some markets might be resolved, but not all
        for market in event["markets"]:
            if "liquidityNum" not in market or float(market["liquidityNum"]) == 0:
                pass  # no real rules
                # assert market["closed"] == True

    assert len(events) == 500



if __name__ == "__main__":
    test_get_open_markets_limit()
    test__get_events()
    test_get_market_events_offset()
    test__get_market_events()
    test_polymarket_api_integration()