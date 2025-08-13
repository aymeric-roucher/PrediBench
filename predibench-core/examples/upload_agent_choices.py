import json
from datetime import date
from pathlib import Path

import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

load_dotenv()


def collect_agent_choices_for_dataset(output_path: Path) -> pd.DataFrame:
    """Collect all investment choices and format them for the dataset"""
    positions = []

    for agent_dir in output_path.iterdir():
        if agent_dir.is_dir():
            for date_dir in agent_dir.iterdir():
                if date_dir.is_dir():
                    for file_path in date_dir.iterdir():
                        if file_path.suffix == ".json":
                            with file_path.open("r") as f:
                                data = json.load(f)

                            # Convert choice to standardized format
                            choice_mapping = {"yes": 1, "no": -1, "nothing": 0}
                            choice_numeric = choice_mapping.get(
                                data.get("choice", "nothing").lower(), 0
                            )

                            positions.append(
                                {
                                    "agent_name": agent_dir.name,
                                    "date": date.fromisoformat(date_dir.name),
                                    "question": data["question"],
                                    "choice": choice_numeric,
                                    "choice_raw": data.get("choice", "nothing"),
                                    "question_id": data.get(
                                        "id", file_path.stem
                                    ),
                                    "messages_count": len(data.get("messages", [])),
                                    "has_reasoning": len(data.get("messages", [])) > 0,
                                }
                            )

    return pd.DataFrame.from_records(positions)


def upload_to_huggingface(
    df: pd.DataFrame, repo_id: str = "m-ric/predibench-agent-choices"
):
    """Upload the dataset to HuggingFace"""
    dataset = Dataset.from_pandas(df)

    # Add metadata
    dataset = dataset.add_column(
        "timestamp_uploaded", [pd.Timestamp.now()] * len(dataset)
    )

    # Upload to HuggingFace Hub
    dataset.push_to_hub(repo_id, private=False)
    print(f"Dataset uploaded to {repo_id}")


def main():
    output_path = Path("./output")

    # Collect all agent choices
    df = collect_agent_choices_for_dataset(output_path)

    print(
        f"Collected {len(df)} agent decisions from {df['agent_name'].nunique()} agents"
    )
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique questions: {df['question_id'].nunique()}")

    # Display summary
    print("\nAgent summary:")
    agent_summary = (
        df.groupby("agent_name")
        .agg({"choice": "count", "date": ["min", "max"]})
        .round(2)
    )
    print(agent_summary)

    # Upload to HuggingFace
    upload_to_huggingface(df)


if __name__ == "__main__":
    main()
