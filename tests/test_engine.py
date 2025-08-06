import pandas as pd

from market_bench.pnl import PnlCalculator


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

    engine = PnlCalculator(positions, returns)

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

    engine = PnlCalculator(positions, returns)

    pnl_result = engine.calculate_pnl()

    assert positions.shape == (5, 1)
    assert returns.shape == (5, 1)
    assert not pnl_result.empty
    
    # Expected PnL: 0.333333 + (-0.25) + 0.0 = 0.083333
    expected_final_pnl = 0.083333
    actual_final_pnl = pnl_result.sum(axis=1).cumsum().iloc[-1]
    assert abs(actual_final_pnl - expected_final_pnl) < 1e-5


if __name__ == "__main__":
    test_returns()
    test_lewis_hamilton_use_case()
