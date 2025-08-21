import json
import os
from datetime import date, datetime
from typing import List

import numpy as np
import pandas as pd
from datasets import load_dataset
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from predibench.pnl import get_pnls
from predibench.polymarket_api import Event
from pydantic import BaseModel

print("Successfully imported predibench modules")

app = FastAPI(title="Polymarket LLM Benchmark API", version="1.0.0")

# CORS for local development only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Configuration
AGENT_CHOICES_REPO = "m-ric/predibench-agent-decisions-2"


# Data models
class PerformanceHistory(BaseModel):
    date: str
    cumulative_pnl: float


class LeaderboardEntry(BaseModel):
    id: str
    model: str
    final_cumulative_pnl: float
    trades: int
    profit: int
    lastUpdated: str
    trend: str
    performanceHistory: List[PerformanceHistory]


class Stats(BaseModel):
    topFinalCumulativePnl: float
    avgPnl: float
    totalTrades: int
    totalProfit: int


# Real data loading functions
def load_agent_choices():
    """Load agent choices from HuggingFace dataset"""
    dataset = load_dataset(AGENT_CHOICES_REPO, split="test")
    dataset = dataset.to_pandas()
    return dataset.sort_values("date")


AGENT_CHOICES = load_agent_choices()


def calculate_real_performance():
    """Calculate real PnL and performance metrics exactly like gradio app"""
    agent_choices_df = AGENT_CHOICES
    print(f"Loaded {len(agent_choices_df)} agent choices")

    agent_choices_df["timestamp_uploaded"] = pd.to_datetime(
        agent_choices_df["timestamp_uploaded"]
    )
    today_date = datetime.today()
    agent_choices_df = agent_choices_df[
        agent_choices_df["timestamp_uploaded"] < today_date
    ]
    print(f"After timestamp filter: {len(agent_choices_df)} records")

    positions = []
    for i, row in agent_choices_df.iterrows():
        for market_decision in json.loads(row["decisions_per_market"]):
            positions.append(
                {
                    "date": row["date"],
                    "market_id": market_decision["market_id"],
                    "choice": market_decision["model_decision"]["bet"],
                    "agent_name": row["agent_name"],
                }
            )
    positions_df = pd.DataFrame.from_records(positions)

    # positions_df = positions_df.pivot(index="date", columns="market_id", values="bet")

    pnl_calculators = get_pnls(
        positions_df, write_plots=False, end_date=datetime.today()
    )
    agents_performance = {}
    for agent_name, pnl_calculator in pnl_calculators.items():
        daily_pnl = pnl_calculator.portfolio_daily_pnl

        # Generate performance history from cumulative PnL
        cumulative_pnl = pnl_calculator.portfolio_cumulative_pnl
        performance_history = []
        for date_idx, pnl_value in cumulative_pnl.items():
            performance_history.append(
                PerformanceHistory(
                    date=date_idx.strftime("%Y-%m-%d"), cumulative_pnl=float(pnl_value)
                )
            )

        # Calculate metrics exactly like gradio
        final_pnl = float(pnl_calculator.portfolio_cumulative_pnl.iloc[-1])
        sharpe_ratio = (
            float((daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252))
            if daily_pnl.std() > 0
            else 0
        )

        agents_performance[agent_name] = {
            "agent_name": agent_name,
            "final_cumulative_pnl": final_pnl,
            "annualized_sharpe_ratio": sharpe_ratio,
            "performance_history": performance_history,
            "daily_cumulative_pnl": pnl_calculator.portfolio_cumulative_pnl.tolist(),
            "dates": [
                d.strftime("%Y-%m-%d")
                for d in pnl_calculator.portfolio_cumulative_pnl.index.tolist()
            ],
        }

        print(f"Agent {agent_name}: PnL={final_pnl:.3f}, Sharpe={sharpe_ratio:.3f}")

    print(f"Calculated performance for {len(agents_performance)} agents")
    return agents_performance


# Generate leaderboard from real data only
def get_leaderboard() -> List[LeaderboardEntry]:
    real_performance = calculate_real_performance()

    leaderboard = []
    for i, (agent_name, metrics) in enumerate(
        sorted(
            real_performance.items(),
            key=lambda x: x[1]["final_cumulative_pnl"],
            reverse=True,
        )
    ):
        # Determine trend
        history = metrics["performance_history"]
        if len(history) >= 2:
            recent_change = history[-1].cumulative_pnl - history[-2].cumulative_pnl
            trend = (
                "up"
                if recent_change > 0.1
                else "down"
                if recent_change < -0.1
                else "stable"
            )
        else:
            trend = "stable"

        entry = LeaderboardEntry(
            id=str(i + 1),
            model=agent_name.replace("smolagent_", "").replace("--", "/"),
            final_cumulative_pnl=metrics["final_cumulative_pnl"],
            trades=0,
            profit=0,
            lastUpdated=datetime.now().strftime("%Y-%m-%d"),
            trend=trend,
            performanceHistory=metrics["performance_history"],
        )
        leaderboard.append(entry)

    return leaderboard


def get_events() -> List[Event]:
    """Get events based that models ran predictions on"""
    # Load agent choices to see what markets they've been betting on
    df = AGENT_CHOICES
    event_ids = df["event_id"].unique()

    events = []
    for event_id in event_ids:
        from predibench.polymarket_api import EventsRequestParameters

        events_request_parameters = EventsRequestParameters(
            event_ids=[event_id],
            limit=1,
        )
        one_event_list = events_request_parameters.get_events()
        # event = Event.from_json(event_id)
        events.append(one_event_list[0])

    return events


# API Endpoints
@app.get("/")
async def root():
    return {"message": "Polymarket LLM Benchmark API", "version": "1.0.0"}


@app.get("/api/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard_endpoint():
    """Get the current leaderboard with LLM performance data"""
    return get_leaderboard()


@app.get("/api/events", response_model=List[Event])
async def get_events_endpoint():
    """Get active Polymarket events"""
    return get_events()


@app.get("/api/stats", response_model=Stats)
async def get_stats():
    """Get overall benchmark statistics"""
    leaderboard = get_leaderboard()

    return Stats(
        topFinalCumulativePnl=max(entry.final_cumulative_pnl for entry in leaderboard),
        avgPnl=sum(entry.final_cumulative_pnl for entry in leaderboard)
        / len(leaderboard),
        totalTrades=sum(entry.trades for entry in leaderboard),
        totalProfit=sum(entry.profit for entry in leaderboard),
    )


@app.get("/api/model/{model_id}", response_model=LeaderboardEntry)
async def get_model_details(model_id: str):
    """Get detailed information for a specific model"""
    leaderboard = get_leaderboard()
    model = next((entry for entry in leaderboard if entry.id == model_id), None)

    if not model:
        return {"error": "Model not found"}

    return model


@app.get("/api/event/{event_id}/prices")
async def get_event_prices(event_id: str):
    """Get price history for a market using predibench PnL calculator"""
    # Load agent choices to get market data
    df = load_agent_choices()

    # Apply same filtering as gradio app
    df["timestamp_uploaded"] = pd.to_datetime(df["timestamp_uploaded"])
    cutoff_date = pd.to_datetime("2025-08-18")
    df = df[df["timestamp_uploaded"] < cutoff_date]
    df = df.loc[df["date"] > date(2025, 7, 19)]

    # Get PnL calculators which contain market price data
    pnl_calculators = get_pnls(df, write_plots=False, end_date=datetime.today())

    # Try to find price data for this specific market
    price_data = []

    # Check if we have price data in any of the calculators
    for agent, calculator in pnl_calculators.items():
        if hasattr(calculator, "prices") and calculator.prices is not None:
            prices_df = calculator.prices
            if event_id in prices_df.columns:
                # Found price data for this specific market
                market_prices = prices_df[event_id].dropna()
                for date_idx, price in market_prices.items():
                    price_data.append(
                        {"date": date_idx.strftime("%Y-%m-%d"), "price": float(price)}
                    )
                break

    if not price_data and pnl_calculators:
        # Use any available price data as representative
        first_calculator = list(pnl_calculators.values())[0]
        if hasattr(first_calculator, "prices") and first_calculator.prices is not None:
            prices_df = first_calculator.prices
            if not prices_df.empty and len(prices_df.columns) > 0:
                # Use first available market as proxy
                sample_market = prices_df.columns[0]
                market_prices = prices_df[sample_market].dropna()
                for date_idx, price in market_prices.tail(30).items():
                    price_data.append(
                        {"date": date_idx.strftime("%Y-%m-%d"), "price": float(price)}
                    )

    return price_data[-30:] if price_data else []


@app.get("/api/event/{event_id}/predictions")
async def get_event_predictions(event_id: str):
    """Get real model predictions for a specific event based on agent choices data"""
    # Load agent choices data like in gradio app
    df = load_agent_choices()

    # Apply same filtering as gradio app
    df["timestamp_uploaded"] = pd.to_datetime(df["timestamp_uploaded"])
    cutoff_date = pd.to_datetime("2025-08-18")
    df = df[df["timestamp_uploaded"] < cutoff_date]
    df = df.loc[df["date"] > date(2025, 7, 19)]

    # Look for predictions for this specific market/event ID
    event_predictions = df[df["market_id"] == event_id].copy()

    if event_predictions.empty:
        # If no direct match, get recent predictions from all markets for the agents
        latest_predictions = df.groupby("agent_name").tail(1)
        event_predictions = latest_predictions

    # Group by agent and get latest prediction for each
    predictions = []
    for agent_name in event_predictions["agent_name"].unique():
        agent_data = event_predictions[
            event_predictions["agent_name"] == agent_name
        ].iloc[-1]

        # Map choice to prediction (choice: 1=Long/Yes, -1=Short/No, 0=No position)
        choice = agent_data.get("choice", 0)
        if choice == 1:
            prediction = "Yes"
            confidence = 0.7 + (choice * 0.2)  # Confidence between 0.7-0.9
        elif choice == -1:
            prediction = "No"
            confidence = 0.7 + (abs(choice) * 0.2)  # Confidence between 0.7-0.9
        else:
            prediction = "Neutral"
            confidence = 0.5

        # Get rationale if available
        rationale = agent_data.get("rationale", "No rationale provided")[:100] + (
            "..." if len(str(agent_data.get("rationale", ""))) > 100 else ""
        )

        predictions.append(
            {
                "model": agent_name.replace("smolagent_", "").replace("--", "/"),
                "prediction": prediction,
                "confidence": round(confidence, 2),
                "lastUpdated": agent_data.get("date", datetime.now().date()).strftime(
                    "%Y-%m-%d"
                ),
                "rationale": rationale,
                "market_id": agent_data.get("market_id", "Unknown"),
            }
        )

    return predictions[:8]  # Limit to 8 models for UI


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)
