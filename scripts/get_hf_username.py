#!/usr/bin/env python3
"""
Get Hugging Face username from API token
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from huggingface_hub import HfApi

    token = os.getenv('HUGGINGFACE_TOKEN')
    if not token:
        print("ERROR: HUGGINGFACE_TOKEN not found in environment", file=sys.stderr)
        sys.exit(1)

    api = HfApi(token=token)
    user_info = api.whoami()

    # Print just the username for easy parsing
    print(user_info['name'])

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
