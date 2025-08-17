import json
import os
import textwrap
from datetime import date, datetime
from typing import Literal

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from smolagents import (
    ChatMessage,
    InferenceClientModel,
    LiteLLMModel,
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
from predibench.logger_config import get_logger
from pydantic import BaseModel

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


def run_smolagent_for_event(
    model_id: str, question: str, cutoff_date: datetime
) -> ToolCallingAgent:
    """Run smolagent for event-level analysis with multi-market tools."""
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
        final_market_decisions,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=40, return_full_result=True
    )
    return agent.run(question)


def validate_event_decisions(raw_output: dict, market_data: list, target_date: date) -> dict:
    """Validate and structure event decisions using LiteLLM with structured output."""
    
    class MarketDecision(BaseModel):
        decision: Literal["BUY", "SELL", "NOTHING"]
        reasoning: str
    
    class EventDecisions(BaseModel):
        decisions: dict[str, MarketDecision]
        overall_reasoning: str
    
    # Prepare market IDs for validation
    market_ids = [market_info['id'] for market_info in market_data]
    closed_markets = [market_info['id'] for market_info in market_data if market_info['is_closed']]
    
    # Create validation prompt
    validation_prompt = f"""
    Please validate and structure the following investment decisions for date {target_date.strftime("%B %d, %Y")}:
    
    Raw agent output: {raw_output}
    
    Expected market IDs: {market_ids}
    Closed markets (should be NOTHING): {closed_markets}
    
    Rules:
    1. All closed markets must have decision "NOTHING"
    2. Each market must have a valid decision: BUY, SELL, or NOTHING
    3. Each decision must include reasoning
    4. If a market is missing from the raw output, set decision to "NOTHING" with appropriate reasoning
    
    Please structure this into the required format with decisions for all markets.
    """
    
    model = LiteLLMModel(
        model_id="gpt-4o-mini",
        requests_per_minute=10,
    )
    
    output = model.generate(
        [ChatMessage(role="user", content=validation_prompt)],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "event_decisions",
                "schema": EventDecisions.model_json_schema(),
            },
        },
    )
    
    # Parse and validate the structured output
    structured_data = json.loads(output.content)
    validated_decisions = EventDecisions(**structured_data)
    
    # Ensure all markets are covered and closed markets are set to NOTHING
    final_decisions = {}
    for market_info in market_data:
        market_id = market_info['id']
        if market_id in validated_decisions.decisions:
            decision_data = validated_decisions.decisions[market_id]
            # Force NOTHING for closed markets
            if market_info['is_closed']:
                final_decisions[market_id] = {
                    "decision": "NOTHING",
                    "reasoning": f"Market is closed. Original reasoning: {decision_data.reasoning}"
                }
            else:
                final_decisions[market_id] = {
                    "decision": decision_data.decision,
                    "reasoning": decision_data.reasoning
                }
        else:
            # Market missing from decisions
            final_decisions[market_id] = {
                "decision": "NOTHING",
                "reasoning": "No decision provided by agent" + (" - Market is closed" if market_info['is_closed'] else "")
            }
    
    return {
        "decisions": final_decisions,
        "overall_reasoning": validated_decisions.overall_reasoning
    }


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
    list_models: list[str], 
    events: list[Event], 
    target_date: date | None = None,
    backward_mode: bool = False
) -> None:
    """
    Launch agent investments for events on a specific date.
    Runs each model sequentially (will be parallelized later).
    
    Args:
        list_models: List of model IDs to run investments with
        events: List of events to analyze
        target_date: Date for backward compatibility (defaults to today)
        backward_mode: Whether running in backward compatibility mode
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Running agent investments for {len(list_models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")
    
    for model_id in list_models:
        logger.info(f"Processing model: {model_id}")
        process_single_model(model_id=model_id, events=events, target_date=target_date, backward_mode=backward_mode)


def process_single_model(model_id: str, events: list[Event], target_date: date, backward_mode: bool) -> ModelInvestmentResult:
    """Process investments for all events for a specific model and save results."""
    event_results = []
    
    for event in events:
        logger.info(f"Processing event: {event.title}")
        event_result = process_event_investment(model_id=model_id, event=event, target_date=target_date, backward_mode=backward_mode)
        event_results.append(event_result)
    
    model_result = ModelInvestmentResult(
        model_id=model_id,
        target_date=target_date,
        event_results=event_results
    )
    
    save_model_result(model_result, target_date)
    return model_result


def process_event_investment(model_id: str, event: Event, target_date: date, backward_mode: bool) -> EventInvestmentResult:
    """Process investment decisions for all markets in an event."""
    logger.info(f"Processing event: {event.title} with {len(event.markets)} markets")
    
    # Prepare market data for all markets in the event
    market_data = []
    for market in event.markets:
        if market.prices is None:
            market.fill_prices(end_time=datetime.combine(target_date, datetime.min.time()))
        
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
            "is_closed": is_closed
        }
        market_data.append(market_info)
    
    # Create comprehensive question for all markets in the event
    market_summaries = []
    for i, market_info in enumerate(market_data, 1):
        closed_status = " (MARKET CLOSED - NO BETTING ALLOWED)" if market_info['is_closed'] else ""
        summary = f"""
Market {i} (ID: {market_info['id']}){closed_status}:
Question: {market_info['question']}
Description: {market_info['description']}
Historical YES prices:
{market_info['recent_prices']}
Last available price: {market_info['current_price']}
        """
        market_summaries.append(summary)
    
    full_question = f"""
Date: {target_date.strftime("%B %d, %Y")}

Event: {event.title}
Event Description: {event.description or "No description provided"}

You are analyzing {len(event.markets)} markets within this event. Consider how these markets might be related and make informed investment decisions.

Markets to analyze:
{"".join(market_summaries)}

For each market, decide whether to BUY (if undervalued), SELL (if overvalued), or do NOTHING (if fairly priced or uncertain).
Consider market correlations within this event when making decisions.

Use the final_market_decisions tool to provide your decisions with reasoning for each market.
    """
    
    # Get agent decisions using smolagents
    if model_id == "test_random":
        # Generate random decisions for testing
        decisions_dict = {}
        for market_info in market_data:
            choice = np.random.choice(["BUY", "SELL", "NOTHING"], p=[0.3, 0.3, 0.4])
            decisions_dict[market_info['id']] = {
                "decision": choice,
                "reasoning": f"Random decision for testing market {market_info['id']}"
            }
        response_output = decisions_dict
        token_usage = None
        overall_reasoning = "Random decisions generated for testing purposes"
    else:
        response = run_smolagent_for_event(model_id, full_question, cutoff_date=target_date)
        response_output = response.output
        token_usage = response.token_usage._asdict() if response.token_usage else None
        overall_reasoning = str(response.messages[-1]) if response.messages else "No overall reasoning provided"
    
    # Validate and structure the output using LiteLLM
    structured_result = validate_event_decisions(response_output, market_data, target_date)
    
    # Create market decisions
    market_decisions = []
    for market_info in market_data:
        market_id = market_info['id']
        if market_id in structured_result['decisions']:
            decision_data = structured_result['decisions'][market_id]
            market_decision = MarketInvestmentDecision(
                market_id=market_id,
                market_question=market_info['question'],
                decision=decision_data['decision'],
                reasoning=decision_data.get('reasoning', 'No reasoning provided'),
                market_price=market_info['current_price'],
                is_closed=market_info['is_closed']
            )
        else:
            # Fallback if market not in decisions
            market_decision = MarketInvestmentDecision(
                market_id=market_id,
                market_question=market_info['question'],
                decision="NOTHING",
                reasoning="No decision provided by agent",
                market_price=market_info['current_price'],
                is_closed=market_info['is_closed']
            )
        market_decisions.append(market_decision)
    
    return EventInvestmentResult(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_decisions=market_decisions,
        overall_reasoning=structured_result.get('overall_reasoning', overall_reasoning),
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
