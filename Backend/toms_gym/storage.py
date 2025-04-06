import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

# Initialize Google Cloud Storage client
storage_client = storage.Client()

# Set the bucket name to the existing bucket in toms-gym project
bucket_name = 'jtr-lift-u-4ever-cool-bucket'
bucket = storage_client.bucket(bucket_name)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mov', 'mp4', 'avi', 'mkv'} 