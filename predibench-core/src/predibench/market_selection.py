import json
import textwrap
from datetime import date, timedelta

from smolagents import ChatMessage, LiteLLMModel

from predibench.common import OUTPUT_PATH
from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    Market,
    Event,
    MarketsRequestParameters,
    EventsRequestParameters,
)


def _filter_interesting_questions(questions: list[str]) -> list[str]:
    """Get interesting questions from markets"""

    from pydantic import BaseModel

    class InterestingQuestions(BaseModel):
        questions: list[str]

    model = LiteLLMModel(
        model_id="gpt-4.1-mini",
        requests_per_minute=10,
    )
    output = model.generate(
        [
            ChatMessage(
                role="user",
                content=textwrap.dedent(f"""Please select the most interesting deduplicated questions out of the following list:
                {questions}
                2 questions being deduplicated means that one of them gives >70% info on the other one. In that case, remove all but the first occurence.
                For instance in "Winnie the Pooh becomes US president by October 2025?" and "Winnie the Pooh becomes US president by November 2025?" and "Piglet gets over 50% of the vote in the 2025 US presidential election?", you should remove the second and third one - the second because it is just a later date so heavily impacted by the first, and the third because Winne and Piglet winning is mutually exclusive so one gives out the other.
                Interesting means: remove crypto questions."""),
            )
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": InterestingQuestions.model_json_schema(),
            },
        },
    )
    return json.loads(output.content)["questions"]


def _filter_out_resolved_markets(
    markets: list[Market], threshold: float = 0.02
) -> list[Market]:
    """Filter out markets that are already close to 0 or 1, as these are probably already resolved"""
    return [
        market
        for market in markets
        if not (
            market.prices[-10:].mean() > 1 - threshold
            or market.prices[-10:].mean() < threshold
        )
    ]


def _filter_events_by_volume_and_markets(events: list[Event], n_events: int, min_volume: float = 1000) -> list[Event]:
    """Filter events based on volume threshold and presence of markets."""
    filtered_events = []
    for event in events:
        if event.markets and len(event.markets) > 0:
            # Check if event has volume and is interesting
            if event.volume24hr and event.volume24hr > min_volume:  # Minimum volume threshold
                filtered_events.append(event)
        
        if len(filtered_events) >= n_events:
            break
    
    return filtered_events


def choose_events(today_date: date, n_events: int) -> list[Event]:
    """Pick top events by volume for investment."""
    request_parameters = EventsRequestParameters(
        limit=500,
        order="volume1wk",
        ascending=False,
        end_date_min=today_date + timedelta(days=1),
        end_date_max=today_date + timedelta(days=21),
    )
    events = request_parameters.get_events()
    
    # Filter events by volume and market availability
    filtered_events = _filter_events_by_volume_and_markets(events, n_events)
    
    # Add timeseries data to first market in each event (for testing purposes)
    for event in filtered_events:
        for i, market in enumerate(event.markets):
            if i == 0:  # Only fill prices for first market in each event for faster testing
                market.fill_prices(
                    start_time=today_date - timedelta(days=7),  # Only last 7 days for faster testing
                    end_time=today_date
                )
            else:
                market.prices = None  # Skip timeseries for other markets to speed up testing
    
    output_dir = OUTPUT_PATH
    output_dir.mkdir(exist_ok=True)
    events_file = output_dir / "selected_events.json"
    
    # Save selected events
    with open(events_file, "w") as f:
        events_data = []
        for event in filtered_events:
            event_dict = {
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "description": event.description,
                "volume": event.volume,
                "liquidity": event.liquidity,
                "start_date": event.start_date.isoformat() if event.start_date else None,
                "end_date": event.end_date.isoformat() if event.end_date else None,
                "markets": [
                    {
                        "id": market.id,
                        "question": market.question,
                        "outcomes": [{"name": outcome.name, "price": outcome.price} for outcome in market.outcomes],
                        "volume": market.volumeNum,
                        "liquidity": market.liquidity,
                    }
                    for market in event.markets
                ]
            }
            events_data.append(event_dict)
        json.dump(events_data, f, indent=2)
    
    return filtered_events[:n_events]


def choose_markets(today_date: date, n_markets: int = 10) -> list[Market]:
    """Pick some interesting questions to invest in."""
    request_parameters = MarketsRequestParameters(
        limit=n_markets * 10,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=today_date + timedelta(days=1),
        end_date_max=today_date + timedelta(days=21),
    )
    markets = request_parameters.get_markets(
        start_time=today_date - MAX_INTERVAL_TIMESERIES,
        end_time=today_date,
    )
    markets = _filter_out_resolved_markets(markets)

    output_dir = OUTPUT_PATH
    output_dir.mkdir(exist_ok=True)
    questions_file = output_dir / "interesting_questions.json"
    old_questions_file = output_dir / "interesting_questions_old.json"

    if old_questions_file.exists():
        print("LOADING INTERESTING QUESTIONS FROM FILE")
        with open(old_questions_file, "r") as f:
            # where is the logic when from one week to another, we remove some interesting questions for newer ones ?
            interesting_questions = json.load(f)
    else:
        # I strongly dislike this function, interesting questions should be based on a specific criteria
        interesting_questions = _filter_interesting_questions(
            [market.question for market in markets]
        )
    markets = [market for market in markets if market.question in interesting_questions]

    with open(questions_file, "w") as f:
        json.dump(
            {
                market.id: market.model_dump(mode="json", exclude={"prices"})
                for market in markets
            },
            f,
            indent=2,
        )
    markets_dict = {market.id: market for market in markets}
    return markets_dict
