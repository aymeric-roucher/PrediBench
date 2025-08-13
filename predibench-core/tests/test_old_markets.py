"""
Test MarketRequests for old closed markets to verify price series retrieval.

This test verifies that we can:
1. Make MarketRequests to questions that closed several months ago
2. Retrieve their price series over several months of historical data
3. Test this functionality with 3 different market examples
"""

from datetime import datetime

import pandas as pd
from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    HistoricalTimeSeriesRequestParameters,
    MarketsRequestParameters,
)

# Test markets from late 2024 (about 6 months ago)
TEST_MARKETS = [
    {
        "id": "253591",
        "token_id": "21742633143463906290569050155826241533067272736897614950488156847949938836455",
        "question": "Will Donald Trump win the 2024 US Presidential Election?",
        "end_date": "2024-11-05T12:00:00Z",
    },
    {
        "id": "253597",
        "token_id": "69236923620077691027083946871148646972011131466059644796654161903044970987404",
        "question": "Will Kamala Harris win the 2024 US Presidential Election?",
        "end_date": "2024-11-04T12:00:00Z",
    },
    {
        "id": "512340",
        "token_id": "53033438245279373213426094525005043480366615306824323472317521871682514379120",
        "question": "Will Nicolae Ciucă win the 2024 Romanian Presidential election?",
        "end_date": "2024-12-08T12:00:00Z",
    },
]


def test_market_request_for_old_closed_markets():
    """Test that MarketRequests can retrieve old closed markets from 6+ months ago."""
    # Create a request for closed markets from late 2024
    end_date_min = datetime(2024, 10, 1)
    end_date_max = datetime(2025, 1, 1)

    request_parameters = MarketsRequestParameters(
        limit=20,
        closed=True,
        active=False,
        end_date_min=end_date_min,
        end_date_max=end_date_max,
        order="volumeNum",
        ascending=False,
    )

    markets = request_parameters.get_open_markets()

    # Verify we got some markets
    assert len(markets) > 0, "Should find some closed markets from late 2024"

    # Verify all markets are closed and from the expected time period
    for market in markets:
        assert market.closed is True, f"Market {market.id} should be closed"
        # assert market.active is False, f"Market {market.id} should be inactive"
        assert end_date_min <= market.end_date <= end_date_max, (
            f"Market {market.id} end date should be in expected range"
        )


def test_price_series_retrieval_over_several_months():
    """Test retrieving price series over several months for old closed markets."""

    for i, market_data in enumerate(TEST_MARKETS):
        print(f"\nTesting market {i + 1}: {market_data['question']}")

        # Parse the end date
        end_date = datetime.fromisoformat(market_data["end_date"].replace("Z", ""))

        # Create request for 3 months before market closed
        start_date = end_date - MAX_INTERVAL_TIMESERIES

        # Use the existing function with proper parameters
        timeseries_request_parameters = HistoricalTimeSeriesRequestParameters(
            market=market_data["token_id"],
            start_time=start_date,
            end_time=end_date,
            interval="1d",
            fidelity_minutes=60 * 24,  # Default daily fidelity
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
    print("Testing old closed markets...")
    test_market_request_for_old_closed_markets()
    test_price_series_retrieval_over_several_months()
    print("All tests completed!")
