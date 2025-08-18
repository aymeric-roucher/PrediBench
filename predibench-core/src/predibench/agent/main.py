from datetime import date, datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from datasets import load_dataset, concatenate_datasets, Dataset

from predibench.polymarket_api import Event
from predibench.logger_config import get_logger
from predibench.storage_utils import write_to_storage
from predibench.utils import get_timestamp_string
from predibench.agent.dataclasses import EventDecisions, MarketInvestmentDecision, EventInvestmentResult, ModelInvestmentResult
from predibench.agent.smolagents_utils import run_smolagents
from smolagents import (
    RunResult,
    Timing,
    ApiModel,
)

load_dotenv()

logger = get_logger(__name__)




def create_market_investment_decision(
    event_decision: EventDecisions, selected_market_info: dict
) -> MarketInvestmentDecision:
    """Convert EventDecision to MarketInvestmentDecision."""
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


def _upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentResult], 
    target_date: date, 
    dataset_name: str,
    split: str,
    hf_token: str,
    timestamp_for_saving: str,
) -> None:
    """Upload investment results to Hugging Face dataset."""
    choice_mapping = {"BUY": 1, "SELL": 0, "NOTHING": -1}
    
    new_rows = [
        {
            "agent_name": model_result.model_id,
            "date": target_date,
            "question": event_result.market_decision.market_question,
            "choice": choice_mapping.get(event_result.market_decision.decision, -1),
            "choice_raw": event_result.market_decision.decision.lower(),
            "market_id": event_result.market_decision.market_id,
            "messages_count": 0,
            "has_reasoning": event_result.market_decision.rationale is not None,
            "timestamp_uploaded": timestamp_for_saving,
            "rationale": event_result.market_decision.rationale or "",
        }
        for model_result in results_per_model
        for event_result in model_result.event_results
    ]
    
    if not new_rows:
        logger.warning("No data to upload to HF dataset")
        return
        
    ds = load_dataset(dataset_name)
    existing_data = ds.get(split, Dataset.from_list([]))
    
    combined_dataset = concatenate_datasets([existing_data, Dataset.from_list(new_rows)])
    combined_dataset.push_to_hub(dataset_name, split=split, token=hf_token)
    
    logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")


def save_model_result(
    model_result: ModelInvestmentResult, 
    date_output_path: Path,
    timestamp_for_saving: str
) -> None:
    """Save model result to file."""

    filename = f"{model_result.model_id.replace('/', '--')}_{timestamp_for_saving}.json"
    filepath = date_output_path / filename

    content = model_result.model_dump_json(indent=2)
    write_to_storage(filepath, content)

    logger.info(f"Saved model result to {filepath}")



def process_event_investment(
    model: ApiModel | str,
    event: Event,
    target_date: date,
    backward_mode: bool,
    date_output_path: Path | None,
    main_market_price_history_limit: int,
    other_markets_price_history_limit: int,
    timestamp_for_saving: str
) -> EventInvestmentResult:
    """Process investment decision for selected market."""
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
        prompt_file = (
            date_output_path
            / model_id.replace("/", "--")
            / f"prompt_event_{event.id}_{timestamp_for_saving}.txt"
        )

        write_to_storage(prompt_file, full_question)
        logger.info(f"Saved prompt to {prompt_file}")

    # Get agent decisions using smolagents
    if isinstance(model, str) and model == "test_random":
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
        event_decision = run_smolagents(
            model, full_question, cutoff_date=cutoff_datetime
        )

    # Convert to MarketInvestmentDecision for selected market
    market_decision = create_market_investment_decision(
        event_decision, selected_market_info
    )

    return EventInvestmentResult(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_decision=market_decision,
    )


def _process_single_model(
    model: ApiModel | str,
    events: list[Event],
    target_date: date,
    backward_mode: bool,
    date_output_path: Path | None,
    main_market_price_history_limit: int,
    other_markets_price_history_limit: int,
    timestamp_for_saving: str
) -> ModelInvestmentResult:
    """Process investments for all events for a model."""
    event_results = []

    for event in events:
        logger.info(f"Processing event: {event.title}")
        event_result = process_event_investment(
            model=model,
            event=event,
            target_date=target_date,
            backward_mode=backward_mode,
            date_output_path=date_output_path,
            main_market_price_history_limit=main_market_price_history_limit,
            other_markets_price_history_limit=other_markets_price_history_limit,
            timestamp_for_saving=timestamp_for_saving,
        )
        event_results.append(event_result)

    model_id = model.model_id if isinstance(model, ApiModel) else model
    model_result = ModelInvestmentResult(
        model_id=model_id, target_date=target_date, event_results=event_results
    )

    if date_output_path:
        save_model_result(model_result=model_result, date_output_path=date_output_path, timestamp_for_saving=timestamp_for_saving)
    return model_result


def run_agent_investments(
    models: list[ApiModel | str],
    events: list[Event],
    target_date: date,
    backward_mode: bool,
    date_output_path: Path | None,
    dataset_name: str,
    split: str,
    main_market_price_history_limit: int,
    other_markets_price_history_limit: int,
    hf_token_for_dataset: str | None
) -> list[ModelInvestmentResult]:
    """Launch agent investments for events on a specific date."""
    logger.info(f"Running agent investments for {len(models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")

    timestamp_for_saving = get_timestamp_string()
    results = []
    for model in models:
        model_name = model.model_id if isinstance(model, ApiModel) else model
        logger.info(f"Processing model: {model_name}")
        model_result = _process_single_model(
            model=model,
            events=events,
            target_date=target_date,
            backward_mode=backward_mode,
            date_output_path=date_output_path,
            main_market_price_history_limit=main_market_price_history_limit,
            other_markets_price_history_limit=other_markets_price_history_limit,
            timestamp_for_saving=timestamp_for_saving,
        )
        results.append(model_result)
        
    if hf_token_for_dataset:
        _upload_results_to_hf_dataset(
            results_per_model=results, 
            target_date=target_date, 
            dataset_name=dataset_name, 
            split=split,
            hf_token=hf_token_for_dataset
        )

    return results
