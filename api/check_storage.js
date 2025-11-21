import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('📦 Checking generated-images bucket...\n')

const { data: files, error } = await supabase.storage
  .from('generated-images')
  .list('', {
    limit: 100,
    offset: 0,
    sortBy: { column: 'created_at', order: 'desc' }
  })

if (error) {
  console.error('Error:', error)
} else {
  console.log(`Found ${files.length} files in bucket`)
  if (files.length > 0) {
    console.log('\nMost recent files:')
    files.slice(0, 10).forEach(file => {
      console.log(`  - ${file.name} (${Math.round(file.metadata?.size / 1024)}KB)`)
    })
  }
}

console.log('\n📊 Checking completed jobs...\n')

const { data: completedJobs, error: jobError } = await supabase
  .from('generation_jobs')
  .select('id, status, result_image_url, created_at')
  .eq('status', 'completed')
  .order('created_at', { ascending: false })
  .limit(10)

if (jobError) {
  console.error('Error:', jobError)
} else {
  console.log(`Found ${completedJobs.length} completed jobs`)
  completedJobs.forEach(job => {
    console.log(`  Job #${job.id}: ${job.result_image_url ? '✅ Has image' : '❌ No image'}`)
  })
}
