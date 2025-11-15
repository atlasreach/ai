import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

interface Model {
  id: string
  name: string
  thumbnail_url: string | null
  description: string
}

interface GalleryImage {
  id: string
  image_url: string
  caption: string | null
}

export default function Models() {
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([])
  const [loading, setLoading] = useState(true)
  const [imageCount, setImageCount] = useState(0)

  // Fetch models directly from Supabase
  useEffect(() => {
    async function fetchModels() {
      try {
        const { data, error } = await supabase
          .from('characters')
          .select('*')
          .eq('is_active', true)
          .order('name')

        if (error) throw error

        setModels(data || [])
        if (data && data.length > 0) {
          setSelectedModel(data[0].id)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchModels()
  }, [])

  // Fetch gallery images when model is selected
  useEffect(() => {
    async function fetchGallery() {
      if (!selectedModel) return

      try {
        const { data, error } = await supabase
          .from('model_gallery')
          .select('*')
          .eq('character_id', selectedModel)
          .order('display_order')

        if (error) throw error

        setGalleryImages(data || [])
        setImageCount(data?.length || 0)
      } catch (error) {
        console.error('Failed to load gallery:', error)
      }
    }

    fetchGallery()
  }, [selectedModel])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading models...</div>
      </div>
    )
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-12rem)]">
      {/* Left Sidebar - Model List */}
      <div className="w-64 flex-shrink-0">
        <h2 className="text-xl font-bold mb-4">Models</h2>
        <div className="space-y-2">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => setSelectedModel(model.id)}
              className={`w-full p-4 rounded-lg text-left transition-all ${
                selectedModel === model.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 hover:bg-slate-700 text-gray-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-slate-700 rounded-lg overflow-hidden flex-shrink-0">
                  {model.thumbnail_url ? (
                    <img src={model.thumbnail_url} alt={model.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-2xl">
                      👤
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold truncate">{model.name}</div>
                  <div className="text-xs opacity-75">
                    {selectedModel === model.id ? `${imageCount} images` : 'View gallery'}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right Panel - Image Gallery */}
      <div className="flex-1 bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 p-6 overflow-y-auto">
        {selectedModel && (
          <>
            <div className="mb-6">
              <h2 className="text-2xl font-bold mb-1">
                {models.find(m => m.id === selectedModel)?.name}
              </h2>
              <p className="text-gray-400">
                {galleryImages.length} training images
              </p>
            </div>

            <div className="grid grid-cols-4 gap-4">
              {galleryImages.map((image) => (
                <div
                  key={image.id}
                  className="aspect-square bg-slate-700 rounded-lg overflow-hidden hover:ring-2 hover:ring-purple-500 transition-all cursor-pointer group relative"
                >
                  <img
                    src={image.image_url}
                    alt={image.caption || 'Training image'}
                    className="w-full h-full object-cover"
                  />
                  {image.caption && (
                    <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity p-2 overflow-y-auto">
                      <p className="text-xs text-gray-300">{image.caption}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {galleryImages.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                No images found for this model
              </div>
            )}
          </>
        )}

        {!selectedModel && (
          <div className="text-center py-12 text-gray-400">
            Select a model to view images
          </div>
        )}
      </div>
    </div>
  )
}
