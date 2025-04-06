import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

# Initialize Google Cloud Storage client
storage_client = storage.Client.from_service_account_json(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
)
bucket_name = os.getenv('GCS_BUCKET_NAME')
bucket = storage_client.bucket(bucket_name)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mov', 'mp4', 'avi', 'mkv'} 