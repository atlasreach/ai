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

// POST /api/upload-face - Upload face image to Supabase Storage
app.post('/api/upload-face', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' })
    }

    const timestamp = Date.now()
    const filename = `face_${timestamp}_${req.file.originalname}`

    const { data, error } = await supabase.storage
      .from('face-images')
      .upload(filename, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: false
      })

    if (error) throw error

    const { data: publicUrlData } = supabase.storage
      .from('face-images')
      .getPublicUrl(filename)

    res.json({
      success: true,
      url: publicUrlData.publicUrl
    })
  } catch (error) {
    console.error('Face upload error:', error)
    res.status(500).json({
      error: 'Failed to upload face image',
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
        reference_images (filename, storage_path, vision_description)
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

// GET /api/gallery-images - Get all gallery images (from generated_images table)
app.get('/api/gallery-images', async (req, res) => {
  try {
    const { data: images } = await supabase
      .from('generated_images')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(200)

    res.json(images || [])
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

    // First check if still in queue
    let queueResponse
    try {
      queueResponse = await axios.get(
        `${COMFYUI_API_URL}/queue`,
        {
          headers: {
            'Authorization': `Bearer ${RUNPOD_API_KEY}`
          }
        }
      )
    } catch (queueError) {
      console.log('Queue check failed:', queueError.message)
    }

    // Check if job is still queued or executing
    if (queueResponse?.data) {
      const allQueuedJobs = [...(queueResponse.data.queue_running || []), ...(queueResponse.data.queue_pending || [])]
      const isQueued = allQueuedJobs.some(item => item[1] === job.runpod_job_id || item[2]?.client_id === `job_${job.id}`)

      if (isQueued) {
        return res.json({ status: 'processing' })
      }
    }

    // Check history for completed jobs
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

      // Insert into generated_images for gallery
      const { data: updatedJob } = await supabase
        .from('generation_jobs')
        .select('*, models(name, slug), reference_images(filename, vision_description)')
        .eq('id', job.id)
        .single()

      if (updatedJob) {
        await supabase
          .from('generated_images')
          .insert({
            job_id: updatedJob.id,
            model_id: updatedJob.model_id,
            reference_image_id: updatedJob.reference_image_id,
            image_url: supabaseImageUrl,
            storage_path: storagePath,
            prompt_used: updatedJob.prompt_used,
            negative_prompt_used: updatedJob.negative_prompt_used,
            parameters: updatedJob.parameters,
            model_name: updatedJob.models?.name,
            model_slug: updatedJob.models?.slug,
            reference_filename: updatedJob.reference_images?.filename,
            reference_caption: updatedJob.reference_images?.vision_description,
            generated_at: updatedJob.completed_at
          })
      }

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

// ===== SUB-MODELS ENDPOINTS =====

// GET /api/sub-models - Get all sub-models with their main model
app.get('/api/sub-models', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('sub_models')
      .select('*, models(*)')
      .order('created_at', { ascending: false })

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// GET /api/models/:modelId/sub-models - Get sub-models for specific main model
app.get('/api/models/:modelId/sub-models', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('sub_models')
      .select('*')
      .eq('model_id', req.params.modelId)
      .order('created_at', { ascending: false })

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/sub-models - Create new sub-model
app.post('/api/sub-models', async (req, res) => {
  try {
    const { model_id, name, face_image_url, fanhub_account, description } = req.body

    const { data, error } = await supabase
      .from('sub_models')
      .insert({ model_id, name, face_image_url, fanhub_account, description })
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// PUT /api/sub-models/:id - Update sub-model
app.put('/api/sub-models/:id', async (req, res) => {
  try {
    const { name, face_image_url, fanhub_account, description } = req.body

    const { data, error } = await supabase
      .from('sub_models')
      .update({ name, face_image_url, fanhub_account, description, updated_at: new Date() })
      .eq('id', req.params.id)
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// DELETE /api/sub-models/:id - Delete sub-model
app.delete('/api/sub-models/:id', async (req, res) => {
  try {
    const { error } = await supabase
      .from('sub_models')
      .delete()
      .eq('id', req.params.id)

    if (error) throw error
    res.json({ success: true })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// ===== CONTENT TYPES ENDPOINTS =====

// GET /api/sub-models/:subModelId/content-types - Get content types for sub-model
app.get('/api/sub-models/:subModelId/content-types', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('content_types')
      .select('*')
      .eq('sub_model_id', req.params.subModelId)
      .order('created_at', { ascending: false })

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/content-types - Create new content type
app.post('/api/content-types', async (req, res) => {
  try {
    const { sub_model_id, name, instagram_account, description } = req.body

    const { data, error } = await supabase
      .from('content_types')
      .insert({ sub_model_id, name, instagram_account, description })
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// PUT /api/content-types/:id - Update content type
app.put('/api/content-types/:id', async (req, res) => {
  try {
    const { name, instagram_account, description } = req.body

    const { data, error } = await supabase
      .from('content_types')
      .update({ name, instagram_account, description, updated_at: new Date() })
      .eq('id', req.params.id)
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// DELETE /api/content-types/:id - Delete content type
app.delete('/api/content-types/:id', async (req, res) => {
  try {
    const { error } = await supabase
      .from('content_types')
      .delete()
      .eq('id', req.params.id)

    if (error) throw error
    res.json({ success: true })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`)
})
