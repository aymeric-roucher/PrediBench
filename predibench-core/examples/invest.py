from datetime import date

from dotenv import load_dotenv
from predibench.agent import launch_agent_investments
from predibench.pnl import compute_pnls
from predibench.polymarket_api import (
    get_historical_returns,
)
from predibench.utils import OUTPUT_PATH, choose_markets, collect_investment_choices

load_dotenv()

portfolio_performance_path = OUTPUT_PATH / "portfolio_performance"
if not portfolio_performance_path.exists():
    portfolio_performance_path.mkdir(parents=True)


if __name__ == "__main__":
    N_MARKETS = 10

    # today = datetime.now().replace(tzinfo=None).date()
    end_date = date(2025, 8, 1)

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

    launch_agent_investments(list_models, investment_dates, prices_df, markets)

    positions_df = collect_investment_choices(output_path=OUTPUT_PATH)
    final_pnls, cumulative_pnls, figures = compute_pnls(investment_dates, positions_df)

    print("Final PnL per agent:")

    print(final_pnls)
