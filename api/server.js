import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import { createClient } from '@supabase/supabase-js'
import axios from 'axios'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import multer from 'multer'
import FormData from 'form-data'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

dotenv.config()

const app = express()
app.use(cors())
app.use(express.json())

// Setup multer for file uploads
const upload = multer({ storage: multer.memoryStorage() })

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

const RUNPOD_API_KEY = process.env.RUNPOD_API_KEY
const COMFYUI_API_URL = process.env.COMFYUI_API_URL

// Load workflow template
async function loadWorkflowTemplate(slug) {
  const templatePath = path.join(__dirname, '../workflows', `${slug}.json`)
  const content = await fs.readFile(templatePath, 'utf-8')
  return JSON.parse(content)
}

// Replace template variables
function fillWorkflowTemplate(template, variables) {
  let workflowStr = JSON.stringify(template)

  for (const [key, value] of Object.entries(variables)) {
    // Replace standalone variables: "{{key}}" -> value
    const standaloneRegex = new RegExp(`"{{${key}}}"`, 'g')
    workflowStr = workflowStr.replace(standaloneRegex, JSON.stringify(value))

    // Replace variables inside strings: "text {{key}} more" -> "text value more"
    const inlineRegex = new RegExp(`{{${key}}}`, 'g')
    workflowStr = workflowStr.replace(inlineRegex, value)
  }

  return JSON.parse(workflowStr)
}

// Generate random seed
function randomSeed() {
  return Math.floor(Math.random() * 999999999999999)
}

// POST /api/upload-image - Upload image to ComfyUI
app.post('/api/upload-image', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' })
    }

    const formData = new FormData()
    formData.append('image', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype
    })

    const uploadResponse = await axios.post(
      `${COMFYUI_API_URL}/upload/image`,
      formData,
      {
        headers: {
          ...formData.getHeaders(),
          'Authorization': `Bearer ${RUNPOD_API_KEY}`
        },
        maxBodyLength: Infinity,
        maxContentLength: Infinity
      }
    )

    res.json({
      success: true,
      filename: uploadResponse.data.name || req.file.originalname
    })
  } catch (error) {
    console.error('Upload Error:', error.response?.data || error.message)
    res.status(500).json({
      error: 'Failed to upload image',
      details: error.message
    })
  }
})

// POST /api/generate - Queue a new generation job
app.post('/api/generate', async (req, res) => {
  try {
    const { modelId, workflowSlug, uploadedImageFilename, parameters } = req.body

    if (!uploadedImageFilename) {
      return res.status(400).json({ error: 'uploadedImageFilename is required' })
    }

    // Fetch model
    const { data: model } = await supabase
      .from('models')
      .select('*')
      .eq('id', modelId)
      .single()

    if (!model) {
      return res.status(404).json({ error: 'Model not found' })
    }

    // Load workflow template
    const template = await loadWorkflowTemplate(workflowSlug)

    // Build prompts
    const positivePrompt = `${model.trigger_word}, ${model.hair_style}, ${model.skin_tone} skin, ${parameters.positive_prompt_suffix || ''}`
    const negativePrompt = `${model.negative_prompt}, ${parameters.negative_prompt_suffix || 'blurry, deformed, bad anatomy'}`

    // Prepare template variables
    const seed = parameters.seed === -1 ? randomSeed() : parameters.seed
    const variables = {
      reference_image: uploadedImageFilename,
      lora_file: model.lora_file,
      lora_strength: parameters.lora_strength || 0.65,
      positive_prompt: positivePrompt.trim(),
      negative_prompt: negativePrompt.trim(),
      seed,
      steps: parameters.steps || 28,
      cfg: parameters.cfg || 3.8,
      denoise: parameters.denoise || 0.75,
      model_name: model.slug,
      reference_filename: uploadedImageFilename.split('.')[0]
    }

    // Fill workflow template
    const filledWorkflow = fillWorkflowTemplate(template, variables)

    // Create job record
    const { data: job, error: jobError } = await supabase
      .from('generation_jobs')
      .insert({
        model_id: modelId,
        workflow_id: null,
        reference_image_id: null,
        parameters: { ...parameters, workflow_slug: workflowSlug, uploaded_image: uploadedImageFilename },
        prompt_used: positivePrompt,
        negative_prompt_used: negativePrompt,
        status: 'queued'
      })
      .select()
      .single()

    if (jobError) {
      throw jobError
    }

    // Submit to ComfyUI
    try {
      const comfyResponse = await axios.post(
        `${COMFYUI_API_URL}/prompt`,
        {
          prompt: filledWorkflow,
          client_id: `job_${job.id}`
        },
        {
          headers: {
            'Authorization': `Bearer ${RUNPOD_API_KEY}`
          }
        }
      )

      // Update job with RunPod job ID
      await supabase
        .from('generation_jobs')
        .update({
          runpod_job_id: comfyResponse.data.prompt_id,
          status: 'processing',
          started_at: new Date().toISOString()
        })
        .eq('id', job.id)

      res.json({
        success: true,
        jobId: job.id,
        runpodJobId: comfyResponse.data.prompt_id
      })
    } catch (comfyError) {
      console.error('ComfyUI Error:', comfyError.response?.data || comfyError.message)

      await supabase
        .from('generation_jobs')
        .update({
          status: 'failed',
          error_message: comfyError.message
        })
        .eq('id', job.id)

      res.status(500).json({
        error: 'Failed to submit to ComfyUI',
        details: comfyError.message
      })
    }
  } catch (error) {
    console.error('Generate Error:', error)
    res.status(500).json({ error: error.message })
  }
})

// GET /api/jobs - Get all jobs
app.get('/api/jobs', async (req, res) => {
  try {
    const { data: jobs } = await supabase
      .from('generation_jobs')
      .select(`
        *,
        models (name, slug),
        workflows (name, slug),
        reference_images (filename, storage_path)
      `)
      .order('created_at', { ascending: false })
      .limit(50)

    res.json(jobs)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// GET /api/jobs/:id - Get specific job status
app.get('/api/jobs/:id', async (req, res) => {
  try {
    const { data: job } = await supabase
      .from('generation_jobs')
      .select(`
        *,
        models (name, slug),
        workflows (name, slug),
        reference_images (filename, storage_path, vision_description)
      `)
      .eq('id', req.params.id)
      .single()

    if (!job) {
      return res.status(404).json({ error: 'Job not found' })
    }

    res.json(job)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// GET /api/workflows - Get all workflows from filesystem
app.get('/api/workflows', async (req, res) => {
  try {
    const workflowsDir = path.join(__dirname, '../workflows')
    const files = await fs.readdir(workflowsDir)

    const workflows = files
      .filter(f => f.endsWith('.json'))
      .map(f => ({
        slug: f.replace('.json', ''),
        name: f.replace('.json', '').split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
        description: 'ComfyUI workflow'
      }))

    res.json(workflows)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/jobs/:id/check - Check job status with ComfyUI
app.post('/api/jobs/:id/check', async (req, res) => {
  try {
    const { data: job } = await supabase
      .from('generation_jobs')
      .select('*')
      .eq('id', req.params.id)
      .single()

    if (!job || !job.runpod_job_id) {
      return res.status(404).json({ error: 'Job not found' })
    }

    // Check status with ComfyUI
    const historyResponse = await axios.get(
      `${COMFYUI_API_URL}/history/${job.runpod_job_id}`,
      {
        headers: {
          'Authorization': `Bearer ${RUNPOD_API_KEY}`
        }
      }
    )

    const history = historyResponse.data[job.runpod_job_id]

    if (history && history.status?.completed) {
      // Job completed, get the output image
      const outputs = history.outputs

      // Find the SaveImage node output (node 12 in our workflow)
      let supabaseImageUrl = null
      if (outputs['12']?.images?.[0]) {
        const image = outputs['12'].images[0]
        const comfyImageUrl = `${COMFYUI_API_URL}/view?filename=${image.filename}&subfolder=${image.subfolder || ''}&type=${image.type || 'output'}`

        try {
          // Download image from ComfyUI
          const imageResponse = await axios.get(comfyImageUrl, {
            headers: { 'Authorization': `Bearer ${RUNPOD_API_KEY}` },
            responseType: 'arraybuffer'
          })

          // Upload to Supabase Storage
          const imageBuffer = Buffer.from(imageResponse.data)
          const storagePath = `${image.filename}`

          const { data: uploadData, error: uploadError } = await supabase.storage
            .from('generated-images')
            .upload(storagePath, imageBuffer, {
              contentType: 'image/png',
              upsert: true
            })

          if (uploadError) {
            console.error('Supabase upload error:', uploadError)
            supabaseImageUrl = comfyImageUrl // Fallback to ComfyUI URL
          } else {
            // Get public URL
            const { data: publicUrlData } = supabase.storage
              .from('generated-images')
              .getPublicUrl(storagePath)

            supabaseImageUrl = publicUrlData.publicUrl
          }
        } catch (downloadError) {
          console.error('Image download/upload error:', downloadError)
          supabaseImageUrl = comfyImageUrl // Fallback to ComfyUI URL
        }
      }

      // Update job
      await supabase
        .from('generation_jobs')
        .update({
          status: 'completed',
          result_image_url: supabaseImageUrl,
          completed_at: new Date().toISOString()
        })
        .eq('id', job.id)

      res.json({ status: 'completed', imageUrl: supabaseImageUrl })
    } else if (history?.status?.status_str === 'error') {
      await supabase
        .from('generation_jobs')
        .update({
          status: 'failed',
          error_message: 'ComfyUI error'
        })
        .eq('id', job.id)

      res.json({ status: 'failed' })
    } else {
      res.json({ status: 'processing' })
    }
  } catch (error) {
    console.error('Check status error:', error)
    res.status(500).json({ error: error.message })
  }
})

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`)
})
