from datetime import date, timedelta
from unittest.mock import patch

from predibench.agent.dataclasses import (
    EventInvestmentResult,
    MarketInvestmentResult,
    ModelInvestmentResult,
)
from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from smolagents.models import InferenceClientModel


def create_mock_investment_results(models, target_date):
    """Create mock investment results for testing."""
    return [
        ModelInvestmentResult(
            model_id=model.model_id if hasattr(model, "model_id") else str(model),
            target_date=target_date,
            event_results=[
                EventInvestmentResult(
                    event_id="test_event_1",
                    event_title="Test Event 1",
                    event_description="Test event description",
                    market_decision=MarketInvestmentResult(
                        market_id="test_market_1",
                        market_question="Test market question?",
                        decision="BUY",
                        rationale="Test rationale for buying",
                        market_price=0.55,
                        is_closed=False,
                    ),
                ),
            ],
        )
        for model in models
    ]


@patch("predibench.invest.run_agent_investments")
def test_invest(mock_run_agent_investments):
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]
    target_date = date(2025, 7, 16)

    # Set up mock return value
    mock_run_agent_investments.return_value = create_mock_investment_results(
        models, target_date
    )

    result = run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
        target_date=target_date,
    )

    # Verify the mock was called and returned expected results
    mock_run_agent_investments.assert_called_once()
    assert len(result) == 1
    assert result[0].model_id == "openai/gpt-oss-120b"
    assert result[0].target_date == target_date


@patch("predibench.invest.run_agent_investments")
def test_invest_backward(mock_run_agent_investments):
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]
    target_date = date(2025, 7, 16)

    # Set up mock return value
    mock_run_agent_investments.return_value = create_mock_investment_results(
        models, target_date
    )

    result = run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
        target_date=target_date,
    )

    # Verify the mock was called and returned expected results
    mock_run_agent_investments.assert_called_once()
    assert len(result) == 1
    assert result[0].model_id == "openai/gpt-oss-120b"
    assert result[0].target_date == target_date
