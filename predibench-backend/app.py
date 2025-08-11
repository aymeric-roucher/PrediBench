import os
import textwrap
from datetime import date, datetime, timedelta

import gradio as gr
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from datasets import Dataset
from dotenv import load_dotenv
from huggingface_hub import HfApi
from predibench.agent import run_smolagent
from predibench.polymarket_api import (
    MarketRequest,
    filter_interesting_questions,
    filter_out_resolved_markets,
    get_open_markets,
)

load_dotenv()

# Configuration
WEEKLY_MARKETS_REPO = "m-ric/predibench-weekly-markets"
AGENT_CHOICES_REPO = "m-ric/predibench-agent-choices"
N_MARKETS = 10

list_models = [
    "huggingface/openai/gpt-oss-120b",
    "huggingface/openai/gpt-oss-20b",
    "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507",
    "huggingface/deepseek-ai/DeepSeek-R1-0528",
    "huggingface/Qwen/Qwen3-4B-Thinking-2507",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4.1-mini",
    "o4-mini",
    "gpt-5",
    "gpt-5-mini",
    "o3-deep-research",
    "test_random",
    # "anthropic/claude-sonnet-4-20250514",
]


def restart_space():
    """Restart the HuggingFace space"""
    try:
        HfApi(token=os.getenv("HF_TOKEN", None)).restart_space(
            repo_id="m-ric/predibench-backend"  # Update with your actual space repo
        )
        print(f"Space restarted on {datetime.now()}")
    except Exception as e:
        print(f"Failed to restart space: {e}")


def get_top_polymarket_questions(n_markets: int = 10) -> list:
    """Fetch top questions from Polymarket API"""
    end_date = date.today() + timedelta(days=7)

    request = MarketRequest(
        limit=n_markets * 10,
        active=True,
        closed=False,
        order="volumeNum",
        ascending=False,
        end_date_min=end_date,
        end_date_max=end_date + timedelta(days=21),
    )

    markets = get_open_markets(request)
    markets = filter_out_resolved_markets(markets)

    # Filter for interesting questions
    interesting_questions = filter_interesting_questions(
        [market.question for market in markets]
    )
    markets = [market for market in markets if market.question in interesting_questions]

    return markets[:n_markets]


def upload_weekly_markets(markets: list):
    """Upload weekly markets to HuggingFace dataset"""
    markets_data = []
    for market in markets:
        markets_data.append(
            {
                "id": market.id,
                "question": market.question,
                "slug": market.slug,
                "description": market.description,
                "end_date": market.end_date,
                "active": market.active,
                "closed": market.closed,
                "volume": market.volume,
                "liquidity": market.liquidity,
                "week_selected": date.today().strftime("%Y-%m-%d"),
                "timestamp": datetime.now(),
            }
        )

    df = pd.DataFrame(markets_data)
    dataset = Dataset.from_pandas(df)

    try:
        # Try to load existing dataset and append
        existing_dataset = Dataset.from_parquet(f"hf://datasets/{WEEKLY_MARKETS_REPO}")
        combined_dataset = existing_dataset.concatenate(dataset)
        combined_dataset.push_to_hub(WEEKLY_MARKETS_REPO, private=False)
    except:
        # If no existing dataset, create new one
        dataset.push_to_hub(WEEKLY_MARKETS_REPO, private=False)

    print(f"Uploaded {len(markets_data)} markets to {WEEKLY_MARKETS_REPO}")


def run_agent_decisions(markets: list, model_ids: list = None):
    """Run agent decision-making logic on the selected markets"""
    if model_ids is None:
        model_ids = [
            "gpt-4o",
            "gpt-4.1",
            "anthropic/claude-sonnet-4-20250514",
            "huggingface/Qwen/Qwen3-30B-A3B-Instruct-2507",
        ]

    today = date.today()
    decisions = []

    for model_id in model_ids:
        for market in markets:
            # Create the investment decision prompt
            full_question = textwrap.dedent(
                f"""Let's say we are the {today.strftime("%B %d, %Y")}.
                Please answer the below question by yes or no. But first, run a detailed analysis.
                Here is the question:
                {market.question}
                More details:
                {market.description}

                Invest in yes only if you think the yes is underrated, and invest in no only if you think that the yes is overrated.
                What would you decide: buy yes, buy no, or do nothing?
                """
            )

            try:
                response = run_smolagent(model_id, full_question, cutoff_date=today)
                choice = response.output.lower()

                # Standardize choice format
                if "yes" in choice:
                    choice_standardized = 1
                    choice_raw = "yes"
                elif "no" in choice:
                    choice_standardized = -1
                    choice_raw = "no"
                else:
                    choice_standardized = 0
                    choice_raw = "nothing"

                decisions.append(
                    {
                        "agent_name": f"smolagent_{model_id}".replace("/", "--"),
                        "date": today,
                        "question": market.question,
                        "question_id": market.id,
                        "choice": choice_standardized,
                        "choice_raw": choice_raw,
                        "messages_count": len(response.messages),
                        "has_reasoning": len(response.messages) > 0,
                        "timestamp": datetime.now(),
                    }
                )

                print(f"Completed decision for {model_id} on {market.question[:50]}...")

            except Exception as e:
                print(f"Error processing {model_id} on {market.question[:50]}: {e}")
                continue

    return decisions


def upload_agent_choices(decisions: list):
    """Upload agent choices to HuggingFace dataset"""
    df = pd.DataFrame(decisions)
    dataset = Dataset.from_pandas(df)

    try:
        # Try to load existing dataset and append
        existing_dataset = Dataset.from_parquet(f"hf://datasets/{AGENT_CHOICES_REPO}")
        combined_dataset = existing_dataset.concatenate(dataset)
        combined_dataset.push_to_hub(AGENT_CHOICES_REPO, private=False)
    except:
        # If no existing dataset, create new one
        dataset.push_to_hub(AGENT_CHOICES_REPO, private=False)

    print(f"Uploaded {len(decisions)} agent decisions to {AGENT_CHOICES_REPO}")


def weekly_pipeline():
    """Main weekly pipeline that runs every Sunday"""
    print(f"Starting weekly pipeline at {datetime.now()}")

    try:
        # 1. Get top 10 questions from Polymarket
        markets = get_top_polymarket_questions(N_MARKETS)
        print(f"Retrieved {len(markets)} markets from Polymarket")

        # 2. Upload to weekly markets dataset
        upload_weekly_markets(markets)

        # 3. Run agent decision-making
        decisions = run_agent_decisions(markets)
        print(f"Generated {len(decisions)} agent decisions")

        # 4. Upload agent choices
        upload_agent_choices(decisions)

        print("Weekly pipeline completed successfully")

    except Exception as e:
        print(f"Weekly pipeline failed: {e}")


# Set up scheduler to run every Sunday at 8:30 AM
scheduler = BackgroundScheduler()
scheduler.add_job(restart_space, "cron", day_of_week="sun", hour=8, minute=0)
scheduler.add_job(weekly_pipeline, "cron", day_of_week="sun", hour=8, minute=30)
scheduler.start()


# Simple Gradio interface for monitoring
def get_status():
    """Get current status of the backend"""
    try:
        # Check if datasets exist and get their info
        api = HfApi()

        weekly_info = "Not available"
        choices_info = "Not available"

        try:
            weekly_dataset = Dataset.from_parquet(
                f"hf://datasets/{WEEKLY_MARKETS_REPO}"
            )
            weekly_info = f"{len(weekly_dataset)} markets"
        except:
            pass

        try:
            choices_dataset = Dataset.from_parquet(
                f"hf://datasets/{AGENT_CHOICES_REPO}"
            )
            choices_info = f"{len(choices_dataset)} decisions"
        except:
            pass

        return f"""
        Backend Status (Last updated: {datetime.now()})
        
        Weekly Markets Dataset: {weekly_info}
        Agent Choices Dataset: {choices_info}
        
        Next scheduled run: Next Sunday at 8:30 AM UTC
        """
    except Exception as e:
        return f"Error getting status: {e}"


def manual_run():
    """Manually trigger the weekly pipeline"""
    weekly_pipeline()
    return "Manual pipeline run completed. Check logs for details."


# Create Gradio interface
with gr.Blocks(title="PrediBench Backend") as demo:
    gr.Markdown("# PrediBench Backend Monitor")
    gr.Markdown(
        "This backend automatically fetches new Polymarket questions every Sunday and runs agent predictions."
    )

    with gr.Row():
        status_text = gr.Textbox(label="Status", value=get_status(), lines=10)
        refresh_btn = gr.Button("Refresh Status")
        refresh_btn.click(get_status, outputs=status_text)

    with gr.Row():
        manual_btn = gr.Button("Run Manual Pipeline", variant="primary")
        manual_output = gr.Textbox(label="Manual Run Output", lines=5)
        manual_btn.click(manual_run, outputs=manual_output)

if __name__ == "__main__":
    print("Starting PrediBench backend...")
    demo.launch(server_name="0.0.0.0", server_port=7860)
