from datetime import datetime

import pandas as pd
from predibench.polymarket_api import (
    MarketsRequestParameters,
    _HistoricalTimeSeriesRequestParameters,
)

# Test markets from late 2024 (about 6 months ago)
TEST_MARKETS = [
    {
        "id": "511754",
        "token_id": "103864131794756285503734468197278890131080300305704085735435172616220564121629",
        "question": "Will Zelenskyy wear a suit before July?",
        "start_date": "2025-05-25T12:00:00Z",
        "end_date": "2025-06-28T12:00:00Z",
    },
    {
        "id": "253597",
        "token_id": "69236923620077691027083946871148646972011131466059644796654161903044970987404",
        "question": "Will Kamala Harris win the 2024 US Presidential Election?",
        "end_date": "2024-02-04T12:00:00Z",
        "start_date": "2024-01-01T12:00:00Z",
    },
]


def test_market_request_for_old_closed_markets():
    """Test that MarketRequests can retrieve old closed markets from 6+ months ago."""
    # Create a request for closed markets from late 2024
    end_datetime_min = datetime(2025, 3, 1)
    end_datetime_max = datetime(2025, 7, 1)

    request_parameters = MarketsRequestParameters(
        limit=20,
        closed=True,
        active=False,
        end_datetime_min=end_datetime_min,
        end_datetime_max=end_datetime_max,
        order="volumeNum",
        ascending=False,
    )

    markets = request_parameters.get_markets()

    # Verify we got some markets
    assert len(markets) > 0, "Should find some closed markets from late 2024"

    # Verify all markets are closed and from the expected time period
    for market in markets[:3]:
        assert market.volume24hr is None or market.volume24hr == 0, (
            f"Market {market.id} should be inactive"
        )
        assert end_datetime_min <= market.end_datetime <= end_datetime_max, (
            f"Market {market.id} end date should be in expected range"
        )


def test_price_series_retrieval_over_several_months():
    """Test retrieving price series over several months for old closed markets."""

    for i, market_data in enumerate(TEST_MARKETS):
        print(f"\nTesting market {i + 1}: {market_data['question']}")

        end_datetime = datetime.fromisoformat(market_data["end_date"].replace("Z", ""))
        start_datetime = datetime.fromisoformat(
            market_data["start_date"].replace("Z", "")
        )

        # Use the existing function with proper parameters
        timeseries_request_parameters = _HistoricalTimeSeriesRequestParameters(
            market_id=market_data["token_id"],
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            interval="1d",
        )

        # Use the method from the request object
        timeseries = timeseries_request_parameters.get_token_daily_timeseries()

        print(f"  Retrieved {len(timeseries)} data points")

        assert len(timeseries) > 0
        print(f"  Date range: {timeseries.index[0]} to {timeseries.index[-1]}")
        print(f"  Price range: {timeseries.min():.4f} to {timeseries.max():.4f}")
        print(f"  Final price: {timeseries.iloc[-1]:.4f}")

        # Verify we have reasonable amount of data
        assert len(timeseries) >= 1, (
            f"Should have at least 1 data point for market {market_data['id']}"
        )

        # Verify prices are reasonable (between 0 and 1 for prediction markets)
        for price in timeseries.values:
            assert 0 <= price <= 1, f"Price {price} should be between 0 and 1"

        # Verify data is a pandas Series
        assert isinstance(timeseries, pd.Series), "Should return pandas Series"


if __name__ == "__main__":
    test_market_request_for_old_closed_markets()
    test_price_series_retrieval_over_several_months()
