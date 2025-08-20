from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel
import random

app = FastAPI(title="Polymarket LLM Benchmark API", version="1.0.0")

# CORS for local development only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Data models
class PerformanceHistory(BaseModel):
    date: str
    score: float

class LeaderboardEntry(BaseModel):
    id: str
    model: str
    score: float
    accuracy: float
    trades: int
    profit: int
    lastUpdated: str
    trend: str
    performanceHistory: List[PerformanceHistory]

class Event(BaseModel):
    id: str
    title: str
    description: str
    probability: float
    volume: int
    endDate: str
    category: str
    status: str

class Stats(BaseModel):
    topScore: float
    avgAccuracy: float
    totalTrades: int
    totalProfit: int

# Mock data generation
def generate_performance_history(base_score: float, days: int = 5) -> List[PerformanceHistory]:
    history = []
    current_score = base_score - random.uniform(3, 8)
    base_date = datetime.now() - timedelta(days=days-1)
    
    for i in range(days):
        date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        # Add some realistic variation
        variation = random.uniform(-1.5, 2.0) if i > 0 else 0
        current_score = max(0, min(100, current_score + variation))
        
        history.append(PerformanceHistory(
            date=date,
            score=round(current_score, 1)
        ))
    
    return history

# Generate mock leaderboard data
def get_mock_leaderboard() -> List[LeaderboardEntry]:
    models = [
        {"name": "GPT-5", "base_score": 94.2, "accuracy": 0.87, "trend": "up"},
        {"name": "Claude-4", "base_score": 92.8, "accuracy": 0.85, "trend": "up"},
        {"name": "GPT-4o", "base_score": 89.1, "accuracy": 0.82, "trend": "stable"},
        {"name": "Gemini Pro", "base_score": 86.5, "accuracy": 0.79, "trend": "down"},
        {"name": "LLaMA-3.1", "base_score": 84.3, "accuracy": 0.76, "trend": "up"},
        {"name": "Mixtral-8x7B", "base_score": 81.7, "accuracy": 0.73, "trend": "stable"},
    ]
    
    leaderboard = []
    for i, model in enumerate(models):
        trades = random.randint(70, 150)
        profit = int(model["base_score"] * trades * random.uniform(0.8, 1.2))
        
        entry = LeaderboardEntry(
            id=str(i + 1),
            model=model["name"],
            score=model["base_score"],
            accuracy=model["accuracy"],
            trades=trades,
            profit=profit,
            lastUpdated=datetime.now().strftime("%Y-%m-%d"),
            trend=model["trend"],
            performanceHistory=generate_performance_history(model["base_score"])
        )
        leaderboard.append(entry)
    
    return sorted(leaderboard, key=lambda x: x.score, reverse=True)

# Generate mock events data
def get_mock_events() -> List[Event]:
    events_data = [
        {
            "title": "Will Bitcoin reach $100K by end of 2025?",
            "description": "Bitcoin price prediction for end of year 2025",
            "probability": 0.72,
            "volume": 1250000,
            "endDate": "2025-12-31",
            "category": "Crypto"
        },
        {
            "title": "US Election 2028 - Democratic Nominee",
            "description": "Who will be the Democratic nominee for President in 2028?",
            "probability": 0.45,
            "volume": 890000,
            "endDate": "2028-07-01",
            "category": "Politics"
        },
        {
            "title": "AI Breakthrough in 2025",
            "description": "Will there be a major AI breakthrough announcement in 2025?",
            "probability": 0.68,
            "volume": 675000,
            "endDate": "2025-12-31",
            "category": "Technology"
        },
        {
            "title": "Climate Goals Met by 2030",
            "description": "Will global climate targets be achieved by 2030?",
            "probability": 0.23,
            "volume": 445000,
            "endDate": "2030-12-31",
            "category": "Environment"
        },
        {
            "title": "SpaceX Mars Landing 2026",
            "description": "Will SpaceX successfully land humans on Mars by 2026?",
            "probability": 0.35,
            "volume": 820000,
            "endDate": "2026-12-31",
            "category": "Technology"
        },
        {
            "title": "Ethereum 2.0 Fully Deployed",
            "description": "Will Ethereum 2.0 be fully operational by end of 2025?",
            "probability": 0.89,
            "volume": 560000,
            "endDate": "2025-12-31",
            "category": "Crypto"
        }
    ]
    
    events = []
    for i, event_data in enumerate(events_data):
        event = Event(
            id=str(i + 1),
            title=event_data["title"],
            description=event_data["description"],
            probability=event_data["probability"],
            volume=event_data["volume"],
            endDate=event_data["endDate"],
            category=event_data["category"],
            status="active"
        )
        events.append(event)
    
    return events

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Polymarket LLM Benchmark API", "version": "1.0.0"}

@app.get("/api/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard():
    """Get the current leaderboard with LLM performance data"""
    return get_mock_leaderboard()

@app.get("/api/events", response_model=List[Event])
async def get_events():
    """Get active Polymarket events"""
    return get_mock_events()

@app.get("/api/stats", response_model=Stats)
async def get_stats():
    """Get overall benchmark statistics"""
    leaderboard = get_mock_leaderboard()
    
    return Stats(
        topScore=max(entry.score for entry in leaderboard),
        avgAccuracy=sum(entry.accuracy for entry in leaderboard) / len(leaderboard),
        totalTrades=sum(entry.trades for entry in leaderboard),
        totalProfit=sum(entry.profit for entry in leaderboard)
    )

@app.get("/api/model/{model_id}", response_model=LeaderboardEntry)
async def get_model_details(model_id: str):
    """Get detailed information for a specific model"""
    leaderboard = get_mock_leaderboard()
    model = next((entry for entry in leaderboard if entry.id == model_id), None)
    
    if not model:
        return {"error": "Model not found"}
    
    return model

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)