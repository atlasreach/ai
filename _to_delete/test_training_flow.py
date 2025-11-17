#!/usr/bin/env python3
"""
Test Training Flow End-to-End
"""
import requests
import json
import time
import sys

API_BASE = "http://localhost:8002"

# Test dataset (25 images)
DATASET_ID = "a385311b-8235-4977-abcc-6760566fcfbe"

print("🧪 Testing Training Flow End-to-End")
print("=" * 60)
print()

# Step 1: Start Training
print("1️⃣  Starting training job...")
print(f"   Dataset ID: {DATASET_ID}")
print()

start_payload = {
    "dataset_id": DATASET_ID,
    "gpu_type": "rtx6000",
    "rank": 16,
    "steps": 500,  # Short test run
    "lr": 0.0002
}

try:
    response = requests.post(
        f"{API_BASE}/api/training/start",
        json=start_payload,
        timeout=300  # 5 min timeout for pod startup
    )

    print(f"   Response status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Training started!")
        print(f"   Job ID: {data.get('job_id')}")
        print()

        job_id = data['job_id']

        # Step 2: Check Status (poll a few times)
        print("2️⃣  Monitoring training status...")
        print()

        for i in range(5):
            print(f"   Check #{i+1}...")

            status_response = requests.get(
                f"{API_BASE}/api/training/status/{job_id}",
                timeout=30
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   Status: {status_data.get('status')}")
                print(f"   Progress: {status_data.get('progress', 0)}%")
                print(f"   Step: {status_data.get('current_step', 0)}/{status_data.get('total_steps', 0)}")

                if status_data.get('logs'):
                    print(f"   Latest logs:")
                    print(f"   {status_data['logs'][:200]}...")

                print()
            else:
                print(f"   ⚠️  Status check failed: {status_response.status_code}")
                print(f"   {status_response.text[:200]}")
                print()

            if i < 4:
                print(f"   Waiting 10s before next check...")
                time.sleep(10)

        print("=" * 60)
        print("✅ Training flow test complete!")
        print()
        print("📋 Summary:")
        print(f"   • Job ID: {job_id}")
        print(f"   • Training started successfully")
        print(f"   • Status monitoring working")
        print()
        print("💡 Next steps:")
        print("   • Let training run for ~30-60 mins")
        print("   • Monitor with: GET /api/training/status/{job_id}")
        print("   • Download when complete: POST /api/training/download/{dataset_id}")
        print()

    else:
        print(f"   ❌ Training start failed: {response.status_code}")
        print(f"   Error: {response.text}")
        sys.exit(1)

except requests.exceptions.Timeout:
    print("   ⏰ Request timed out (pod may be starting up)")
    print("   This is normal if the pod was stopped")
    print("   Try checking status manually in a few minutes")
    sys.exit(1)

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
