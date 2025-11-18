import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the API key from the environment.
# The 'get' method returns None if the key isn't found.
API_KEY = os.getenv("API_KEY")

# Make sure the API key is set before starting the app
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set.")


api_key_header = APIKeyHeader(name="x-api-key")


def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=403,
        detail="Could not validate credentials. Invalid API Key."
    )