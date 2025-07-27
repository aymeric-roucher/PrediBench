import requests
from dataclasses import dataclass
from datetime import datetime
from market_bench.common import BASE_URL_POLYMARKET

@dataclass
class PolymarketMarket:
    id: str
    question: str
    slug: str
    description: str
    active: bool
    closed: bool
    createdAt: datetime
    volumeNum: float
    liquidityNum: float | None = None
    json: dict | None = None

@dataclass
class PolymarketMarketEvent:
    id: str
    ticker: str
    title: str
    description: str
    createdAt: datetime
    endDate: datetime | None = None
    json: dict | None = None
    markets: list[PolymarketMarket] | None = None
    
def convert_polymarket_time_to_datetime(time_str: str) -> datetime:
    """Convert a Polymarket time string to a datetime object."""
    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))


def _json_to_polymarket_market(market_data: dict) -> PolymarketMarket:
    """Convert a market JSON object to a PolymarketMarket dataclass."""
    closed = bool(market_data['closed']) if isinstance(market_data['closed'], bool) else market_data['closed'].lower() == 'true'
    active = bool(market_data['active']) if isinstance(market_data['active'], bool) else market_data['active'].lower() == 'true'
    return PolymarketMarket(
        id=market_data['id'],
        question=market_data['question'],
        slug=market_data['slug'],
        description=market_data['description'],
        active=active,
        closed=closed,
        createdAt=convert_polymarket_time_to_datetime(market_data['createdAt']),
        volumeNum=float(market_data['volumeNum']) if 'volumeNum' in market_data else None,
        liquidityNum=float(market_data['liquidityNum']) if 'liquidityNum' in market_data else None,
        json=market_data
    )
    
    
def _get_market_events(limit: int = 500, offset: int = 0) -> list[dict]:
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
        "ascending": "false"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    output = response.json()
    return output

def get_market_events(limit: int = 500, offset: int = 0) -> list[PolymarketMarketEvent]:
    """Get market events from Polymarket, sorted by volume.
    
    There is a limit of 500 markets per request, one must use pagination to get all markets.
    """
    output = _get_market_events(limit, offset)
    events = []
    for event in output:
        end_date = None
        if event.get('endDate'):
            end_date = convert_polymarket_time_to_datetime(event['endDate'])
        
        markets = None
        if event.get('markets'):
            markets = [_json_to_polymarket_market(market_data) for market_data in event['markets']]
        
        polymarket_event = PolymarketMarketEvent(
            id=event['id'],
            ticker=event['ticker'],
            title=event['title'],
            description=event['description'],
            createdAt=convert_polymarket_time_to_datetime(event['createdAt']),
            endDate=end_date,
            json=event,
            markets=markets
        )
        events.append(polymarket_event)
    
    return events


def _get_open_markets(limit: int = 500, offset: int = 0) -> list[dict]:
    """Get open markets from Polymarket, sorted by volume.
    
    There is a limit of 500 markets per request, one must use pagination to get all markets.
    """
    url = f"{BASE_URL_POLYMARKET}/markets"
    assert limit <= 500, "Limit must be less than or equal to 500"
    params = {
        "limit": limit,
        "offset": offset,
        "active": "true",
        "closed": "false",
        "order": "volumeNum",
        "ascending": "false"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    output = response.json()
    return output

def get_open_markets(limit: int = 500) -> list[PolymarketMarket]:
    """Get open markets from Polymarket, sorted by volume.
    
    There is a limit of 500 markets per request, one must use pagination to get all markets.
    """
    output = _get_open_markets(limit)
    return [_json_to_polymarket_market(market) for market in output]

