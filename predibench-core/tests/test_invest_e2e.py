from datetime import date, timedelta

from predibench.common import DATA_PATH
from predibench.invest import run_investments_for_specific_date
from smolagents.models import InferenceClientModel


def test_invest_e2e():
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]

    run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
    )


def test_invest_e2e_backward():
    models = [
        InferenceClientModel(model_id="openai/gpt-oss-120b"),
    ]

    run_investments_for_specific_date(
        time_until_ending=timedelta(days=21),
        max_n_events=3,
        models=models,
        output_path=DATA_PATH,
        target_date=date(2025, 7, 16),
    )
