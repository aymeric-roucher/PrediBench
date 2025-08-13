from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

from predibench.agent import launch_agent_investments, launch_agent_event_investments
from predibench.pnl import compute_pnls, get_historical_returns
from predibench.common import OUTPUT_PATH
from predibench.utils import collect_investment_choices
from predibench.market_selection import choose_markets, choose_events

load_dotenv()


@dataclass(frozen=True)
class InvestmentHyperparameters:
    """Configuration parameters for investment simulation."""
    n_events: int
    end_date: date
    investment_dates: list[date]
    model_names: list[str]
    use_events: bool = True  # Toggle between event-based and market-based


HYPERPARAMETERS = InvestmentHyperparameters(
    n_events=3,
    end_date=date(2025, 8, 1),
    investment_dates=[date(2025, 7, 25), date(2025, 8, 1)],
    use_events=True,
    model_names=[
        "test_random",
        # "gpt-4.1-mini",  # Commented out for testing without API keys
        # Add back other models once testing is complete
        # "huggingface/openai/gpt-oss-120b",
        # "huggingface/openai/gpt-oss-20b",
        # "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507",
        # "huggingface/deepseek-ai/DeepSeek-R1-0528",
        # "huggingface/Qwen/Qwen3-4B-Thinking-2507",
        # "gpt-4.1",
        # "gpt-4o",
        # "o4-mini",
        # "gpt-5",
        # "gpt-5-mini",
        # "o3-deep-research",
        # "anthropic/claude-sonnet-4-20250514",
    ],
)


def run_event_based_investment(hyperparams: InvestmentHyperparameters) -> None:
    """Run event-based investment simulation with multiple AI models."""
    print("Using event-based investment approach")
    
    selected_events = choose_events(
        today_date=hyperparams.end_date, 
        n_events=hyperparams.n_events
    )
    
    print(f"Selected {len(selected_events)} events for analysis")
    for event in selected_events:
        print(f"- {event.title} (Volume: ${event.volume:,.0f})")
    
    launch_agent_event_investments(
        list_models=hyperparams.model_names,
        investment_dates=hyperparams.investment_dates,
        events=selected_events
    )
    
    print("Event-based investment analysis complete!")
    # TODO: Implement PnL calculation for event-based investments


def run_market_based_investment(hyperparams: InvestmentHyperparameters) -> None:
    """Run legacy market-based investment simulation with multiple AI models."""
    print("Using legacy market-based investment approach") 
    
    selected_markets = choose_markets(
        today_date=hyperparams.end_date, 
        n_markets=hyperparams.n_events  # Use n_events for backward compatibility
    )
    returns_df, prices_data = get_historical_returns(markets=selected_markets)

    launch_agent_investments(
        list_models=hyperparams.model_names,
        investment_dates=hyperparams.investment_dates,
        prices_df=prices_data,
        markets=selected_markets,
    )

    positions_data = collect_investment_choices(output_path=OUTPUT_PATH)
    final_pnl_results, cumulative_pnl_results, visualization_figures = compute_pnls(
        investment_dates=hyperparams.investment_dates, positions_df=positions_data
    )

    print("Final PnL per agent:")
    print(final_pnl_results)


def main(hyperparams: InvestmentHyperparameters) -> None:
    """Run the investment simulation with multiple AI models."""
    
    if hyperparams.use_events:
        run_event_based_investment(hyperparams)
    else:
        run_market_based_investment(hyperparams)


if __name__ == "__main__":
    main(hyperparams=HYPERPARAMETERS)
