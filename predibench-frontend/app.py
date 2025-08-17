from datetime import datetime

import gradio as gr
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datasets import load_dataset
from predibench.pnl import compute_pnls

# Configuration
AGENT_CHOICES_REPO = "m-ric/predibench-agent-choices"


def load_agent_choices():
    """Load agent choices from HuggingFace dataset"""
    dataset = load_dataset(AGENT_CHOICES_REPO, split="train")
    return dataset.to_pandas()


def add_reasoning_markers(fig, agent_data):
    """Add square markers with reasoning to the price chart for each position taken"""
    import plotly.express as px
    
    # Get the colors used in the figure for consistency
    colors = px.colors.qualitative.Plotly
    
    # Filter positions where a choice was made (not 0)
    positions_taken = agent_data[agent_data["choice"] != 0].copy()
    
    if len(positions_taken) == 0:
        return fig
    
    # Group by market_id to get consistent colors
    for i, (market_id, market_positions) in enumerate(positions_taken.groupby("market_id")):
        col_color = colors[i % len(colors)]
        
        # Add square markers at y=1 for each position
        fig.add_trace(
            go.Scatter(
                x=market_positions["date"],
                y=[1] * len(market_positions),  # Arbitrary y value of 1
                mode="markers",
                marker=dict(
                    symbol="square",
                    size=12,
                    color=col_color,
                    line=dict(width=2, color="black")
                ),
                hovertemplate="<b>Position Taken</b><br>" +
                             "Date: %{x}<br>" +
                             "Market: " + str(market_id)[:40] + "<br>" +
                             "Choice: %{customdata[0]}<br>" +
                             "Reasoning: %{customdata[1]}<br>" +
                             "<extra></extra>",
                customdata=list(zip(market_positions["choice"], market_positions["reasoning"])),
                showlegend=False,
                name=f"Positions - {str(market_id)[:20]}",
            ),
            row=1,  # Add to the price chart (top subplot)
            col=1
        )
    
    return fig


def calculate_pnl_and_performance(positions_df: pd.DataFrame):
    """Calculate real PnL and performance metrics for each agent using historical market data"""
    investment_dates = sorted(positions_df["date"].unique())
    portfolio_daily_pnls, portfolio_cumulative_pnls, figures = compute_pnls(
        investment_dates, positions_df, write_plots=False
    )

    # Convert to the format expected by frontend
    agents_performance = {}
    for agent in positions_df["agent_name"].unique():
        agent_data = positions_df[positions_df["agent_name"] == agent].copy()
        daily_pnl = portfolio_daily_pnls[agent]
        cumulative_pnl = portfolio_cumulative_pnls[agent]

        # Enhance the figure with reasoning markers
        enhanced_figure = add_reasoning_markers(figures[agent], agent_data)

        agents_performance[agent] = {
            "long_positions": len(agent_data[agent_data["choice"] == 1]),
            "short_positions": len(agent_data[agent_data["choice"] == -1]),
            "no_positions": len(agent_data[agent_data["choice"] == 0]),
            "cumulative_pnl": portfolio_cumulative_pnls[agent].iloc[-1],
            "annualized_sharpe_ratio": (daily_pnl.mean() / daily_pnl.std())
            * np.sqrt(252),
            "daily_cumulative_pnl": cumulative_pnl.tolist(),
            "dates": cumulative_pnl.index.tolist(),
            "figure": enhanced_figure,
        }

    return agents_performance


def create_leaderboard(performance_data):
    """Create leaderboard table"""
    leaderboard_data = []

    for agent, metrics in performance_data.items():
        leaderboard_data.append(
            {
                "Agent": agent.replace("smolagent_", "").replace("--", "/"),
                "Cumulative PnL": f"{metrics['cumulative_pnl']:.3f}",
                "Annualized Sharpe Ratio": f"{metrics['annualized_sharpe_ratio']:.3f}",
                "Long Positions": metrics["long_positions"],
                "Short Positions": metrics["short_positions"],
                "No Position": metrics["no_positions"],
            }
        )

    # Sort by cumulative PnL
    leaderboard_df = pd.DataFrame(leaderboard_data)
    leaderboard_df["PnL_numeric"] = leaderboard_df["Cumulative PnL"].astype(float)
    leaderboard_df = leaderboard_df.sort_values("PnL_numeric", ascending=False)
    leaderboard_df = leaderboard_df.drop("PnL_numeric", axis=1)

    return leaderboard_df


def create_pnl_plot(performance_data):
    """Create interactive PnL plot"""
    fig = go.Figure()

    colors = px.colors.qualitative.Set1

    for i, agent in enumerate(performance_data.keys()):
        if agent not in performance_data:
            continue

        metrics = performance_data[agent]
        daily_cumulative_pnl = metrics["daily_cumulative_pnl"]
        dates = metrics["dates"]

        # Calculate cumulative PnL over time
        plot_dates = [dates[0]] + dates if dates else [datetime.now()]

        fig.add_trace(
            go.Scatter(
                x=plot_dates,
                y=daily_cumulative_pnl,
                name=agent.replace("smolagent_", "").replace("--", "/"),
                line=dict(color=colors[i % len(colors)], width=2),
                mode="lines+markers",
                hovertemplate="<b>%{fullData.name}</b><br>"
                + "Date: %{x}<br>"
                + "Cumulative PnL: %{y:.3f}<br>"
                + "<extra></extra>",
            )
        )

    fig.update_layout(
        title="Agent Performance - Cumulative PnL Over Time",
        xaxis_title="Date",
        yaxis_title="Cumulative PnL",
        hovermode="x unified",
        template="plotly_white",
        height=500,
        showlegend=True,
    )

    # Add horizontal line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    return fig


# Initialize data
df = load_agent_choices()
performance_data = calculate_pnl_and_performance(df)

# Create Gradio interface
with gr.Blocks(title="PrediBench Leaderboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏆 PrediBench - Can LLMs predict the future?")
    gr.Markdown(
        f"Track the performance of AI agents making predictions on Polymarket questions. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    with gr.Tabs():
        with gr.TabItem("🏆 Leaderboard"):
            leaderboard_table = gr.Dataframe(
                value=create_leaderboard(performance_data), interactive=False, wrap=True
            )

            pnl_plot = gr.Plot(value=create_pnl_plot(performance_data))

        with gr.TabItem("🔍 Portfolio Details"):
            with gr.Row():
                portfolio_dropdown = gr.Dropdown(
                    choices=[agent for agent in performance_data.keys()],
                    value=list(performance_data.keys())[0]
                    if performance_data
                    else None,
                    label="Select Agent Portfolio",
                    scale=3,
                )

            portfolio_plot = gr.Plot(
                value=performance_data[list(performance_data.keys())[0]]["figure"]
                if performance_data
                else None
            )

            # Update portfolio plot when agent selection changes
            def update_portfolio_plot(selected_agent):
                if selected_agent and selected_agent in performance_data:
                    return performance_data[selected_agent]["figure"]
                return None

            portfolio_dropdown.change(
                fn=update_portfolio_plot,
                inputs=portfolio_dropdown,
                outputs=portfolio_plot,
            )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
