import json
import textwrap
from datetime import date

from predibench.logger_config import get_logger
from pydantic import BaseModel
from smolagents import (
    ApiModel,
    ChatMessage,
    LiteLLMModel,
    Tool,
    ToolCallingAgent,
    VisitWebpageTool,
    tool,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from typing import Literal


class MarketDecision(BaseModel):
    market_id: str
    reasoning: str
    probability_assessment: float  # Model's assessment of probability (0.0 to 1.0)
    confidence_in_assessment: float  # Confidence level (0.0 to 1.0)
    direction: Literal["buy_yes", "buy_no", "nothing"]  # Direction of the bet
    amount: float  # Fraction of allocated capital (0.0 to 1.0)


class EventDecisions(BaseModel):
    market_decisions: list[MarketDecision]


logger = get_logger(__name__)


class GoogleSearchTool(Tool):
    name = "web_search"
    description = """Performs Google web search and returns top results."""
    inputs = {
        "query": {"type": "string", "description": "The search query to perform."},
    }
    output_type = "string"

    def __init__(self, provider: str, cutoff_date: date | None, api_key: str):
        super().__init__()
        self.provider = provider
        self.organic_key = "organic_results" if provider == "serpapi" else "organic"
        self.api_key = api_key
        self.cutoff_date = cutoff_date

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
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
    market_decisions: list[dict], unallocated_capital: float
) -> EventDecisions:
    """
    This tool is used to validate and return the final event decisions for all relevant markets.

    This tool must be used only once. Provide decisions for all markets you want to bet on.

    Args:
        market_decisions (list[dict]): List of market decisions. Each dict should contain:
            - market_id (str): The market ID
            - reasoning (str): Reasoning for the decision
            - probability_assessment (float): Your probability assessment (0.0 to 1.0)
            - confidence_in_assessment (float): Your confidence level (0.0 to 1.0)
            - direction (str): "buy_yes", "buy_no", or "nothing"
            - amount (float): Fraction of allocated capital (0.0 to 1.0)
        unallocated_capital (float): Fraction of capital not allocated to any bet (0.0 to 1.0)

    Returns:
        EventDecisions: The validated EventDecisions object, raises error if invalid.
    """
    validated_decisions = []
    total_allocated = 0.0

    for decision_dict in market_decisions:
        # Validate market decision fields
        assert decision_dict["direction"] in ["buy_yes", "buy_no", "nothing"], (
            "Invalid direction, must be buy_yes, buy_no, or nothing"
        )
        assert 0.0 <= decision_dict["amount"] <= 1.0, (
            "Amount must be between 0.0 and 1.0"
        )
        assert len(decision_dict["reasoning"]) > 0, "Reasoning must be non-empty"
        assert 0.0 <= decision_dict["probability_assessment"] <= 1.0, (
            "Probability assessment must be between 0.0 and 1.0"
        )
        assert 0.0 <= decision_dict["confidence_in_assessment"] <= 1.0, (
            "Confidence must be between 0.0 and 1.0"
        )

        # Only count non-nothing bets toward total allocation
        if decision_dict["direction"] != "nothing":
            total_allocated += decision_dict["amount"]

        market_decision = MarketDecision(
            market_id=decision_dict["market_id"],
            reasoning=decision_dict["reasoning"],
            probability_assessment=decision_dict["probability_assessment"],
            confidence_in_assessment=decision_dict["confidence_in_assessment"],
            direction=decision_dict["direction"],
            amount=decision_dict["amount"],
        )
        validated_decisions.append(market_decision)

    # Validate that total allocation adds up to 1.0
    assert 0.0 <= unallocated_capital <= 1.0, (
        "Unallocated capital must be between 0.0 and 1.0"
    )
    total_capital_used = total_allocated + unallocated_capital
    assert abs(total_capital_used - 1.0) < 0.001, (
        f"Total capital allocation must equal 1.0, got {total_capital_used:.3f} (allocated: {total_allocated:.3f}, unallocated: {unallocated_capital:.3f})"
    )

    return EventDecisions(market_decisions=validated_decisions)


def run_smolagents(
    model: ApiModel,
    question: str,
    cutoff_date: date | None,
    search_provider: str,
    search_api_key: str,
    max_steps: int,
) -> EventDecisions:
    """Run smolagent for event-level analysis with structured output."""

    prompt = f"""{question}
        
Use the final_answer tool to validate your output before providing the final answer.
The final_answer tool must contain the arguments rationale and decision.
"""

    tools = [
        GoogleSearchTool(
            provider=search_provider, cutoff_date=cutoff_date, api_key=search_api_key
        ),
        VisitWebpageTool(),
        final_answer,
    ]
    agent = ToolCallingAgent(
        tools=tools, model=model, max_steps=max_steps, return_full_result=True
    )

    result = agent.run(prompt)

    return result.output


def run_deep_research(
    model_id: str,
    question: str,
    structured_output_model_id: str,
) -> EventDecisions:
    from openai import OpenAI

    client = OpenAI(timeout=3600)

    response = client.responses.create(
        model=model_id,
        input=question
        + "\n\nProvide your detailed analysis and reasoning, then clearly state your final decisions for each market you want to bet on.",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
        ],
    )
    research_output = response.output_text

    # Use structured output to get EventDecisions
    structured_model = LiteLLMModel(
        model_id=structured_output_model_id,
    )

    structured_prompt = textwrap.dedent(f"""
        Based on the following research output, extract the investment decisions for each market:
        
        {research_output}
        
        You must provide a list of market decisions. Each decision should include:
        1. market_id: The ID of the market
        2. reasoning: Your reasoning for this decision
        3. probability_assessment: Your probability assessment (0.0 to 1.0)
        4. confidence_in_assessment: Your confidence level (0.0 to 1.0)
        5. direction: "buy_yes", "buy_no", or "nothing"
        6. amount: Fraction of capital to bet (0.0 to 1.0)
        
        The sum of all amounts must not exceed 1.0.
    """)

    structured_output = structured_model.generate(
        [ChatMessage(role="user", content=structured_prompt)],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": EventDecisions.model_json_schema(),
            },
        },
    )

    parsed_output = json.loads(structured_output.content)
    return EventDecisions(market_decisions=parsed_output["market_decisions"])
