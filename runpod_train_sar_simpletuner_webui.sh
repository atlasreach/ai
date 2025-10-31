#!/bin/bash
# SAR LoRA Training using SimpleTuner WebUI
# Alternative approach with user-friendly interface

set -e

echo "=========================================="
echo "  SAR LoRA Training (SimpleTuner WebUI)"
echo "  Flux.1-dev | 7 images"
echo "=========================================="

# SET YOUR AWS CREDENTIALS:
export AWS_REGION='us-east-2'
export BUCKET_NAME='destinty-workflow-1761724503'

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✗ Set AWS credentials first!"
    exit 1
fi

#############################################
# STEP 1: Install SimpleTuner
#############################################

cd /workspace

if [ ! -d "SimpleTuner" ]; then
    echo ""
    echo "Step 1: Installing SimpleTuner..."

    git clone --branch=release https://github.com/bghira/SimpleTuner.git
    cd SimpleTuner
    python -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    pip install -U poetry pip
    poetry install --no-root

    echo "✓ SimpleTuner installed"
else
    echo "✓ SimpleTuner already installed"
    cd /workspace/SimpleTuner
    source .venv/bin/activate
fi

#############################################
# STEP 2: Download dataset
#############################################

echo ""
echo "Step 2: Downloading dataset..."

if ! command -v aws &> /dev/null; then
    pip install -q awscli
fi

mkdir -p /workspace/sar_dataset

aws s3 sync "s3://$BUCKET_NAME/results/nsfw/source_1/enhanced/" /workspace/sar_dataset/ \
    --exclude "*" \
    --include "sar-s1-*-enhanced.jpg" \
    --include "sar-s1-*-enhanced.txt" \
    --region us-east-2

IMAGE_COUNT=$(ls -1 /workspace/sar_dataset/*.jpg 2>/dev/null | wc -l)

echo "✓ Downloaded $IMAGE_COUNT images"

#############################################
# STEP 3: Launch WebUI
#############################################

echo ""
echo "=========================================="
echo "  Starting SimpleTuner WebUI"
echo "=========================================="
echo ""
echo "The WebUI will start on port 8001"
echo ""
echo "Access it via:"
echo "  1. Go to RunPod dashboard"
echo "  2. Click 'Connect' → 'HTTP Service'"
echo "  3. Navigate to port 8001"
echo ""
echo "OR use SSH tunnel:"
echo "  ssh -L 8001:localhost:8001 root@your-runpod-ip"
echo ""
echo "Then open: http://localhost:8001"
echo ""
echo "Configuration:"
echo "  • Model: black-forest-labs/FLUX.1-dev"
echo "  • Dataset: /workspace/sar_dataset"
echo "  • Trigger: sar"
echo "  • Steps: 1000"
echo "  • Rank: 16"
echo ""

cd /workspace/SimpleTuner
python toolkit/ui/webui.py
