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
from smolagents.models import ApiModel

from predibench.polymarket_api import Market, Event
from predibench.utils import OUTPUT_PATH
from predibench.logger_config import get_logger
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

load_dotenv()

logger = get_logger(__name__)


class MarketInvestmentDecision(BaseModel):
    market_id: str
    market_question: str
    decision: Literal["BUY", "SELL", "NOTHING"]
    reasoning: str | None = None
    market_price: float | None = None
    is_closed: bool = False


class EventInvestmentResult(BaseModel):
    event_id: str
    event_title: str
    event_description: str | None = None
    market_decisions: list[MarketInvestmentDecision]
    overall_reasoning: str  # Overall reasoning for the event
    token_usage: dict | None = None


class ModelInvestmentResult(BaseModel):
    model_id: str
    target_date: date
    event_results: list[EventInvestmentResult]


class MarketDecision(BaseModel):
    decision: Literal["BUY", "SELL", "NOTHING"]
    reasoning: str


class EventDecisions(BaseModel):
    decisions: dict[str, MarketDecision]
    overall_reasoning: str


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
def validate_event_decisions_json(json_str: str) -> EventDecisions:
    """
    This tool is used to validate the output of the event decisions agent.
    
    Args:
        json_str (str): The JSON string to validate for event decisions.
        
    Returns:
        EventDecisions: The validated EventDecisions object, raises error if invalid.
    """
    data = json.loads(json_str)
    return EventDecisions(**data)


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
def final_market_decisions(
    decisions: dict,
) -> dict:
    """
    Provides final investment decisions for all markets in an event with reasoning.

    Args:
        decisions: Dictionary mapping market_id to decision details.
                  Example: {
                      "market_123": {"decision": "BUY", "reasoning": "Market undervalues the probability based on recent events"},
                      "market_456": {"decision": "SELL", "reasoning": "Current price overestimates likelihood due to hype"},
                      "market_789": {"decision": "NOTHING", "reasoning": "Insufficient information to make confident prediction"}
                  }
                  Valid decisions: "BUY", "SELL", "NOTHING"
    """
    logger.info(f"Final market decisions: {decisions}")
    return decisions


def run_smolagent_for_event(
    model: ApiModel, question: str, cutoff_date: datetime
) -> EventDecisions:
    """Run smolagent for event-level analysis with multi-market tools using structured output."""
    
    # Create the parser and prompt template
    parser = PydanticOutputParser(pydantic_object=EventDecisions)
    prompt_template = PromptTemplate(
        template="""
        {question}
        
        {format_instructions}
        
        You must return a valid JSON object that matches the EventDecisions schema and nothing else.
        
        Use the validate_event_decisions_json tool to validate your output before providing the final answer.
        Give your final answer only if it passes the validation.
        """,
        input_variables=["question"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Format the prompt
    prompt = prompt_template.format(question=question)
    
    tools = [
        GoogleSearchTool(provider="serper", cutoff_date=cutoff_date),
        VisitWebpageTool(),
        validate_event_decisions_json,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=40, return_full_result=True
    )
    
    result = agent.run(prompt)
    
    # Parse and return the structured output
    return EventDecisions.model_validate_json(result.output)


def create_market_investment_decisions(
    event_decisions: EventDecisions, 
    market_data: list
) -> list[MarketInvestmentDecision]:
    """Convert EventDecisions to MarketInvestmentDecision objects, handling closed markets."""
    market_decisions = []
    
    for market_info in market_data:
        market_id = market_info['id']
        
        if market_id in event_decisions.decisions:
            decision_data = event_decisions.decisions[market_id]
            # Force NOTHING for closed markets
            if market_info['is_closed']:
                market_decision = MarketInvestmentDecision(
                    market_id=market_id,
                    market_question=market_info['question'],
                    decision="NOTHING",
                    reasoning=f"Market is closed. Original reasoning: {decision_data.reasoning}",
                    market_price=market_info['current_price'],
                    is_closed=True
                )
            else:
                market_decision = MarketInvestmentDecision(
                    market_id=market_id,
                    market_question=market_info['question'],
                    decision=decision_data.decision,
                    reasoning=decision_data.reasoning,
                    market_price=market_info['current_price'],
                    is_closed=False
                )
        else:
            # Fallback if market not in decisions
            market_decision = MarketInvestmentDecision(
                market_id=market_id,
                market_question=market_info['question'],
                decision="NOTHING",
                reasoning="No decision provided by agent" + (" - Market is closed" if market_info['is_closed'] else ""),
                market_price=market_info['current_price'],
                is_closed=market_info['is_closed']
            )
        
        market_decisions.append(market_decision)
    
    return market_decisions


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

def launch_agent_investments(
    list_models: list[ApiModel | str], 
    events: list[Event], 
    target_date: date | None = None,
    backward_mode: bool = False
) -> None:
    """
    Launch agent investments for events on a specific date.
    Runs each model sequentially (will be parallelized later).
    
    Args:
        list_models: List of ApiModel objects or "test_random" string to run investments with
        events: List of events to analyze
        target_date: Date for backward compatibility (defaults to today)
        backward_mode: Whether running in backward compatibility mode
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Running agent investments for {len(list_models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")
    
    for model in list_models:
        model_name = model.model_id if isinstance(model, ApiModel) else model
        logger.info(f"Processing model: {model_name}")
        process_single_model(model=model, events=events, target_date=target_date, backward_mode=backward_mode)


def process_single_model(model: ApiModel | str, events: list[Event], target_date: date, backward_mode: bool) -> ModelInvestmentResult:
    """Process investments for all events for a specific model and save results."""
    event_results = []
    
    for event in events:
        logger.info(f"Processing event: {event.title}")
        event_result = process_event_investment(model=model, event=event, target_date=target_date, backward_mode=backward_mode)
        event_results.append(event_result)
    
    model_id = model.model_id if isinstance(model, ApiModel) else model
    model_result = ModelInvestmentResult(
        model_id=model_id,
        target_date=target_date,
        event_results=event_results
    )
    
    save_model_result(model_result, target_date)
    return model_result


def process_event_investment(model: ApiModel | str, event: Event, target_date: date, backward_mode: bool) -> EventInvestmentResult:
    """Process investment decisions for all markets in an event."""
    logger.info(f"Processing event: {event.title} with {len(event.markets)} markets")
    
    # Prepare market data for all markets in the event
    market_data = []
    for market in event.markets:
        if market.prices is None:
            raise ValueError("markets are supposed to be filtered, this should not be possible")
        
        # Check if market is closed and get price data
        if market.prices is not None and target_date in market.prices.index:
            recent_prices = (
                market.prices.loc[:target_date]
                .dropna()
                .to_string(index=True, header=False)
            )
            current_price = float(market.prices.loc[target_date])
            is_closed = False
        else:
            # Market is closed - get all available historical prices
            if market.prices is not None and len(market.prices) > 0:
                recent_prices = (
                    market.prices
                    .dropna()
                    .to_string(index=True, header=False)
                )
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
            "price_outcome_name": market.price_outcome_name or "Unknown outcome"
        }
        market_data.append(market_info)
    
    # Create comprehensive question for all markets in the event
    market_summaries = []
    for i, market_info in enumerate(market_data, 1):
        closed_status = " (MARKET CLOSED - NO BETTING ALLOWED)" if market_info['is_closed'] else ""
        outcome_name = market_info['price_outcome_name']
        summary = f"""
Market {i} (ID: {market_info['id']}){closed_status}:
Question: {market_info['question']}
Description: {market_info['description']}
Historical prices for the named outcome "{outcome_name}":
{market_info['recent_prices']}
Last available price for "{outcome_name}": {market_info['current_price']}
        """
        market_summaries.append(summary)
    
    full_question = f"""
Date: {target_date.strftime("%B %d, %Y")}

Event: {event.title}
Event Description: {event.description or "No description provided"}

You are analyzing {len(event.markets)} markets within this event. Consider how these markets might be related and make informed investment decisions.

Markets to analyze:
{"".join(market_summaries)}

For each market, decide whether to BUY (if the shown outcome is undervalued), SELL (if the shown outcome is overvalued), or do NOTHING (if fairly priced or uncertain).
Note: The prices shown are specifically for the named outcome in each market. BUY means you think that outcome is more likely than the current price suggests.
Consider market correlations within this event when making decisions.

Use the final_market_decisions tool to provide your decisions with reasoning for each market.
    """
    
    # Get agent decisions using smolagents
    if isinstance(model, str) and model == "test_random":
        # Generate random decisions for testing
        decisions_dict = {}
        for market_info in market_data:
            choice = np.random.choice(["BUY", "SELL", "NOTHING"], p=[0.3, 0.3, 0.4])
            decisions_dict[market_info['id']] = MarketDecision(
                decision=choice,
                reasoning=f"Random decision for testing market {market_info['id']}"
            )
        event_decisions = EventDecisions(
            decisions=decisions_dict,
            overall_reasoning="Random decisions generated for testing purposes"
        )
        token_usage = None
    else:
        event_decisions = run_smolagent_for_event(model, full_question, cutoff_date=target_date)
        token_usage = None  # TODO: Extract token usage from agent if needed
    
    # Convert to MarketInvestmentDecision objects using helper function
    market_decisions = create_market_investment_decisions(event_decisions, market_data)
    
    return EventInvestmentResult(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_decisions=market_decisions,
        overall_reasoning=event_decisions.overall_reasoning,
        token_usage=token_usage
    )


def save_model_result(model_result: ModelInvestmentResult, target_date: date) -> None:
    """Save model investment result to file."""
    output_dir = OUTPUT_PATH / "investments" / target_date.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{model_result.model_id.replace('/', '--')}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        f.write(model_result.model_dump_json(indent=2))
    
    logger.info(f"Saved model result to {filepath}")
if __name__ == "__main__":
    run_smolagent(
        "gpt-4.1",
        "Will the S&P 500 close above 4,500 by the end of the year?",
        datetime(2024, 6, 1),
    )
