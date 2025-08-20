import os
from datetime import date, datetime
from pathlib import Path

import numpy as np
from datasets import Dataset, concatenate_datasets, load_dataset
from dotenv import load_dotenv
from predibench.agent.dataclasses import (
    EventInvestmentResult,
    MarketInvestmentResult,
    ModelInvestmentResult,
)
from predibench.agent.smolagents_utils import (
    EventDecisions,
    run_deep_research,
    run_smolagents,
)
from predibench.date_utils import is_backward_mode
from predibench.logger_config import get_logger
from predibench.polymarket_api import Event
from predibench.storage_utils import write_to_storage
from smolagents import ApiModel

load_dotenv()

logger = get_logger(__name__)


def _create_market_investment_decisions(
    event_decisions: EventDecisions, market_info_dict: dict
) -> list[MarketInvestmentResult]:
    """Convert EventDecisions to list of MarketInvestmentResult."""
    results = []
    
    for market_decision in event_decisions.market_decisions:
        market_info = market_info_dict[market_decision.market_id]
        
        if market_info["is_closed"]:
            # Create a "nothing" decision for closed markets
            from predibench.agent.dataclasses import BettingResult
            betting_decision = BettingResult(
                direction="nothing",
                amount=0.0,
                reasoning=f"Market is closed. Original reasoning: {market_decision.betting_decision.reasoning}"
            )
            result = MarketInvestmentResult(
                market_id=market_info["id"],
                market_question=market_info["question"],
                probability_assessment=market_decision.probability_assessment,
                market_odds=market_decision.market_odds,
                confidence_in_assessment=market_decision.confidence_in_assessment,
                betting_decision=betting_decision,
                market_price=market_info["current_price"],
                is_closed=True,
            )
        else:
            result = MarketInvestmentResult(
                market_id=market_info["id"],
                market_question=market_info["question"],
                probability_assessment=market_decision.probability_assessment,
                market_odds=market_decision.market_odds,
                confidence_in_assessment=market_decision.confidence_in_assessment,
                betting_decision=market_decision.betting_decision,
                market_price=market_info["current_price"],
                is_closed=False,
            )
        results.append(result)
    
    return results


def _upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentResult],
    target_date: date,
    hf_token: str,
    dataset_name: str = "m-ric/predibench-agent-choices",
    split: str = "train",
) -> None:
    """Upload investment results to the Hugging Face dataset."""
    # Load the existing dataset
    ds = load_dataset(dataset_name)

    # Prepare new data rows
    new_rows = []
    current_timestamp = datetime.now()

    for model_result in results_per_model:
        for event_result in model_result.event_results:
            # Handle multiple market decisions per event
            for market_decision in event_result.market_decisions:
                # Map decision to choice value
                choice_mapping = {"buy_yes": 1, "buy_no": 0, "nothing": -1}
                choice = choice_mapping.get(market_decision.betting_decision.direction, -1)

                row = {
                    "agent_name": model_result.model_id,
                    "date": target_date,
                    "question": market_decision.market_question,
                    "choice": choice,
                    "choice_raw": market_decision.betting_decision.direction,
                    "market_id": market_decision.market_id,
                    "messages_count": 0,  # This would need to be tracked during agent execution
                    "has_reasoning": market_decision.betting_decision.reasoning is not None,
                    "timestamp_uploaded": current_timestamp,
                    "rationale": market_decision.betting_decision.reasoning or "",
                    "probability_assessment": market_decision.probability_assessment,
                    "market_odds": market_decision.market_odds,
                    "confidence_in_assessment": market_decision.confidence_in_assessment,
                    "betting_amount": market_decision.betting_decision.amount,
                }
                new_rows.append(row)

    if new_rows:
        # Create a new dataset with the new rows
        new_dataset = Dataset.from_list(new_rows)
        # Concatenate with existing dataset using datasets.concatenate_datasets

        # Check if split exists, if not use empty dataset
        try:
            existing_data = ds[split]
        except KeyError:
            existing_data = Dataset.from_list([])

        combined_dataset = concatenate_datasets([existing_data, new_dataset])

        # Push back to hub as a pull request (safer approach)
        combined_dataset.push_to_hub(
            dataset_name,
            split=split,
            token=hf_token,
        )

        logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")
    else:
        logger.warning("No data to upload to HF dataset")


def save_model_result(
    model_result: ModelInvestmentResult,
    date_output_path: Path,
    timestamp_for_saving: str,
) -> None:
    """Save model result to file."""

    filename = f"{model_result.model_id.replace('/', '--')}_{timestamp_for_saving}.json"
    filepath = date_output_path / filename

    content = model_result.model_dump_json(indent=2)
    write_to_storage(filepath, content)

    logger.info(f"Saved model result to {filepath}")


def _process_event_investment(
    model: ApiModel | str,
    event: Event,
    target_date: date,
    date_output_path: Path | None,
    timestamp_for_saving: str,
    main_market_price_history_limit: int = 200,
    other_markets_price_history_limit: int = 20,
) -> EventInvestmentResult:
    """Process investment decisions for all relevant markets."""
    logger.info(f"Processing event: {event.title} with {len(event.markets)} markets")
    backward_mode = is_backward_mode(target_date)

    # Prepare market data for all markets
    market_data = {}

    for market in event.markets:
        if market.prices is None:
            raise ValueError(
                "markets are supposed to be filtered, this should not be possible"
            )

        # Use shorter price history for all markets to keep context manageable
        price_limit = other_markets_price_history_limit

        # Check if market is closed and get price data
        if market.prices is not None and target_date in market.prices.index:
            if backward_mode:
                price_data = market.prices.loc[:target_date].dropna()
            else:
                price_data = market.prices.dropna()
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
        market_data[market.id] = market_info

    # Create summaries for all markets
    market_summaries = []

    for market_info in market_data.values():
        outcome_name = market_info["price_outcome_name"]

        summary = f"""
Market ID: {market_info["id"]}
Question: {market_info["question"]}
Description: {market_info["description"] or "No description"}
Historical prices for the outcome "{outcome_name}":
{market_info["recent_prices"]}
Last available price for "{outcome_name}": {market_info["current_price"]}
        """
        market_summaries.append(summary)

    full_question = f"""
Date: {target_date.strftime("%B %d, %Y")}

Event: {event.title}

You have access to {len(market_data)} markets related to this event. For EACH market you want to bet on, you need to provide:

1. probability_assessment: Your assessment of the true probability (0.0 to 1.0)
2. market_odds: The current market price/odds (0.0 to 1.0) 
3. confidence_in_assessment: How confident you are in your assessment (0.0 to 1.0)
4. betting_decision: 
   - direction: "buy_yes" (bet outcome happens), "buy_no" (bet outcome doesn't happen), or "nothing" (don't bet)
   - amount: Fraction of allocated capital to bet (0.0 to 1.0)
   - reasoning: Explanation for your decision

AVAILABLE MARKETS:
{"".join(market_summaries)}

Use the final_answer tool to provide your decisions. You can bet on multiple markets or skip markets you're not confident about.

Note: The prices shown are for the specific outcome mentioned. "buy_yes" means you think that outcome is more likely than the current price suggests. "buy_no" means you think it's less likely.
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
        # Create random decisions for all markets
        from predibench.agent.smolagents_utils import MarketDecision
        from predibench.agent.dataclasses import BettingResult
        
        market_decisions = []
        for market_info in market_data.values():
            direction = np.random.choice(["buy_yes", "buy_no", "nothing"], p=[0.3, 0.3, 0.4])
            amount = np.random.uniform(0.1, 0.5) if direction != "nothing" else 0.0
            
            betting_decision = BettingResult(
                direction=direction,
                amount=amount,
                reasoning=f"Random decision for testing market {market_info['id']}"
            )
            
            market_decision = MarketDecision(
                market_id=market_info["id"],
                probability_assessment=np.random.uniform(0.1, 0.9),
                market_odds=market_info["current_price"] or 0.5,
                confidence_in_assessment=np.random.uniform(0.3, 0.8),
                betting_decision=betting_decision
            )
            market_decisions.append(market_decision)
        
        event_decisions = EventDecisions(market_decisions=market_decisions)
    elif isinstance(model, str) and model == "o3-deep-research":
        event_decisions = run_deep_research(
            model_id="o3-deep-research",
            question=full_question,
            structured_output_model_id="gpt-5",
        )
    else:
        event_decisions = run_smolagents(
            model=model,
            question=full_question,
            cutoff_date=target_date if backward_mode else None,
            search_provider="serper",
            search_api_key=os.getenv("SERPER_API_KEY"),
            max_steps=20,
        )

    # Convert to MarketInvestmentResults for all markets
    market_decisions = _create_market_investment_decisions(
        event_decisions=event_decisions, market_info_dict=market_data
    )

    return EventInvestmentResult(
        event_id=event.id,
        event_title=event.title,
        event_description=event.description,
        market_decisions=market_decisions,
    )


def _process_single_model(
    model: ApiModel | str,
    events: list[Event],
    target_date: date,
    date_output_path: Path | None,
    timestamp_for_saving: str,
) -> ModelInvestmentResult:
    """Process investments for all events for a model."""
    event_results = []

    for event in events:
        logger.info(f"Processing event: {event.title}")
        event_result = _process_event_investment(
            model=model,
            event=event,
            target_date=target_date,
            date_output_path=date_output_path,
            timestamp_for_saving=timestamp_for_saving,
        )
        event_results.append(event_result)

    model_id = model.model_id if isinstance(model, ApiModel) else model
    model_result = ModelInvestmentResult(
        model_id=model_id, target_date=target_date, event_results=event_results
    )

    if date_output_path:
        save_model_result(
            model_result=model_result,
            date_output_path=date_output_path,
            timestamp_for_saving=timestamp_for_saving,
        )
    return model_result


def run_agent_investments(
    models: list[ApiModel | str],
    events: list[Event],
    target_date: date,
    date_output_path: Path | None,
    dataset_name: str,
    split: str,
    hf_token_for_dataset: str | None,
    timestamp_for_saving: str,
) -> list[ModelInvestmentResult]:
    """Launch agent investments for events on a specific date."""
    logger.info(f"Running agent investments for {len(models)} models on {target_date}")
    logger.info(f"Processing {len(events)} events")

    results = []
    for model in models:
        model_name = model.model_id if isinstance(model, ApiModel) else model
        logger.info(f"Processing model: {model_name}")
        model_result = _process_single_model(
            model=model,
            events=events,
            target_date=target_date,
            date_output_path=date_output_path,
            timestamp_for_saving=timestamp_for_saving,
        )
        results.append(model_result)

    if hf_token_for_dataset:
        _upload_results_to_hf_dataset(
            results_per_model=results,
            target_date=target_date,
            dataset_name=dataset_name,
            split=split,
            hf_token=hf_token_for_dataset,
        )

    return results
