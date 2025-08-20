from pydantic import BaseModel
from typing import Literal
from datetime import date


class BettingResult(BaseModel):
    direction: Literal["buy_yes", "buy_no", "nothing"]
    amount: float  # Fraction of allocated capital (0.0 to 1.0)
    reasoning: str


class MarketInvestmentResult(BaseModel):
    market_id: str
    market_question: str
    probability_assessment: float  # Model's assessment of probability (0.0 to 1.0)
    market_odds: float  # Current market price/odds (0.0 to 1.0)
    confidence_in_assessment: float  # Confidence level (0.0 to 1.0)
    betting_decision: BettingResult
    market_price: float | None = None
    is_closed: bool = False


class EventInvestmentResult(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_decisions: list[MarketInvestmentResult]  # Multiple markets per event


class ModelInvestmentResult(BaseModel):
    model_id: str
    target_date: date
    event_results: list[EventInvestmentResult]
