import { useState, useEffect } from 'react'
import { supabase } from './supabase'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

function getImageUrl(storagePath) {
  if (!storagePath) return ''
  return `${SUPABASE_URL}/storage/v1/object/public/reference-images/${storagePath}`
}

function App() {
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [referenceImages, setReferenceImages] = useState([])
  const [selectedImages, setSelectedImages] = useState([])
  const [generatedImages, setGeneratedImages] = useState([])
  const [loading, setLoading] = useState(false)

  // Fetch models on mount only
  useEffect(() => {
    fetchModels()
    fetchCategories()
  }, [])

  // Fetch reference images when model or category changes
  useEffect(() => {
    if (selectedModel) {
      fetchReferenceImages()
    }
  }, [selectedModel, selectedCategory])

  async function fetchModels() {
    const { data } = await supabase
      .from('models')
      .select('*')
      .order('name')

    setModels(data || [])
    if (data && data.length > 0) {
      setSelectedModel(data[0])
    }
  }

  async function fetchCategories() {
    const { data } = await supabase
      .from('reference_images')
      .select('category')

    const uniqueCategories = [...new Set(data?.map(r => r.category) || [])]
    setCategories(uniqueCategories)
  }

  async function fetchReferenceImages() {
    let query = supabase
      .from('reference_images')
      .select('*')
      .order('created_at', { ascending: false })

    if (selectedCategory !== 'all') {
      query = query.eq('category', selectedCategory)
    }

    const { data } = await query
    setReferenceImages(data || [])
  }

  async function fetchGeneratedImages() {
    if (!selectedModel) return

    const { data } = await supabase
      .from('generated_images')
      .select(`
        *,
        reference_images (*)
      `)
      .eq('model_id', selectedModel.id)
      .order('created_at', { ascending: false })

    setGeneratedImages(data || [])
  }

  function toggleImageSelection(image) {
    setSelectedImages(prev => {
      const exists = prev.find(img => img.id === image.id)
      if (exists) {
        return prev.filter(img => img.id !== image.id)
      }
      return [...prev, image]
    })
  }

  async function handleRunGeneration() {
    if (selectedImages.length === 0 || !selectedModel) return

    setLoading(true)
    // TODO: Call backend API to queue ComfyUI generations
    alert(`Queuing ${selectedImages.length} generations for ${selectedModel.name}`)
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 py-2">
          <h1 className="text-xl font-bold">AI Model Generator</h1>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-4">
        {/* Models Selection */}
        <section className="mb-4">
          <h2 className="text-lg font-semibold mb-2">Select Model</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {models.map(model => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model)}
                className={`p-3 rounded-lg border-2 transition-all ${
                  selectedModel?.id === model.id
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
                }`}
              >
                <h3 className="text-base font-semibold">{model.name}</h3>
                <p className="text-xs text-gray-400 mt-0.5">{model.hair_style}</p>
                <p className="text-xs text-gray-500">{model.skin_tone} skin</p>
              </button>
            ))}
          </div>
        </section>

        {selectedModel && (
          <>
            {/* Category Filter */}
            <section className="mb-4">
              <h2 className="text-lg font-semibold mb-2">Category</h2>
              <div className="flex gap-1.5 flex-wrap">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                    selectedCategory === 'all'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  All
                </button>
                {categories.map(category => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-all ${
                      selectedCategory === category
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-800 hover:bg-gray-700'
                    }`}
                  >
                    {category.replace(/-/g, ' ')}
                  </button>
                ))}
              </div>
            </section>

            {/* Reference Images Grid */}
            <section className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-lg font-semibold">
                  Reference Images ({referenceImages.length})
                </h2>
                {selectedImages.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">
                      {selectedImages.length} selected
                    </span>
                    <button
                      onClick={handleRunGeneration}
                      disabled={loading}
                      className="px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold disabled:opacity-50"
                    >
                      {loading ? 'Processing...' : 'Run Generation'}
                    </button>
                    <button
                      onClick={() => setSelectedImages([])}
                      className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {referenceImages.map(image => (
                  <div
                    key={image.id}
                    onClick={() => toggleImageSelection(image)}
                    className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                      selectedImages.find(img => img.id === image.id)
                        ? 'border-blue-500 ring-2 ring-blue-500/50'
                        : 'border-transparent hover:border-gray-600'
                    }`}
                  >
                    <img
                      src={getImageUrl(image.storage_path)}
                      alt={image.filename}
                      className="w-full aspect-square object-cover"
                    />
                    {selectedImages.find(img => img.id === image.id) && (
                      <div className="absolute top-1 right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                    {image.vision_description && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm p-1">
                        <p className="text-xs text-gray-300 line-clamp-2">
                          {image.vision_description}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {referenceImages.length === 0 && (
                <div className="text-center py-8 text-sm text-gray-500">
                  No reference images found for this category
                </div>
              )}
            </section>

            {/* Generated Images Section */}
            <section>
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-lg font-semibold">Generated Images</h2>
                <button
                  onClick={fetchGeneratedImages}
                  className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
                >
                  Refresh
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {generatedImages.map(gen => (
                  <div key={gen.id} className="bg-gray-800/50 rounded-lg overflow-hidden border border-gray-700">
                    <div className="grid grid-cols-2 gap-px">
                      {/* Reference Image */}
                      <div className="relative">
                        <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-black/60 rounded text-xs">
                          Reference
                        </div>
                        <img
                          src={getImageUrl(gen.reference_images?.storage_path)}
                          alt="Reference"
                          className="w-full aspect-square object-cover"
                        />
                      </div>
                      {/* Generated Image */}
                      <div className="relative">
                        <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-blue-600/80 rounded text-xs">
                          Generated
                        </div>
                        <img
                          src={gen.storage_path}
                          alt="Generated"
                          className="w-full aspect-square object-cover"
                        />
                      </div>
                    </div>
                    <div className="p-2">
                      <p className="text-xs text-gray-400 line-clamp-2">
                        {gen.prompt_used}
                      </p>
                      <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
                        <span>{gen.status}</span>
                        <span>{new Date(gen.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {generatedImages.length === 0 && (
                <div className="text-center py-8 text-sm text-gray-500">
                  No generated images yet. Select reference images and click "Run Generation"
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}

export default App
