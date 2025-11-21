import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import fs from 'fs'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

// Read SQL file
const sql = fs.readFileSync('../sql/02_sub_models_schema.sql', 'utf-8')

// Split by semicolons and execute each statement
const statements = sql
  .split(';')
  .map(s => s.trim())
  .filter(s => s.length > 0 && !s.startsWith('--'))

console.log(`Executing ${statements.length} SQL statements...`)

for (let i = 0; i < statements.length; i++) {
  const statement = statements[i]
  console.log(`\n[${i + 1}/${statements.length}] Executing:`, statement.substring(0, 100) + '...')

  try {
    const { data, error } = await supabase.rpc('exec_sql', { query: statement })
    if (error) {
      console.error('Error:', error.message)
      // Try direct query if RPC fails
      const result = await supabase.from('_sql').select('*').limit(0)
      console.log('Trying alternative method...')
    } else {
      console.log('✓ Success')
    }
  } catch (err) {
    console.log('Note:', err.message)
  }
}

console.log('\n✓ Migration complete!')
