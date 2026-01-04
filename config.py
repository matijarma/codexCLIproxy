# config.py
import os
from dotenv import load_dotenv
import sys

# Load environment variables from a .env file if it exists.
# This allows for easy configuration without modifying the script directly.
load_dotenv()

# --- REQUIRED CONFIGURATION ---
# The full URL of your target OpenAI-compatible API endpoint.
# This is the destination for the proxied requests.
# Example for Azure OpenAI: 
# AZURE_ENDPOINT="https://<your-resource-name>.openai.azure.com/openai/deployments/<your-deployment-name>/chat/completions?api-version=<your-api-version>"
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# The API key for authenticating with the target endpoint.
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

# --- OPTIONAL CONFIGURATION ---
# The model name to be forced in the request body.
# If the client sends a different model, this will override it.
FORCED_MODEL = os.getenv("FORCED_MODEL", None)

# The port on which this proxy server will listen.
PORT = int(os.getenv("PORT", 8888))

# The number of times to retry a request to the target endpoint if it fails.
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 10))

# The base time in seconds for the progressive backoff between retries.
# The wait time will be attempt_number * RETRY_WAIT_SECONDS.
RETRY_WAIT_SECONDS = int(os.getenv("RETRY_WAIT_SECONDS", 15))


# --- VALIDATION ---
# Ensure that the required environment variables are set.
# If not, print an informative error message and exit.
if not AZURE_ENDPOINT or not AZURE_API_KEY:
    print("FATAL ERROR: Missing required environment variables.", file=sys.stderr)
    print("Please create a .env file and set AZURE_ENDPOINT and AZURE_API_KEY.", file=sys.stderr)
    print("You can use the .env.example file as a template.", file=sys.stderr)
    sys.exit(1)

