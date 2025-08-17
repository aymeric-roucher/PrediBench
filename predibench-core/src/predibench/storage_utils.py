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



def write_job_file_to_storage(domain_name: str, job_id: str, filename: str, content: str) -> bool:
    """
    Write content to a job-specific file in the storage structure: domain_name/job_id/filename
    """
    blob_name = f"{domain_name}/{job_id}/{filename}"
    return _write_to_bucket_or_data_dir(content, blob_name)


def write_job_file_from_path_to_storage(domain_name: str, job_id: str, filename: str, file_path: Path) -> bool:
    """
    Upload a file from local path to job-specific storage: domain_name/job_id/filename
    """
    blob_name = f"{domain_name}/{job_id}/{filename}"
    return _write_file_to_bucket_or_data_dir(file_path, blob_name)


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

def read_job_file_from_storage(domain_name: str, job_id: str, filename: str) -> str:
    """
    Read a job-specific file from storage: domain_name/job_id/filename
    """
    blob_name = f"{domain_name}/{job_id}/{filename}"
    return _read_file_from_bucket_or_data_dir(blob_name)

if __name__ == "__main__":
    print(has_bucket_access())