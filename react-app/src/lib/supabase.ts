import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://yiriqesejsbzmzxdxiqt.supabase.co'
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlpcmlxZXNlanNiem16eGR4aXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxNTA2MjUsImV4cCI6MjA3ODcyNjYyNX0.Ii8uNcc5X3lxt8PCt2VpmEQl2pyECgHRVklUfky7DEk'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
