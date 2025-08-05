from market_bench.polymarket_api import (
    _get_market_events,
    _get_open_markets,
    convert_polymarket_time_to_datetime,
    get_market_events,
    get_open_markets,
)


def test__get_open_markets():
    """Test basic market retrieval."""
    markets = _get_open_markets()
    for market in markets:
        assert len(market["events"]) == 1
    assert len(markets) == 500


def test__get_market_events():
    """Test basic market event retrieval."""
    events = _get_market_events()
    for event in events:
        # ticker is sometimes different from slug
        assert event["ticker"] in event["slug"]

        # those dates are typically the same, but sometimes different
        assert (
            convert_polymarket_time_to_datetime(event["creationDate"]).date()
            >= convert_polymarket_time_to_datetime(event["createdAt"]).date()
        )

        # some markets might be resolved, but not all
        for market in event["markets"]:
            if "liquidityNum" not in market or float(market["liquidityNum"]) == 0:
                pass  # no real rules
                # assert market["closed"] == True

    assert len(events) == 500


def test_get_open_markets():
    """Test basic market retrieval."""
    markets = get_open_markets()
    assert len(markets) == 500


def test_get_open_markets_field_values():
    """Test that field values are reasonable."""
    markets = get_open_markets(limit=5)

    for market in markets:
        assert len(market.id) > 0

        assert len(market.question) > 0

        assert market.volumeNum >= 0
        assert market.liquidityNum >= 0

        assert market.active is True


def test_get_open_markets_limit():
    """Test that limit parameter works correctly."""
    markets_small = get_open_markets(limit=5)
    markets_large = get_open_markets(limit=20)

    assert len(markets_small) == 5
    assert len(markets_large) == 20
    assert len(markets_large) > len(markets_small)


def test_get_market_events():
    """Test basic market event retrieval."""
    events = get_market_events()
    assert len(events) == 500


def test_get_market_events_offset():
    """Test that offset parameter works correctly."""
    events_first = get_market_events(limit=5, offset=0)
    events_second = get_market_events(limit=5, offset=5)

    assert len(events_first) == 5
    assert len(events_second) == 5

    first_ids = {event.id for event in events_first}
    second_ids = {event.id for event in events_second}
    assert first_ids.isdisjoint(second_ids)


if __name__ == "__main__":
    test_get_market_events()
