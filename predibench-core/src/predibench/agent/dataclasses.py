from datetime import date

from pydantic import BaseModel, Field


class MarketInvestmentResult(BaseModel):
    market_id: str
    market_question: str
    market_odds: float = Field(
        ..., ge=0.0, le=1.0
    )  # Current market price/odds (0.0 to 1.0) # NOTE: price of 'yes' and odd of 'yes' should be equal, since normalized to 1
    model_odds: float = Field(
        ..., ge=0.0, le=1.0
    )  # Model's assessment of probability (0.0 to 1.0)
    model_bet: float = Field(
        ..., ge=-1.0, le=1.0
    )  # Model's bet on this market (-1.0 to 1.0, sums of absolute values must be 1 with bets on other markets from this event)
    model_rationale: str


class EventInvestmentResult(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_decisions: list[MarketInvestmentResult]  # Multiple markets per event


class ModelInvestmentResult(BaseModel):
    model_id: str
    target_date: date
    event_results: list[EventInvestmentResult]
