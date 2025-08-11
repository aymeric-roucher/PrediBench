import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import gradio as gr
from datetime import datetime, date, timedelta
from datasets import Dataset
from huggingface_hub import HfApi

from predibench.pnl import compute_pnls

# Configuration
AGENT_CHOICES_REPO = "m-ric/predibench-agent-choices"

def load_agent_choices():
    """Load agent choices from HuggingFace dataset"""
    dataset = Dataset.from_parquet(f"hf://datasets/{AGENT_CHOICES_REPO}")
    return dataset.to_pandas()

def calculate_pnl_and_performance(df: pd.DataFrame):
    """Calculate real PnL and performance metrics for each agent using historical market data"""
    investment_dates = sorted(df['date'].unique())
    final_pnls, cumulative_pnls, figures = compute_pnls(investment_dates, df)
    
    # Convert to the format expected by frontend
    agents_performance = {}
    for agent in df['agent_name'].unique():
        agent_data = df[df['agent_name'] == agent].copy()
        cumulative_pnl = cumulative_pnls[agent]
        
        agents_performance[agent] = {
            'total_decisions': len(agent_data),
            'long_positions': len(agent_data[agent_data['choice'] == 1]),
            'short_positions': len(agent_data[agent_data['choice'] == -1]),
            'no_positions': len(agent_data[agent_data['choice'] == 0]),
            'cumulative_pnl': final_pnls[agent],
            'sharpe_ratio': 0.0,  # Would need more calculation for proper Sharpe
            'win_rate': 0.0,      # Would need daily PnL for win rate
            'daily_pnl': cumulative_pnl.tolist(),
            'dates': cumulative_pnl.index.tolist(),
            'figure': figures[agent]
        }
    
    return agents_performance

def create_leaderboard(performance_data):
    """Create leaderboard table"""
    leaderboard_data = []
    
    for agent, metrics in performance_data.items():
        leaderboard_data.append({
            'Agent': agent.replace('smolagent_', '').replace('--', '/'),
            'Total Decisions': metrics['total_decisions'],
            'Long Positions': metrics['long_positions'],
            'Short Positions': metrics['short_positions'],
            'No Position': metrics['no_positions'],
            'Cumulative PnL': f"{metrics['cumulative_pnl']:.3f}",
            'Sharpe Ratio': f"{metrics['sharpe_ratio']:.3f}",
            'Win Rate': f"{metrics['win_rate']:.1%}",
        })
    
    # Sort by cumulative PnL
    leaderboard_df = pd.DataFrame(leaderboard_data)
    leaderboard_df['PnL_numeric'] = leaderboard_df['Cumulative PnL'].astype(float)
    leaderboard_df = leaderboard_df.sort_values('PnL_numeric', ascending=False)
    leaderboard_df = leaderboard_df.drop('PnL_numeric', axis=1)
    
    return leaderboard_df

def create_pnl_plot(performance_data, selected_agent=None):
    """Create interactive PnL plot"""
    fig = go.Figure()
    
    agents_to_plot = [selected_agent] if selected_agent and selected_agent in performance_data else performance_data.keys()
    
    colors = px.colors.qualitative.Set1
    
    for i, agent in enumerate(agents_to_plot):
        if agent not in performance_data:
            continue
            
        metrics = performance_data[agent]
        daily_pnl = metrics['daily_pnl']
        dates = metrics['dates']
        
        # Calculate cumulative PnL over time
        cumulative_pnl = np.cumsum([0] + daily_pnl)
        plot_dates = [dates[0]] + dates if dates else [datetime.now()]
        
        fig.add_trace(go.Scatter(
            x=plot_dates,
            y=cumulative_pnl,
            name=agent.replace('smolagent_', '').replace('--', '/'),
            line=dict(color=colors[i % len(colors)], width=2),
            mode='lines+markers',
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Date: %{x}<br>' +
                         'Cumulative PnL: %{y:.3f}<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title="Agent Performance - Cumulative PnL Over Time",
        xaxis_title="Date",
        yaxis_title="Cumulative PnL",
        hovermode='x unified',
        template="plotly_white",
        height=500,
        showlegend=True
    )
    
    # Add horizontal line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig

def create_position_breakdown_plot(performance_data):
    """Create position breakdown plot"""
    agents = list(performance_data.keys())
    long_positions = [performance_data[agent]['long_positions'] for agent in agents]
    short_positions = [performance_data[agent]['short_positions'] for agent in agents]
    no_positions = [performance_data[agent]['no_positions'] for agent in agents]
    
    # Clean agent names for display
    clean_agents = [agent.replace('smolagent_', '').replace('--', '/') for agent in agents]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Long Positions',
        x=clean_agents,
        y=long_positions,
        marker_color='green',
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        name='Short Positions', 
        x=clean_agents,
        y=short_positions,
        marker_color='red',
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        name='No Position',
        x=clean_agents,
        y=no_positions,
        marker_color='gray',
        opacity=0.7
    ))
    
    fig.update_layout(
        title="Position Breakdown by Agent",
        xaxis_title="Agent",
        yaxis_title="Number of Decisions",
        barmode='stack',
        template="plotly_white",
        height=400
    )
    
    return fig

def get_agent_list(df):
    """Get list of agents for dropdown"""
    if df.empty:
        return ["No agents available"]
    agents = df['agent_name'].unique()
    clean_agents = [agent.replace('smolagent_', '').replace('--', '/') for agent in agents]
    return ["All Agents"] + clean_agents

def update_plot(selected_agent):
    """Update plot based on selected agent"""
    df = load_agent_choices()
    performance_data = calculate_pnl_and_performance(df)
    
    # Map clean name back to original name
    if selected_agent != "All Agents" and selected_agent != "No agents available":
        original_name = None
        for agent in performance_data.keys():
            clean_name = agent.replace('smolagent_', '').replace('--', '/')
            if clean_name == selected_agent:
                original_name = agent
                break
        selected_agent = original_name
    else:
        selected_agent = None
    
    return create_pnl_plot(performance_data, selected_agent)

def refresh_data():
    """Refresh all data and return updated components"""
    df = load_agent_choices()
    performance_data = calculate_pnl_and_performance(df)
    
    leaderboard = create_leaderboard(performance_data)
    pnl_plot = create_pnl_plot(performance_data)
    position_plot = create_position_breakdown_plot(performance_data)
    agent_list = get_agent_list(df)
    portfolio_list = list(performance_data.keys())
    first_portfolio_plot = performance_data[portfolio_list[0]]['figure'] if portfolio_list else None
    
    return (leaderboard, pnl_plot, position_plot, 
            gr.update(choices=agent_list), 
            gr.update(choices=portfolio_list, value=portfolio_list[0] if portfolio_list else None),
            first_portfolio_plot,
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Initialize data
df = load_agent_choices()
performance_data = calculate_pnl_and_performance(df)

# Create Gradio interface
with gr.Blocks(title="PrediBench Leaderboard", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏆 PrediBench Agent Leaderboard")
    gr.Markdown("Track the performance of AI agents making predictions on Polymarket questions")
    
    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Data", variant="primary")
        last_updated = gr.Textbox(
            value=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
            label="Status", 
            interactive=False,
            scale=3
        )
    
    with gr.Tabs():
        with gr.TabItem("📊 Leaderboard"):
            gr.Markdown("### Agent Performance Ranking")
            leaderboard_table = gr.Dataframe(
                value=create_leaderboard(performance_data),
                interactive=False,
                wrap=True
            )
            
            gr.Markdown("### Position Breakdown")
            position_breakdown = gr.Plot(
                value=create_position_breakdown_plot(performance_data)
            )
        
        with gr.TabItem("📈 Individual Performance"):
            gr.Markdown("### Select Agent to View Detailed Performance")
            
            with gr.Row():
                agent_dropdown = gr.Dropdown(
                    choices=get_agent_list(df),
                    value="All Agents",
                    label="Select Agent",
                    scale=3
                )
            
            pnl_plot = gr.Plot(
                value=create_pnl_plot(performance_data)
            )
            
            # Update plot when agent selection changes
            agent_dropdown.change(
                fn=update_plot,
                inputs=agent_dropdown,
                outputs=pnl_plot
            )
        
        with gr.TabItem("📊 Portfolio Details"):
            gr.Markdown("### Detailed Portfolio Analysis")
            
            with gr.Row():
                portfolio_dropdown = gr.Dropdown(
                    choices=[agent for agent in performance_data.keys()],
                    value=list(performance_data.keys())[0] if performance_data else None,
                    label="Select Agent Portfolio",
                    scale=3
                )
            
            portfolio_plot = gr.Plot(
                value=performance_data[list(performance_data.keys())[0]]['figure'] if performance_data else None
            )
            
            # Update portfolio plot when agent selection changes
            def update_portfolio_plot(selected_agent):
                if selected_agent and selected_agent in performance_data:
                    return performance_data[selected_agent]['figure']
                return None
                
            portfolio_dropdown.change(
                fn=update_portfolio_plot,
                inputs=portfolio_dropdown,
                outputs=portfolio_plot
            )
    
    # Refresh functionality
    refresh_btn.click(
        fn=refresh_data,
        outputs=[leaderboard_table, pnl_plot, position_breakdown, agent_dropdown, portfolio_dropdown, portfolio_plot, last_updated]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)