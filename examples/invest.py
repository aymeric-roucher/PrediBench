import json
import os
import textwrap
from datetime import date, timedelta
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
) -> None:
    """Create investment positions: 1 to buy, -1 to sell, 0 to do nothing"""
    print("\nCreating investment positions with agent...")
    print(date, markets[0].prices.index)
    assert date in markets[0].prices.index

    output_dir = (
        OUTPUT_PATH
        / f"smolagent_{model_id}".replace("/", "--")
        / date.strftime("%Y-%m-%d")
    )
    os.makedirs(output_dir, exist_ok=True)
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
    return


def validate_continuous_returns(
    returns_df: pd.DataFrame, start_date: date, end_date: date
) -> None:
    """Validate that returns data is continuous for the given date range.

    Args:
        returns_df: DataFrame with returns data indexed by date
        start_date: First date that should have data
        end_date: Last date that should have data

    Raises:
        ValueError: If any dates are missing from the range
    """
    expected_date_range = pd.date_range(start=start_date, end=end_date, freq="D").date
    actual_dates = set(returns_df.index)
    expected_dates = set(expected_date_range)

    missing_dates = expected_dates - actual_dates
    if missing_dates:
        raise ValueError(f"Missing returns data for dates: {sorted(missing_dates)}")


def collect_investment_choices(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    positions = []
    for agent_name in os.listdir(output_path):
        if os.path.isdir(output_path / agent_name):
            for date_folder in os.listdir(output_path / agent_name):
                for file in os.listdir(output_path / agent_name / date_folder):
                    if file.endswith(".json"):
                        with open(
                            output_path / agent_name / date_folder / file, "r"
                        ) as f:
                            data = json.load(f)
                        try:
                            positions.append(
                                {
                                    "agent_name": agent_name,
                                    "date": date.fromisoformat(date_folder),
                                    "question": data["question"],
                                    "choice": (
                                        0
                                        if data["choice"] == "nothing"
                                        else (1 if data["choice"] == "yes" else -1)
                                    ),
                                    "question_id": data["id"],
                                }
                            )
                        except Exception as e:
                            print(f"Error for {file}: {e}")
                            print(data)
                            raise e
                            continue
    return pd.DataFrame.from_records(positions)


def choose_markets(end_date: date, n_markets: int = 10) -> list[Market]:
    request = MarketRequest(
        limit=n_markets * 10,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=end_date + timedelta(days=1),
        end_date_max=end_date + timedelta(days=21),
    )
    markets = get_open_markets(
        request,
        add_timeseries=[
            end_date - timedelta(days=15),
            end_date,
        ],  # 15 days back is the maximum allowed by the API
    )
    markets = filter_out_resolved_markets(markets)

    output_dir = OUTPUT_PATH
    output_dir.mkdir(exist_ok=True)
    questions_file = output_dir / "interesting_questions.json"
    old_questions_file = output_dir / "interesting_questions_old.json"

    if old_questions_file.exists():
        print("LOADING INTERESTING QUESTIONS FROM FILE")
        with open(old_questions_file, "r") as f:
            interesting_questions = json.load(f)
    else:
        interesting_questions = filter_interesting_questions(
            [market.question for market in markets]
        )
    markets = [market for market in markets if market.question in interesting_questions]

    with open(questions_file, "w") as f:
        json.dump(
            {
                market.id: market.model_dump(mode="json", exclude={"prices"})
                for market in markets
            },
            f,
            indent=2,
        )
    markets = markets[:n_markets]
    assert len(markets) == n_markets
    return markets


def compute_cumulative_pnl(
    positions_agent_df: pd.DataFrame, returns_df: pd.DataFrame, prices_df: pd.DataFrame
) -> pd.DataFrame:
    # Convert positions_agent_df to have date as index, question as columns, and choice as values
    positions_agent_df = positions_agent_df.pivot(
        index="date", columns="question", values="choice"
    )

    # Forward-fill positions to all daily dates in the returns range
    daily_index = returns_df.index[returns_df.index >= investment_dates[0]]
    positions_agent_df = positions_agent_df.reindex(daily_index, method="ffill")
    positions_agent_df = positions_agent_df.loc[
        positions_agent_df.index >= investment_dates[0]
    ]
    returns_df = returns_df.loc[returns_df.index >= investment_dates[0]]

    positions_agent_df = positions_agent_df.loc[
        :, positions_agent_df.columns.isin(returns_df.columns)
    ]
    print("\nAnalyzing portfolio performance with PnlCalculator...")

    print("\nPositions Table (first 15 rows):")
    print(positions_agent_df.head(15))
    print(f"\nPositions shape: {positions_agent_df.shape}")

    print("\nReturns Table (first 15 rows):")
    print(returns_df.head(15))
    print(f"\nReturns shape: {returns_df.shape}")

    print("\nData summary:")
    print(
        f"  Investment positions: {(positions_agent_df != 0.0).sum().sum()} out of {positions_agent_df.size} possible"
    )
    print(
        f"  Non-zero returns: {(returns_df != 0).sum().sum()} out of {returns_df.notna().sum().sum()} non-NaN"
    )
    print(
        f"  Returns range: {returns_df.min().min():.4f} to {returns_df.max().max():.4f}"
    )

    engine = PnlCalculator(positions_agent_df, returns_df, prices_df)

    fig = engine.plot_pnl(stock_details=True)

    print(engine.get_performance_metrics().round(2))

    cumulative_pnl = engine.pnl.sum(axis=1).cumsum()
    return cumulative_pnl, fig


if __name__ == "__main__":
    N_MARKETS = 10

    # today = datetime.now().replace(tzinfo=None).date()
    end_date = date(2025, 8, 1)

    if False:
        markets = choose_markets(end_date, n_markets=N_MARKETS)
        returns_df, prices_df = get_historical_returns(markets)

    investment_dates = [date(2025, 7, 25), date(2025, 8, 1)]

    list_models = [
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
    ]

    def launch_agent_investments(list_models, investment_dates, prices_df, markets):
        for model_id in list_models:
            try:
                for investment_date in investment_dates:
                    agent_invest_positions(
                        model_id, markets, prices_df, investment_date
                    )
            except Exception as e:
                print(f"Error for {model_id}: {e}")
                # raise e
                continue

    if False:
        launch_agent_investments(list_models, investment_dates, prices_df, markets)

    def get_choices_compute_pnls(investment_dates, output_path: Path = OUTPUT_PATH):
        # Validate that we have continuous returns data
        expected_start = investment_dates[0]
        expected_end = investment_dates[-1] + timedelta(days=7)

        positions_df = collect_investment_choices(output_path)
        markets = []
        for question_id in positions_df["question_id"].unique():
            request = MarketRequest(
                id=question_id,
            )
            market = get_open_markets(
                request,
                add_timeseries=[
                    expected_start,
                    expected_end,
                ],  # 15 days back is the maximum allowed by the API
            )[0]
            markets.append(market)
        returns_df, prices_df = get_historical_returns(markets)

        validate_continuous_returns(returns_df, expected_start, expected_end)

        final_pnls = {}
        for agent_name in positions_df["agent_name"].unique():
            positions_agent_df = positions_df[
                positions_df["agent_name"] == agent_name
            ].drop(columns=["agent_name"])
            positions_agent_df = positions_agent_df.loc[
                positions_agent_df["date"].isin(investment_dates)
            ]
            positions_agent_df = positions_agent_df.loc[
                positions_df["question"].isin(returns_df.columns)
            ]  # TODO: This should be removed when we can save

            cumulative_pnl, fig = compute_cumulative_pnl(positions_agent_df, returns_df, prices_df)

            portfolio_output_path = f"./portfolio_performance/{agent_name}"
            fig.write_html(portfolio_output_path + ".html")
            fig.write_image(portfolio_output_path + ".png")
            print(
                f"\nPortfolio visualization saved to: {portfolio_output_path}.html and {portfolio_output_path}.png"
            )

            final_pnl = float(cumulative_pnl.iloc[-1])
            print(f"Final Cumulative PnL for {agent_name}: {final_pnl:.4f}")
            print(cumulative_pnl)

            final_pnls[agent_name] = final_pnl
        return final_pnls

    final_pnls = get_choices_compute_pnls(investment_dates, output_path=OUTPUT_PATH)

    print("Final PnL per agent:")

    print(final_pnls)
