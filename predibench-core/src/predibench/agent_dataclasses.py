from pydantic import BaseModel
from typing import Literal
from datetime import date

class MarketInvestmentDecision(BaseModel):
    market_id: str
    market_question: str
    decision: Literal["BUY", "SELL", "NOTHING"]
    rationale: str | None = None
    market_price: float | None = None
    is_closed: bool = False


class EventInvestmentResult(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_decision: MarketInvestmentDecision


class ModelInvestmentResult(BaseModel):
    model_id: str
    target_date: date
    event_results: list[EventInvestmentResult]


class EventDecisions(BaseModel):
    rationale: str
    decision: Literal["BUY", "SELL", "NOTHING"]
