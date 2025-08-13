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
    end_date: datetime
    active: bool
    closed: bool
    createdAt: datetime
    volume: float
    liquidity: float | None
    outcomes: list[MarketOutcome]
    prices: pd.Series | None = None
    
    @staticmethod
    def from_json(market_data: dict) -> Market:
        """Convert a market JSON object to a PolymarketMarket dataclass."""
        closed = (
            bool(market_data["closed"])
            if isinstance(market_data["closed"], bool)
            else market_data["closed"].lower() == "true"
        )
        active = (
            bool(market_data["active"])
            if isinstance(market_data["active"], bool)
            else market_data["active"].lower() == "true"
        )
        outcomes = json.loads(market_data["outcomes"])
        if len(outcomes) != 2:
            print("FOR MARKET:\n", market_data["id"])
            raise ValueError(f"Expected 2 outcomes, got {len(outcomes)}")
        outcome_names = json.loads(market_data["outcomes"])
        outcome_prices = json.loads(market_data["outcomePrices"])
        outcome_clob_token_ids = json.loads(market_data["clobTokenIds"])
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
            end_date=convert_polymarket_time_to_datetime(market_data["endDate"]),
            active=active,
            closed=closed,
            createdAt=convert_polymarket_time_to_datetime(market_data["createdAt"]),
            volume=float(market_data["volume"]),
            liquidity=float(market_data["liquidity"])
            if "liquidity" in market_data
            else None,
            # json=market_data,
        )



class MarketsRequestParameters(BaseModel):
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

    def get_open_markets(
        self, add_timeseries: tuple[datetime, datetime] | None = None
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
        if self.end_date_min:
            assert all(
                self.end_date_min <= market.end_date <= self.end_date_max
                for market in markets
            ), "Some markets were created after the end date"

        if add_timeseries:
            start_date, end_date = add_timeseries
            for market in markets:
                ts_request = _HistoricalTimeSeriesRequestParameters(
                    market=market.outcomes[0].clob_token_id,
                    start_time=start_date,
                    end_time=end_date,
                    interval="1d",
                )
                market.prices = ts_request.get_token_daily_timeseries()
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


class Event(BaseModel):
    id: str
    slug: str
    title: str
    liquidity: float
    volume: float
    start_date: datetime
    end_date: datetime
    tags: list[str]
    
    @staticmethod
    def _get_events(
        limit: int = 500,
        offset: int = 0,
        end_date_min: datetime | None = None,
        end_date_max: datetime | None = None,
    ) -> list[dict]:
        """Get open markets from Polymarket, sorted by volume.

        There is a limit of 500 markets per request, one must use pagination to get all markets.
        """
        url = f"{BASE_URL_POLYMARKET}/events"
        assert limit <= 500, "Limit must be less than or equal to 500"
        params = {
            "limit": limit,
            "offset": offset,
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
            "end_date_min": end_date_min.isoformat() if end_date_min else None,
            "end_date_max": end_date_max.isoformat() if end_date_max else None,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        output = response.json()
        return output

    
    @staticmethod
    def get_market_events(limit: int = 500, offset: int = 0) -> list[Event]:
        """Get market events from Polymarket, sorted by volume.

        There is a limit of 500 markets per request, one must use pagination to get all markets.
        """
        output = Event._get_events(limit, offset)
        events = []
        for event in output:
            polymarket_event = Event(
                id=event["id"],
                slug=event["slug"],
                title=event["title"],
                liquidity=float(event["liquidity"]),
                volume=float(event["volume"]),
                start_date=convert_polymarket_time_to_datetime(event["startDate"]),
                end_date=convert_polymarket_time_to_datetime(event["endDate"]),
                tags=event["tags"],
            )
            events.append(polymarket_event)

        return events




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
    
    

def get_historical_returns(markets: list[Market]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Get historical returns directly from timeseries data"""

    returns_df = pd.DataFrame(
        np.nan,
        index=markets[0].prices.index,
        columns=[market.question for market in markets],
    )
    prices_df = pd.DataFrame(
        np.nan,
        index=markets[0].prices.index,
        columns=[market.question for market in markets],
    )

    for i, market in enumerate(markets):
        prices_df[market.question] = market.prices

        token_returns = market.prices.pct_change(periods=1)
        returns_df[market.question] = token_returns

    return returns_df, prices_df



