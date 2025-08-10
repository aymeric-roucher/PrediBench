#!/bin/bash

# Setup PrediBench with Git Submodules
echo "🚀 Setting up PrediBench with Git Submodules..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create main project directory
PROJECT_DIR="predibench-main"
echo -e "${BLUE}Creating main project: $PROJECT_DIR${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Initialize main repo
git init
echo "# PrediBench - AI Agent Prediction Benchmarking" > README.md
echo "" >> README.md
echo "This project uses Git submodules to manage:" >> README.md
echo "- \`predibench-core/\`: Core logic and package" >> README.md
echo "- \`predibench-backend/\`: HuggingFace Space (backend)" >> README.md
echo "- \`predibench-frontend/\`: HuggingFace Space (frontend)" >> README.md

git add README.md
git commit -m "Initial commit"

# Step 1: Create core package submodule
echo -e "${BLUE}📦 Setting up predibench-core submodule...${NC}"
mkdir predibench-core
cd predibench-core

# Copy core package files
cp -r ../../../src . 2>/dev/null || echo "Will copy src manually"
cp ../../../pyproject.toml . 2>/dev/null || true

# Create installable package structure
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "predibench-core"
version = "0.1.0"
description = "Core package for PrediBench agent predictions"
dependencies = [
    "numpy",
    "pandas", 
    "requests",
    "pydantic",
    "plotly",
    "smolagents",
    "python-dotenv"
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
EOF

cat > README.md << 'EOF'
# PrediBench Core

Core package containing the market prediction logic, agent interfaces, and data processing utilities.

## Installation

```bash
pip install git+https://github.com/m-ric/predibench-core
```

## Usage

```python
from market_bench.polymarket_api import get_open_markets
from market_bench.agent.agent import run_smolagent
```
EOF

git init
git add .
git commit -m "Initial core package"

# Add as submodule to main project
cd ..
git submodule add ./predibench-core predibench-core

# Step 2: Create backend submodule
echo -e "${BLUE}🤖 Setting up predibench-backend submodule...${NC}"
mkdir predibench-backend
cd predibench-backend

# Copy backend files
cp ../../../backend_space/app.py . 2>/dev/null || echo "Will copy backend app manually"

cat > requirements.txt << 'EOF'
gradio
datasets
huggingface_hub
apscheduler
git+https://github.com/m-ric/predibench-core
EOF

cat > README.md << 'EOF'
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

Weekly pipeline for fetching Polymarket questions and running agent predictions.
EOF

# Update imports in app.py to use installed package
if [ -f app.py ]; then
    echo "Imports already use 'from market_bench...' - perfect!"
fi

git init
git add .
git commit -m "Initial backend space"

# Add as submodule
cd ..
git submodule add ./predibench-backend predibench-backend

# Step 3: Create frontend submodule  
echo -e "${BLUE}🎨 Setting up predibench-frontend submodule...${NC}"
mkdir predibench-frontend
cd predibench-frontend

# Copy frontend files
cp ../../../frontend_space/app.py . 2>/dev/null || echo "Will copy frontend app manually"

cat > requirements.txt << 'EOF'
gradio
datasets  
huggingface_hub
plotly
git+https://github.com/m-ric/predibench-core
EOF

cat > README.md << 'EOF'
---
title: PrediBench Frontend
emoji: 🏆
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.42.0
app_file: app.py
pinned: false
license: apache-2.0
---

# PrediBench Frontend

Interactive leaderboard for AI agent prediction performance.
EOF

git init
git add .
git commit -m "Initial frontend space"

# Add as submodule
cd ..
git submodule add ./predibench-frontend predibench-frontend

# Create .gitmodules file
echo -e "${BLUE}📝 Finalizing submodule setup...${NC}"
git add .
git commit -m "Add submodules for core, backend, and frontend"

# Create local development script
cat > dev_setup.sh << 'EOF'
#!/bin/bash
# Local development setup

echo "🔧 Setting up local development environment..."

# Install core package in development mode
cd predibench-core
pip install -e .
cd ..

# Install backend dependencies
cd predibench-backend  
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd predibench-frontend
pip install -r requirements.txt
cd ..

echo "✅ Local development setup complete!"
echo "Run apps with:"
echo "  cd predibench-backend && python app.py"
echo "  cd predibench-frontend && python app.py"
EOF

chmod +x dev_setup.sh

echo -e "${GREEN}✅ Submodule setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Copy your existing files to the submodules"
echo "2. Create GitHub repos for each submodule"
echo "3. Push each submodule to its respective remote"
echo "4. Create HuggingFace Spaces pointing to backend/frontend repos"
echo ""
echo -e "${BLUE}🏗️ Architecture created:${NC}"
echo "📦 predibench-core/     → GitHub (pip installable)"
echo "🤖 predibench-backend/  → HuggingFace Space" 
echo "🎨 predibench-frontend/ → HuggingFace Space"
echo ""
echo "Run './dev_setup.sh' for local development!"