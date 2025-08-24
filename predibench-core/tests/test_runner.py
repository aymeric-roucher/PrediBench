import json
from datetime import date

from datasets import load_dataset
from predibench.agent.dataclasses import (
    EventInvestmentDecisions,
    MarketInvestmentDecision,
    ModelInvestmentDecisions,
    SingleModelDecision,
)
from predibench.agent.runner import _upload_results_to_hf_dataset


def test_upload_results_to_hf_dataset():
    # Create dummy result with multiple events and markets
    dummy_result = ModelInvestmentDecisions(
        model_id="test_model",
        target_date=date(2025, 8, 21),
        event_investment_decisions=[
            EventInvestmentDecisions(
                event_id="event_1",
                event_title="Test Event 1",
                event_description="First test event",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_1",
                        model_decision=SingleModelDecision(
                            rationale="Bullish on market 1", odds=0.6, bet=0.4
                        ),
                    ),
                    MarketInvestmentDecision(
                        market_id="market_2",
                        model_decision=SingleModelDecision(
                            rationale="Bearish on market 2", odds=0.3, bet=-0.2
                        ),
                    ),
                ],
            ),
            EventInvestmentDecisions(
                event_id="event_2",
                event_title="Test Event 2",
                event_description="Second test event",
                market_investment_decisions=[
                    MarketInvestmentDecision(
                        market_id="market_3",
                        model_decision=SingleModelDecision(
                            rationale="Neutral on market 3", odds=0.5, bet=0.1
                        ),
                    )
                ],
            ),
        ],
    )

    # Call function with dummy dataset name
    _upload_results_to_hf_dataset(
        [dummy_result],
        date(2025, 8, 21),
        dataset_name="Sibyllic/dummy",
        split="test",
        erase_existing=True,
    )
    dataset = load_dataset("Sibyllic/dummy")
    df_dataset = dataset["test"].to_pandas()

    # Test the dataset
    assert len(df_dataset) == 2
    assert len(df_dataset["model_id"].unique()) == 1
    assert len(df_dataset["event_id"].unique()) == 2
    assert "event_1" in df_dataset["event_id"].values
    assert json.loads(df_dataset["decisions_per_market"].iloc[0]) == [
        {
            "market_id": "market_1",
            "model_decision": {
                "rationale": "Bullish on market 1",
                "odds": 0.6,
                "bet": 0.4,
            },
            "market_question": None,
        },
        {
            "market_id": "market_2",
            "model_decision": {
                "rationale": "Bearish on market 2",
                "odds": 0.3,
                "bet": -0.2,
            },
            "market_question": None,
        },
    ]

    _upload_results_to_hf_dataset(
        [dummy_result],
        date(2025, 8, 21),
        dataset_name="Sibyllic/dummy",
        split="test",
        erase_existing=False,
    )
    dataset = load_dataset("Sibyllic/dummy")
    df_dataset = dataset["test"].to_pandas()
    assert len(df_dataset) == 4
