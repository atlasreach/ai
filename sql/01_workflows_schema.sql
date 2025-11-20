-- Create workflows and generation jobs tables

-- Workflows table - stores workflow templates
CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    comfyui_workflow JSONB NOT NULL,
    editable_params JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Generation jobs table - tracks ComfyUI job queue
CREATE TABLE IF NOT EXISTS generation_jobs (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id),
    workflow_id INTEGER REFERENCES workflows(id),
    reference_image_id INTEGER REFERENCES reference_images(id),
    parameters JSONB,
    prompt_used TEXT,
    negative_prompt_used TEXT,
    runpod_job_id VARCHAR(200),
    status VARCHAR(50) DEFAULT 'queued',
    result_image_url TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_model ON generation_jobs(model_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON generation_jobs(created_at DESC);

-- Insert the img2img workflow
INSERT INTO workflows (name, slug, description, comfyui_workflow, editable_params)
VALUES (
    'Image-to-Image with LoRA',
    'img2img-lora',
    'Transfer a reference image style to the model using LoRA',
    '{}'::jsonb,
    '{
        "denoise": {"type": "slider", "min": 0.5, "max": 1.0, "step": 0.05, "default": 0.75, "label": "Denoise Strength"},
        "cfg": {"type": "slider", "min": 1.0, "max": 15.0, "step": 0.1, "default": 3.8, "label": "CFG Scale"},
        "steps": {"type": "number", "min": 10, "max": 50, "default": 28, "label": "Sampling Steps"},
        "seed": {"type": "number", "min": -1, "max": 999999999999999, "default": -1, "label": "Seed (-1 for random)"},
        "lora_strength": {"type": "slider", "min": 0.3, "max": 1.0, "step": 0.05, "default": 0.65, "label": "LoRA Strength"},
        "positive_prompt_suffix": {"type": "text", "default": "bikini, professional photo, ultra detailed skin, sharp focus, 8k, photorealistic masterpiece", "label": "Additional Positive Prompt"}
    }'::jsonb
)
ON CONFLICT (slug) DO UPDATE SET
    comfyui_workflow = EXCLUDED.comfyui_workflow,
    editable_params = EXCLUDED.editable_params,
    updated_at = NOW();
