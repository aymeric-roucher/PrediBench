# Polymarket LLM Benchmark API

FastAPI backend for the Polymarket LLM Benchmark application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

- `GET /api/leaderboard` - Get LLM performance leaderboard
- `GET /api/events` - Get active Polymarket events
- `GET /api/stats` - Get overall statistics
- `GET /api/model/{model_id}` - Get detailed model information
- `GET /api/health` - Health check endpoint