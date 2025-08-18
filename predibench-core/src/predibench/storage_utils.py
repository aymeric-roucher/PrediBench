"""
All of the data is stored in a bucket shared by all of the instances of the webportal crawlers.

For local development, the data is stored in the data directory.

This module contains utility functions for interacting with Google Cloud Storage.
"""

from google.cloud import storage
from google.api_core.exceptions import ClientError
import os
import uuid
from functools import cache
from pathlib import Path
from predibench.common import DATA_PATH
from predibench.agent import ModelInvestmentResult
from datasets import load_dataset, Dataset
from datetime import date, datetime
from predibench.logger_config import get_logger


logger = get_logger(__name__)

BUCKET_ENV_VAR = 'BUCKET_PREDIBENCH'

STORAGE_CLIENT = storage.Client()

@cache
def get_bucket() -> storage.Bucket | None:
    if BUCKET_ENV_VAR not in os.environ:
        print(f"To enable bucket access please set the {BUCKET_ENV_VAR} environment variable, defaulting to data directory.")
        return None
    
    bucket_name = os.getenv(BUCKET_ENV_VAR)
    return STORAGE_CLIENT.bucket(bucket_name)

@cache
def has_bucket_access(write_access_only: bool = True) -> bool:
    """
    Check if the bucket is set and working.
    
    If not set, the data is stored in the data directory.
    
    If set but not working, raising an error.
    """
    
    bucket = get_bucket()
    if bucket is None:
        return False
    
    try:
        random_string = str(uuid.uuid4())
        blob = bucket.blob(f'ping/ping_{random_string}.txt')
        blob.upload_from_string('ping')
        print(f"File uploaded to {blob.name}")
        if not write_access_only:
            file_content = blob.download_as_bytes().decode('utf-8')
            print(f"File content: {file_content}")
            assert file_content == 'ping'
            blob.delete()
        return True
    except ClientError as e:
        print(f"Error accessing bucket {bucket.name}: {e}")
        raise e
    except AssertionError as e:
        print(f"Error while uploading file: {e}, file content is {file_content}, not 'ping'")
        raise e


def _write_file_to_bucket_or_data_dir(file_path: Path, blob_name: str) -> bool:
    """
    Upload a local file to bucket if available, and also save locally for debugging.
    """
    # Always save locally for debugging
    local_dest = DATA_PATH / blob_name
    local_dest.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']:
        # For images, copy the binary file
        local_dest.write_bytes(file_path.read_bytes())
    else:
        # For text files
        local_dest.write_text(file_path.read_text())
    
    # Also upload to bucket if available
    if has_bucket_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(file_path))
        print(f"✅ Uploaded {blob_name} to bucket and saved locally")
    else:
        print(f"✅ Saved {blob_name} locally only (no bucket access)")
    
    return True


def _write_to_bucket_or_data_dir(content: str, blob_name: str) -> bool:
    """
    Write content to a file in bucket if available, and also save locally for debugging.
    """
    # Always save locally for debugging
    local_path = DATA_PATH / blob_name
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content)
    
    # Also upload to bucket if available
    if has_bucket_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content)
        print(f"✅ Uploaded {blob_name} to bucket and saved locally")
    else:
        print(f"✅ Saved {blob_name} locally only (no bucket access)")
    
    return True



def write_to_storage(file_path: Path, content: str) -> bool:
    """
    Write content to a file in storage at the given path relative to DATA_PATH.
    
    Args:
        file_path: Path object that must be relative to DATA_PATH
        content: Content to write to the file
    
    Raises:
        ValueError: If the path is not relative to DATA_PATH
    """
    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")
    
    relative_path = file_path.relative_to(DATA_PATH)
    return _write_to_bucket_or_data_dir(content, str(relative_path))


def _read_file_from_bucket_or_data_dir(blob_name: str) -> str:
    """
    Read a file from local data directory first, then from bucket if not found.
    """
    # Try local first
    local_path = DATA_PATH / blob_name
    if local_path.exists():
        return local_path.read_text()
    
    # If not found locally, try bucket
    if has_bucket_access():
        bucket = get_bucket()
        blob = bucket.blob(blob_name)
        return blob.download_as_text()
    else:
        raise FileNotFoundError(f"File not found locally or in bucket: {blob_name}")

def read_from_storage(file_path: Path) -> str:
    """
    Read a file from storage at the given path relative to DATA_PATH.
    
    Args:
        file_path: Path object that must be relative to DATA_PATH
    
    Returns:
        Content of the file as string
    
    Raises:
        ValueError: If the path is not relative to DATA_PATH
        FileNotFoundError: If the file is not found in storage
    """
    # Ensure the path is relative to DATA_PATH
    if not file_path.is_relative_to(DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to DATA_PATH {DATA_PATH}")
    
    relative_path = file_path.relative_to(DATA_PATH)
    return _read_file_from_bucket_or_data_dir(str(relative_path))


def upload_results_to_hf_dataset(results_per_model: list[ModelInvestmentResult], base_date: date) -> None:
    """Upload investment results to the Hugging Face dataset."""
    # Load the existing dataset
    ds = load_dataset("m-ric/predibench-agent-choices")
    
    # Prepare new data rows
    new_rows = []
    current_timestamp = datetime.now()
    
    for model_result in results_per_model:
        for event_result in model_result.event_results:
            # Map decision to choice value
            choice_mapping = {"BUY": 1, "SELL": 0, "NOTHING": -1}
            choice = choice_mapping.get(event_result.market_decision.decision, -1)
            
            row = {
                "agent_name": model_result.model_id,
                "date": base_date,
                "question": event_result.market_decision.market_question,
                "choice": choice,
                "choice_raw": event_result.market_decision.decision.lower(),
                "market_id": event_result.market_decision.market_id,
                "messages_count": 0,  # This would need to be tracked during agent execution
                "has_reasoning": event_result.market_decision.rationale is not None,
                "timestamp_uploaded": current_timestamp,
                "rationale": event_result.market_decision.rationale or ""
            }
            new_rows.append(row)
    
    if new_rows:
        # Create a new dataset with the new rows
        new_dataset = Dataset.from_list(new_rows)
        # Concatenate with existing dataset using datasets.concatenate_datasets
        from datasets import concatenate_datasets
        combined_dataset = concatenate_datasets([ds["train"], new_dataset])
        
        # Push back to hub as a pull request (safer approach)
        combined_dataset.push_to_hub(
            "m-ric/predibench-agent-choices", 
            split="train",
            token=os.getenv("HF_TOKEN_PREDIBENCH")
        )
        
        logger.info(f"Successfully uploaded {len(new_rows)} new rows to HF dataset")
    else:
        logger.warning("No data to upload to HF dataset")
            


if __name__ == "__main__":
    print(has_bucket_access())