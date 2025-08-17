from pathlib import Path


PREDIBENCH_PATH = Path(__file__).parent
PREDIBENCH_REPO_PATH = PREDIBENCH_PATH.parent.parent

DATA_PATH = PREDIBENCH_REPO_PATH / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

BASE_URL_POLYMARKET = "https://gamma-api.polymarket.com"
    
