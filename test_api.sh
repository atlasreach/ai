#!/bin/bash
# API Test Suite for All Parameters

API_URL="http://localhost:8001"

echo "=== Testing API Parameters ==="
echo ""

# Test 1: Basic generation with custom steps and CFG
echo "Test 1: Custom steps (20) and CFG (6.0)"
curl -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Milan, woman in elegant red dress, studio portrait, professional lighting",
    "negative_prompt": "blurry, low quality",
    "character": "milan",
    "width": 768,
    "height": 768,
    "num_inference_steps": 20,
    "guidance_scale": 6.0,
    "lora_strength": 0.9,
    "seed": 42
  }' \
  --max-time 180 \
  -o /tmp/test1.json

echo ""
echo "✅ Test 1 complete. Check /tmp/test1.json"
echo ""
sleep 2

# Test 2: Batch generation (2 images)
echo "Test 2: Batch generation (2 images)"
curl -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Milan, woman, casual outfit, outdoor park",
    "negative_prompt": "blurry, low quality",
    "character": "milan",
    "width": 512,
    "height": 512,
    "num_inference_steps": 25,
    "guidance_scale": 4.0,
    "lora_strength": 0.8,
    "num_images": 2,
    "seed": 100
  }' \
  --max-time 240 \
  -o /tmp/test2.json

echo ""
echo "✅ Test 2 complete. Check /tmp/test2.json"
echo ""
sleep 2

# Test 3: Upscaling enabled (1.5x)
echo "Test 3: Upscaling enabled (1.5x)"
curl -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Milan, woman, professional business suit, office background",
    "negative_prompt": "blurry, low quality",
    "character": "milan",
    "width": 512,
    "height": 512,
    "num_inference_steps": 30,
    "guidance_scale": 4.5,
    "lora_strength": 0.85,
    "enable_upscaling": true,
    "upscale_factor": 1.5,
    "seed": 200
  }' \
  --max-time 300 \
  -o /tmp/test3.json

echo ""
echo "✅ Test 3 complete. Check /tmp/test3.json"
echo ""
sleep 2

# Test 4: Custom model sampling shift
echo "Test 4: Custom model sampling shift (3.0)"
curl -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Milan, woman, summer dress on beach, sunset lighting",
    "negative_prompt": "blurry, low quality",
    "character": "milan",
    "width": 768,
    "height": 1024,
    "num_inference_steps": 30,
    "guidance_scale": 5.0,
    "lora_strength": 0.8,
    "model_sampling_shift": 3.0,
    "seed": 300
  }' \
  --max-time 180 \
  -o /tmp/test4.json

echo ""
echo "✅ Test 4 complete. Check /tmp/test4.json"
echo ""
sleep 2

# Test 5: All parameters combined
echo "Test 5: All parameters combined (upscale + batch + custom shift)"
curl -X POST "$API_URL/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Milan, woman, fashionable outfit, city street, golden hour",
    "negative_prompt": "blurry, low quality, distorted",
    "character": "milan",
    "width": 640,
    "height": 640,
    "num_inference_steps": 35,
    "guidance_scale": 5.5,
    "lora_strength": 0.9,
    "num_images": 2,
    "enable_upscaling": true,
    "upscale_factor": 2.0,
    "model_sampling_shift": 2.5,
    "seed": 400
  }' \
  --max-time 360 \
  -o /tmp/test5.json

echo ""
echo "✅ Test 5 complete. Check /tmp/test5.json"
echo ""

echo "=== All tests complete ==="
echo ""
echo "Results saved in /tmp/test*.json"
echo "Check outputs/milan/ for generated images"
