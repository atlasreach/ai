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
import Replicate from 'replicate'

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

// Initialize Replicate client
const replicate = new Replicate({
  auth: process.env.REPLICATE_API_TOKEN
})

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
    const { modelId, workflowSlug, uploadedImageFilename, parameters, batchId } = req.body

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
        status: 'queued',
        batch_id: batchId || null
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
    const { starred } = req.query

    let query = supabase
      .from('generated_images')
      .select('*')
      .eq('is_deleted', false)

    if (starred === 'true') {
      query = query.eq('is_starred', true)
    }

    const { data: images } = await query
      .order('created_at', { ascending: false })
      .limit(1000000)

    res.json(images || [])
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/star - Toggle star/favorite
app.post('/api/gallery-images/:id/star', async (req, res) => {
  try {
    const { id } = req.params
    const { starred } = req.body

    const { data, error } = await supabase
      .from('generated_images')
      .update({ is_starred: starred })
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// DELETE /api/gallery-images/:id - Soft delete image
app.delete('/api/gallery-images/:id', async (req, res) => {
  try {
    const { id } = req.params

    const { data, error } = await supabase
      .from('generated_images')
      .update({
        is_deleted: true,
        deleted_at: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    res.json(data)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/face-swap - Face swap using Replicate
app.post('/api/gallery-images/:id/face-swap', async (req, res) => {
  try {
    const { id } = req.params
    const { faceSourceUrl } = req.body

    // Get the original image
    const { data: originalImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !originalImage) {
      return res.status(404).json({ error: 'Image not found' })
    }

    // Default face source URL (source.jpg from Supabase storage)
    const swapFaceUrl = faceSourceUrl || `${process.env.SUPABASE_URL}/storage/v1/object/public/face-sources/source.jpg`

    console.log('Starting face swap...')
    console.log('Input image:', originalImage.image_url)
    console.log('Swap face:', swapFaceUrl)

    // Run face swap with Replicate
    const output = await replicate.run(
      "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
      {
        input: {
          input_image: originalImage.image_url,
          swap_image: swapFaceUrl
        }
      }
    )

    // Download the result from Replicate
    const imageResponse = await axios.get(output, { responseType: 'arraybuffer' })
    const imageBuffer = Buffer.from(imageResponse.data)

    // Upload to Supabase Storage
    const timestamp = Date.now()
    const storagePath = `face_swap_${timestamp}.png`

    const { error: uploadError } = await supabase.storage
      .from('generated-images')
      .upload(storagePath, imageBuffer, {
        contentType: 'image/png',
        upsert: false
      })

    if (uploadError) throw uploadError

    // Get public URL
    const { data: publicUrlData } = supabase.storage
      .from('generated-images')
      .getPublicUrl(storagePath)

    // Insert new image into generated_images
    const { data: newImage, error: insertError } = await supabase
      .from('generated_images')
      .insert({
        parent_image_id: originalImage.id,
        model_id: originalImage.model_id,
        image_url: publicUrlData.publicUrl,
        storage_path: storagePath,
        prompt_used: originalImage.prompt_used,
        negative_prompt_used: originalImage.negative_prompt_used,
        parameters: originalImage.parameters,
        model_name: originalImage.model_name,
        model_slug: originalImage.model_slug,
        edit_type: 'face_swap',
        face_swap_source: swapFaceUrl,
        batch_id: originalImage.batch_id,
        group_id: originalImage.group_id  // Preserve manual grouping
      })
      .select()
      .single()

    if (insertError) throw insertError

    // Auto-delete the original image
    await supabase
      .from('generated_images')
      .update({
        is_deleted: true,
        deleted_at: new Date().toISOString()
      })
      .eq('id', originalImage.id)

    console.log(`✅ Face swap complete and original image ${originalImage.id} deleted`)

    res.json({ success: true, image: newImage })
  } catch (error) {
    console.error('Face swap error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/wavespeed-edit - Single image edit with Wavespeed
app.post('/api/gallery-images/:id/wavespeed-edit', async (req, res) => {
  try {
    const { id } = req.params
    const { editPrompt } = req.body

    if (!editPrompt) {
      return res.status(400).json({ error: 'Edit prompt is required' })
    }

    // Get the original image
    const { data: originalImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !originalImage) {
      return res.status(404).json({ error: 'Image not found' })
    }

    console.log('Starting Wavespeed edit...')
    console.log('Input image:', originalImage.image_url)
    console.log('Edit prompt:', editPrompt)

    // Call Wavespeed API
    const wavespeedResponse = await axios.post(
      'https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit',
      {
        prompt: editPrompt,
        images: [originalImage.image_url],
        enable_sync_mode: true
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const editedImageUrl = wavespeedResponse.data.data.outputs[0]

    // Download the result
    const imageResponse = await axios.get(editedImageUrl, { responseType: 'arraybuffer' })
    const imageBuffer = Buffer.from(imageResponse.data)

    // Upload to Supabase Storage
    const timestamp = Date.now()
    const storagePath = `wavespeed_edit_${timestamp}.png`

    const { error: uploadError } = await supabase.storage
      .from('generated-images')
      .upload(storagePath, imageBuffer, {
        contentType: 'image/png',
        upsert: false
      })

    if (uploadError) throw uploadError

    // Get public URL
    const { data: publicUrlData } = supabase.storage
      .from('generated-images')
      .getPublicUrl(storagePath)

    // Insert new image into generated_images
    const { data: newImage, error: insertError } = await supabase
      .from('generated_images')
      .insert({
        parent_image_id: originalImage.id,
        model_id: originalImage.model_id,
        image_url: publicUrlData.publicUrl,
        storage_path: storagePath,
        prompt_used: editPrompt,
        negative_prompt_used: originalImage.negative_prompt_used,
        parameters: { ...originalImage.parameters, wavespeed_edit_prompt: editPrompt },
        model_name: originalImage.model_name,
        model_slug: originalImage.model_slug,
        edit_type: 'wavespeed_edit',
        batch_id: originalImage.batch_id,
        group_id: originalImage.group_id
      })
      .select()
      .single()

    if (insertError) throw insertError

    res.json({ success: true, image: newImage })
  } catch (error) {
    console.error('Wavespeed edit error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/edit-with-reference - Edit generated image comparing to its reference
app.post('/api/gallery-images/:id/edit-with-reference', async (req, res) => {
  console.log('📸 Edit with Reference request for image:', req.params.id)

  try {
    const { id } = req.params
    const { editPrompt } = req.body

    if (!editPrompt) {
      console.error('❌ No edit prompt provided')
      return res.status(400).json({ error: 'Edit prompt is required' })
    }

    // Get the generated image
    const { data: generatedImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !generatedImage) {
      console.error('❌ Image not found:', fetchError)
      return res.status(404).json({ error: 'Image not found', details: fetchError?.message })
    }

    console.log('✓ Found generated image:', generatedImage.id)
    console.log('  - reference_filename:', generatedImage.reference_filename)
    console.log('  - parameters.uploaded_image:', generatedImage.parameters?.uploaded_image)

    // Get reference image URL
    let referenceImageUrl
    if (generatedImage.reference_filename) {
      const { data: publicUrlData } = supabase.storage
        .from('reference-images')
        .getPublicUrl(generatedImage.reference_filename)
      referenceImageUrl = publicUrlData.publicUrl
      console.log('✓ Using Supabase reference URL:', referenceImageUrl)
    } else if (generatedImage.parameters?.uploaded_image) {
      // Fallback to ComfyUI path
      referenceImageUrl = `https://4bpau787p5p1t6-3001.proxy.runpod.net/view?filename=${generatedImage.parameters.uploaded_image}&subfolder=&type=input`
      console.log('✓ Using ComfyUI reference URL:', referenceImageUrl)
    } else {
      console.error('❌ No reference image found')
      return res.status(400).json({
        error: 'No reference image found for this generated image',
        details: 'Image has no reference_filename or uploaded_image parameter'
      })
    }

    console.log('📤 Calling Wavespeed API...')
    console.log('  - Generated image:', generatedImage.image_url)
    console.log('  - Reference image:', referenceImageUrl)
    console.log('  - Edit instruction:', editPrompt)

    // Call Wavespeed API with BOTH images
    const wavespeedResponse = await axios.post(
      'https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit',
      {
        prompt: editPrompt,
        images: [generatedImage.image_url, referenceImageUrl],  // Send both images
        enable_sync_mode: true
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const editedImageUrl = wavespeedResponse.data.data.outputs[0]

    // Download the result
    const imageResponse = await axios.get(editedImageUrl, { responseType: 'arraybuffer' })
    const imageBuffer = Buffer.from(imageResponse.data)

    // Upload to Supabase Storage
    const timestamp = Date.now()
    const storagePath = `edit_with_reference_${timestamp}.png`

    const { error: uploadError } = await supabase.storage
      .from('generated-images')
      .upload(storagePath, imageBuffer, {
        contentType: 'image/png',
        upsert: false
      })

    if (uploadError) throw uploadError

    // Get public URL
    const { data: publicUrlData } = supabase.storage
      .from('generated-images')
      .getPublicUrl(storagePath)

    // Insert new image into generated_images
    const { data: newImage, error: insertError } = await supabase
      .from('generated_images')
      .insert({
        parent_image_id: generatedImage.id,
        model_id: generatedImage.model_id,
        image_url: publicUrlData.publicUrl,
        storage_path: storagePath,
        prompt_used: editPrompt,
        negative_prompt_used: generatedImage.negative_prompt_used,
        parameters: {
          ...generatedImage.parameters,
          edit_with_reference_prompt: editPrompt,
          reference_image: referenceImageUrl
        },
        model_name: generatedImage.model_name,
        model_slug: generatedImage.model_slug,
        edit_type: 'edit_with_reference',
        batch_id: generatedImage.batch_id,
        group_id: generatedImage.group_id,
        reference_filename: generatedImage.reference_filename
      })
      .select()
      .single()

    if (insertError) throw insertError

    console.log('✅ Edit with reference complete:', newImage.id)
    res.json({ success: true, image: newImage })
  } catch (error) {
    console.error('Edit with reference error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/wavespeed-variations - Generate multiple variations with Wavespeed
app.post('/api/gallery-images/:id/wavespeed-variations', async (req, res) => {
  try {
    const { id } = req.params
    const { variationPrompt, numImages } = req.body

    const imageCount = numImages || 4
    if (imageCount < 1 || imageCount > 15) {
      return res.status(400).json({ error: 'Number of images must be between 1 and 15' })
    }

    // Get the original image
    const { data: originalImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !originalImage) {
      return res.status(404).json({ error: 'Image not found' })
    }

    console.log('Starting Wavespeed variations...')
    console.log('Input image:', originalImage.image_url)
    console.log('Variation prompt:', variationPrompt)
    console.log('Number of images:', imageCount)

    // Build the prompt with image count
    const fullPrompt = variationPrompt
      ? `${imageCount} images: ${variationPrompt}`
      : `${imageCount} images with subtle variations`

    // Call Wavespeed API for sequential editing
    const wavespeedResponse = await axios.post(
      'https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit-sequential',
      {
        prompt: fullPrompt,
        images: [originalImage.image_url],
        max_images: imageCount,
        enable_sync_mode: true
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const outputUrls = wavespeedResponse.data.data.outputs

    // Create a batch ID for these variations
    const batchId = `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // Process each generated image
    const newImages = []
    for (let i = 0; i < outputUrls.length; i++) {
      const imageUrl = outputUrls[i]

      // Download the result
      const imageResponse = await axios.get(imageUrl, { responseType: 'arraybuffer' })
      const imageBuffer = Buffer.from(imageResponse.data)

      // Upload to Supabase Storage
      const timestamp = Date.now()
      const storagePath = `wavespeed_var_${timestamp}_${i}.png`

      const { error: uploadError } = await supabase.storage
        .from('generated-images')
        .upload(storagePath, imageBuffer, {
          contentType: 'image/png',
          upsert: false
        })

      if (uploadError) throw uploadError

      // Get public URL
      const { data: publicUrlData } = supabase.storage
        .from('generated-images')
        .getPublicUrl(storagePath)

      // Insert new image into generated_images
      const { data: newImage, error: insertError } = await supabase
        .from('generated_images')
        .insert({
          parent_image_id: originalImage.id,
          model_id: originalImage.model_id,
          image_url: publicUrlData.publicUrl,
          storage_path: storagePath,
          prompt_used: fullPrompt,
          negative_prompt_used: originalImage.negative_prompt_used,
          parameters: {
            ...originalImage.parameters,
            wavespeed_variation_prompt: variationPrompt,
            variation_index: i + 1
          },
          model_name: originalImage.model_name,
          model_slug: originalImage.model_slug,
          edit_type: 'wavespeed_variation',
          batch_id: batchId
        })
        .select()
        .single()

      if (insertError) throw insertError
      newImages.push(newImage)
    }

    res.json({ success: true, images: newImages, count: newImages.length })
  } catch (error) {
    console.error('Wavespeed variations error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/carousel-variations - Generate carousel variations (minimal changes, high consistency)
app.post('/api/gallery-images/:id/carousel-variations', async (req, res) => {
  try {
    const { id } = req.params
    const { variationPrompt, numImages } = req.body

    const imageCount = numImages || 3
    if (imageCount < 2 || imageCount > 7) {
      return res.status(400).json({ error: 'Number of images must be between 2 and 7' })
    }

    // Get the original image
    const { data: originalImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !originalImage) {
      return res.status(404).json({ error: 'Image not found' })
    }

    console.log('Starting Carousel variations...')
    console.log('Input image:', originalImage.image_url)
    console.log('Variation prompt:', variationPrompt)
    console.log('Number of images:', imageCount)

    // Build highly specific prompt for consistency
    const userVariation = variationPrompt || 'different camera angle, facial expression, and pose'
    const fullPrompt = `${imageCount} images: KEEP EXACT SAME: background, clothing, lighting, style, quality. ONLY CHANGE: ${userVariation}. Maintain perfect consistency.`

    console.log('Full carousel prompt:', fullPrompt)

    // Call Wavespeed API for sequential editing with consistency emphasis
    const wavespeedResponse = await axios.post(
      'https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit-sequential',
      {
        prompt: fullPrompt,
        images: [originalImage.image_url],
        max_images: imageCount,
        enable_sync_mode: true
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const outputUrls = wavespeedResponse.data.data.outputs

    // Inherit batch ID from parent if it exists, otherwise create new carousel batch
    const batchId = originalImage.batch_id || `carousel_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // Process each generated image
    const newImages = []
    for (let i = 0; i < outputUrls.length; i++) {
      const imageUrl = outputUrls[i]

      // Download the result
      const imageResponse = await axios.get(imageUrl, { responseType: 'arraybuffer' })
      const imageBuffer = Buffer.from(imageResponse.data)

      // Upload to Supabase Storage
      const timestamp = Date.now()
      const storagePath = `carousel_${timestamp}_${i}.png`

      const { error: uploadError } = await supabase.storage
        .from('generated-images')
        .upload(storagePath, imageBuffer, {
          contentType: 'image/png',
          upsert: false
        })

      if (uploadError) throw uploadError

      // Get public URL
      const { data: publicUrlData } = supabase.storage
        .from('generated-images')
        .getPublicUrl(storagePath)

      // Insert new image into generated_images
      const { data: newImage, error: insertError } = await supabase
        .from('generated_images')
        .insert({
          parent_image_id: originalImage.id,
          model_id: originalImage.model_id,
          image_url: publicUrlData.publicUrl,
          storage_path: storagePath,
          prompt_used: fullPrompt,
          negative_prompt_used: originalImage.negative_prompt_used,
          parameters: {
            ...originalImage.parameters,
            carousel_variation_prompt: variationPrompt,
            carousel_index: i + 1,
            is_carousel: true
          },
          model_name: originalImage.model_name,
          model_slug: originalImage.model_slug,
          edit_type: 'carousel_variation',
          batch_id: batchId,
          reference_filename: originalImage.reference_filename
        })
        .select()
        .single()

      if (insertError) throw insertError
      newImages.push(newImage)
    }

    console.log(`✅ Carousel complete: ${newImages.length} images created in batch ${batchId}`)
    res.json({ success: true, images: newImages, count: newImages.length, batchId })
  } catch (error) {
    console.error('Carousel variations error:', error)
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
      let storagePath = null
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
          storagePath = `${image.filename}`

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
            generated_at: updatedJob.completed_at,
            batch_id: updatedJob.batch_id
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

// POST /api/jobs/clear-stuck - Clear all stuck processing jobs
app.post('/api/jobs/clear-stuck', async (req, res) => {
  try {
    // Mark jobs older than 15 minutes still processing as failed
    const fifteenMinutesAgo = new Date(Date.now() - 15 * 60 * 1000).toISOString()

    const { data: stuckJobs } = await supabase
      .from('generation_jobs')
      .select('id, created_at')
      .eq('status', 'processing')
      .lt('started_at', fifteenMinutesAgo)

    if (!stuckJobs || stuckJobs.length === 0) {
      return res.json({ message: 'No stuck jobs found', count: 0 })
    }

    const { error } = await supabase
      .from('generation_jobs')
      .update({
        status: 'failed',
        error_message: 'Job timed out or was cleared from queue'
      })
      .eq('status', 'processing')
      .lt('started_at', fifteenMinutesAgo)

    if (error) throw error

    res.json({ message: `Cleared ${stuckJobs.length} stuck jobs`, count: stuckJobs.length })
  } catch (error) {
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

// POST /api/enhance-prompt - Enhance prompts with Grok AI
app.post('/api/enhance-prompt', async (req, res) => {
  try {
    const { prompt } = req.body

    if (!prompt || !prompt.trim()) {
      return res.status(400).json({ error: 'Prompt is required' })
    }

    console.log('Enhancing prompt:', prompt)

    const grokResponse = await axios.post(
      'https://api.x.ai/v1/chat/completions',
      {
        model: 'grok-2-latest',
        messages: [
          {
            role: 'system',
            content: `You are an expert prompt engineer for Bytedance Seedream V4 image editing AI. Seedream excels at realistic image modifications when given clear, detailed instructions. When given a brief editing request, enhance it to be more effective for Seedream by:

1. Being specific about what to change and how
2. Mentioning texture, lighting, and blend requirements to maintain realism
3. Specifying quality expectations (natural, seamless, photorealistic)
4. Keeping instructions clear and actionable

Return ONLY the enhanced prompt text, no explanations or quotes.`
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.GROK_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const enhancedPrompt = grokResponse.data.choices[0].message.content

    console.log('Enhanced prompt:', enhancedPrompt)

    res.json({
      original: prompt,
      enhanced: enhancedPrompt
    })
  } catch (error) {
    console.error('Grok API error:', error.response?.data || error.message)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/smart-blend - Smart blend two images with Grok Vision + Wavespeed
app.post('/api/smart-blend', async (req, res) => {
  try {
    const { sourceImageId, referenceImageId, instruction, numVariations } = req.body

    console.log('Smart Blend:', { sourceImageId, referenceImageId, instruction, numVariations })

    // Get both images from database
    const { data: sourceImage } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', sourceImageId)
      .single()

    const { data: referenceImage } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', referenceImageId)
      .single()

    if (!sourceImage || !referenceImage) {
      return res.status(404).json({ error: 'Images not found' })
    }

    console.log('Analyzing images with Grok Vision...')

    // Use Grok Vision to analyze both images and create transfer prompt
    const grokResponse = await axios.post(
      'https://api.x.ai/v1/chat/completions',
      {
        model: 'grok-2-vision-1212',
        messages: [
          {
            role: 'system',
            content: `You are an expert at analyzing images and creating precise image editing instructions for Bytedance Seedream V4.

Your task: User has two images and wants to transfer specific elements from image 2 to image 1. Based on the user's instruction, analyze both images and create a SIMPLE, FOCUSED editing prompt.

IMPORTANT RULES:
- Only describe the specific transfer requested
- DO NOT add lighting adjustments, texture improvements, or quality mentions
- Keep it concise and actionable
- Return ONLY the editing prompt, no explanations`
          },
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: `User wants to: "${instruction}"

IMAGE 1 (keep everything from this image):
`
              },
              {
                type: 'image_url',
                image_url: { url: sourceImage.image_url }
              },
              {
                type: 'text',
                text: `\nIMAGE 2 (reference for the element to transfer):
`
              },
              {
                type: 'image_url',
                image_url: { url: referenceImage.image_url }
              },
              {
                type: 'text',
                text: `\n\nCreate a SHORT prompt that changes ONLY the requested element in image 1 to match what's in image 2. Keep everything else from image 1 exactly the same.`
              }
            ]
          }
        ],
        temperature: 0.7
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.GROK_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const editingPrompt = grokResponse.data.choices[0].message.content
    console.log('Generated editing prompt:', editingPrompt)

    // Call Wavespeed with the generated prompt
    console.log(`Calling Wavespeed for ${numVariations} variation(s)...`)

    const wavespeedResponse = await axios.post(
      'https://api.wavespeed.ai/api/v3/bytedance/seedream-v4/edit-sequential',
      {
        prompt: `${numVariations} images: ${editingPrompt}`,
        images: [sourceImage.image_url, referenceImage.image_url],
        max_images: numVariations,
        enable_sync_mode: true
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const outputUrls = wavespeedResponse.data.data.outputs
    // Inherit batch_id from source image if it exists, otherwise create new batch for multi-image results
    const batchId = numVariations > 1 ? (sourceImage.batch_id || `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`) : sourceImage.batch_id

    console.log(`Received ${outputUrls.length} images from Wavespeed`)

    // Download and upload each result
    const newImages = []
    for (let i = 0; i < outputUrls.length; i++) {
      const imageUrl = outputUrls[i]
      const timestamp = Date.now()
      const filename = `smart_blend_${timestamp}_${i}.png`

      // Download image
      const imageResponse = await axios.get(imageUrl, { responseType: 'arraybuffer' })
      const imageBuffer = Buffer.from(imageResponse.data)

      // Upload to Supabase
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('generated-images')
        .upload(filename, imageBuffer, {
          contentType: 'image/png',
          upsert: false
        })

      if (uploadError) throw uploadError

      const { data: publicUrlData } = supabase.storage
        .from('generated-images')
        .getPublicUrl(filename)

      // Insert into database
      const { data: newImage } = await supabase
        .from('generated_images')
        .insert({
          model_id: sourceImage.model_id,
          image_url: publicUrlData.publicUrl,
          storage_path: filename,
          prompt_used: sourceImage.prompt_used,
          negative_prompt_used: sourceImage.negative_prompt_used,
          parameters: {
            ...sourceImage.parameters,
            smart_blend_instruction: instruction,
            smart_blend_prompt: editingPrompt,
            variation_index: i + 1
          },
          parent_image_id: sourceImage.id,
          edit_type: 'smart_blend',
          batch_id: batchId,
          group_id: sourceImage.group_id,
          created_at: new Date().toISOString()
        })
        .select()
        .single()

      newImages.push(newImage)
    }

    console.log(`Smart Blend complete: ${newImages.length} images created`)

    res.json({
      success: true,
      images: newImages,
      count: newImages.length,
      editingPrompt
    })
  } catch (error) {
    console.error('Smart Blend error:', error.response?.data || error.message)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/group - Manually group multiple images together
app.post('/api/gallery-images/group', async (req, res) => {
  try {
    const { imageIds } = req.body

    if (!imageIds || imageIds.length < 2) {
      return res.status(400).json({ error: 'At least 2 image IDs required' })
    }

    // Create a unique group ID
    const groupId = `manual_group_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    console.log(`Creating manual group ${groupId} with ${imageIds.length} images`)

    // Update all selected images with the same group_id
    const { error: updateError } = await supabase
      .from('generated_images')
      .update({ group_id: groupId })
      .in('id', imageIds)

    if (updateError) throw updateError

    console.log(`✅ Grouped ${imageIds.length} images with group_id: ${groupId}`)
    res.json({ success: true, groupId, count: imageIds.length })
  } catch (error) {
    console.error('Group images error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/gallery-images/:id/face-swap-group - Face swap all images in the same group
app.post('/api/gallery-images/:id/face-swap-group', async (req, res) => {
  try {
    const { id } = req.params
    const { faceSourceUrl } = req.body

    // Get the source image to find its group
    const { data: sourceImage, error: fetchError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !sourceImage) {
      return res.status(404).json({ error: 'Image not found' })
    }

    // Find group_id or batch_id
    const groupIdentifier = sourceImage.group_id || sourceImage.batch_id
    if (!groupIdentifier) {
      return res.status(400).json({ error: 'Image is not part of a group' })
    }

    // Get all images in the same group
    let query = supabase
      .from('generated_images')
      .select('*')

    if (sourceImage.group_id) {
      query = query.eq('group_id', sourceImage.group_id)
    } else {
      query = query.eq('batch_id', sourceImage.batch_id)
    }

    const { data: groupImages, error: groupError } = await query

    if (groupError) throw groupError

    console.log(`Face swapping ${groupImages.length} images in group ${groupIdentifier}`)

    // Default face source URL
    const swapFaceUrl = faceSourceUrl || `${process.env.SUPABASE_URL}/storage/v1/object/public/face-sources/source.jpg`

    // Face swap each image
    const results = []
    for (const image of groupImages) {
      try {
        // Run face swap with Replicate
        const output = await replicate.run(
          "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
          {
            input: {
              input_image: image.image_url,
              swap_image: swapFaceUrl
            }
          }
        )

        // Download the result
        const imageResponse = await axios.get(output, { responseType: 'arraybuffer' })
        const imageBuffer = Buffer.from(imageResponse.data)

        // Upload to Supabase Storage
        const timestamp = Date.now()
        const storagePath = `face_swap_${timestamp}_${image.id}.png`

        const { error: uploadError } = await supabase.storage
          .from('generated-images')
          .upload(storagePath, imageBuffer, {
            contentType: 'image/png',
            upsert: false
          })

        if (uploadError) throw uploadError

        // Get public URL
        const { data: publicUrlData } = supabase.storage
          .from('generated-images')
          .getPublicUrl(storagePath)

        // Insert new image
        const { data: newImage, error: insertError } = await supabase
          .from('generated_images')
          .insert({
            parent_image_id: image.id,
            model_id: image.model_id,
            image_url: publicUrlData.publicUrl,
            storage_path: storagePath,
            prompt_used: image.prompt_used,
            negative_prompt_used: image.negative_prompt_used,
            parameters: image.parameters,
            model_name: image.model_name,
            model_slug: image.model_slug,
            edit_type: 'face_swap',
            face_swap_source: swapFaceUrl,
            batch_id: image.batch_id,
            group_id: image.group_id
          })
          .select()
          .single()

        if (insertError) throw insertError

        results.push({ success: true, originalId: image.id, newImageId: newImage.id })
      } catch (err) {
        console.error(`Failed to face swap image ${image.id}:`, err)
        results.push({ success: false, originalId: image.id, error: err.message })
      }
    }

    const succeeded = results.filter(r => r.success).length
    const failed = results.filter(r => !r.success).length

    // Auto-delete all original images that were successfully face swapped
    const successfulOriginalIds = results.filter(r => r.success).map(r => r.originalId)
    if (successfulOriginalIds.length > 0) {
      await supabase
        .from('generated_images')
        .update({
          is_deleted: true,
          deleted_at: new Date().toISOString()
        })
        .in('id', successfulOriginalIds)

      console.log(`✅ Auto-deleted ${successfulOriginalIds.length} original images`)
    }

    console.log(`✅ Face swap group complete: ${succeeded} succeeded, ${failed} failed`)

    res.json({
      success: true,
      total: groupImages.length,
      succeeded,
      failed,
      results
    })
  } catch (error) {
    console.error('Face swap group error:', error)
    res.status(500).json({ error: error.message })
  }
})

// ==============================================================
// VIDEO GENERATION (KLING 2.1) ENDPOINTS
// ==============================================================

// POST /api/generate-video-prompt - Generate prompts from images using Grok
app.post('/api/generate-video-prompt', async (req, res) => {
  try {
    const { startImageId, endImageId, provider = 'kling' } = req.body

    if (!startImageId || !endImageId) {
      return res.status(400).json({ error: 'startImageId and endImageId are required' })
    }

    // Fetch both images
    const { data: startImg, error: startError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', startImageId)
      .single()

    if (startError || !startImg) {
      console.error('Start image error:', startError)
      return res.status(404).json({ error: 'Start image not found' })
    }

    const { data: endImg, error: endError } = await supabase
      .from('generated_images')
      .select('*')
      .eq('id', endImageId)
      .single()

    if (endError || !endImg) {
      console.error('End image error:', endError)
      return res.status(404).json({ error: 'End image not found' })
    }

    console.log(`Calling Grok Vision API with images for provider: ${provider}...`)
    console.log('Start image:', startImg.image_url)
    console.log('End image:', endImg.image_url)

    // Generate provider-specific prompt
    let grokPrompt

    if (provider === 'wavespeed') {
      // WAN 2.2 - NSFW focused, intimate content
      grokPrompt = `You are an expert video prompt generator for AI-powered NSFW/adult video generation using WAN 2.2.

I'm showing you TWO images of a model:
- IMAGE 1: The START frame (first image below)
- IMAGE 2: The END frame (second image below)

ANALYZE THESE IMAGES VISUALLY and describe the REALISTIC PHYSICAL TRANSITION between them.

WHAT TO ANALYZE:
- Starting pose, body position, clothing, facial expression
- Ending pose, body position, clothing, facial expression
- What PHYSICAL ACTION would naturally connect these two poses?

CRITICAL: Focus on what the MODEL DOES, not what the camera does!
- DON'T say: "camera slowly shifts" or "camera zooms"
- DO say: "she turns her body", "she leans back", "she adjusts her hair", "she shifts her weight"

NSFW/ADULT CONTENT FOCUS:
✓ Sensual, intimate movements
✓ Natural body language and expressions
✓ Suggestive but realistic transitions
✓ Focus on the model's actions and adjustments
✓ Describe clothing changes or reveals if applicable

TASK: Describe the REALISTIC ACTION the model performs to go from the first pose to the second pose.
Think: What would she actually DO to get from pose A to pose B?

Return ONLY a JSON object:
{
  "positive_prompt": "Describe the model's physical actions/movements to transition from start to end. Be specific about body movements, not camera movements. Focus on sensual, intimate actions. 2-3 sentences.",
  "negative_prompt": "static image, camera movement, zoom, pan, shift, unrealistic morphing, distorted body, bad anatomy, jerky motion, artificial transition"
}

Make it REALISTIC based on what the model would actually DO!`
    } else {
      // Kling 2.1 - Instagram Reel focused
      grokPrompt = `You are an expert video prompt generator for AI-powered Instagram Reels using Kling 2.1.

I'm showing you TWO images of a model:
- IMAGE 1: The START frame (first image below)
- IMAGE 2: The END frame (second image below)

ANALYZE THESE IMAGES VISUALLY and describe the REALISTIC PHYSICAL TRANSITION between them.

WHAT TO ANALYZE:
- Starting pose, body position, clothing, facial expression
- Ending pose, body position, clothing, facial expression
- What PHYSICAL ACTION would naturally connect these two poses?

CRITICAL: Focus on what the MODEL DOES, not what the camera does!
- DON'T say: "camera slowly shifts" or "camera zooms"
- DO say: "she turns to face the camera", "she tosses her hair", "she adjusts her outfit", "she strikes a new pose"

INSTAGRAM REEL STYLE:
✓ Fashion-forward, confident movements
✓ Natural, engaging transitions
✓ Professional modeling actions
✓ Describe what the model actually does
✓ Include subtle camera work only if needed

TASK: Describe the REALISTIC ACTION the model performs to go from the first pose to the second pose.
Think: What would a model actually DO in a photoshoot to get from pose A to pose B?

Return ONLY a JSON object:
{
  "positive_prompt": "Describe the model's physical actions/movements to transition from start to end. Be specific about body movements, not camera movements. Focus on natural modeling actions. 2-3 sentences.",
  "negative_prompt": "static image, unmotivated camera movement, unrealistic morphing, distorted body, bad anatomy, jerky motion, artificial transition"
}

Make it REALISTIC based on what the model would actually DO!`
    }

    // Use Grok Vision with image URLs
    const grokResponse = await axios.post(
      'https://api.x.ai/v1/chat/completions',
      {
        model: 'grok-2-vision-1212',  // Grok Vision model
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'text',
                text: grokPrompt
              },
              {
                type: 'image_url',
                image_url: {
                  url: startImg.image_url
                }
              },
              {
                type: 'image_url',
                image_url: {
                  url: endImg.image_url
                }
              }
            ]
          }
        ],
        temperature: 0.7
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.GROK_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    )

    const grokContent = grokResponse.data.choices[0].message.content
    // Try to extract JSON from the response
    const jsonMatch = grokContent.match(/\{[\s\S]*\}/)
    const prompts = jsonMatch ? JSON.parse(jsonMatch[0]) : {
      positive_prompt: grokContent,
      negative_prompt: 'blurry, distorted, unnatural movement, bad quality, choppy, laggy'
    }

    res.json({
      success: true,
      startImage: {
        id: startImg.id,
        url: startImg.image_url,
        prompt: startImg.prompt_used
      },
      endImage: {
        id: endImg.id,
        url: endImg.image_url,
        prompt: endImg.prompt_used
      },
      ...prompts
    })
  } catch (error) {
    console.error('Generate video prompt error:', error.response?.data || error)
    res.status(500).json({
      error: 'Failed to generate video prompts',
      details: error.message
    })
  }
})

// POST /api/generate-video - Submit video generation to Kling 2.1 or WAN 2.2
app.post('/api/generate-video', async (req, res) => {
  try {
    const {
      startImageId,
      endImageId,
      modelId,
      positivePrompt,
      negativePrompt,
      duration,
      mode,
      provider = 'kling'  // 'kling' or 'wavespeed'
    } = req.body

    if (!startImageId || !positivePrompt) {
      return res.status(400).json({ error: 'startImageId and positivePrompt are required' })
    }

    // Fetch images to get URLs
    const { data: startImg } = await supabase
      .from('generated_images')
      .select('id, image_url, storage_path')
      .eq('id', startImageId)
      .single()

    if (!startImg) {
      return res.status(404).json({ error: 'Start image not found' })
    }

    let endImg = null
    if (endImageId) {
      const { data } = await supabase
        .from('generated_images')
        .select('id, image_url, storage_path')
        .eq('id', endImageId)
        .single()
      endImg = data
    }

    // Create job record first
    const { data: job, error: jobError } = await supabase
      .from('video_generation_jobs')
      .insert({
        start_image_id: startImageId,
        end_image_id: endImageId || null,
        model_id: modelId,
        positive_prompt: positivePrompt,
        negative_prompt: negativePrompt || '',
        duration: duration || 5,
        mode: mode || 'standard',
        provider: provider,
        status: 'pending'
      })
      .select()
      .single()

    if (jobError) {
      console.error('Job creation error:', jobError)
      return res.status(500).json({ error: 'Failed to create job', details: jobError.message })
    }

    let externalId = null

    if (provider === 'wavespeed') {
      // Submit to WaveSpeedAI WAN 2.2
      const wavespeedPayload = {
        duration: duration || 5,
        image: startImg.image_url,
        prompt: positivePrompt,
        negative_prompt: negativePrompt || '',
        seed: -1,
        high_noise_loras: [],
        low_noise_loras: [],
        loras: []
      }

      if (endImg) {
        wavespeedPayload.last_image = endImg.image_url
      }

      console.log('Submitting to WaveSpeedAI WAN 2.2:', wavespeedPayload)

      try {
        const wavespeedResponse = await axios.post(
          'https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/i2v-720p-lora',
          wavespeedPayload,
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`
            }
          }
        )

        console.log('WaveSpeedAI response:', JSON.stringify(wavespeedResponse.data, null, 2))

        externalId = wavespeedResponse.data.data?.id || wavespeedResponse.data.id

        if (!externalId) {
          throw new Error(`No ID in WaveSpeedAI response: ${JSON.stringify(wavespeedResponse.data)}`)
        }

        console.log(`WaveSpeedAI request submitted. ID: ${externalId}`)

        // Update job with WaveSpeedAI ID
        await supabase
          .from('video_generation_jobs')
          .update({
            replicate_id: externalId,  // Using replicate_id field for WaveSpeedAI ID too
            status: 'processing',
            metadata: { wavespeed_input: wavespeedPayload, wavespeed_response: wavespeedResponse.data }
          })
          .eq('id', job.id)
      } catch (wavespeedError) {
        console.error('WaveSpeedAI API Error:', {
          message: wavespeedError.message,
          status: wavespeedError.response?.status,
          statusText: wavespeedError.response?.statusText,
          data: wavespeedError.response?.data,
          headers: wavespeedError.response?.headers
        })

        // Update job to failed
        await supabase
          .from('video_generation_jobs')
          .update({
            status: 'failed',
            metadata: {
              error: wavespeedError.message,
              error_response: wavespeedError.response?.data
            }
          })
          .eq('id', job.id)

        throw new Error(`WaveSpeedAI API Error: ${wavespeedError.response?.data?.message || wavespeedError.message}`)
      }

    } else {
      // Submit to Replicate Kling 2.1 API
      const replicateInput = {
        prompt: positivePrompt,
        start_image: startImg.image_url,
        duration: duration || 5,
        mode: mode || 'standard'
      }

      if (negativePrompt) {
        replicateInput.negative_prompt = negativePrompt
      }

      // IMPORTANT: end_image parameter requires 'pro' mode
      if (endImg) {
        replicateInput.end_image = endImg.image_url
        // Force pro mode if end image is provided
        if (mode !== 'pro') {
          console.log('⚠️  Forcing pro mode because end_image is provided (required by Kling API)')
          replicateInput.mode = 'pro'
        }
      }

      console.log('Submitting to Kling 2.1:', replicateInput)

      const prediction = await replicate.predictions.create({
        model: 'kwaivgi/kling-v2.1',
        input: replicateInput
      })

      externalId = prediction.id

      // Update job with Replicate ID
      await supabase
        .from('video_generation_jobs')
        .update({
          replicate_id: prediction.id,
          status: 'processing',
          metadata: { replicate_input: replicateInput }
        })
        .eq('id', job.id)
    }

    res.json({
      success: true,
      jobId: job.id,
      externalId: externalId,
      provider: provider,
      status: 'processing'
    })
  } catch (error) {
    console.error('Generate video error:', error)
    res.status(500).json({
      error: 'Failed to generate video',
      details: error.message
    })
  }
})

// GET /api/video-jobs - List all video generation jobs
app.get('/api/video-jobs', async (req, res) => {
  try {
    const { status, limit } = req.query

    let query = supabase
      .from('video_generation_jobs')
      .select(`
        *,
        start_image:start_image_id (id, image_url, storage_path),
        end_image:end_image_id (id, image_url, storage_path),
        model:model_id (id, name, slug)
      `)
      .order('created_at', { ascending: false })

    if (status) {
      query = query.eq('status', status)
    }

    if (limit) {
      query = query.limit(parseInt(limit))
    }

    const { data, error } = await query

    if (error) throw error

    res.json(data || [])
  } catch (error) {
    console.error('Fetch video jobs error:', error)
    res.status(500).json({ error: error.message })
  }
})

// GET /api/video-jobs/:id - Get single video job with details
app.get('/api/video-jobs/:id', async (req, res) => {
  try {
    const { id } = req.params

    const { data: job, error } = await supabase
      .from('video_generation_jobs')
      .select(`
        *,
        start_image:start_image_id (id, image_url, storage_path, prompt_used),
        end_image:end_image_id (id, image_url, storage_path, prompt_used),
        model:model_id (id, name, slug)
      `)
      .eq('id', id)
      .single()

    if (error || !job) {
      return res.status(404).json({ error: 'Video job not found' })
    }

    res.json(job)
  } catch (error) {
    console.error('Fetch video job error:', error)
    res.status(500).json({ error: error.message })
  }
})

// POST /api/video-jobs/:id/check - Check status and update from provider (Kling or WaveSpeedAI)
app.post('/api/video-jobs/:id/check', async (req, res) => {
  try {
    const { id } = req.params

    // Fetch job
    const { data: job, error: jobError } = await supabase
      .from('video_generation_jobs')
      .select('*')
      .eq('id', id)
      .single()

    if (jobError || !job) {
      return res.status(404).json({ error: 'Job not found' })
    }

    if (!job.replicate_id) {
      return res.status(400).json({ error: 'No external ID for this job' })
    }

    let updateData = {}
    let externalStatus = null

    if (job.provider === 'wavespeed') {
      // Check WaveSpeedAI status
      const wavespeedResponse = await axios.get(
        `https://api.wavespeed.ai/api/v3/predictions/${job.replicate_id}/result`,
        {
          headers: {
            'Authorization': `Bearer ${process.env.WAVESPEED_API_KEY}`
          }
        }
      )

      const result = wavespeedResponse.data.data
      externalStatus = result.status

      console.log(`Video job ${id} (WaveSpeedAI) status:`, externalStatus)

      updateData = {
        status: result.status === 'completed' ? 'completed' :
                result.status === 'failed' ? 'failed' : 'processing'
      }

      if (result.status === 'completed' && result.outputs && result.outputs.length > 0) {
        updateData.video_url = result.outputs[0]
        updateData.completed_at = new Date().toISOString()
      }

      if (result.status === 'failed') {
        updateData.error = result.error || 'Video generation failed'
        updateData.completed_at = new Date().toISOString()
      }

    } else {
      // Check Replicate Kling status
      const prediction = await replicate.predictions.get(job.replicate_id)
      externalStatus = prediction.status

      console.log(`Video job ${id} (Kling) status:`, externalStatus)

      updateData = {
        status: prediction.status === 'succeeded' ? 'completed' :
                prediction.status === 'failed' ? 'failed' : 'processing'
      }

      if (prediction.status === 'succeeded' && prediction.output) {
        updateData.video_url = prediction.output
        updateData.completed_at = new Date().toISOString()
      }

      if (prediction.status === 'failed') {
        updateData.error = prediction.error || 'Video generation failed'
        updateData.completed_at = new Date().toISOString()
      }
    }

    // Update job in database
    const { error: updateError } = await supabase
      .from('video_generation_jobs')
      .update(updateData)
      .eq('id', id)

    if (updateError) {
      console.error('Update error:', updateError)
    }

    res.json({
      success: true,
      status: updateData.status,
      videoUrl: updateData.video_url,
      error: updateData.error,
      provider: job.provider,
      externalStatus: externalStatus
    })
  } catch (error) {
    console.error('Check video job error:', error)
    res.status(500).json({ error: error.message })
  }
})

// ==============================================================
// AUTOMATIC JOB POLLING - Checks processing jobs every 8 seconds
// ==============================================================

async function checkProcessingJob(job) {
  try {
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
      // Queue check failed, continue to history check
    }

    // Check if job is still queued or executing
    if (queueResponse?.data) {
      const allQueuedJobs = [...(queueResponse.data.queue_running || []), ...(queueResponse.data.queue_pending || [])]
      const isQueued = allQueuedJobs.some(item => item[1] === job.runpod_job_id || item[2]?.client_id === `job_${job.id}`)

      if (isQueued) {
        return 'still_processing'
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
      let storagePath = null
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
          storagePath = `${image.filename}`

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
            generated_at: updatedJob.completed_at,
            batch_id: updatedJob.batch_id
          })
      }

      console.log(`✓ Job ${job.id} completed and saved to gallery`)
      return 'completed'
    } else if (history?.status?.status_str === 'error') {
      await supabase
        .from('generation_jobs')
        .update({
          status: 'failed',
          error_message: 'ComfyUI error'
        })
        .eq('id', job.id)

      console.log(`✗ Job ${job.id} failed`)
      return 'failed'
    } else {
      return 'still_processing'
    }
  } catch (error) {
    console.error(`Error checking job ${job.id}:`, error.message)
    return 'error'
  }
}

async function pollProcessingJobs() {
  try {
    // Fetch all processing jobs
    const { data: jobs } = await supabase
      .from('generation_jobs')
      .select('*')
      .eq('status', 'processing')
      .order('created_at', { ascending: true })
      .limit(50)

    if (jobs && jobs.length > 0) {
      console.log(`⏳ Checking ${jobs.length} processing jobs...`)

      // Check jobs sequentially to avoid overwhelming the API
      for (const job of jobs) {
        await checkProcessingJob(job)
        // Small delay between checks
        await new Promise(resolve => setTimeout(resolve, 200))
      }
    }
  } catch (error) {
    console.error('Job polling error:', error.message)
  }
}

// Start automatic polling every 8 seconds
let pollingInterval
function startJobPolling() {
  console.log('🤖 Starting automatic job polling (every 8 seconds)...')
  pollingInterval = setInterval(pollProcessingJobs, 8000)
  // Run once immediately
  pollProcessingJobs()
}

// ==============================================================

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`API server running on port ${PORT}`)
  // Start automatic job polling
  startJobPolling()
})
