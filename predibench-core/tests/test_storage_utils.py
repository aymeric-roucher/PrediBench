from predibench.storage_utils import write_to_storage, read_from_storage

from pathlib import Path
from predibench.common import DATA_PATH


def test_storage_utils():
    file_path = DATA_PATH / "test.txt"
    write_to_storage(file_path, "test")
    assert read_from_storage(file_path) == "test"
