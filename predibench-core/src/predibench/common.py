from pathlib import Path


BASE_URL_POLYMARKET = "https://gamma-api.polymarket.com"
OUTPUT_PATH = Path("output")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH.mkdir(parents=True)