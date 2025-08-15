#!/usr/bin/env python3
"""
End-to-end tests for market selection functionality.

This test suite covers:
1. Event caching functionality (save/load cycle)
2. Backward compatibility testing for choose_events()
3. API integration and data integrity verification
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from predibench.market_selection import choose_events
from predibench.polymarket_data import save_events_to_file, load_events_from_file, CACHE_PATH
from predibench.logging import get_logger

logger = get_logger(__name__)


def test_choose_events_event_caching_e2e():
    """End-to-end test for event save/load functionality."""
    
    # Test parameters (same as used in invest.py)
    today_date = datetime.now(timezone.utc)
    time_until_ending = timedelta(days=21)
    max_n_events = 3
    
    logger.info("Starting e2e event caching test...")
    
    # Step 1: Fetch events from API
    logger.info("Step 1: Fetching events from API...")
    selected_events = choose_events(
        today_date=today_date,
        time_until_ending=time_until_ending,
        n_events=max_n_events
    )
    
    # checking events
    nb_markets_with_prices = 0
    nb_markets_without_prices = 0
    assert len(selected_events) == max_n_events, f"Expected {max_n_events} events, got {len(selected_events)}"
    for event in selected_events:
        assert len(event.markets) > 0, f"Event {event.title} has no markets"
        assert event.volume24hr is not None, f"Event {event.title} has no volume24hr"
        assert event.volume24hr > 0, f"Event {event.title} has no volume24hr"
        assert event.end_date.astimezone(timezone.utc) <= today_date + time_until_ending, f"Event {event.title} has end_date {event.end_date} which is after {today_date + time_until_ending}"
        
        for market in event.markets:
            assert len(market.outcomes) == 2, f"Market {market.question} has {len(market.outcomes)} outcomes, expected 2"
            if market.prices is not None and len(market.prices) >= 1:
                nb_markets_with_prices += 1
            else:
                nb_markets_without_prices += 1
    assert nb_markets_with_prices > nb_markets_without_prices * 3 # it will not work for some, 3 is a safe margin

    # Step 2: Save events to file
    logger.info("Step 2: Saving events to file...")
    test_filename = "test_events_e2e.json"
    save_events_to_file(selected_events, test_filename)
    
    # Verify file was created
    cache_file = CACHE_PATH / test_filename
    assert cache_file.exists(), f"Cache file was not created: {cache_file}"
    logger.info(f"✓ Events successfully saved to {cache_file}")
    
    # Step 3: Load events from file
    logger.info("Step 3: Loading events from file...")
    loaded_events = load_events_from_file(test_filename)
    
    logger.info(f"Loaded {len(loaded_events)} events from file")
    for i, event in enumerate(loaded_events):
        logger.info(f"  {i+1}. {event.title} (ID: {event.id}, Markets: {len(event.markets)})")
    
    # Step 4: Verify data integrity
    logger.info("Step 4: Verifying data integrity...")
    
    # Check basic counts
    assert len(selected_events) == len(loaded_events), \
        f"Event count mismatch: original={len(selected_events)}, loaded={len(loaded_events)}"
    
    # Check each event
    for i, (original, loaded) in enumerate(zip(selected_events, loaded_events)):
        logger.info(f"Verifying event {i+1}: {original.title}")
        
        # Check basic event properties
        assert original.id == loaded.id, f"Event ID mismatch for event {i}"
        assert original.title == loaded.title, f"Event title mismatch for event {i}"
        assert original.slug == loaded.slug, f"Event slug mismatch for event {i}"
        assert original.description == loaded.description, f"Event description mismatch for event {i}"
        
        # Check numeric fields
        assert original.volume == loaded.volume, f"Event volume mismatch for event {i}"
        assert original.volume24hr == loaded.volume24hr, f"Event volume24hr mismatch for event {i}"
        assert original.liquidity == loaded.liquidity, f"Event liquidity mismatch for event {i}"
        
        # Check markets count
        assert len(original.markets) == len(loaded.markets), \
            f"Markets count mismatch for event {i}: original={len(original.markets)}, loaded={len(loaded.markets)}"
        
        # Check first market details (if exists)
        if original.markets and loaded.markets:
            orig_market = original.markets[0]
            loaded_market = loaded.markets[0]
            
            assert orig_market.id == loaded_market.id, f"Market ID mismatch for event {i}"
            assert orig_market.question == loaded_market.question, f"Market question mismatch for event {i}"
            assert len(orig_market.outcomes) == len(loaded_market.outcomes), \
                f"Market outcomes count mismatch for event {i}"
    
    logger.info("✓ All data integrity checks passed!")
    
    # Step 5: Cleanup
    logger.info("Step 5: Cleaning up test files...")
    if cache_file.exists():
        cache_file.unlink()
        logger.info(f"✓ Cleaned up test file: {cache_file}")
    
    logger.info("🎉 End-to-end event caching test completed successfully!")
    

def test_choose_events_backward_compatibility():
    """Test choose_events function for backward compatibility with different modes."""
    
    logger.info("Starting choose_events backward compatibility test...")
    
    # Test parameters
    base_date = datetime(2025, 7, 15, tzinfo=timezone.utc)  # Fixed date for testing
    time_until_ending = timedelta(days=7)
    n_events = 3
    
    # Test 1: Normal mode (backward_mode=False)
    logger.info("Test 1: Testing normal mode (backward_mode=False)...")
    
    events_normal = choose_events(
        today_date=base_date,
        time_until_ending=time_until_ending,
        n_events=n_events,
        backward_mode=True
    )
    
    logger.info(f"Normal mode returned {len(events_normal)} events")
    assert len(events_normal) <= n_events, f"Expected at most {n_events} events, got {len(events_normal)}"
    
    for i, event in enumerate(events_normal):
        logger.info(f"  Normal event {i+1}: {event.title} (Volume: ${event.volume:,.0f})")
        
        # Verify event has markets
        assert len(event.markets) > 0, f"Event {i+1} has no markets"
        
        # In normal mode, events should be filtered by volume24hr
        if event.volume24hr is not None:
            assert event.volume24hr >= 1000, f"Event {i+1} volume24hr ({event.volume24hr}) below minimum threshold"
        
        # Check that markets have price data (should be filled in normal mode)
        for j, market in enumerate(event.markets):
            if market.prices is not None:
                logger.info(f"    Market {j+1}: {market.question} - Price data: {len(market.prices)} points")
            else:
                logger.warning(f"    Market {j+1}: {market.question} - No price data")
    
    # Test 2: Backward compatibility mode (backward_mode=True)
    logger.info("Test 2: Testing backward compatibility mode (backward_mode=True)...")
    
    events_backward = choose_events(
        today_date=base_date,
        time_until_ending=time_until_ending,
        n_events=n_events,
        backward_mode=True
    )
    
    logger.info(f"Backward mode returned {len(events_backward)} events")
    assert len(events_backward) <= n_events, f"Expected at most {n_events} events, got {len(events_backward)}"
    
    for i, event in enumerate(events_backward):
        logger.info(f"  Backward event {i+1}: {event.title} (Volume: ${event.volume:,.0f})")
        
        # Verify event has markets
        assert len(event.markets) > 0, f"Event {i+1} has no markets"
        
        # In backward mode, volume24hr filtering is not applied
        # Events may have lower volume24hr or None
        
        # Check that markets have historical price data (should be filled for specific date range)
        for j, market in enumerate(event.markets):
            if market.prices is not None:
                logger.info(f"    Market {j+1}: {market.question} - Historical price data: {len(market.prices)} points")
                # Verify price data covers the expected time range (7 days before base_date)
                assert len(market.prices) > 0, f"Market {j+1} has empty price data"
            else:
                logger.warning(f"    Market {j+1}: {market.question} - No historical price data")
    

def main():
    test_choose_events_event_caching_e2e()
    test_choose_events_backward_compatibility()



if __name__ == "__main__":
    main()