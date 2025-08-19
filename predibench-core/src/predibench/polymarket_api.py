from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

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
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from predibench.common import BASE_URL_POLYMARKET
from predibench.logger_config import get_logger
from predibench.utils import convert_polymarket_time_to_datetime

MAX_INTERVAL_TIMESERIES = timedelta(days=14, hours=23, minutes=0)
# NOTE: above is refined by experience: seems independant from the resolution

logger = get_logger(__name__)


def _split_date_range(
    start_datetime: datetime, end_datetime: datetime
) -> list[tuple[datetime, datetime]]:
    """Split a date range into chunks of MAX_INTERVAL_TIMESERIES or smaller.

    Args:
        start_datetime: Start datetime
        end_datetime: End datetime

    Returns:
        List of (start, end) datetime tuples, each representing a chunk <= MAX_INTERVAL_TIMESERIES
    """
    # Generate segment start times using pd.date_range
    segment_starts = pd.date_range(
        start=start_datetime, end=end_datetime, freq=MAX_INTERVAL_TIMESERIES
    )
    segment_starts = [start.to_pydatetime() for start in segment_starts]

    chunks = []
    for i, segment_start in enumerate(segment_starts):
        if i == len(segment_starts) - 1:
            # Last segment: end at the original end_datetime
            chunk_end = end_datetime
        else:
            # Regular segment: end at next segment start - 1 second to avoid overlap
            chunk_end = segment_starts[i + 1] - timedelta(hours=1)

        chunks.append((segment_start, chunk_end))

    return chunks


class MarketOutcome(BaseModel):
    clob_token_id: str
    name: str
    price: float


class Market(BaseModel, arbitrary_types_allowed=True):
    id: str
    question: str
    slug: str
    description: str
    end_datetime: datetime | None
    creation_datetime: datetime
    volumeNum: float | None
    volume24hr: float | None
    volume1wk: float | None
    volume1mo: float | None
    volume1yr: float | None
    liquidity: float | None
    outcomes: list[MarketOutcome]
    prices: pd.Series | None = None
    price_outcome_name: str | None = None  # Name of the outcome the prices represent

    def fill_prices(self, start_datetime: datetime, end_datetime: datetime) -> None:
        """Fill the prices field with timeseries data.

        Args:
            start_datetime: Start time for timeseries data
            end_datetime: End time for timeseries data
            interval: Time interval for data points (default: "1d")
        """
        if self.outcomes and len(self.outcomes) == 2 and self.outcomes[0].clob_token_id:
            ts_request = _HistoricalTimeSeriesRequestParameters(
                market_id=self.outcomes[0].clob_token_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )
            self.prices = ts_request.get_token_daily_timeseries()
            self.price_outcome_name = self.outcomes[
                0
            ].name  # Store which outcome the prices represent
            assert self.price_outcome_name.lower() != "no", (
                "Price outcome should be YES or a sport's team name."
            )
        else:
            logger.error(
                f"Incorrect outcomes for market {self.id} with name {self.question} and outcomes {self.outcomes}"
            )
            self.prices = None
            self.price_outcome_name = None

    @staticmethod
    def from_json(market_data: dict) -> Market:
        """Convert a market JSON object to a PolymarketMarket dataclass."""

        assert "outcomes" in market_data
        outcomes = json.loads(market_data["outcomes"])
        assert len(outcomes) >= 2, (
            f"Expected at least 2 outcomes, got {len(outcomes)} for market:\n{market_data['id']}\n{market_data['question']}"
        )
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
            end_datetime=convert_polymarket_time_to_datetime(market_data["endDate"])
            if "endDate" in market_data
            else None,
            creation_datetime=convert_polymarket_time_to_datetime(
                market_data["createdAt"]
            ),
            volumeNum=float(market_data["volumeNum"])
            if market_data.get("volumeNum") is not None
            else None,
            volume24hr=float(market_data["volume24hr"])
            if market_data.get("volume24hr") is not None
            else None,
            volume1wk=float(market_data["volume1wk"])
            if market_data.get("volume1wk") is not None
            else None,
            volume1mo=float(market_data["volume1mo"])
            if market_data.get("volume1mo") is not None
            else None,
            volume1yr=float(market_data["volume1yr"])
            if market_data.get("volume1yr") is not None
            else None,
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
    end_datetime_min: datetime | None = None
    end_datetime_max: datetime | None = None
    tag_id: int | None = None
    related_tags: bool | None = None


class MarketsRequestParameters(_RequestParameters):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type(
            (
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            )
        ),
    )
    def get_markets(
        self,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
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
        if self.end_datetime_min and self.end_datetime_max:
            filtered_markets = []
            excluded_count = 0
            for market in markets:
                assert market is not None
                if (
                    not (
                        self.end_datetime_min
                        <= market.end_datetime
                        <= self.end_datetime_max
                    )
                    and market.end_datetime is not None
                ):
                    excluded_count += 1
                    logger.warning(
                        f"Excluded market {market.question} because it doesn't fit the date criteria"
                    )
                else:
                    filtered_markets.append(market)
            if excluded_count > 0:
                logger.warning(
                    f"Excluded {excluded_count} markets that don't fit the date criteria"
                )
            markets = filtered_markets

        if start_datetime and end_datetime:
            for market in markets:
                market.fill_prices(start_datetime, end_datetime)
        return markets


class _HistoricalTimeSeriesRequestParameters(BaseModel):
    market_id: str
    start_datetime: datetime
    end_datetime: datetime

    def get_token_daily_timeseries(self) -> pd.Series | None:
        """Get token timeseries data using this request configuration.

        Why no fidelity ? Because when the market is closed in an Event that is still open (bitcoin price for instance),
        the argument fidelity will return an empty timeseries. Better get as much data as possible.

        Some markets are present in the API and yet without prices, it is because they are not used and not traded,
        in that case we will return None

        If the requested date range exceeds MAX_INTERVAL_TIMESERIES, this method will split the range
        into multiple requests and concatenate the results.
        """
        # If no date range specified or range is within limit, use original logic
        if (
            self.start_datetime is None
            or self.end_datetime is None
            or (self.end_datetime - self.start_datetime) <= MAX_INTERVAL_TIMESERIES
        ):
            return self._get_single_timeseries_request()

        # Split the date range into smaller chunks to comply with API duration limits
        date_chunks = _split_date_range(self.start_datetime, self.end_datetime)
        logger.info(
            f"Splitting date range into {len(date_chunks)} chunks for market {self.market_id}"
        )

        all_timeseries = []

        for chunk_start, chunk_end in date_chunks:
            # Create a new instance for this chunk to avoid modifying self
            chunk_request = _HistoricalTimeSeriesRequestParameters(
                market_id=self.market_id,
                start_datetime=chunk_start,
                end_datetime=chunk_end,
            )

            chunk_timeseries = chunk_request._get_single_timeseries_request()
            if chunk_timeseries is None:
                logger.warning(
                    f"No timeseries data found for market {self.market_id} between {chunk_start.date()} and {chunk_end.date()}"
                )
                continue
            all_timeseries.append(chunk_timeseries)

        if not all_timeseries:
            return None

        # Concatenate all timeseries
        combined_timeseries = pd.concat(all_timeseries).sort_index()

        # Remove duplicates (keep last value for each date)
        combined_timeseries = combined_timeseries[
            ~combined_timeseries.index.duplicated(keep="last")
        ]

        return combined_timeseries

    def _get_single_timeseries_request(self) -> pd.Series | None:
        """Make a single API request for timeseries data."""
        url = "https://clob.polymarket.com/prices-history"
        assert self.market_id is not None

        params = {
            "market": self.market_id,
            # "interval": self.interval, # NOTE: interval and startTs are mutually exclusive
            "startTs": str(int(self.start_datetime.timestamp())),
            "endTs": str(int(self.end_datetime.timestamp())),
            "fidelity": "60",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if len(data["history"]) == 0:
            return None

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
        timeseries.index = timeseries.index.tz_localize(timezone.utc).date

        # Filter timeseries to only include dates between start_datetime and end_datetime
        timeseries = timeseries.loc[
            (timeseries.index >= self.start_datetime.date())
            & (timeseries.index <= self.end_datetime.date())
        ]

        return timeseries


class EventsRequestParameters(_RequestParameters):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type(
            (
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            )
        ),
    )
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
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    creation_datetime: datetime
    volume: float | None = None
    volume24hr: float | None = None
    volume1wk: float | None = None
    volume1mo: float | None = None
    volume1yr: float | None = None
    liquidity: float | None = None
    markets: list[Market]
    selected_market_id: str | None = None  # ID of the selected market for prediction

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
            start_datetime=convert_polymarket_time_to_datetime(event_data["startDate"])
            if "startDate" in event_data
            else None,
            end_datetime=convert_polymarket_time_to_datetime(event_data["endDate"])
            if "endDate" in event_data
            else None,
            creation_datetime=convert_polymarket_time_to_datetime(
                event_data["createdAt"]
            ),
            volume=float(event_data["volume"])
            if event_data.get("volume") is not None
            else None,
            volume24hr=float(event_data["volume24hr"])
            if event_data.get("volume24hr") is not None
            else None,
            volume1wk=float(event_data["volume1wk"])
            if event_data.get("volume1wk") is not None
            else None,
            volume1mo=float(event_data["volume1mo"])
            if event_data.get("volume1mo") is not None
            else None,
            volume1yr=float(event_data["volume1yr"])
            if event_data.get("volume1yr") is not None
            else None,
            liquidity=float(event_data["liquidity"])
            if event_data.get("liquidity") is not None
            else None,
            markets=markets,
        )

    def select_random_market(self) -> None:
        """Select a random market from this event for prediction."""
        import random

        if self.markets:
            selected_market = random.choice(self.markets)
            self.selected_market_id = selected_market.id
        else:
            self.selected_market_id = None


################################################################################
# Useful for the future but unused functions
################################################################################


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
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type(
            (
                requests.exceptions.RequestException,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            )
        ),
    )
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

        bids = [
            OrderLevel(price=bid["price"], size=bid["size"]) for bid in data["bids"]
        ]
        asks = [
            OrderLevel(price=ask["price"], size=ask["size"]) for ask in data["asks"]
        ]

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
