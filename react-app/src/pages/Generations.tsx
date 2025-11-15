import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

interface Generation {
  id: string
  character_id: string | null
  content_type: string
  original_file_url: string
  face_swapped_url: string | null
  video_url: string | null
  created_at: string
}

interface Model {
  id: string
  name: string
}

export default function Generations() {
  const [generations, setGenerations] = useState<Generation[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('all')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [viewingMedia, setViewingMedia] = useState<Generation | null>(null)

  // Fetch models for filter
  useEffect(() => {
    async function fetchModels() {
      try {
        const { data, error } = await supabase
          .from('characters')
          .select('id, name')
          .eq('is_active', true)
          .order('name')

        if (error) throw error
        setModels(data || [])
      } catch (error) {
        console.error('Failed to load models:', error)
      }
    }

    fetchModels()
  }, [])

  // Fetch generations
  useEffect(() => {
    async function fetchGenerations() {
      try {
        let query = supabase
          .from('content_items')
          .select('*')
          .order('created_at', { ascending: false })

        // Filter by model if selected
        if (selectedModel !== 'all') {
          query = query.eq('character_id', selectedModel)
        }

        // Filter by type if selected
        if (selectedType !== 'all') {
          query = query.eq('content_type', selectedType)
        }

        const { data, error } = await query

        if (error) throw error
        setGenerations(data || [])

        // Auto-refresh if there are processing items
        const hasProcessing = data?.some(g => g.status === 'processing')
        if (hasProcessing) {
          setTimeout(fetchGenerations, 10000) // Refresh every 10 seconds
        }
      } catch (error) {
        console.error('Failed to load generations:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchGenerations()
  }, [selectedModel, selectedType])

  const getDisplayUrl = (gen: Generation) => {
    return gen.face_swapped_url || gen.video_url || gen.original_file_url
  }

  const isVideo = (gen: Generation) => {
    return gen.content_type === 'reel' || gen.content_type === 'video' || gen.video_url !== null
  }

  const getModelName = (characterId: string | null) => {
    if (!characterId) return 'No Model'
    const model = models.find(m => m.id === characterId)
    return model?.name || characterId
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading generations...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Generations</h1>
        <p className="text-gray-400">View all your generated content</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-2">Filter by Model</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">All Models</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1">
          <label className="block text-sm font-medium mb-2">Filter by Type</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="all">All Types</option>
            <option value="face_swap">Face Swap</option>
            <option value="video">Video</option>
            <option value="reel">Reel</option>
          </select>
        </div>
      </div>

      {/* Generations Grid */}
      {generations.length > 0 ? (
        <div className="grid grid-cols-4 gap-4">
          {generations.map((gen) => (
            <div
              key={gen.id}
              className="bg-slate-800/50 backdrop-blur rounded-lg border border-slate-700 overflow-hidden hover:ring-2 hover:ring-purple-500 transition-all cursor-pointer group"
              onClick={() => setViewingMedia(gen)}
            >
              {/* Media Display */}
              <div className="aspect-square bg-slate-700 relative">
                {gen.status === 'processing' ? (
                  <div className="w-full h-full flex items-center justify-center bg-slate-800">
                    <div className="text-center">
                      <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mb-3"></div>
                      <div className="text-sm text-gray-400">Processing...</div>
                    </div>
                  </div>
                ) : gen.status === 'failed' ? (
                  <div className="w-full h-full flex items-center justify-center bg-red-900/20">
                    <div className="text-center">
                      <div className="text-4xl mb-2">❌</div>
                      <div className="text-sm text-red-400">Failed</div>
                    </div>
                  </div>
                ) : isVideo(gen) ? (
                  <>
                    <video
                      src={gen.video_url || ''}
                      className="w-full h-full object-cover"
                      preload="metadata"
                    />
                    {/* Play Button Overlay */}
                    <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/50 transition-colors">
                      <div className="w-16 h-16 rounded-full bg-purple-600 flex items-center justify-center">
                        <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </div>
                    </div>
                  </>
                ) : (
                  <img
                    src={getDisplayUrl(gen)}
                    alt="Generation"
                    className="w-full h-full object-cover"
                  />
                )}
                {/* Status Badge */}
                <div className={`absolute top-2 right-2 px-2 py-1 rounded text-xs font-semibold ${
                  gen.status === 'processing' ? 'bg-blue-600' :
                  gen.status === 'failed' ? 'bg-red-600' :
                  'bg-black/70'
                }`}>
                  {gen.status === 'processing' ? '⏳ Processing' :
                   gen.status === 'failed' ? '❌ Failed' :
                   gen.content_type}
                </div>
              </div>

              {/* Info */}
              <div className="p-3">
                <div className="text-sm font-semibold mb-1">
                  {getModelName(gen.character_id)}
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(gen.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="text-4xl mb-4">📭</div>
          <p className="text-gray-400 mb-2">No generations yet</p>
          <p className="text-sm text-gray-500">
            Create your first face swap in the Tools page
          </p>
        </div>
      )}

      {/* Media Viewer Modal */}
      {viewingMedia && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-8"
          onClick={() => setViewingMedia(null)}
        >
          <div
            className="relative max-w-6xl max-h-full"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              onClick={() => setViewingMedia(null)}
              className="absolute -top-12 right-0 text-white hover:text-gray-300 text-xl font-bold"
            >
              ✕ Close
            </button>

            {/* Media Content */}
            <div className="bg-slate-900 rounded-lg overflow-hidden">
              {isVideo(viewingMedia) ? (
                <video
                  src={viewingMedia.video_url || ''}
                  controls
                  autoPlay
                  className="max-w-full max-h-[80vh]"
                />
              ) : (
                <img
                  src={getDisplayUrl(viewingMedia)}
                  alt="Generation"
                  className="max-w-full max-h-[80vh]"
                />
              )}

              {/* Info Panel */}
              <div className="p-6 bg-slate-800">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Model</div>
                    <div className="font-semibold">{getModelName(viewingMedia.character_id)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Type</div>
                    <div className="font-semibold capitalize">{viewingMedia.content_type}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400 mb-1">Created</div>
                    <div className="font-semibold">
                      {new Date(viewingMedia.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-end">
                    <a
                      href={getDisplayUrl(viewingMedia)}
                      download
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-semibold transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Download
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
