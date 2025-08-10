---
title: PrediBench Backend
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.42.0
app_file: app.py
pinned: false
license: apache-2.0
---

# PrediBench Backend

Automated system that fetches Polymarket questions weekly and runs AI agent predictions.

## Features

- 🔄 Weekly restart every Sunday at 8:00 AM UTC
- 📊 Fetches top 10 Polymarket questions at 8:30 AM UTC  
- 🤖 Runs predictions from multiple AI agents
- 📈 Uploads results to HuggingFace datasets
- 🖥️ Monitoring interface

## Environment Variables

Set these in your Space settings:
- `HF_TOKEN`: Your HuggingFace API token
- Add any model API keys (OpenAI, Anthropic, etc.)

## Datasets

Creates and updates:
- `m-ric/predibench-weekly-markets`
- `m-ric/predibench-agent-choices`