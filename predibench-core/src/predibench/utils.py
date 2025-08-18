from datetime import datetime
from predibench.logger_config import get_logger

logger = get_logger(__name__)


def convert_polymarket_time_to_datetime(time_str: str) -> datetime:
    """Convert a Polymarket time string to a datetime object."""
    return datetime.fromisoformat(time_str.replace("Z", "")).replace(tzinfo=None)


def get_timestamp_string() -> str:
    """Generate a timestamp string for filenames to avoid overwriting."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
