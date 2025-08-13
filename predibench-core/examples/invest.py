from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

from predibench.agent import launch_agent_investments
from predibench.pnl import compute_pnls
from predibench.polymarket_api import get_historical_returns
from predibench.utils import OUTPUT_PATH, choose_markets, collect_investment_choices

load_dotenv()

@dataclass(frozen=True)
class InvestmentHyperparameters:
    """Configuration parameters for investment simulation."""
    n_markets: int
    end_date: date
    investment_dates: list[date]
    model_names: list[str]

HYPERPARAMETERS = InvestmentHyperparameters(
    n_markets=10,
    end_date=date(2025, 8, 1),
    investment_dates=[date(2025, 7, 25), date(2025, 8, 1)],
    model_names=[
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
    ],
)


def main(hyperparams: InvestmentHyperparameters) -> None:
    """Run the investment simulation with multiple AI models."""
    
    selected_markets = choose_markets(
        today_date=hyperparams.end_date, n_markets=hyperparams.n_markets
    )
    returns_df, prices_data = get_historical_returns(markets=selected_markets)

    launch_agent_investments(
        list_models=hyperparams.model_names, 
        investment_dates=hyperparams.investment_dates, 
        prices_df=prices_data, 
        markets=selected_markets
    )

    positions_data = collect_investment_choices(output_path=OUTPUT_PATH)
    final_pnl_results, cumulative_pnl_results, visualization_figures = compute_pnls(
        investment_dates=hyperparams.investment_dates, positions_df=positions_data
    )

    print("Final PnL per agent:")
    print(final_pnl_results)


if __name__ == "__main__":
    main(hyperparams=HYPERPARAMETERS)
