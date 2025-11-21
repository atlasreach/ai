import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('📋 Checking all tables...\n')

// Check if generated_images table exists
try {
  const { data, error, count } = await supabase
    .from('generated_images')
    .select('*', { count: 'exact' })
    .limit(5)

  if (error) {
    console.log('❌ generated_images table: DOES NOT EXIST or NO ACCESS')
    console.log('   Error:', error.message)
  } else {
    console.log('✅ generated_images table EXISTS')
    console.log(`   Total rows: ${count}`)
    if (data.length > 0) {
      console.log('   Sample columns:', Object.keys(data[0]))
    }
  }
} catch (e) {
  console.log('❌ generated_images:', e.message)
}

console.log('\n📊 generation_jobs table structure:')
const { data: jobSample } = await supabase
  .from('generation_jobs')
  .select('*')
  .limit(1)

if (jobSample && jobSample[0]) {
  console.log('   Columns:', Object.keys(jobSample[0]).join(', '))
  console.log('\n   Sample job:')
  console.log('   - ID:', jobSample[0].id)
  console.log('   - Status:', jobSample[0].status)
  console.log('   - result_image_url:', jobSample[0].result_image_url ? 'HAS URL' : 'NO URL')
  console.log('   - prompt_used:', jobSample[0].prompt_used ? 'HAS PROMPT' : 'NO PROMPT')
  console.log('   - parameters:', jobSample[0].parameters ? 'HAS PARAMS' : 'NO PARAMS')
}
