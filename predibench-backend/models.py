from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Agent model for database and API"""
    id: Optional[str] = None
    name: str
    token: str
    created_at: datetime
    last_used: Optional[datetime] = None
    user_id: str


class AgentCreate(BaseModel):
    """Model for creating a new agent"""
    name: str


class AgentResponse(BaseModel):
    """Response model for agent data"""
    id: str
    name: str
    token: str
    created_at: datetime
    last_used: Optional[datetime] = None


# Simplified submission classes based on ModelInvestmentDecisions
class SimpleMarketDecision(BaseModel):
    """Simplified market decision - only essential fields"""
    market_id: str
    bet: float = Field(..., ge=-1.0, le=1.0, description="Model's bet on this market (-1.0 to 1.0)")

class SimpleEventDecision(BaseModel):
    """Simplified event decision - only essential fields"""
    event_id: str
    market_decisions: List[SimpleMarketDecision]

class AgentSubmission(BaseModel):
    """Agent submission containing multiple events and their market decisions"""
    event_decisions: List[SimpleEventDecision]


class SubmissionResponse(BaseModel):
    """Response model for submission confirmation"""
    success: bool
    message: str
    submission_id: Optional[str] = None
    agent_name: Optional[str] = None


class AgentTokenUpdate(BaseModel):
    """Model for token regeneration"""
    agent_id: str