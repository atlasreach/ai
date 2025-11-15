import { useState } from 'react'

interface ContentItem {
  id: string
  character_id: string
  content_type: string
  status: string
  original_file_url: string
  face_swapped_url?: string
  video_url?: string
  caption?: string
  created_at: string
}

export default function Library() {
  const [selectedItem, setSelectedItem] = useState<ContentItem | null>(null)
  const [filterModel, setFilterModel] = useState('all')
  const [filterType, setFilterType] = useState('all')

  // Mock data - will be replaced with API call
  const mockItems: ContentItem[] = [
    {
      id: '1',
      character_id: 'milan',
      content_type: 'image',
      status: 'ready',
      original_file_url: 'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/1.jpg',
      face_swapped_url: 'https://replicate.delivery/yhqm/TzPMCd5lgcLSGZmm3a4JAgHNoz4L83T8OgYyxE4NHZLx2VaF/1763165380.jpg',
      caption: 'Beach vibes with Milan ☀️🌊',
      created_at: '2 hours ago'
    },
    {
      id: '2',
      character_id: 'skyler',
      content_type: 'video',
      status: 'ready',
      original_file_url: 'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/2.jpg',
      video_url: 'https://example.com/video.mp4',
      caption: 'Professional studio shoot 📸',
      created_at: '1 day ago'
    },
    {
      id: '3',
      character_id: 'milan',
      content_type: 'image',
      status: 'processing',
      original_file_url: 'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/3.jpg',
      created_at: 'Just now'
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Content Library</h1>
          <p className="text-gray-400">127 items • Showing 1-12</p>
        </div>
        <button className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg font-semibold hover:from-purple-600 hover:to-pink-600 transition-all">
          + Create New
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <input
          type="text"
          placeholder="🔍 Search..."
          className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
        />

        <select
          value={filterModel}
          onChange={(e) => setFilterModel(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="all">All Models</option>
          <option value="milan">Milan</option>
          <option value="skyler">Skyler</option>
          <option value="sara">Sara</option>
        </select>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="all">All Types</option>
          <option value="image">Images</option>
          <option value="video">Videos</option>
        </select>

        <button className="p-2 bg-slate-800 border border-slate-600 rounded-lg hover:bg-slate-700">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <button className="p-2 bg-purple-600 rounded-lg">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-4 gap-6">
        {mockItems.map((item) => (
          <div
            key={item.id}
            onClick={() => setSelectedItem(item)}
            className="bg-slate-800/50 backdrop-blur rounded-xl overflow-hidden border border-slate-700 hover:border-purple-500 transition-all cursor-pointer group"
          >
            <div className="aspect-square bg-slate-700 relative overflow-hidden">
              <img
                src={item.face_swapped_url || item.original_file_url}
                alt=""
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
              />
              {item.content_type === 'video' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                  <div className="w-16 h-16 bg-white/20 backdrop-blur rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </div>
                </div>
              )}
              {item.status === 'processing' && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                    <p className="text-sm">Processing...</p>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase text-gray-400">{item.character_id}</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  item.status === 'ready' ? 'bg-green-500/20 text-green-400' :
                  item.status === 'processing' ? 'bg-blue-500/20 text-blue-400' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {item.status === 'ready' ? '✓ Ready' :
                   item.status === 'processing' ? '⏳ Processing' :
                   'Draft'}
                </span>
              </div>

              {item.caption && (
                <p className="text-sm text-gray-300 mb-2 line-clamp-2">{item.caption}</p>
              )}

              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>{item.created_at}</span>
                <span className="uppercase">{item.content_type}</span>
              </div>

              <div className="flex gap-2 mt-3">
                <button className="flex-1 py-1.5 bg-purple-600 hover:bg-purple-700 rounded text-xs font-semibold">
                  📅 Schedule
                </button>
                <button className="flex-1 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs font-semibold">
                  ✏️ Edit
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selectedItem && (
        <div
          onClick={() => setSelectedItem(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-slate-800 rounded-xl max-w-5xl w-full max-h-[90vh] overflow-auto border border-slate-700"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold">{selectedItem.character_id.toUpperCase()}</h2>
                  <p className="text-gray-400">{selectedItem.created_at}</p>
                </div>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div className="col-span-2">
                  {selectedItem.content_type === 'video' ? (
                    <div className="aspect-video bg-slate-900 rounded-lg flex items-center justify-center">
                      <p className="text-gray-400">Video Player</p>
                    </div>
                  ) : (
                    <img
                      src={selectedItem.face_swapped_url || selectedItem.original_file_url}
                      alt=""
                      className="w-full rounded-lg"
                    />
                  )}

                  <div className="mt-4 space-y-3">
                    <div className="bg-slate-700/50 rounded-lg p-4">
                      <h3 className="font-semibold mb-2">💬 Caption</h3>
                      <p className="text-gray-300">{selectedItem.caption || 'No caption'}</p>
                      <button className="mt-2 text-sm text-purple-400 hover:text-purple-300">✏️ Edit Caption</button>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <h3 className="font-semibold mb-3">📊 Details</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Model:</span>
                        <span className="font-semibold">{selectedItem.character_id}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Type:</span>
                        <span>{selectedItem.content_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Status:</span>
                        <span className="text-green-400">✓ Ready</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <h3 className="font-semibold mb-3">✨ Operations</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-green-400">✅</span>
                        <span>Face swapped</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-green-400">✅</span>
                        <span>Video generated</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-green-400">✅</span>
                        <span>Caption created</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <button className="w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-lg font-semibold">
                      📅 Schedule Post
                    </button>
                    <button className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-semibold">
                      ⬇️ Download
                    </button>
                    <button className="w-full py-3 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg font-semibold">
                      🗑️ Delete
                    </button>
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
