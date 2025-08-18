import pandas as pd
from predibench.pnl import PnlCalculator


def test_returns():
    date_range = pd.date_range(start="2024-01-01", periods=6, freq="D")
    returns = pd.DataFrame(
        data=[100, 1, -1, 0, 0, 0],
        index=date_range,
    )
    # The first high return will not be invested (should be invested by the position previous to the first day), so it will be lost.
    positions = pd.DataFrame(
        data=[1, 1, 0, 0, 1, 1],
        index=date_range,
    )

    # Create dummy prices data for testing
    prices = pd.DataFrame(
        data=[1.0, 1.01, 1.0, 1.0, 1.0, 1.0],
        index=date_range,
    )

    engine = PnlCalculator(positions, prices)

    engine.calculate_pnl()
    pnl_sum = engine.pnl.sum(axis=1).cumsum()
    assert pnl_sum.iloc[-1] == 0


def test_lewis_hamilton_use_case():
    date_range = pd.date_range(start="2025-07-26", periods=5, freq="D")
    positions = pd.DataFrame(
        data=[1.0, 1.0, 1.0, 1.0, 1.0],
        index=date_range,
        columns=["Will Lewis Hamilton be the 2025 Drivers Champion?"],
    )

    returns = pd.DataFrame(
        index=date_range, columns=["Will Lewis Hamilton be the 2025 Drivers Champion?"]
    )
    returns.iloc[0, 0] = float("nan")
    returns.iloc[1, 0] = float("nan")
    returns.iloc[2, 0] = 0.333333
    returns.iloc[3, 0] = -0.250000
    returns.iloc[4, 0] = 0.000000

    # Create dummy prices data for testing
    prices = pd.DataFrame(
        index=date_range, columns=["Will Lewis Hamilton be the 2025 Drivers Champion?"]
    )
    prices.iloc[0, 0] = 0.5
    prices.iloc[1, 0] = 0.5
    prices.iloc[2, 0] = 0.667
    prices.iloc[3, 0] = 0.5
    prices.iloc[4, 0] = 0.5

    engine = PnlCalculator(positions, prices)

    pnl_result = engine.calculate_pnl()

    assert positions.shape == (5, 1)
    assert returns.shape == (5, 1)
    assert not pnl_result.empty

    # Expected PnL: 0.333333 + (-0.25) + 0.0 = 0.083333
    expected_final_pnl = 0.083333
    actual_final_pnl = pnl_result.sum(axis=1).cumsum().iloc[-1]
    assert abs(actual_final_pnl - expected_final_pnl) < 1e-5


def test_complex_positions_and_price_changes():
    """Test with successive positions (2, -1, 0) and changing daily prices"""
    date_range = pd.date_range(start="2024-01-01", periods=7, freq="D")

    # Positions: 2, 2, -1, -1, 0, 0, 0
    positions = pd.DataFrame(
        data=[2, 2, -1, -1, 0, 0, 0], index=date_range, columns=["TestAsset"]
    )

    # Daily changing prices: starting at 1.0, then varying
    prices = pd.DataFrame(
        data=[1.0, 1.05, 1.10, 0.95, 1.00, 1.02, 0.98],
        index=date_range,
        columns=["TestAsset"],
    )

    # Calculate returns from price percentage changes
    price_changes = prices.pct_change()
    returns = price_changes.copy()

    engine = PnlCalculator(positions, prices)
    pnl_result = engine.calculate_pnl()

    # Manual calculation for expected PnL:
    # Day 1: position=2, return=NaN (first day) -> PnL = 0
    # Day 2: position=2, return=0.05 (5% increase) -> PnL = 2 * 0.05 = 0.10
    # Day 3: position=2, return=0.047619 (1.10/1.05 - 1) -> PnL = 2 * 0.047619 = 0.095238
    # Day 4: position=-1, return=-0.136364 (0.95/1.10 - 1) -> PnL = -1 * -0.136364 = 0.136364
    # Day 5: position=-1, return=0.052632 (1.00/0.95 - 1) -> PnL = -1 * 0.052632 = -0.052632
    # Day 6: position=0, return=0.02 (1.02/1.00 - 1) -> PnL = 0 * 0.02 = 0
    # Day 7: position=0, return=-0.039216 (0.98/1.02 - 1) -> PnL = 0 * -0.039216 = 0

    expected_daily_pnl = [0.0, 0.10, 0.095238, 0.136364, -0.052632, 0.0, 0.0]
    expected_cumulative_pnl = sum(expected_daily_pnl[1:])  # Skip first day (NaN return)

    actual_cumulative_pnl = pnl_result.sum(axis=1).cumsum().iloc[-1]

    # Allow for small floating point differences
    assert abs(actual_cumulative_pnl - expected_cumulative_pnl) < 1e-4

    # Verify shapes
    assert positions.shape == (7, 1)
    assert returns.shape == (7, 1)
    assert not pnl_result.empty


if __name__ == "__main__":
    test_returns()
    test_lewis_hamilton_use_case()
    test_complex_positions_and_price_changes()
