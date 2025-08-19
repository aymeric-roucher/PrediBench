import json
import textwrap
from datetime import date
from typing import Literal

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


class EventDecisions(BaseModel):
    rationale: str
    decision: Literal["BUY", "SELL", "NOTHING"]


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
        + "\n\nProvide your detailed analysis and reasoning, then clearly state your final decision.",
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
        Based on the following research output, extract the investment decision and rationale:
        
        {research_output}
        
        You must provide:
        1. A clear rationale summarizing the key points from the research
        2. A decision that must be exactly one of: BUY, SELL, or NOTHING
        
        BUY means you think the outcome is undervalued (more likely than current price suggests)
        SELL means you think the outcome is overvalued (less likely than current price suggests)  
        NOTHING means fairly priced or too uncertain to bet
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
    return EventDecisions(
        rationale=parsed_output["rationale"], decision=parsed_output["decision"]
    )
