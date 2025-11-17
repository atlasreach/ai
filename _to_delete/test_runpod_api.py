#!/usr/bin/env python3
"""
Test Runpod API to list available pods
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
RUNPOD_API_BASE = "https://api.runpod.io/graphql"

print("🧪 Testing Runpod API")
print("=" * 50)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RUNPOD_API_KEY}"
}

# Query to list all pods
query = """
{
    myself {
        pods {
            id
            name
            desiredStatus
            imageName
            machine {
                gpuDisplayName
            }
        }
    }
}
"""

try:
    response = requests.post(RUNPOD_API_BASE, json={"query": query}, headers=headers)
    response.raise_for_status()

    result = response.json()

    if "errors" in result:
        print(f"❌ GraphQL Errors:")
        for error in result["errors"]:
            print(f"   {error.get('message')}")
    else:
        pods = result.get("data", {}).get("myself", {}).get("pods", [])

        print(f"\n📦 Found {len(pods)} pods:\n")

        for pod in pods:
            print(f"  ID: {pod['id']}")
            print(f"  Name: {pod.get('name', 'N/A')}")
            print(f"  Status: {pod.get('desiredStatus', 'N/A')}")
            print(f"  GPU: {pod.get('machine', {}).get('gpuDisplayName', 'N/A')}")
            print(f"  Image: {pod.get('imageName', 'N/A')}")
            print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
