from predibench.polymarket_api import (
    MarketsRequestParameters,
    _get_events,
    convert_polymarket_time_to_datetime,
)


def test_get_open_markets():
    """Test basic market retrieval."""
    request_parameters = MarketsRequestParameters(limit=500)
    markets = request_parameters.get_open_markets()
    for market in markets:
        assert len(market.outcomes) >= 1
    assert len(markets) == 500


def test__get_market_events():
    """Test basic market event retrieval."""
    events = _get_events()
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


def test_get_open_markets_field_values():
    """Test that field values are reasonable."""
    request_parameters = MarketsRequestParameters(limit=5)
    markets = request_parameters.get_open_markets()

    for market in markets:
        assert len(market.id) > 0

        assert len(market.question) > 0

        assert market.volumeNum >= 0
        assert market.liquidityNum >= 0

        assert market.active is True


def test_get_open_markets_limit():
    """Test that limit parameter works correctly."""
    request_small = MarketsRequestParameters(limit=5)
    request_large = MarketsRequestParameters(limit=20)
    markets_small = request_small.get_open_markets()
    markets_large = request_large.get_open_markets()

    assert len(markets_small) == 5
    assert len(markets_large) == 20
    assert len(markets_large) > len(markets_small)


def test__get_events():
    """Test basic market event retrieval."""
    events = _get_events()
    assert len(events) == 500


def test_get_market_events_offset():
    """Test that offset parameter works correctly."""
    events_first = _get_events(limit=5, offset=0)
    events_second = _get_events(limit=5, offset=5)

    assert len(events_first) == 5
    assert len(events_second) == 5

    first_ids = {event.id for event in events_first}
    second_ids = {event.id for event in events_second}
    assert first_ids.isdisjoint(second_ids)


if __name__ == "__main__":
    test__get_events()
    test_get_open_markets_limit()
    test_get_market_events_offset()
