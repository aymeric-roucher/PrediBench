import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from market_bench.pnl import PnlCalculator
from market_bench.polymarket_api import (
    HistoricalTimeSeriesRequest,
    Market,
    MarketRequest,
    convert_polymarket_time_to_datetime,
    get_open_markets,
    get_token_timeseries,
)


def get_historical_returns(markets: list[Market], days_back: int = 30) -> pd.DataFrame:
    """Get historical returns directly from timeseries data"""
    print(f"\nGetting historical returns over {days_back} days...")

    end_date = datetime.today()
    start_date = end_date - timedelta(days=days_back)

    selected_tokens = []
    for market in markets:
        selected_tokens.append(
            {
                "question": market.question,
                "first_choice_token_id": market.clob_token_ids[0],
            }
        )

    print(f"Selected {len(selected_tokens)} tokens for returns calculation")

    all_dates = pd.date_range(start=start_date, end=end_date, freq="D", normalize=True)
    returns_df = pd.DataFrame(
        np.nan,
        index=all_dates,
        columns=[token["question"] for token in selected_tokens],
    )

    for i, token_info in enumerate(selected_tokens):
        ts_request = HistoricalTimeSeriesRequest(
            market=token_info["first_choice_token_id"],
            start_time=start_date,
            end_time=end_date,
            interval="1d",
        )

        timeseries = get_token_timeseries(ts_request)

        # Create price series
        prices = (
            pd.Series(
                [point.price for point in timeseries.series],
                index=[point.timestamp for point in timeseries.series],
            )
            .sort_index()
            .resample("1D")
            .last()
            .ffill()
        )

        # Calculate returns
        token_returns = prices.pct_change().dropna()

        # Align with our date range - match by date only (ignore time)
        for ts_date, return_val in token_returns.items():
            for date in all_dates:
                if date.date() == ts_date.date():
                    returns_df.loc[date, token_info["question"]] = return_val
                    break

        filled_returns = returns_df[token_info["question"]].notna().sum()
        print(
            f"  Token {i + 1}/{len(selected_tokens)}: {token_info['question'][:8]}... - {len(token_returns)} returns, {filled_returns} aligned"
        )

    return returns_df


def create_investment_positions(
    returns_df: pd.DataFrame, investment_probability: float = 0.3
) -> pd.DataFrame:
    """Create investment positions DataFrame with 1s where investments are made"""
    print(
        f"\nCreating investment positions with probability {investment_probability}..."
    )

    positions_df = pd.DataFrame(0.0, index=returns_df.index, columns=returns_df.columns)

    for date in returns_df.index:
        for token in returns_df.columns:
            # Randomly decide to invest with given probability
            if random.random() < investment_probability:
                positions_df.loc[date, token] = 1.0

    investment_count = (positions_df == 1.0).sum().sum()
    print(
        f"Created {investment_count} investment decisions across {len(returns_df.index)} days and {len(returns_df.columns)} tokens"
    )

    return positions_df


def test_timestamp_extraction():
    """Test the timestamp extraction functionality from polymarket_api.py"""
    print("Testing timestamp extraction...")

    test_timestamps = [
        "2024-01-15T10:30:00Z",
        "2024-02-20T15:45:30.123Z",
        "2024-03-25T00:00:00Z",
    ]

    for ts_str in test_timestamps:
        dt = convert_polymarket_time_to_datetime(ts_str)
        print(f"  {ts_str} -> {dt}")

    print("Timestamp extraction test completed successfully!\n")


def get_market_sample(n_markets: int = 10) -> list[Market]:
    """Get a sample of markets for testing"""
    print(f"Fetching {n_markets} markets...")

    request = MarketRequest(
        limit=n_markets, active=True, closed=False, order="volumeNum", ascending=False
    )

    markets = get_open_markets(request)
    print(f"Retrieved {len(markets)} markets")

    for i, market in enumerate(markets[:5]):
        print(f"  {i + 1}. {market.question[:60]}...")
        print(f"     Created: {market.createdAt}")
        print(f"     Volume: ${market.volume:,.2f}")
        print(f"     Tokens: {len(market.clob_token_ids)}")
        print(market)
    quit()

    return markets


def build_portfolio_data(
    markets: list[Market], days_back: int = 30
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build positions and returns DataFrames for PnlCalculator"""
    print(f"\nBuilding portfolio data over {days_back} days...")

    # Get historical returns from actual timeseries data
    returns_df = get_historical_returns(markets, days_back)

    # Create investment positions (1s where we invest)
    positions_df = create_investment_positions(returns_df, investment_probability=0.3)

    print(f"\nBuilt positions table: {positions_df.shape}")
    print(f"Built returns table: {returns_df.shape}")

    return positions_df, returns_df


def analyze_portfolio_performance(positions_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Analyze portfolio performance using PnlCalculator"""
    print("\nAnalyzing portfolio performance with PnlCalculator...")

    print("\nPositions Table (first 5 rows):")
    print(positions_df.head())
    print(f"\nPositions shape: {positions_df.shape}")

    print("\nReturns Table (first 5 rows):")
    print(returns_df.head())
    print(f"\nReturns shape: {returns_df.shape}")

    print("\nData summary:")
    print(
        f"  Investment positions: {(positions_df == 1.0).sum().sum()} out of {positions_df.size} possible"
    )
    print(
        f"  Non-zero returns: {(returns_df != 0).sum().sum()} out of {returns_df.notna().sum().sum()} non-NaN"
    )
    print(
        f"  Returns range: {returns_df.min().min():.4f} to {returns_df.max().max():.4f}"
    )

    engine = PnlCalculator(positions_df, returns_df)

    fig = engine.plot_pnl(stock_details=True)

    print(engine.get_performance_metrics().round(2))

    output_path = "/Users/aymeric/Documents/Code/market-bench/portfolio_performance"
    fig.write_html(output_path + ".html")
    fig.write_image(output_path + ".png")
    print(f"\nPortfolio visualization saved to: {output_path}")

    cumulative_pnl = engine.pnl.sum(axis=1).cumsum()
    if not cumulative_pnl.empty:
        final_pnl = cumulative_pnl.iloc[-1]
        print(f"Final Cumulative PnL: {final_pnl:.4f}")

    return cumulative_pnl


def main():
    """Main execution function"""
    markets = get_market_sample(10)

    positions_df, returns_df = build_portfolio_data(markets, days_back=14)

    analyze_portfolio_performance(positions_df, returns_df)


if __name__ == "__main__":
    test_timestamp_extraction()

    main()
