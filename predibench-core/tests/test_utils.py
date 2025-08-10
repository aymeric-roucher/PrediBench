from market_bench.polymarket_api import convert_polymarket_time_to_datetime


def test_timestamp_extraction():
    """Test the timestamp extraction functionality from polymarket_api.py"""
    print("Testing timestamp extraction...")

    test_timestamps = [
        "2024-01-15T10:30:00Z",
        "2024-02-20T15:45:30.123Z",
        "2024-03-25T00:00:00Z",
    ]

    for ts_str in test_timestamps:
        dt = convert_polymarket_time_to_datetime(ts_str)
        print(f"  {ts_str} -> {dt}")

    print("Timestamp extraction test completed successfully!\n")
