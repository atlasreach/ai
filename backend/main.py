"""
AI Character Generation Platform - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import routers
from backend.routers import generate, characters


# Create FastAPI app
app = FastAPI(
    title="AI Character Generation API",
    description="Generate AI images using custom character LoRA models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generate.router, prefix="/api")
app.include_router(characters.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {
        "name": "AI Character Generation API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "characters": "/api/characters",
            "generate": "/api/generate"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check environment variables
    env_status = {
        "grok_api": bool(os.getenv("GROK_API_KEY")),
        "runpod_url": bool(os.getenv("RUNPOD_API_URL")),
        "aws_configured": all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("AWS_S3_BUCKET")
        ]),
        "huggingface_token": bool(os.getenv("HUGGINGFACE_TOKEN"))
    }

    all_configured = all(env_status.values())

    return {
        "status": "healthy" if all_configured else "degraded",
        "services": env_status,
        "message": "All services configured" if all_configured else "Some services not configured"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║  AI Character Generation API                         ║
    ║  FastAPI Backend Server                              ║
    ╠══════════════════════════════════════════════════════╣
    ║  Server:  http://localhost:{port}                   ║
    ║  Docs:    http://localhost:{port}/docs              ║
    ║  Health:  http://localhost:{port}/health            ║
    ╚══════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
