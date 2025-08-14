import json
import textwrap
from datetime import date, timedelta

from smolagents import ChatMessage, LiteLLMModel

from predibench.common import OUTPUT_PATH
from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    Market,
    MarketsRequestParameters,
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


def choose_markets(today_date: date, n_markets: int = 10) -> dict[Market]:
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
        add_timeseries=(
            today_date - MAX_INTERVAL_TIMESERIES,
            today_date,
        )
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
