import os
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from smolagents import OpenAIModel, Tool, ToolCallingAgent, VisitWebpageTool, tool

load_dotenv()


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
            print(f"Error response: {response.status_code}")
            print(f"Response text: {response.text}")
            raise ValueError(response.json())

        if self.organic_key not in results.keys():
            raise Exception(
                f"No results found for query: '{query}'. Use a less restrictive query."
            )
        if len(results[self.organic_key]) == 0:
            return f"No results found for '{query}'. Try with a more general query, or remove the year filter."

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
    print(f"Final answer: {answer}")
    return answer


if __name__ == "__main__":
    tool = GoogleSearchTool(provider="serper", cutoff_date=datetime(2024, 6, 1))
    results_with_filter = tool.forward("OpenAI GPT-5 news")

    tool = GoogleSearchTool(provider="serper")
    results_without_filter = tool.forward("OpenAI GPT-5 news")

    assert results_with_filter != results_without_filter


def run_smolagent(
    model_id: str, question: str, cutoff_date: datetime
) -> ToolCallingAgent:
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
    prompt = f"""Let's say we are the {cutoff_date.strftime("%B %d, %Y")}.
    Please answer the below question by yes or no. But first, run a detailed analysis. You can search the web for information.
    One good method for analyzing is to break down the question into sub-parts, like a tree, and assign probabilities to each sub-branch of the tree, to get a total probability of the question being true.
    Here is the question:
    {question}

    What would you decide: buy yes, buy no, or do nothing?
    """
    return agent.run(prompt)


# visit_webpage_tool = VisitWebpageTool()
# print(
#     visit_webpage_tool.forward(
#         "https://www.axios.com/2025/07/24/openai-gpt-5-august-2025"
#     )
# )

if __name__ == "__main__":
    run_smolagent(
        "Will the S&P 500 close above 4,500 by the end of the year?",
        datetime(2024, 6, 1),
    )
