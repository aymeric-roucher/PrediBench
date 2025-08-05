import numpy as np
import pandas as pd
import plotly.express as px


class PnlCalculator:
    sharpe_constant_normalization = 252**0.5

    def __init__(
        self,
        positions: pd.DataFrame,
        returns: pd.DataFrame,
        to_vol_target: bool = False,
        vol_targeting_window: str = "30D",
    ):
        """
        positions: Daily positions: pd.DataFrame with columns as markets and index as dates
        returns: Daily returns: pd.DataFrame with columns as markets and index as dates
        to_vol_target: bool, if True, will target volatility
        vol_targeting_window: str, window for volatility targeting
        """
        self.positions = positions
        self._assert_index_is_date(self.positions)
        self.returns = returns
        self._assert_index_is_date(self.returns)
        self.to_vol_target = to_vol_target
        self.vol_targeting_window = vol_targeting_window
        self.pnl = self.calculate_pnl()

    def _assert_index_is_date(self, df: pd.DataFrame):
        assert all(
            isinstance(idx, pd.Timestamp)
            and idx.time() == pd.Timestamp("00:00:00").time()
            for idx in df.index
        ), "All index values must be dates without time component"

    def calculate_pnl(self):
        if self.to_vol_target:
            volatility = (
                self.returns.apply(
                    lambda x: x.dropna().rolling(self.vol_targeting_window).std()
                )
                .resample("1D")
                .last()
                .ffill()
            )
            self.new_positions = (
                (self.positions / volatility).resample("1D").last().ffill()
            )
            pnls_ = pd.concat(
                [
                    self.new_positions[col]
                    .reindex(self.returns[col].dropna().index)
                    .shift(1)
                    * self.returns[col]
                    for col in self.new_positions
                ],
                axis=1,
            )
            return pnls_
        else:
            pnls_ = pd.concat(
                [
                    self.positions[col]
                    .reindex(self.returns[col].dropna().index)
                    .shift(1)
                    * self.returns[col]
                    for col in self.positions
                ],
                axis=1,
            )
            return pnls_

    def plot_pnl(self, stock_details: bool = False):
        import plotly.graph_objects as go

        if not stock_details:
            cumulative_pnl = self.pnl.sum(axis=1).cumsum()
            fig = px.line(
                x=cumulative_pnl.index.date,
                y=cumulative_pnl.values,
                labels={"x": "Date", "y": "Cumulative PnL"},
            )
            fig.data[0].update(mode="markers+lines")
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative PnL",
            )
            return fig
        else:
            # Plot each stock's cumulative pnl as a separate line
            fig = go.Figure()

            colors = px.colors.qualitative.Plotly
            columns = list(self.pnl.columns)
            for i, col in enumerate(columns):
                col_color = colors[i % len(colors)]
                cumulative_pnl = self.pnl[col].cumsum()
                fig.add_trace(
                    go.Scatter(
                        x=cumulative_pnl.index.date,
                        y=cumulative_pnl.values,
                        mode="markers+lines",
                        name=col,
                        line=dict(color=col_color),
                    )
                )
                # Add markers for positions taken
                position_changes = self.positions[col][self.positions[col] != 0]
                pnl_at_position_changes = cumulative_pnl.loc[position_changes.index]
                fig.add_trace(
                    go.Scatter(
                        x=position_changes.index.date,
                        y=pnl_at_position_changes.values,
                        text=position_changes.values,
                        hovertemplate="Taking Position: %{text:.2f}<extra></extra>",
                        mode="markers",
                        marker=dict(
                            symbol=[
                                "triangle-up" if pos > 0 else "triangle-down"
                                for pos in position_changes.values
                            ],
                            size=10,
                            color=col_color,
                            line=dict(width=1, color="black"),
                        ),
                        showlegend=False,
                    )
                )
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative PnL",
                legend_title="Stock",
                width=1200,
                height=600,
                yaxis=dict(tickformat=".0%"),
            )
            return fig

    def vol_pnl_daily(self):
        return self.pnl.sum(axis=1).std()

    def vol_pnl_annualized(self):
        return self.pnl.sum(axis=1).std() * self.sharpe_constant_normalization

    def sharpe_daily(self):
        return self.pnl.sum(axis=1).mean() / self.pnl.sum(axis=1).std()

    def sharpe_annualized(self):
        return (
            self.pnl.sum(axis=1).mean()
            / self.pnl.sum(axis=1).std()
            * self.sharpe_constant_normalization
        )

    def compute_sortino_ratio(self, risk_free_rate: float = 0.0):
        """
        Sortino Ratio = (Mean Return - Risk-Free Rate) / Downside Deviation
        """
        daily_pnl = self.pnl.sum(axis=1)
        excess_returns = daily_pnl - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = np.std(downside_returns, ddof=1)
        if downside_deviation == 0:
            return np.inf
        return excess_returns.mean() / downside_deviation

    def max_drawdown(self):
        """
        Maximum Drawdown = (Peak - Trough) / Peak
        Assumes daily returns
        """
        cumulative_returns = self.pnl.sum(axis=1).cumsum()
        peak = cumulative_returns.cummax()
        drawdown = (peak - cumulative_returns) / peak
        return drawdown.max()

    def compute_calmar_ratio(self, risk_free_rate: float = 0.0):
        """
        Calmar Ratio = Annualized Return / Maximum Drawdown
        Assumes daily returns
        """
        max_drawdown = self.max_drawdown()
        annualized_return = self.pnl.sum(axis=1).mean() * 252
        if max_drawdown == 0:
            return np.inf
        return annualized_return / abs(max_drawdown)

    def turnover(self):
        """
        Calculate turnover in %.
        """
        turnover = (
            100
            * self.positions.diff().abs().sum(axis=1).sum()
            / self.positions.abs().sum(axis=1).sum()
        )
        return turnover
