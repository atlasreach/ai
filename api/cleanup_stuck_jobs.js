import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('Marking stuck processing jobs as failed...')

const { data, error } = await supabase
  .from('generation_jobs')
  .update({
    status: 'failed',
    error_message: 'Job was killed in ComfyUI'
  })
  .eq('status', 'processing')
  .select()

if (error) {
  console.error('Error:', error)
} else {
  console.log(`✅ Marked ${data.length} jobs as failed`)
}
