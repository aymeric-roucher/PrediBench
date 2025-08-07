import json
import os
import random
import textwrap
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from smolagents import ChatMessage, LiteLLMModel

from market_bench.agent.agent import run_smolagent
from market_bench.pnl import PnlCalculator
from market_bench.polymarket_api import (
    Market,
    MarketRequest,
    get_open_markets,
)


def get_historical_returns(markets: list[Market]) -> pd.DataFrame:
    """Get historical returns directly from timeseries data"""

    returns_df = pd.DataFrame(
        np.nan,
        index=markets[0].timeseries.index,
        columns=[market.question for market in markets],
    )
    prices_df = pd.DataFrame(
        np.nan,
        index=markets[0].timeseries.index,
        columns=[market.question for market in markets],
    )

    for i, market in enumerate(markets):
        prices_df[market.question] = market.timeseries

        token_returns = market.timeseries.pct_change(periods=1)
        returns_df[market.question] = token_returns

    return returns_df, prices_df


def filter_out_resolved_markets(
    markets: list[Market], threshold: float = 0.02
) -> list[Market]:
    """Filter out markets that are already close to 0 or 1, as these are probably already resolved"""
    return [
        market
        for market in markets
        if not (
            market.timeseries[-10:].mean() > 1 - threshold
            or market.timeseries[-10:].mean() < threshold
        )
    ]


def agent_invest_positions(
    markets: list[Market],
    prices_df: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Create investment positions DataFrame: 1 to buy, -1 to sell, 0 to do nothing"""
    print("\nCreating investment positions with agent...")
    assert start_date in markets[0].timeseries.index
    assert end_date in markets[0].timeseries.index

    positions_df = pd.DataFrame(
        0.0,
        index=pd.date_range(start=start_date, end=end_date, freq="D").date,
        columns=prices_df.columns,
    )

    for date in positions_df.index:
        for i, question in enumerate(prices_df.columns):
            market = markets[i]
            assert market.question == question
            if np.isnan(prices_df.loc[date, question]):
                continue

            full_question = (
                market.question
                + "\nMore details: "
                + market.description
                + "\n\n"
                + f" Here are the latest rates for the 'yes' to that question (rates for 'yes' and 'no' sum to 1), to guide you:\n{prices_df.loc[:date, question].dropna().to_string(index=True, header=False)}\nInvest in yes only if you think the yes is underrated, and invest in no only if you think that the yes is overrated."
            )
            response = run_smolagent(
                full_question,
                cutoff_date=date,
            )
            position = 0 if response == "nothing" else (1 if response == "yes" else -1)
            positions_df.loc[date, question] = position
    return positions_df


def invest_on_random_positions(
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


def filter_interesting_questions(questions: list[str]) -> list[str]:
    """Get interesting questions from markets"""

    from pydantic import BaseModel

    class InterestingQuestions(BaseModel):
        questions: list[str]

    # model = OpenAIModel(
    #     model_id="gpt-4.1",
    #     api_key=os.getenv("OPENAI_API_KEY"),
    # )

    # print(
    #     model.generate(
    #         [
    #             ChatMessage(
    #                 role="user",
    #                 content=f"Please select the most interesting deduplicated questions out of the following list:\n{[market.question for market in markets]}.\nDeduplicated means that you should remove any successive question that has the same content and only a different end date than another one. Interesting means: remove crypto questions.",
    #             )
    #         ],
    #     )
    # )
    # quit()

    model = LiteLLMModel(
        model_id="gpt-4.1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    output = model.generate(
        [
            ChatMessage(
                role="user",
                content=textwrap.dedent(f"""Please select the most interesting deduplicated questions out of the following list:
                {questions}
                2 questions being deduplicated means that one of them gives >70% info on the other one. In that case, remove all but the first occurence.
                For instance in "Winnie the Pooh becomes US president by October 2025?" and "Winnie the Pooh becomes US president by November 2025?" and "Piglet gets over 50% of the vote in the 2025 US presidential election?", you should remove the second and third one - the second because it is just a later date so heavily impacted by the first, and the third because Winne and Piglet winning is mutually exclusive so one gives out the other.
                Interesting means: remove crypto questions."""),
            )
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": InterestingQuestions.model_json_schema(),
            },
        },
    )
    return json.loads(output.content)["questions"]


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


if __name__ == "__main__":
    today = datetime.now().replace(tzinfo=None).date()
    request = MarketRequest(
        limit=50,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=today + timedelta(days=1),
        end_date_max=today + timedelta(days=30),
    )
    markets = get_open_markets(
        request, add_timeseries=[today - timedelta(days=20), today]
    )
    markets = filter_out_resolved_markets(markets)

    interesting_questions = filter_interesting_questions(
        [market.question for market in markets]
    )
    markets = [market for market in markets if market.question in interesting_questions]
    markets = markets[:10]

    returns_df, prices_df = get_historical_returns(markets)
    print("\n".join([market.question for market in markets]))

    # positions_df = invest_on_random_positions(returns_df, investment_probability=1)
    positions_df = agent_invest_positions(
        markets, prices_df, today - timedelta(days=10), today
    )

    analyze_portfolio_performance(positions_df, returns_df)
