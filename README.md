# MaxStudio AI Workflow

Production-grade CLI tool for AI model creation through face swapping and image enhancement using MaxStudio API.

## Phase 1: CLI Workflow (Current)

Multi-model support with face swap, enhancement, and S3 integration.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables

Create a `.env` file with:

```bash
MAXSTUDIO_API_KEY=your_api_key_here
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-2
AWS_S3_BUCKET=your_bucket_name
```

## Usage

### Start the CLI

```bash
python3 master.py
```

### Main Menu

1. **Create New Model** - Set up a new model with source/target images
2. **Work with Existing Model** - Process face swaps and enhancements
3. **View All Models** - See all models and their stats
4. **Exit**

### Creating a Model

1. Choose option 1 from main menu
2. Enter model name (e.g., "andie", "blondie")
3. Copy source face images to `models/{model}/source/`
4. Choose NSFW, SFW, or both target types
5. Copy target body images to `models/{model}/targets/nsfw/` or `/sfw/`
6. Optionally create S3 bucket
7. Model created!

### Processing a Model

1. Choose option 2 from main menu
2. Select your model
3. Choose NSFW or SFW processing
4. Workflow runs automatically:
   - Uploads images to S3
   - Performs face detection
   - Creates face swap jobs
   - Enhances results (2x upscaling)
   - Saves locally + uploads to S3

### File Organization

```
models/
└── {model_name}/
    ├── config.json          # Model configuration
    ├── progress.json        # Resume capability
    ├── source/              # Source face images
    │   ├── image1.jpg
    │   └── image2.jpg
    ├── targets/
    │   ├── nsfw/            # NSFW target bodies
    │   │   ├── 001.jpg
    │   │   └── 002.jpg
    │   └── sfw/             # SFW target bodies
    │       ├── 001.jpg
    │       └── 002.jpg
    └── results/
        └── nsfw/            # or sfw/
            └── source_1/
                ├── swapped/
                │   └── {model}-s1-t1-nsfw-swapped.jpg
                └── enhanced/
                    └── {model}-s1-t1-nsfw-enhanced.jpg
```

### Smart File Naming

Format: `{model}-s{source#}-t{target#}-{type}-{stage}.jpg`

Examples:
- `andie-s1-t3-nsfw-swapped.jpg` - Source 1, Target 3, NSFW, Swapped
- `blondie-s2-t1-sfw-enhanced.jpg` - Source 2, Target 1, SFW, Enhanced

## Features

### ✅ Multi-Model Support
- Create and manage multiple models (andie, blondie, etc.)
- Each model has independent source images and targets
- Separate NSFW/SFW processing

### ✅ Face Detection Validation
- OpenCV face detection before upload
- Validates all source and target images
- Prevents processing images without faces

### ✅ Progress Tracking
- Resume capability after interruptions
- Tracks completion per source/target combination
- View progress stats per model

### ✅ Smart Processing
- Nested loops: each source × each target
- Automatic retry logic
- Polls MaxStudio API for job completion
- Error handling with detailed logging

### ✅ S3 Integration
- Auto-upload to AWS S3
- Presigned URLs for MaxStudio API
- Organized folder structure
- 7-day URL expiry

### ✅ Image Enhancement
- 2x upscaling by default
- Automatic enhancement after face swap
- Base64 encoding/decoding

## API Integration

### MaxStudio API Endpoints

- `POST /detect-face-image` - Face detection
- `POST /swap-image` - Face swap job creation
- `GET /swap-image/{jobId}` - Job status polling
- `POST /image-enhancer` - Enhancement with upscaling
- `GET /image-enhancer/{jobId}` - Enhancement status

### S3 Operations

- Bucket creation with timestamp
- Regional endpoints (s3.{region}.amazonaws.com)
- Presigned URLs (7-day expiry)
- Organized key structure

## Workflow Steps

1. **Upload** - All images to S3 with presigned URLs
2. **Detect** - Face detection on each target image
3. **Swap** - Face swap API for each source × target
4. **Download** - Fetch swapped results from CDN
5. **Enhance** - 2x upscaling via enhancement API
6. **Save** - Local storage + S3 upload

## Coming Soon (Phase 2)

- Caption generation (BLIP/CLIP)
- LoRA training for Stable Diffusion
- Automated training pipeline
- Quality assessment tools

## Project Structure

```
ai/
├── master.py              # Main CLI interface
├── scripts/
│   └── lib/               # Reusable library modules
│       ├── s3_manager.py
│       ├── maxstudio_api.py
│       ├── face_detector.py
│       ├── file_utils.py
│       └── progress.py
├── models/                # All model data
├── .env                   # Environment config
├── requirements.txt       # Python dependencies
├── CLAUDE.md             # Project roadmap
└── README.md             # This file
```

## Troubleshooting

### Face Detection Fails
- Ensure images have clear, visible faces
- Check image quality and resolution
- Try images with frontal face views

### API Errors (500/400)
- Verify MAXSTUDIO_API_KEY in .env
- Check presigned URL expiry (7 days)
- Ensure regional S3 URLs are used

### S3 Upload Fails
- Verify AWS credentials in .env
- Check bucket permissions
- Ensure region matches bucket

### Job Timeout
- MaxStudio jobs typically complete in 5-20 seconds
- Check MaxStudio API status
- Retry failed tasks from progress menu

## Documentation

- **CLAUDE.md** - Full project roadmap with all 4 phases
- **WORKFLOW_REPORT.md** - Detailed test results from initial andie workflow

## Credits

Built with Claude Code for MaxStudio API integration.