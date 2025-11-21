import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('📋 Inspecting generated_images table...\n')

// Try to insert a test row to see what columns exist
const testData = {
  id: 999999,
  model_id: 1,
  job_id: 1,
  image_url: 'test',
  prompt_used: 'test',
  negative_prompt_used: 'test',
  parameters: {},
  reference_image_id: 1
}

const { data, error } = await supabase
  .from('generated_images')
  .insert(testData)
  .select()

if (error) {
  console.log('Error reveals which columns exist:')
  console.log(error.message)

  // Try simpler structure
  console.log('\nTrying minimal insert...')
  const { data: data2, error: error2 } = await supabase
    .from('generated_images')
    .insert({})
    .select()

  if (error2) {
    console.log('Minimal error:', error2.message)
  }
} else {
  console.log('✅ Test insert succeeded! Columns:', Object.keys(data[0]))

  // Delete test row
  await supabase.from('generated_images').delete().eq('id', 999999)
}
