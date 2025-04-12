"""Custom JSON encoder for handling special types."""
import json
import uuid
import datetime

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle UUIDs and datetime objects."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj) 