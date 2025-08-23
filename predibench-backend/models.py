from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


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


class PredictionSubmission(BaseModel):
    """Model for prediction submissions"""
    event_id: str
    market_decisions: List[dict]  # List of market decisions
    rationale: Optional[str] = None


class SubmissionResponse(BaseModel):
    """Response model for submission confirmation"""
    success: bool
    message: str
    submission_id: Optional[str] = None
    agent_name: Optional[str] = None


class AgentTokenUpdate(BaseModel):
    """Model for token regeneration"""
    agent_id: str