import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import numpy as np
from dotenv import load_dotenv
from smolagents import (
    RunResult,
    Timing,
    Tool,
    ToolCallingAgent,
    VisitWebpageTool,
    tool,
    ApiModel,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from predibench.polymarket_api import Market, Event
from predibench.common import DATA_PATH
from predibench.logger_config import get_logger
from predibench.storage_utils import write_to_storage
from pydantic import BaseModel
from predibench.utils import get_timestamp_string

load_dotenv()

logger = get_logger(__name__)


class MarketInvestmentDecision(BaseModel):
    market_id: str
    market_question: str
    decision: Literal["BUY", "SELL", "NOTHING"]
    rationale: str | None = None
    market_price: float | None = None
    is_closed: bool = False


class EventInvestmentResult(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_decision: MarketInvestmentDecision


class ModelInvestmentResult(BaseModel):
    model_id: str
    target_date: date
    event_results: list[EventInvestmentResult]


class EventDecisions(BaseModel):
    rationale: str
    decision: Literal["BUY", "SELL", "NOTHING"]


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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type((Exception,)),
    )
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
    rationale: str, decision: Literal["BUY", "SELL", "NOTHING"]
) -> EventDecisions:
    """
    This tool is used to validate and return the final event decision.

    This tool must be used only once. The rationale and decision must be provided in the same call.

    Args:
        rationale (str): The rationale for the decision.
        decision (Literal["BUY", "SELL", "NOTHING"]): The decision to make.

    Returns:
        EventDecisions: The validated EventDecisions object, raises error if invalid.
    """
    assert decision in ["BUY", "SELL", "NOTHING"], (
        "Invalid decision, must be BUY, SELL or NOTHING"
    )
    assert len(rationale) > 0, "Rationale must be a non-empty string"
    return EventDecisions(rationale=rationale, decision=decision)


def run_smolagent_for_event(
    model: ApiModel, question: str, cutoff_date: datetime
) -> EventDecisions:
    """Run smolagent for event-level analysis with single market decision using structured output."""

    # Create the parser and prompt template
    template = """
{question}
        
Use the final_answer tool to validate your output before providing the final answer.
The final_answer tool must contain the arguments rationale and decision.
"""

    # Format the prompt
    prompt = template.format(question=question)

    tools = [
        GoogleSearchTool(provider="serper", cutoff_date=cutoff_date),
        VisitWebpageTool(),
        final_answer,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=40, return_full_result=True
    )

    result = agent.run(prompt)

    # Parse and return the structured output
    return result.output


def create_market_investment_decision(
    event_decision: EventDecisions, selected_market_info: dict
) -> MarketInvestmentDecision:
    """Convert single EventDecision to MarketInvestmentDecision object for the selected market."""
    # Force NOTHING for closed markets
    if selected_market_info["is_closed"]:
        return MarketInvestmentDecision(
            market_id=selected_market_info["id"],
            market_question=selected_market_info["question"],
            decision="NOTHING",
            rationale=f"Market is closed. Original rationale: {event_decision.rationale}",
            market_price=selected_market_info["current_price"],
            is_closed=True,
        )
    else:
        return MarketInvestmentDecision(
            market_id=selected_market_info["id"],
            market_question=selected_market_info["question"],
            decision=event_decision.decision,
            rationale=event_decision.rationale,
            market_price=selected_market_info["current_price"],
            is_closed=False,
        )


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
        token_usage=None,
        timing=Timing(0.0),
    )


def launch_agent_investments(
    models: list[ApiModel | str],
    events: list[Event],
    target_date: date | None = None,
    backward_mode: bool = False,
    date_output_path: Path | None = None,
) -> list[ModelInvestmentResult]:
    """
    Launch agent investments for events on a specific date.
    Runs each model sequentially (will be parallelized later).

    Args:
        models: List of ApiModel objects or "test_random" string to run investments with
        events: List of events to analyze
        target_date: Date for backward compatibility (defaults to today)
        backward_mode: Whether running in backward compatibility mode
    """
    if target_date is None:
        target_date = date.today()

    logger.info(f"Running agent investments for {len(models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")

    results = []
    for model in models:
        model_name = model.model_id if isinstance(model, ApiModel) else model
        logger.info(f"Processing model: {model_name}")
        model_result = process_single_model(
            model=model,
            events=events,
            target_date=target_date,
            backward_mode=backward_mode,
            date_output_path=date_output_path,
        )
        results.append(model_result)

    return results


def process_single_model(
    model: ApiModel | str,
    events: list[Event],
    target_date: date,
    backward_mode: bool,
    date_output_path: Path | None = None,
) -> ModelInvestmentResult:
    """Process investments for all events for a specific model and save results."""
    event_results = []

    for event in events:
        logger.info(f"Processing event: {event.title}")
        event_result = process_event_investment(
            model=model,
            event=event,
            target_date=target_date,
            backward_mode=backward_mode,
            date_output_path=date_output_path,
        )
        event_results.append(event_result)

    model_id = model.model_id if isinstance(model, ApiModel) else model
    model_result = ModelInvestmentResult(
        model_id=model_id, target_date=target_date, event_results=event_results
    )

    save_model_result(model_result=model_result, date_output_path=date_output_path)
    return model_result


def process_event_investment(
    model: ApiModel | str,
    event: Event,
    target_date: date,
    backward_mode: bool,
    date_output_path: Path | None = None,
    main_market_price_history_limit: int = 200,
    other_markets_price_history_limit: int = 20,
) -> EventInvestmentResult:
    """Process investment decision for the selected market in an event."""
    logger.info(f"Processing event: {event.title} with selected market")

    if not event.selected_market_id:
        raise ValueError(f"Event '{event.title}' has no selected market for prediction")

    # Find the selected market
    selected_market = next(
        (m for m in event.markets if m.id == event.selected_market_id), None
    )
    if not selected_market:
        raise ValueError(
            f"Selected market {event.selected_market_id} not found in event {event.title}"
        )

    # Prepare market data for all markets (for context) but focus on selected one
    market_data = []
    selected_market_info = None

    for market in event.markets:
        if market.prices is None:
            raise ValueError(
                "markets are supposed to be filtered, this should not be possible"
            )

        # Determine price history limit based on whether this is the selected market
        price_limit = (
            main_market_price_history_limit
            if market.id == event.selected_market_id
            else other_markets_price_history_limit
        )

        # Check if market is closed and get price data
        if market.prices is not None and target_date in market.prices.index:
            price_data = market.prices.loc[:target_date].dropna()
            # Limit price history
            if len(price_data) > price_limit:
                price_data = price_data.tail(price_limit)
            recent_prices = price_data.to_string(index=True, header=False)
            current_price = float(market.prices.loc[target_date])
            is_closed = False
        else:
            # Market is closed - get all available historical prices
            if market.prices is not None and len(market.prices) > 0:
                price_data = market.prices.dropna()
                # Limit price history
                if len(price_data) > price_limit:
                    price_data = price_data.tail(price_limit)
                recent_prices = price_data.to_string(index=True, header=False)
                current_price = float(market.prices.dropna().iloc[-1])
            else:
                recent_prices = "No price data available"
                current_price = None
            is_closed = True

        market_info = {
            "id": market.id,
            "question": market.question,
            "description": market.description,
            "recent_prices": recent_prices,
            "current_price": current_price,
            "is_closed": is_closed,
            "price_outcome_name": market.price_outcome_name or "Unknown outcome",
        }
        market_data.append(market_info)

        # Keep track of the selected market info
        if market.id == event.selected_market_id:
            selected_market_info = market_info

    # Create context summaries for all markets
    context_summaries = []
    target_market_summary = ""

    for i, market_info in enumerate(market_data, 1):
        closed_status = (
            " (MARKET CLOSED - NO BETTING ALLOWED)" if market_info["is_closed"] else ""
        )
        outcome_name = market_info["price_outcome_name"]
        is_target = (
            " **[TARGET MARKET FOR DECISION]**"
            if market_info["id"] == event.selected_market_id
            else ""
        )

        summary = f"""
Market {i} (ID: {market_info["id"]}){closed_status}{is_target}:
Question: {market_info["question"]}
Description: {market_info["description"]}
Historical prices for the named outcome "{outcome_name}":
{market_info["recent_prices"]}
Last available price for "{outcome_name}": {market_info["current_price"]}
        """

        if market_info["id"] == event.selected_market_id:
            target_market_summary = summary
        else:
            context_summaries.append(summary)

    full_question = f"""
Date: {target_date.strftime("%B %d, %Y")}

Event: {event.title}
Event Description: {event.description or "No description provided"}

IMPORTANT: You must make a decision ONLY on the TARGET MARKET marked below. The other markets are provided for context to help you understand the broader event.

TARGET MARKET FOR DECISION:
{target_market_summary}

CONTEXT MARKETS (for information only):
{"".join(context_summaries)}

For the TARGET MARKET ONLY, decide whether to BUY (if the shown outcome is undervalued), SELL (if the shown outcome is overvalued), or do NOTHING (if fairly priced or uncertain).

Note: The prices shown are specifically for the named outcome. BUY means you think that outcome is more likely than the current price suggests.
Consider how the context markets might relate to your target market decision.

Provide your decision and rationale for the TARGET MARKET only.
    """

    # Save prompt to file if date_output_path is provided
    if date_output_path:
        model_id = model.model_id if isinstance(model, ApiModel) else model
        timestamp = get_timestamp_string()
        prompt_file = (
            date_output_path
            / model_id.replace("/", "--")
            / f"prompt_event_{event.id}_{timestamp}.txt"
        )

        write_to_storage(prompt_file, full_question)
        logger.info(f"Saved prompt to {prompt_file}")

    # Get agent decisions using smolagents
    if isinstance(model, str) and model == "test_random":
        # Generate random decision for testing
        choice = np.random.choice(["BUY", "SELL", "NOTHING"], p=[0.3, 0.3, 0.4])
        event_decision = EventDecisions(
            decision=choice,
            rationale=f"Random decision for testing market {event.selected_market_id}",
        )
    else:
        if backward_mode:
            cutoff_datetime = datetime.combine(target_date, datetime.min.time())
        else:
            cutoff_datetime = None
        event_decision = run_smolagent_for_event(
            model, full_question, cutoff_date=cutoff_datetime
        )

    # Convert to MarketInvestmentDecision object for the selected market only
    market_decision = create_market_investment_decision(
        event_decision, selected_market_info
    )

    return EventInvestmentResult(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_decision=market_decision,
    )


def save_model_result(
    model_result: ModelInvestmentResult, date_output_path: Path
) -> None:
    """Save model investment result to file."""

    timestamp = get_timestamp_string()
    filename = f"{model_result.model_id.replace('/', '--')}_{timestamp}.json"
    filepath = date_output_path / filename

    content = model_result.model_dump_json(indent=2)
    write_to_storage(filepath, content)

    logger.info(f"Saved model result to {filepath}")
