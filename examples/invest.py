import json
import os
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from smolagents import RunResult, Timing, TokenUsage

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
if not OUTPUT_PATH.exists():
    OUTPUT_PATH.mkdir(parents=True)

portfolio_performance_path = OUTPUT_PATH / "portfolio_performance"
if not portfolio_performance_path.exists():
    portfolio_performance_path.mkdir(parents=True)


def run_deep_research(
    model_id: str,
    question: str,
    cutoff_date: date,
) -> RunResult:
    from openai import OpenAI

    client = OpenAI(timeout=3600)

    response = client.responses.create(
        model=model_id,
        input=question + "Preface your answer with 'ANSWER: '",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
        ],
    )
    output_text = response.output_text
    choice = output_text.split("ANSWER: ")[1].strip()
    return RunResult(
        output=choice,
        steps=[],
        state={},
        token_usage=TokenUsage(0, 0),
        timing=Timing(0.0),
    )


def agent_invest_positions(
    model_id: str,
    markets: list[Market],
    prices_df: pd.DataFrame,
    date: date,
    test_mode: bool = False,
) -> dict[str, int]:
    """Create investment positions: 1 to buy, -1 to sell, 0 to do nothing"""
    print("\nCreating investment positions with agent...")
    print(date, markets[0].timeseries.index)
    assert date in markets[0].timeseries.index

    output_dir = (
        OUTPUT_PATH
        / f"smolagent_{model_id}".replace("/", "--")
        / date.strftime("%Y-%m-%d")
    )
    os.makedirs(output_dir, exist_ok=True)
    positions = {}
    for i, question in enumerate(prices_df.columns):
        if (output_dir / f"{question[:50]}.json").exists():
            print(
                f"Getting the result for '{question}' for {model_id} on {date} from file."
            )
            response = json.load(open(output_dir / f"{question[:50]}.json"))
            choice = response["choice"]
        else:
            print(f"NOT FOUND: {output_dir / f'{question[:50]}.json'}")
            market = markets[i]
            assert market.question == question
            if np.isnan(prices_df.loc[date, question]):
                continue
            prices_str = (
                prices_df.loc[:date, question]
                .dropna()
                .to_string(index=True, header=False)
            )
            full_question = textwrap.dedent(
                f"""Let's say we are the {date.strftime("%B %d, %Y")}.
                Please answer the below question by yes or no. But first, run a detailed analysis. You can search the web for information.
                One good method for analyzing is to break down the question into sub-parts, like a tree, and assign probabilities to each sub-branch of the tree, to get a total probability of the question being true.
                Here is the question:
                {question}
                More details:
                {market.description}

                Here are the latest rates for the 'yes' to that question (rates for 'yes' and 'no' sum to 1), to guide you:
                {prices_str}

                Invest in yes only if you think the yes is underrated, and invest in no only if you think that the yes is overrated.
                What would you decide: buy yes, buy no, or do nothing?
                """
            )
            if model_id.endswith("-deep-research"):
                response = run_deep_research(
                    model_id,
                    full_question,
                    cutoff_date=date,
                )
            elif model_id == "test_random":
                response = RunResult(
                    output=("yes" if np.random.random() < 0.3 else "nothing"),
                    messages=[{"value": "ok here is the reasoning process"}],
                    state={},
                    token_usage=TokenUsage(0, 0),
                    timing=Timing(0.0),
                )
            else:
                response = run_smolagent(
                    model_id,
                    full_question,
                    cutoff_date=date,
                )
                for message in response.messages:
                    message["model_input_messages"] = "removed"  # Clean logs
            choice = response.output

            with open(output_dir / f"{question[:50]}.json", "w") as f:
                json.dump(
                    {
                        "question": question,
                        "choice": choice,
                        "messages": response.messages,
                    },
                    f,
                    default=str,
                )
        position = 0 if choice == "nothing" else (1 if choice == "yes" else -1)
        positions[question] = position
    return positions


def get_filtered_markets(today: date, n_markets: int = 10) -> list[Market]:
    request = MarketRequest(
        limit=n_markets * 10,
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

    output_dir = OUTPUT_PATH
    output_dir.mkdir(exist_ok=True)
    questions_file = output_dir / "interesting_questions.json"

    if questions_file.exists():
        print("LOADING INTERESTING QUESTIONS FROM FILE")
        with open(questions_file, "r") as f:
            interesting_questions = json.load(f)
    else:
        interesting_questions = filter_interesting_questions(
            [market.question for market in markets]
        )
        with open(questions_file, "w") as f:
            json.dump(interesting_questions, f, indent=2)
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

    target_dates = [date(2025, 7, 25), date(2025, 8, 1)]
    final_pnls = {}

    for model_id in [
        "huggingface/openai/gpt-oss-120b",
        "huggingface/openai/gpt-oss-20b",
        "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507",
        "huggingface/deepseek-ai/DeepSeek-R1-0528",
        "huggingface/Qwen/Qwen3-4B-Thinking-2507",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4.1-mini",
        "o4-mini",
        "gpt-5",
        "gpt-5-mini",
        "o3-deep-research",
        "test_random",
        # "anthropic/claude-sonnet-4-20250514",
    ]:
        list_positions = []
        agent_name = f"smolagent_{model_id.replace('/', '--')}"
        try:
            for target_date in target_dates:
                positions = agent_invest_positions(
                    model_id, markets, prices_df, target_date
                )
                list_positions.append(positions)
        except Exception as e:
            print(f"Error for {model_id}: {e}")
            continue

        # Create DataFrame with positions on target dates
        print(list_positions, target_dates, len(list_positions), len(target_dates))
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

        engine = PnlCalculator(positions_df, returns_df)

        fig = engine.plot_pnl(stock_details=True)

        print(engine.get_performance_metrics().round(2))

        output_path = f"./portfolio_performance/{agent_name}"
        fig.write_html(output_path + ".html")
        fig.write_image(output_path + ".png")
        print(
            f"\nPortfolio visualization saved to: {output_path}.html and {output_path}.png"
        )

        cumulative_pnl = engine.pnl.sum(axis=1).cumsum()
        if not cumulative_pnl.empty:
            final_pnl = cumulative_pnl.iloc[-1]
            print(f"Final Cumulative PnL: {final_pnl:.4f}")

        final_pnls[agent_name] = final_pnl

        print(cumulative_pnl)
    print("Final PnL per agent:")

    print(json.dumps(final_pnls, indent=2))
