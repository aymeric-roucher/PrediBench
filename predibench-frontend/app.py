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

        agents_performance[agent] = {
            "total_decisions": len(agent_data),
            "long_positions": len(agent_data[agent_data["choice"] == 1]),
            "short_positions": len(agent_data[agent_data["choice"] == -1]),
            "no_positions": len(agent_data[agent_data["choice"] == 0]),
            "cumulative_pnl": portfolio_cumulative_pnls[agent].iloc[-1],
            "annualized_sharpe_ratio": (daily_pnl.mean() / daily_pnl.std())
            * np.sqrt(252),
            "daily_cumulative_pnl": cumulative_pnl.tolist(),
            "dates": cumulative_pnl.index.tolist(),
            "figure": figures[agent],
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
                "Total Decisions": metrics["total_decisions"],
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


def refresh_data():
    """Refresh all data and return updated components"""
    df = load_agent_choices()
    performance_data = calculate_pnl_and_performance(df)

    leaderboard = create_leaderboard(performance_data)
    pnl_plot = create_pnl_plot(performance_data)
    agent_list = [
        agent.replace("smolagent_", "").replace("--", "/")
        for agent in performance_data.keys()
    ]
    portfolio_list = list(performance_data.keys())
    first_portfolio_plot = (
        performance_data[portfolio_list[0]]["figure"] if portfolio_list else None
    )

    return (
        leaderboard,
        pnl_plot,
        gr.update(choices=agent_list),
        gr.update(
            choices=portfolio_list, value=portfolio_list[0] if portfolio_list else None
        ),
        first_portfolio_plot,
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )


# Initialize data
df = load_agent_choices()
performance_data = calculate_pnl_and_performance(df)

# Create Gradio interface
with gr.Blocks(title="PrediBench Leaderboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏆 PrediBench Agent Leaderboard")
    gr.Markdown(
        "Track the performance of AI agents making predictions on Polymarket questions"
    )

    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Data", variant="primary")
        last_updated = gr.Textbox(
            value=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            label="Status",
            interactive=False,
            scale=3,
        )

    with gr.Tabs():
        with gr.TabItem("📊 Leaderboard"):
            gr.Markdown("### Agent Performance Ranking")
            leaderboard_table = gr.Dataframe(
                value=create_leaderboard(performance_data), interactive=False, wrap=True
            )

            pnl_plot = gr.Plot(value=create_pnl_plot(performance_data))

        with gr.TabItem("📊 Portfolio Details"):
            gr.Markdown("### Detailed Portfolio Analysis")

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

    # Refresh functionality
    refresh_btn.click(
        fn=refresh_data,
        outputs=[
            leaderboard_table,
            pnl_plot,
            portfolio_dropdown,
            portfolio_plot,
            last_updated,
        ],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
