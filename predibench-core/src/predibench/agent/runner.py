import os
from datetime import date, datetime
from pathlib import Path

import numpy as np
import datasets
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
                reasoning=f"Market is closed. Original reasoning: {market_decision.reasoning}"
            )
            result = MarketInvestmentResult(
                market_id=market_info["id"],
                market_question=market_info["question"],
                probability_assessment=market_decision.probability_assessment,
                market_odds=market_info["current_price"] or 0.5,
                confidence_in_assessment=market_decision.confidence_in_assessment,
                betting_decision=betting_decision,
                market_price=market_info["current_price"],
                is_closed=True,
            )
        else:
            from predibench.agent.dataclasses import BettingResult
            betting_decision = BettingResult(
                direction=market_decision.direction,
                amount=market_decision.amount,
                reasoning=market_decision.reasoning
            )
            result = MarketInvestmentResult(
                market_id=market_info["id"],
                market_question=market_info["question"],
                probability_assessment=market_decision.probability_assessment,
                market_odds=market_info["current_price"] or 0.5,
                confidence_in_assessment=market_decision.confidence_in_assessment,
                betting_decision=betting_decision,
                market_price=market_info["current_price"],
                is_closed=False,
            )
        results.append(result)
    
    return results


def _upload_results_to_hf_dataset(
    results_per_model: list[ModelInvestmentResult],
    target_date: date,
    hf_token: str,
    dataset_name: str = "charles-azam/predibench",
    split: str = "train",
    erase_existing: bool = False,
) -> None:
    """Upload investment results to the Hugging Face dataset."""
    # Try to load the existing dataset, handle empty dataset case
    try:
        ds = load_dataset(dataset_name)
    except datasets.data_files.EmptyDatasetError:
        logger.info(f"Dataset {dataset_name} is empty, will create with new data")
        ds = None

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
                    # ModelInvestmentResult fields
                    "model_id": model_result.model_id,
                    "agent_name": model_result.model_id,  # Keep for backward compatibility
                    "target_date": model_result.target_date,
                    "date": target_date,  # Keep for backward compatibility
                    
                    # EventInvestmentResult fields
                    "event_id": event_result.event_id,
                    "event_title": event_result.event_title,
                    "event_description": event_result.event_description,
                    
                    # MarketInvestmentResult fields
                    "market_id": market_decision.market_id,
                    "market_question": market_decision.market_question,
                    "question": market_decision.market_question,  # Keep for backward compatibility
                    "probability_assessment": market_decision.probability_assessment,
                    "market_odds": market_decision.market_odds,
                    "confidence_in_assessment": market_decision.confidence_in_assessment,
                    "market_price": market_decision.market_price,
                    "is_closed": market_decision.is_closed,
                    
                    # BettingResult fields
                    "betting_direction": market_decision.betting_decision.direction,
                    "choice_raw": market_decision.betting_decision.direction,  # Keep for backward compatibility
                    "betting_amount": market_decision.betting_decision.amount,
                    "betting_reasoning": market_decision.betting_decision.reasoning,
                    "rationale": market_decision.betting_decision.reasoning or "",  # Keep for backward compatibility
                    
                    # Legacy/computed fields
                    "choice": choice,
                    "messages_count": 0,  # This would need to be tracked during agent execution
                    "has_reasoning": market_decision.betting_decision.reasoning is not None,
                    "timestamp_uploaded": current_timestamp,
                }
                new_rows.append(row)

    if new_rows:
        # Create a new dataset with the new rows
        new_dataset = Dataset.from_list(new_rows)
        # Concatenate with existing dataset using datasets.concatenate_datasets

        # Handle dataset combination based on erase_existing flag
        if erase_existing or ds is None:
            # Either erasing existing data or dataset is empty, just use new data
            combined_dataset = new_dataset
            if erase_existing:
                logger.info(f"Erasing existing dataset and creating fresh dataset with {len(new_dataset)} rows")
            else:
                logger.info(f"Dataset is empty, creating with {len(new_dataset)} rows")
        else:
            try:
                existing_data = ds[split]
                combined_dataset = concatenate_datasets([existing_data, new_dataset])
                logger.info(f"Appending {len(new_dataset)} rows to existing {len(existing_data)} rows")
            except KeyError:
                # Split doesn't exist, just use new data
                combined_dataset = new_dataset
                logger.info(f"Split '{split}' doesn't exist, creating with {len(new_dataset)} rows")

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
    price_history_limit: int = 20,
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
        # Check if market is closed and get price data
        if market.prices is not None and target_date in market.prices.index:
            if backward_mode:
                price_data = market.prices.loc[:target_date].dropna()
            else:
                price_data = market.prices.dropna()
            # Limit price history
            if len(price_data) > price_history_limit:
                price_data = price_data.tail(price_history_limit)
            recent_prices = price_data.to_string(index=True, header=False)
            current_price = float(market.prices.loc[target_date])
            is_closed = False
        else:
            # Market is closed - get all available historical prices
            if market.prices is not None and len(market.prices) > 0:
                price_data = market.prices.dropna()
                # Limit price history
                if len(price_data) > price_history_limit:
                    price_data = price_data.tail(price_history_limit)
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

You have access to {len(market_data)} markets related to this event. You must allocate your capital across these markets.

CAPITAL ALLOCATION RULES:
- You have exactly 1.0 units of capital to allocate
- For each market, specify the fraction of capital to bet (0.0 to 1.0)
- The sum of ALL amounts + unallocated_capital MUST equal 1.0
- You can choose not to bet on markets with poor edges by setting direction="nothing" and amount=0.0
- Any unallocated capital should be specified in the unallocated_capital parameter

For EACH market, provide:
1. market_id: The market ID
2. reasoning: Explanation for your decision
3. probability_assessment: Your assessment of the true probability (0.0 to 1.0)  
4. confidence_in_assessment: How confident you are in your assessment (0.0 to 1.0)
5. direction: "buy_yes" (bet outcome happens), "buy_no" (bet outcome doesn't happen), or "nothing" (don't bet)
6. amount: Fraction of total capital to bet on this market (0.0 to 1.0)

AVAILABLE MARKETS:
{"".join(market_summaries)}

Use the final_answer tool to provide your decisions. Remember:
- The prices shown are for the specific outcome mentioned
- "buy_yes" means you think that outcome is more likely than the current price suggests
- "buy_no" means you think it's less likely than the current price suggests
- Your total capital allocation (sum of amounts + unallocated_capital) must equal 1.0

Example: If you bet 0.3 on market A, 0.2 on market B, and nothing on market C, your unallocated_capital should be 0.5.
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
        # Create random decisions for all markets with capital allocation constraint
        from predibench.agent.smolagents_utils import MarketDecision
        
        market_decisions = []
        remaining_capital = 1.0
        
        market_ids = list(market_data.keys())
        for i, market_info in enumerate(market_data.values()):
            direction = np.random.choice(["buy_yes", "buy_no", "nothing"], p=[0.3, 0.3, 0.4])
            
            # For the last market, use all remaining capital if betting, otherwise leave some unallocated
            is_last_market = (i == len(market_ids) - 1)
            if direction != "nothing":
                if is_last_market:
                    # Use up to remaining capital for last market
                    max_amount = min(remaining_capital, 0.5)
                    amount = np.random.uniform(0.0, max_amount) if max_amount > 0 else 0.0
                else:
                    # Leave some capital for future markets
                    max_amount = min(remaining_capital * 0.6, 0.4)  # Use at most 60% of remaining, cap at 40%
                    amount = np.random.uniform(0.0, max_amount) if max_amount > 0 else 0.0
                remaining_capital -= amount
            else:
                amount = 0.0
            
            market_decision = MarketDecision(
                market_id=market_info["id"],
                reasoning=f"Random decision for testing market {market_info['id']}",
                probability_assessment=np.random.uniform(0.1, 0.9),
                confidence_in_assessment=np.random.uniform(0.3, 0.8),
                direction=direction,
                amount=amount
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
