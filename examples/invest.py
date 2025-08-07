import json
import os
import textwrap
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from market_bench.agent.agent import run_smolagent
from market_bench.pnl import PnlCalculator
from market_bench.polymarket_api import (
    Market,
    MarketRequest,
    filter_interesting_questions,
    filter_out_resolved_markets,
    get_historical_returns,
    get_open_markets,
)

load_dotenv()

OUTPUT_PATH = Path("output")


def agent_invest_positions(
    model_id: str,
    markets: list[Market],
    prices_df: pd.DataFrame,
    date: date,
    test_mode: bool = False,
) -> dict[str, int]:
    """Create investment positions: 1 to buy, -1 to sell, 0 to do nothing"""
    print("\nCreating investment positions with agent...")
    assert date in markets[0].timeseries.index

    positions = {}
    for i, question in enumerate(prices_df.columns):
        market = markets[i]
        assert market.question == question
        if np.isnan(prices_df.loc[date, question]):
            continue
        prices_str = (
            prices_df.loc[:date, question].dropna().to_string(index=True, header=False)
        )
        full_question = (
            question
            + "\nMore details: "
            + market.description
            + textwrap.dedent(
                f"""\n\nHere are the latest rates for the 'yes' to that question (rates for 'yes' and 'no' sum to 1), to guide you:
                {prices_str}
                Invest in yes only if you think the yes is underrated, and invest in no only if you think that the yes is overrated."""
            )
        )
        if not test_mode:
            response = run_smolagent(
                model_id,
                full_question,
                cutoff_date=date,
            )
        else:
            from smolagents import RunResult, Timing, TokenUsage

            response = RunResult(
                output=("yes" if np.random.random() < 0.3 else "nothing"),
                messages=[{"value": "ok here is the reasoning process"}],
                state={},
                token_usage=TokenUsage(0, 0),
                timing=Timing(0.0),
            )
            for message in response.messages:
                message["model_input_messages"] = "removed"  # Clean logs
            model_id = "test"

        output_dir = OUTPUT_PATH / f"smolagent_{model_id}" / date.strftime("%Y-%m-%d")
        os.makedirs(output_dir, exist_ok=True)
        with open(output_dir / f"{question[:50]}.json", "w") as f:
            json.dump(
                {
                    "question": question,
                    "choice": response.output,
                    "full_result": asdict(response),
                },
                f,
                default=str,
            )
        position = 0 if response == "nothing" else (1 if response == "yes" else -1)
        positions[question] = position
    return positions


def analyze_portfolio_performance(positions_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Analyze portfolio performance using PnlCalculator"""
    engine = PnlCalculator(positions_df, returns_df)

    fig = engine.plot_pnl(stock_details=True)

    print(engine.get_performance_metrics().round(2))

    output_path = "/Users/aymeric/Documents/Code/market-bench/portfolio_performance"
    fig.write_html(output_path + ".html")
    fig.write_image(output_path + ".png")
    print(
        f"\nPortfolio visualization saved to: {output_path}.html and {output_path}.png"
    )

    cumulative_pnl = engine.pnl.sum(axis=1).cumsum()
    if not cumulative_pnl.empty:
        final_pnl = cumulative_pnl.iloc[-1]
        print(f"Final Cumulative PnL: {final_pnl:.4f}")

    return cumulative_pnl


def get_filtered_markets(today: date, n_markets: int = 10) -> list[Market]:
    request = MarketRequest(
        limit=n_markets * 5,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=today + timedelta(days=1),
        end_date_max=today + timedelta(days=21),
    )
    markets = get_open_markets(
        request,
        add_timeseries=[
            today - timedelta(days=15),
            today,
        ],  # 15 days back is the maximum allowed by the API
    )
    markets = filter_out_resolved_markets(markets)

    interesting_questions = filter_interesting_questions(
        [market.question for market in markets]
    )
    markets = [market for market in markets if market.question in interesting_questions]
    markets = markets[:n_markets]
    assert len(markets) == n_markets
    return markets


if __name__ == "__main__":
    N_MARKETS = 10

    today = datetime.now().replace(tzinfo=None).date()
    markets = get_filtered_markets(today, n_markets=N_MARKETS)
    print("\n".join([market.question for market in markets]))

    returns_df, prices_df = get_historical_returns(markets)

    list_positions = []
    target_dates = [today - timedelta(days=14), today - timedelta(days=7)]

    for model_id in [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        # "anthropic/claude-sonnet-4-20250514",
        "huggingface/openai/gpt-oss-120b",
        "huggingface/openai/gpt-oss-20b",
        "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507",
    ]:
        if os.path.exists(OUTPUT_PATH / f"smolagent_{model_id}"):
            print(f"Skipping '{model_id}' because its output folder already exists")
            continue
        for target_date in target_dates:
            positions = agent_invest_positions(
                model_id, markets, prices_df, target_date
            )
            list_positions.append(positions)

    # Create DataFrame with positions on target dates
    positions_df = pd.DataFrame(list_positions, index=target_dates)

    # Forward-fill positions to all daily dates in the returns range
    daily_index = returns_df.index[returns_df.index >= target_dates[0]]
    positions_df = positions_df.reindex(daily_index, method="ffill")
    positions_df = positions_df.loc[positions_df.index >= target_dates[0]]
    returns_df = returns_df.loc[returns_df.index >= target_dates[0]]

    print("\nAnalyzing portfolio performance with PnlCalculator...")

    print("\nPositions Table (first 15 rows):")
    print(positions_df.head(15))
    print(f"\nPositions shape: {positions_df.shape}")

    print("\nReturns Table (first 15 rows):")
    print(returns_df.head(15))
    print(f"\nReturns shape: {returns_df.shape}")

    print("\nData summary:")
    print(
        f"  Investment positions: {(positions_df != 0.0).sum().sum()} out of {positions_df.size} possible"
    )
    print(
        f"  Non-zero returns: {(returns_df != 0).sum().sum()} out of {returns_df.notna().sum().sum()} non-NaN"
    )
    print(
        f"  Returns range: {returns_df.min().min():.4f} to {returns_df.max().max():.4f}"
    )

    analyze_portfolio_performance(positions_df, returns_df)
