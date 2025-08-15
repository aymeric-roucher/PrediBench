#!/usr/bin/env python3
"""
End-to-end test for event caching functionality.

This test demonstrates the full save/load cycle for events:
1. Fetch events from API using choose_events()
2. Save events to file using save_events_to_file()
3. Load events from file using load_events_from_file()
4. Verify data integrity between original and loaded events
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from predibench.market_selection import choose_events
from predibench.polymarket_data import save_events_to_file, load_events_from_file, CACHE_PATH
from predibench.logging import get_logger

logger = get_logger(__name__)


def test_event_caching_e2e():
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
    
    logger.info(f"Fetched {len(selected_events)} events from API")
    for i, event in enumerate(selected_events):
        logger.info(f"  {i+1}. {event.title} (ID: {event.id}, Markets: {len(event.markets)})")
    
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
        
        # Check dates (allowing for potential timezone/precision differences)
        if original.start_date and loaded.start_date:
            assert abs((original.start_date - loaded.start_date).total_seconds()) < 1, \
                f"Event start_date mismatch for event {i}"
        assert original.start_date is None or loaded.start_date is not None, \
            f"Event start_date None mismatch for event {i}"
            
        if original.end_date and loaded.end_date:
            assert abs((original.end_date - loaded.end_date).total_seconds()) < 1, \
                f"Event end_date mismatch for event {i}"
        assert original.end_date is None or loaded.end_date is not None, \
            f"Event end_date None mismatch for event {i}"
            
        if original.createdAt and loaded.createdAt:
            assert abs((original.createdAt - loaded.createdAt).total_seconds()) < 1, \
                f"Event createdAt mismatch for event {i}"
        
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
    

def main():
    """Run the e2e test as a standalone script."""
    try:
        test_event_caching_e2e()
        print("✅ E2E Test PASSED")
    except Exception as e:
        logger.error(f"❌ E2E Test FAILED: {e}")
        print(f"❌ E2E Test FAILED: {e}")
        raise


if __name__ == "__main__":
    main()