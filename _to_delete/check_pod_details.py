#!/usr/bin/env python3
"""
Check pod SSH configuration
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
RUNPOD_API_BASE = "https://api.runpod.io/graphql"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RUNPOD_API_KEY}"
}

# Query for detailed pod info including ports
query = """
query Pod($podId: String!) {
    pod(input: {podId: $podId}) {
        id
        name
        desiredStatus
        runtime {
            uptimeInSeconds
            ports {
                ip
                isIpPublic
                privatePort
                publicPort
                type
            }
        }
    }
}
"""

result = requests.post(
    RUNPOD_API_BASE,
    json={"query": query, "variables": {"podId": "my11nkt6jsanmb"}},
    headers=headers
).json()

pod = result.get("data", {}).get("pod", {})

print(f"\n🔍 Pod Details for my11nkt6jsanmb:\n")
print(f"Name: {pod.get('name')}")
print(f"Status: {pod.get('desiredStatus')}")

runtime = pod.get('runtime', {})
ports = runtime.get('ports', [])

print(f"\n📡 Exposed Ports:")
if not ports:
    print("  ⚠️  No ports exposed!")
else:
    for port in ports:
        print(f"  Private: {port.get('privatePort')} → Public: {port.get('publicPort')}")
        print(f"    IP: {port.get('ip')}")
        print(f"    Type: {port.get('type')}")
        print(f"    Public: {port.get('isIpPublic')}")
        print()

# SSH is typically port 22
ssh_port = next((p for p in ports if p.get('privatePort') == 22), None)
if ssh_port:
    print(f"✅ SSH Port Found: {ssh_port.get('publicPort')}")
    print(f"   Connect with: ssh -p {ssh_port.get('publicPort')} root@{ssh_port.get('ip')}")
else:
    print("❌ SSH Port (22) not exposed!")
    print("\n💡 You need to expose SSH port in Runpod pod settings")
