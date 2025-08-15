import json
import os
import textwrap
from datetime import date, datetime
from typing import Literal

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from smolagents import (
    InferenceClientModel,
    OpenAIModel,
    RunResult,
    Timing,
    TokenUsage,
    Tool,
    ToolCallingAgent,
    VisitWebpageTool,
    tool,
)

from predibench.polymarket_api import Market, Event
from predibench.utils import OUTPUT_PATH
from predibench.logging import get_logger

load_dotenv()

logger = get_logger(__name__)


class GoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs a google web search for your query then returns a string of the top search results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
    }
    output_type = "string"

    def __init__(self, provider: str = "serpapi", cutoff_date: datetime | None = None):
        super().__init__()

        self.provider = provider
        if provider == "serpapi":
            self.organic_key = "organic_results"
            api_key_env_name = "SERPAPI_API_KEY"
        else:
            self.organic_key = "organic"
            api_key_env_name = "SERPER_API_KEY"
        self.api_key = os.getenv(api_key_env_name)
        if self.api_key is None:
            raise ValueError(
                f"Missing API key. Make sure you have '{api_key_env_name}' in your env variables."
            )
        self.cutoff_date = cutoff_date

    def forward(self, query: str) -> str:
        import requests

        if self.provider == "serpapi":
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "google_domain": "google.com",
            }
            if self.cutoff_date is not None:
                params["tbs"] = f"cdr:1,cd_max:{self.cutoff_date.strftime('%m/%d/%Y')}"

            response = requests.get("https://serpapi.com/search.json", params=params)
        else:
            payload = {
                "q": query,
            }
            if self.cutoff_date is not None:
                payload["tbs"] = f"cdr:1,cd_max:{self.cutoff_date.strftime('%m/%d/%Y')}"

            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            response = requests.post(
                "https://google.serper.dev/search", json=payload, headers=headers
            )

        if response.status_code == 200:
            results = response.json()
        else:
            logger.error(f"Error response: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            raise ValueError(response.json())

        if self.organic_key not in results.keys():
            raise Exception(
                f"No results found for query: '{query}'. Use a less restrictive query."
            )
        if len(results[self.organic_key]) == 0:
            return f"No results found for '{query}'. Try with a more general query."

        web_snippets = []
        if self.organic_key in results:
            for idx, page in enumerate(results[self.organic_key]):
                date_published = ""
                if "date" in page:
                    date_published = "\nDate published: " + page["date"]

                source = ""
                if "source" in page:
                    source = "\nSource: " + page["source"]

                snippet = ""
                if "snippet" in page:
                    snippet = "\n" + page["snippet"]

                redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
                web_snippets.append(redacted_version)

        return f"## Search Results for '{query}'\n" + "\n\n".join(web_snippets)


@tool
def final_answer(
    answer: Literal["yes", "no", "nothing"],
) -> Literal["yes", "no", "nothing"]:
    """
    Provides a final answer to the given problem.

    Args:
        answer: The final investment or non-investment decision. Do not invest in any outcome if you don't have a clear preference.
    """
    logger.info(f"Final answer: {answer}")
    return answer


@tool  
def final_event_allocation(
    allocations: dict,
) -> dict:
    """
    Provides final investment allocations across multiple events.

    Args:
        allocations: Dictionary mapping event_id to allocation amount (0-100% of portfolio).
                    Example: {"event_123": 25.0, "event_456": 15.0, "event_789": 0.0}
                    All allocations should sum to <= 100.0
    """
    total_allocation = sum(allocations.values())
    if total_allocation > 100.0:
        logger.warning(f"Total allocation ({total_allocation}%) exceeds 100%")
    logger.info(f"Final event allocations: {allocations}")
    return allocations


if __name__ == "__main__":
    tool = GoogleSearchTool(provider="serper", cutoff_date=datetime(2024, 6, 1))
    results_with_filter = tool.forward("OpenAI GPT-5 news")

    tool = GoogleSearchTool(provider="serper")
    results_without_filter = tool.forward("OpenAI GPT-5 news")

    assert results_with_filter != results_without_filter


def run_smolagent(
    model_id: str, question: str, cutoff_date: datetime
) -> ToolCallingAgent:
    if model_id.startswith("huggingface/"):
        model = InferenceClientModel(
            model_id=model_id.replace("huggingface/", ""),
            requests_per_minute=10,
        )
    else:
        model = OpenAIModel(
            model_id=model_id,
            requests_per_minute=10,
        )
    tools = [
        GoogleSearchTool(provider="serper", cutoff_date=cutoff_date),
        VisitWebpageTool(),
        final_answer,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=40, return_full_result=True
    )
    return agent.run(question)


# visit_webpage_tool = VisitWebpageTool()
# print(
#     visit_webpage_tool.forward(
#         "https://www.axios.com/2025/07/24/openai-gpt-5-august-2025"
#     )
# )


def agent_invest_positions(
    model_id: str,
    markets: dict[str, Market],
    prices_df: pd.DataFrame,
    target_date: date,
) -> dict:
    """Let the agent decide on investment positions: 1 to buy, -1 to sell, 0 to do nothing"""
    logger.info("Creating investment positions with agent...")
    logger.debug(f"Target date: {target_date}, Available dates: {markets[list(markets.keys())[0]].prices.index}")
    assert target_date in markets[list(markets.keys())[0]].prices.index

    output_dir = (
        OUTPUT_PATH
        / f"smolagent_{model_id}".replace("/", "--")
        / target_date.strftime("%Y-%m-%d")
    )
    os.makedirs(output_dir, exist_ok=True)
    choices = {}
    for question_id in prices_df.columns:
        if (output_dir / f"{question_id}.json").exists():
            logger.info(
                f"Getting the result for market n°'{question_id}' for {model_id} on {target_date} from file."
            )
            response = json.load(open(output_dir / f"{question_id}.json"))
            choice = response["choice"]
        else:
            logger.info(
                f"No results found in {output_dir / f'{question_id}.json'}, building them new."
            )
            market = markets[question_id]
            assert market.id == question_id
            if np.isnan(prices_df.loc[target_date, question_id]):
                continue
            prices_str = (
                prices_df.loc[:target_date, question_id]
                .dropna()
                .to_string(index=True, header=False)
            )
            full_question = textwrap.dedent(
                f"""Let's say we are the {target_date.strftime("%B %d, %Y")}.
                Please answer the below question by yes or no. But first, run a detailed analysis. You can search the web for information.
                One good method for analyzing is to break down the question into sub-parts, like a tree, and assign probabilities to each sub-branch of the tree, to get a total probability of the question being true.
                Here is the question:
                {market.question}
                More details:
                {market.description}

                Here are the latest rates for the 'yes' to that question (rates for 'yes' and 'no' sum to 1), to guide you:
                {prices_str}

                Invest in yes only if you think the yes is underrated, and invest in no only if you think that the yes is overrated.
                What would you decide: buy yes, buy no, or do nothing?
                """
            )
            if model_id.endswith("-deep-research"):
                response = run_deep_research(
                    model_id,
                    full_question,
                    cutoff_date=target_date,
                )
            elif model_id == "test_random":
                response = RunResult(
                    output=("yes" if np.random.random() < 0.3 else "nothing"),
                    messages=[{"value": "ok here is the reasoning process"}],
                    state={},
                    token_usage=TokenUsage(0, 0),
                    timing=Timing(0.0),
                )
            else:
                response = run_smolagent(
                    model_id,
                    full_question,
                    cutoff_date=target_date,
                )
                for message in response.messages:
                    message["model_input_messages"] = "removed"  # Clean logs
            choice = response.output
            choices[question_id] = choice

            with open(output_dir / f"{question_id}.json", "w") as f:
                json.dump(
                    {
                        "question": market.question,
                        "market_id": market.id,
                        "choice": choice,
                        "messages": response.messages,
                    },
                    f,
                    default=str,
                )
    return choices


def agent_invest_in_events(
    model_id: str,
    events: list[Event],
    date: date,
) -> dict:
    """Let the agent decide on investment allocations across events"""
    logger.info(f"Creating event-based investment allocations with agent for {len(events)} events...")
    
    output_dir = (
        OUTPUT_PATH
        / f"smolagent_events_{model_id}".replace("/", "--")
        / date.strftime("%Y-%m-%d")
    )
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if allocation already exists
    allocation_file = output_dir / "event_allocations.json"
    if allocation_file.exists():
        logger.info(f"Getting event allocations for {model_id} on {date} from file.")
        with open(allocation_file) as f:
            return json.load(f)
    
    # Build event descriptions for the prompt
    events_description = ""
    for i, event in enumerate(events):
        events_description += f"\n\n--- EVENT {i+1}: {event.title} ---\n"
        events_description += f"Event ID: {event.id}\n"
        if event.description:
            events_description += f"Description: {event.description}\n"
        events_description += f"Volume: ${event.volume:,.2f}\n" if event.volume else "Volume: N/A\n"
        events_description += f"Liquidity: ${event.liquidity:,.2f}\n" if event.liquidity else "Liquidity: N/A\n"
        
        if event.end_date:
            events_description += f"End Date: {event.end_date.strftime('%Y-%m-%d')}\n"
        
        events_description += "Markets in this event:\n"
        for j, market in enumerate(event.markets):
            events_description += f"  {j+1}. {market.question}\n"
            for outcome in market.outcomes:
                events_description += f"     - {outcome.name}: {outcome.price:.3f}\n"
            
            # Add price history if available
            if market.prices is not None and len(market.prices) > 0:
                recent_prices = market.prices.tail(7)  # Last 7 days
                events_description += f"     Recent 'Yes' price history:\n"
                for price_date, price in recent_prices.items():
                    events_description += f"       {price_date}: {price:.3f}\n"
    
    full_prompt = textwrap.dedent(f"""
        You are a professional prediction market investor analyzing events on {date.strftime("%B %d, %Y")}.
        
        Your task is to allocate a $10,000 portfolio across the following events. You can allocate 0-100% to each event.
        The total allocation should not exceed 100% of your portfolio.
        
        For each event, consider:
        1. The quality and clarity of the questions
        2. Current market prices vs your assessment of true probabilities
        3. Available liquidity and volume
        4. Time until resolution
        5. Your confidence level in your predictions
        
        Here are the events to analyze:
        {events_description}
        
        Please provide a detailed analysis of each event, then use the final_event_allocation tool to specify 
        your percentage allocation to each event (using the event IDs).
        
        Example allocation: {{"event_123": 25.0, "event_456": 15.0, "event_789": 0.0}}
        
        Only invest in events where you have strong conviction that the market is mispricing the outcomes.
        It's perfectly fine to allocate 0% to events you're uncertain about.
    """)
    
    if model_id.endswith("-deep-research"):
        response = run_deep_research_events(model_id, full_prompt, date)
    elif model_id == "test_random":
        # Random allocation for testing
        allocations = {}
        remaining = 100.0
        for event in events[:-1]:  # All but last
            allocation = np.random.uniform(0, remaining * 0.3)  # Max 30% per event
            allocations[event.id] = round(allocation, 1)
            remaining -= allocation
        allocations[events[-1].id] = max(0, round(remaining * np.random.uniform(0, 0.5), 1))
        
        response = {"allocations": allocations}
    else:
        agent_response = run_smolagent_events(model_id, full_prompt, date)
        response = {"allocations": agent_response.output if isinstance(agent_response.output, dict) else {}}
    
    # Save the allocation
    with open(allocation_file, "w") as f:
        json.dump(response, f, indent=2, default=str)
    
    return response.get("allocations", {})


def run_smolagent_events(
    model_id: str, 
    prompt: str, 
    cutoff_date: date
) -> RunResult:
    """Run smolagent with event allocation tools"""
    if model_id.startswith("huggingface/"):
        model = InferenceClientModel(
            model_id=model_id.replace("huggingface/", ""),
            requests_per_minute=10,
        )
    else:
        model = OpenAIModel(
            model_id=model_id,
            requests_per_minute=10,
        )
    
    tools = [
        GoogleSearchTool(provider="serper", cutoff_date=cutoff_date),
        VisitWebpageTool(),
        final_event_allocation,
    ]
    
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=40, return_full_result=True
    )
    return agent.run(prompt)


def run_deep_research_events(
    model_id: str,
    prompt: str, 
    cutoff_date: date,
) -> dict:
    """Run deep research for event allocation"""
    from openai import OpenAI
    
    client = OpenAI(timeout=3600)
    
    response = client.responses.create(
        model=model_id,
        input=prompt + "\n\nProvide your allocation as a JSON object with event IDs as keys and percentages as values.",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
        ],
    )
    
    output_text = response.output_text
    # Try to extract JSON allocation from response
    try:
        import re
        json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
        if json_match:
            allocations = json.loads(json_match.group())
            return {"allocations": allocations}
    except:
        pass
    
    return {"allocations": {}}


def run_deep_research(
    model_id: str,
    question: str,
    cutoff_date: date,
) -> RunResult:
    from openai import OpenAI

    client = OpenAI(timeout=3600)

    response = client.responses.create(
        model=model_id,
        input=question + "Preface your answer with 'ANSWER: '",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
        ],
    )
    output_text = response.output_text
    choice = output_text.split("ANSWER: ")[1].strip()
    return RunResult(
        output=choice,
        steps=[],
        state={},
        token_usage=TokenUsage(0, 0),
        timing=Timing(0.0),
    )


def launch_agent_investments(list_models, investment_dates, prices_df, markets):
    for model_id in list_models:
        try:
            for investment_date in investment_dates:
                agent_invest_positions(model_id, markets, prices_df, investment_date)
        except Exception as e:
            logger.error(f"Error for {model_id}: {e}")
            raise e
            continue


def launch_agent_event_investments(list_models, investment_dates, events):
    """Launch event-based investment analysis with multiple models"""
    for model_id in list_models:
        try:
            for investment_date in investment_dates:
                allocations = agent_invest_in_events(model_id, events, investment_date)
                logger.info(f"Model {model_id} allocations for {investment_date}: {allocations}")
        except Exception as e:
            logger.error(f"Error for {model_id}: {e}")
            continue


if __name__ == "__main__":
    run_smolagent(
        "gpt-4.1",
        "Will the S&P 500 close above 4,500 by the end of the year?",
        datetime(2024, 6, 1),
    )
