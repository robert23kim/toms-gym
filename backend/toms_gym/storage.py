import os
from google.cloud import storage
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBucket:
    def __init__(self, name):
        self.name = name
        self._blobs = {}
        
    def blob(self, name):
        if name not in self._blobs:
            self._blobs[name] = MockBlob(name, self)
        return self._blobs[name]

class MockBlob:
    def __init__(self, name, bucket):
        self.name = name
        self.bucket = bucket
        self._content = None
        
    def upload_from_file(self, file_obj, content_type=None):
        self._content = file_obj.read()
        logger.info(f"Mock upload: {self.name} ({len(self._content)} bytes)")
        
    def download_to_file(self, file_obj):
        if self._content is None:
            raise Exception(f"Blob {self.name} does not exist")
        file_obj.write(self._content)
        
    def delete(self):
        if self.name in self.bucket._blobs:
            del self.bucket._blobs[self.name]

class MockStorageClient:
    def __init__(self):
        self._buckets = {}
        
    def bucket(self, name):
        if name not in self._buckets:
            self._buckets[name] = MockBucket(name)
        return self._buckets[name]

# Initialize storage client based on environment
USE_MOCK_STORAGE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS') == 'none'
bucket_name = os.getenv('GCS_BUCKET_NAME', 'jtr-lift-u-4ever-cool-bucket')

if USE_MOCK_STORAGE:
    logger.info("Using mock storage client")
    storage_client = MockStorageClient()
else:
    logger.info("Using Google Cloud Storage client")
    storage_client = storage.Client()

bucket = storage_client.bucket(bucket_name)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mov', 'mp4', 'avi', 'mkv'} 