from pathlib import Path
from datetime import timedelta, date

from smolagents.models import InferenceClientModel

from predibench.invest import run_investments_for_today
from predibench.common import DATA_PATH


def test_invest_e2e():
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]

    run_investments_for_today(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
    )


def test_invest_e2e_backward():
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]

    run_investments_for_today(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
        backward_date=date(2025, 7, 16),
    )
