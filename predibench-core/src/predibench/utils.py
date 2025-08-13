import json
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from predibench.polymarket_api import (
    MAX_INTERVAL_TIMESERIES,
    Market,
    MarketRequest,
    filter_interesting_questions,
    filter_out_resolved_markets,
    get_open_markets,
)

OUTPUT_PATH = Path("output")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH.mkdir(parents=True)


def choose_markets(today_date: date, n_markets: int = 10) -> list[Market]:
    """Pick some interesting questions to invest in."""
    request = MarketRequest(
        limit=n_markets * 10,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=today_date + timedelta(days=1),
        end_date_max=today_date + timedelta(days=21),
    )
    markets = get_open_markets(
        request,
        add_timeseries=[
            today_date - MAX_INTERVAL_TIMESERIES,
            today_date,
        ],
    )
    markets = filter_out_resolved_markets(markets)

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
        interesting_questions = filter_interesting_questions(
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
    markets = markets[:n_markets]
    assert len(markets) == n_markets
    return markets


def collect_investment_choices(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """Collect investment choices previously decided by agents and written to local files."""
    # we should have a database
    positions = []
    for agent_name in os.listdir(output_path):
        if os.path.isdir(output_path / agent_name):
            for date_folder in os.listdir(output_path / agent_name):
                for file in os.listdir(output_path / agent_name / date_folder):
                    if file.endswith(".json"):
                        with open(
                            output_path / agent_name / date_folder / file, "r"
                        ) as f:
                            data = json.load(f)
                        try:
                            positions.append(
                                {
                                    "agent_name": agent_name,
                                    "date": date.fromisoformat(date_folder),
                                    "question": data["question"],
                                    "choice": (
                                        0
                                        if data["choice"] == "nothing"
                                        else (1 if data["choice"] == "yes" else -1)
                                    ),
                                    "question_id": data["id"],
                                }
                            )
                        except Exception as e:
                            print(f"Error for {file}: {e}")
                            print(data)
                            raise e
                            continue
    return pd.DataFrame.from_records(positions)
