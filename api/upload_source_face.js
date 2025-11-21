import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import fs from 'fs'

dotenv.config()

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
)

console.log('📤 Uploading source.jpg to Supabase...\n')

async function uploadSourceFace() {
  try {
    // Read the source.jpg file
    const fileBuffer = fs.readFileSync('../source.jpg')

    // Upload to face-sources bucket
    const { data, error } = await supabase.storage
      .from('face-sources')
      .upload('source.jpg', fileBuffer, {
        contentType: 'image/jpeg',
        upsert: true
      })

    if (error) {
      console.error('❌ Upload error:', error.message)

      // Try creating the bucket first
      if (error.message.includes('not found')) {
        console.log('Creating face-sources bucket...')
        const { error: bucketError } = await supabase.storage.createBucket('face-sources', {
          public: true
        })

        if (bucketError) {
          console.error('❌ Bucket creation error:', bucketError)
          return
        }

        // Retry upload
        const { error: retryError } = await supabase.storage
          .from('face-sources')
          .upload('source.jpg', fileBuffer, {
            contentType: 'image/jpeg',
            upsert: true
          })

        if (retryError) {
          console.error('❌ Retry upload error:', retryError)
          return
        }
      } else {
        return
      }
    }

    // Get public URL
    const { data: publicUrlData } = supabase.storage
      .from('face-sources')
      .getPublicUrl('source.jpg')

    console.log('✅ Source face uploaded successfully!')
    console.log('📍 URL:', publicUrlData.publicUrl)
  } catch (err) {
    console.error('❌ Error:', err.message)
  }
}

uploadSourceFace()
