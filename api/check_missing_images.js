import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('🔍 Finding completed jobs not in generated_images...\n')

// Get all completed jobs
const { data: completedJobs } = await supabase
  .from('generation_jobs')
  .select('id, result_image_url, created_at')
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

console.log(`Total completed jobs: ${completedJobs.length}`)
console.log(`Jobs in gallery: ${galleryImages.length}`)
console.log(`Missing from gallery: ${missingJobs.length}\n`)

if (missingJobs.length > 0) {
  console.log('Missing jobs:')
  missingJobs.forEach(job => {
    console.log(`  Job #${job.id} - ${new Date(job.created_at).toLocaleString()}`)
  })
}
