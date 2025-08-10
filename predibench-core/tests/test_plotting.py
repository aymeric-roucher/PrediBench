#!/usr/bin/env python3

from datetime import date

import pandas as pd
from predibench.pnl import PnlCalculator


def test_plotting():
    # Create sample data
    date_range = [
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
        date(2024, 1, 5),
    ]

    positions = pd.DataFrame(
        {"Question A": [1, 1, 0, 1, 1], "Question B": [0, 1, 1, 0, 1]}, index=date_range
    )

    returns = pd.DataFrame(
        {
            "Question A": [0.1, -0.05, 0.02, 0.03, -0.01],
            "Question B": [0.05, 0.02, -0.03, 0.01, 0.04],
        },
        index=date_range,
    )

    prices = pd.DataFrame(
        {
            "Question A": [0.5, 0.55, 0.52, 0.54, 0.53],
            "Question B": [0.3, 0.31, 0.30, 0.30, 0.31],
        },
        index=date_range,
    )

    # Create PnlCalculator with prices
    engine = PnlCalculator(positions, returns, prices)

    # Generate plot
    fig = engine.plot_pnl(stock_details=True)

    # Save to verify
    fig.write_html("test_output.html")
    print("✓ Plot generated successfully with subplots!")
    print("✓ HTML file saved as test_output.html")

    # Check that the figure has subplots
    assert hasattr(fig, "_grid_ref"), "Figure should have grid reference for subplots"
    print("✓ Subplots structure verified")


if __name__ == "__main__":
    test_plotting()
