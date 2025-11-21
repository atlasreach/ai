import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('🔄 Backfilling missing images into gallery...\n')

// Get all completed jobs
const { data: completedJobs } = await supabase
  .from('generation_jobs')
  .select('*, models(name, slug), reference_images(filename, vision_description)')
  .eq('status', 'completed')
  .not('result_image_url', 'is', null)
  .order('created_at', { ascending: false })

// Get all job_ids in generated_images
const { data: galleryImages } = await supabase
  .from('generated_images')
  .select('job_id')

const existingJobIds = new Set(galleryImages.map(img => img.job_id))

// Find missing jobs
const missingJobs = completedJobs.filter(job => !existingJobIds.has(job.id))

console.log(`Missing ${missingJobs.length} jobs from gallery\n`)

// Backfill each missing job
for (const job of missingJobs) {
  console.log(`Backfilling Job #${job.id}...`)

  // Extract storage path from URL
  let storagePath = null
  if (job.result_image_url) {
    const match = job.result_image_url.match(/\/([^/]+)\.png$/)
    if (match) {
      storagePath = `${match[1]}.png`
    }
  }

  const { error } = await supabase
    .from('generated_images')
    .insert({
      job_id: job.id,
      model_id: job.model_id,
      reference_image_id: job.reference_image_id,
      image_url: job.result_image_url,
      storage_path: storagePath,
      prompt_used: job.prompt_used,
      negative_prompt_used: job.negative_prompt_used,
      parameters: job.parameters,
      model_name: job.models?.name,
      model_slug: job.models?.slug,
      reference_filename: job.reference_images?.filename,
      reference_caption: job.reference_images?.vision_description,
      generated_at: job.completed_at,
      created_at: job.created_at
    })

  if (error) {
    console.log(`  ❌ Error: ${error.message}`)
  } else {
    console.log(`  ✅ Added to gallery`)
  }
}

console.log('\n✨ Done!')
