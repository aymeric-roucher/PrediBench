import json
import os
from pathlib import Path

import pandas as pd
from predibench.common import OUTPUT_PATH


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
