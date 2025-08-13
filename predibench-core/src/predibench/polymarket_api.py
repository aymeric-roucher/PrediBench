from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from predibench.utils import convert_polymarket_time_to_datetime

# TODO: respect rate limits:
# **API Rate Limits**
# Endpoint	Limit	Notes
# /books (website)	300 requests / 10s	Throttle requests over the maximum configured rate
# /books	50 requests / 10s	Throttle requests over the maximum configured rate
# /price	100 requests / 10s	Throttle requests over the maximum configured rate
# markets/0x	50 requests / 10s	Throttle requests over the maximum configured rate
# POST /order	500 requests / 10s (50/s)	Burst; throttle requests over the maximum configured rate
# POST /order	3000 requests / 10 min (5/s)	Throttle requests over the maximum configured rate
# DELETE /order	500 requests / 10s (50/s)	Burst; throttle requests over the maximum configured rate
# DELETE /order	3000 requests / 10 min (5/s)	Throttle requests over the maximum configured rate
from pydantic import BaseModel

from predibench.common import BASE_URL_POLYMARKET

MAX_INTERVAL_TIMESERIES = timedelta(days=14, hours=23, minutes=0)
# NOTE: above is refined by experience: seems independant from the resolution


class MarketOutcome(BaseModel):
    clob_token_id: str
    name: str
    price: float


class Market(BaseModel, arbitrary_types_allowed=True):
    id: str
    question: str
    slug: str
    description: str
    end_date: datetime | None
    createdAt: datetime
    volumeNum: float | None
    volume24hr: float | None
    volume1wk: float | None
    volume1mo: float | None
    volume1yr: float | None
    liquidity: float | None
    outcomes: list[MarketOutcome]
    prices: pd.Series | None = None

    def fill_prices(self, start_time: datetime, end_time: datetime, interval: str = "1d") -> None:
        """Fill the prices field with timeseries data.
        
        Args:
            start_time: Start time for timeseries data
            end_time: End time for timeseries data
            interval: Time interval for data points (default: "1d")
        """
        if self.outcomes and len(self.outcomes) > 0 and self.outcomes[0].clob_token_id:
            ts_request = _HistoricalTimeSeriesRequestParameters(
                market=self.outcomes[0].clob_token_id,
                start_time=start_time,
                end_time=end_time,
                interval=interval,
            )
            self.prices = ts_request.get_token_daily_timeseries()
        else:
            self.prices = None

    @staticmethod
    def from_json(market_data: dict) -> Market | None:
        """Convert a market JSON object to a PolymarketMarket dataclass."""

        if not "outcomes" in market_data:
            print("Outcomes missing for market:\n", market_data["id"], market_data["question"])
            return None
        
        outcomes = json.loads(market_data["outcomes"])
        if len(outcomes) < 2:
            # There should be at least 2 
            # Who will the world's richest person be on February 27, 2021?
            print(f"Expected 2 outcomes, got {len(outcomes)} for market:\n", market_data["id"], market_data["question"])
            return None
        outcome_names = json.loads(market_data["outcomes"])
        
        # Handle missing price data
        if "outcomePrices" in market_data:
            outcome_prices = json.loads(market_data["outcomePrices"])
        else:
            # Default to 0.5 for all outcomes if prices not available
            outcome_prices = [0.5] * len(outcomes)
            
        # Handle missing token IDs
        if "clobTokenIds" in market_data:
            outcome_clob_token_ids = json.loads(market_data["clobTokenIds"])
        else:
            # Use empty strings if token IDs not available
            outcome_clob_token_ids = [""] * len(outcomes)
        return Market(
            id=market_data["id"],
            question=market_data["question"],
            outcomes=[
                MarketOutcome(
                    clob_token_id=outcome_clob_token_ids[i],
                    name=outcome_names[i],
                    price=outcome_prices[i],
                )
                for i in range(len(outcomes))
            ],
            slug=market_data["slug"],
            description=market_data["description"],
            end_date=convert_polymarket_time_to_datetime(market_data["endDate"]) if "endDate" in market_data else None,
            createdAt=convert_polymarket_time_to_datetime(market_data["createdAt"]),
            volumeNum=float(market_data["volumeNum"]) if market_data.get("volumeNum") is not None else None,
            volume24hr=float(market_data["volume24hr"]) if market_data.get("volume24hr") is not None else None,
            volume1wk=float(market_data["volume1wk"]) if market_data.get("volume1wk") is not None else None,
            volume1mo=float(market_data["volume1mo"]) if market_data.get("volume1mo") is not None else None,
            volume1yr=float(market_data["volume1yr"]) if market_data.get("volume1yr") is not None else None,
            liquidity=float(market_data["liquidity"])
            if "liquidity" in market_data and market_data["liquidity"] is not None
            else None,
            # json=market_data,
        )


class _RequestParameters(BaseModel):
    limit: int | None = None
    offset: int | None = None
    order: str | None = None
    ascending: bool | None = None
    id: int | None = None
    slug: str | None = None
    archived: bool | None = None
    active: bool | None = None
    closed: bool | None = None
    clob_token_ids: str | None = None
    condition_ids: str | None = None
    liquidity_num_min: float | None = None
    liquidity_num_max: float | None = None
    volume_num_min: float | None = None
    volume_num_max: float | None = None
    start_date_min: datetime | None = None
    start_date_max: datetime | None = None
    end_date_min: datetime | None = None
    end_date_max: datetime | None = None
    tag_id: int | None = None
    related_tags: bool | None = None

class MarketsRequestParameters(_RequestParameters):
    
    def get_markets(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[Market]:
        """Get open markets from Polymarket API using this request configuration."""
        url = f"{BASE_URL_POLYMARKET}/markets"

        if self.limit and self.limit > 500:
            assert False, "Limit must be less than or equal to 500"

        params = {}
        for field_name, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, bool):
                    params[field_name] = "true" if value else "false"
                elif isinstance(value, datetime):
                    params[field_name] = value.date().isoformat()
                else:
                    params[field_name] = value

        response = requests.get(url, params=params)
        response.raise_for_status()
        output = response.json()
        markets = [Market.from_json(market) for market in output]
        markets = [market for market in markets if market is not None]
        if self.end_date_min:
            filtered_markets = []
            excluded_count = 0
            for market in markets:
                if market.end_date is None or not (self.end_date_min <= market.end_date <= self.end_date_max):
                    excluded_count += 1
                    print(f"Excluded market {market.question} because it doesn't fit the date criteria")
                else:
                    filtered_markets.append(market)
            if excluded_count > 0:
                print(f"Warning: Excluded {excluded_count} markets that don't fit the date criteria")
            markets = filtered_markets

        if start_time and end_time:
            for market in markets:
                market.fill_prices(start_time, end_time)
        return markets

class _HistoricalTimeSeriesRequestParameters(BaseModel):
    market: str
    interval: Literal["1m", "1w", "1d", "6h", "1h", "max"] = "1d"
    start_time: datetime | None = None
    end_time: datetime | None = None
    fidelity_minutes: int = 60 * 24  # default to daily

    def get_token_daily_timeseries(self) -> pd.Series:
        """Get token timeseries data using this request configuration."""
        url = "https://clob.polymarket.com/prices-history"

        params = {"market": self.market}

        if self.start_time is not None:
            params["startTs"] = int(self.start_time.timestamp())
        if self.end_time is not None:
            params["endTs"] = int(self.end_time.timestamp())
        params["interval"] = self.interval
        if self.fidelity_minutes is not None:
            params["fidelity"] = str(self.fidelity_minutes)

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        timeseries = (
            pd.Series(
                [point["p"] for point in data["history"]],
                index=pd.to_datetime(
                    [datetime.fromtimestamp(point["t"]) for point in data["history"]]
                ),
            )
            .sort_index()
            .resample("1D")
            .last()
            .ffill()
        )
        timeseries.index = timeseries.index.tz_localize(None).date
        return timeseries



################################################################################
# Useful for the future but unused functions
################################################################################

class EventsRequestParameters(_RequestParameters):
    
    def get_events(self) -> list[Event]:
        """Get events from Polymarket API using this request configuration."""
        url = f"{BASE_URL_POLYMARKET}/events"

        if self.limit and self.limit > 500:
            assert False, "Limit must be less than or equal to 500"

        params = {}
        for field_name, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, bool):
                    params[field_name] = "true" if value else "false"
                elif isinstance(value, datetime):
                    params[field_name] = value.date().isoformat()
                else:
                    params[field_name] = value

        response = requests.get(url, params=params)
        response.raise_for_status()
        output = response.json()
        
        events = []
        for event_data in output:
            event = Event.from_json(event_data)
            events.append(event)
        
        return events


class Event(BaseModel, arbitrary_types_allowed=True):
    id: str
    slug: str
    title: str
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    createdAt: datetime
    volume: float | None = None
    volume24hr: float | None = None
    volume1wk: float | None = None
    volume1mo: float | None = None
    volume1yr: float | None = None
    liquidity: float | None = None
    markets: list[Market]

    @staticmethod
    def from_json(event_data: dict) -> Event:
        """Convert an event JSON object to an Event dataclass."""
        markets = []
        for market_data in event_data.get("markets", []):
            market = Market.from_json(market_data)
            if market is not None:
                markets.append(market)
        
        return Event(
            id=event_data["id"],
            slug=event_data["slug"],
            title=event_data["title"],
            description=event_data.get("description"),
            start_date=convert_polymarket_time_to_datetime(event_data["startDate"]) if "startDate" in event_data else None,
            end_date=convert_polymarket_time_to_datetime(event_data["endDate"]) if "endDate" in event_data else None,
            createdAt=convert_polymarket_time_to_datetime(event_data["createdAt"]),
            volume=float(event_data["volume"]) if event_data.get("volume") is not None else None,
            volume24hr=float(event_data["volume24hr"]) if event_data.get("volume24hr") is not None else None,
            volume1wk=float(event_data["volume1wk"]) if event_data.get("volume1wk") is not None else None,
            volume1mo=float(event_data["volume1mo"]) if event_data.get("volume1mo") is not None else None,
            volume1yr=float(event_data["volume1yr"]) if event_data.get("volume1yr") is not None else None,
            liquidity=float(event_data["liquidity"]) if event_data.get("liquidity") is not None else None,
            markets=markets,
        )



class OrderLevel(BaseModel):
    price: str
    size: str


class OrderBook(BaseModel):
    market: str
    asset_id: str
    hash: str
    timestamp: str
    min_order_size: str
    neg_risk: bool
    tick_size: str
    bids: list[OrderLevel]
    asks: list[OrderLevel]

    @staticmethod
    def get_order_book(token_id: str) -> OrderBook:
        """Get order book for a specific token ID from Polymarket CLOB API.

        Args:
            token_id: Token ID of the market to get the book for

        Returns:
            OrderBook containing bids, asks, and market information
        """
        url = "https://clob.polymarket.com/book"
        params = {"token_id": token_id}

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        bids = [OrderLevel(price=bid["price"], size=bid["size"]) for bid in data["bids"]]
        asks = [OrderLevel(price=ask["price"], size=ask["size"]) for ask in data["asks"]]

        return OrderBook(
            market=data["market"],
            asset_id=data["asset_id"],
            hash=data["hash"],
            timestamp=data["timestamp"],
            min_order_size=data["min_order_size"],
            neg_risk=data["neg_risk"],
            tick_size=data["tick_size"],
            bids=bids,
            asks=asks,
        )
    
    

