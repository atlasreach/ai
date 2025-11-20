import { useState, useEffect } from 'react'
import { supabase } from '../supabase'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

// Detect API URL for Codespaces
function getApiUrl() {
  const url = window.location.origin
  console.log('window.location.origin:', url)
  console.log('VITE_API_URL:', import.meta.env.VITE_API_URL)

  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  // For Codespaces, replace port 5173 with 3001
  if (url.includes('app.github.dev')) {
    const apiUrl = url.replace('-5173.app.github.dev', '-3001.app.github.dev')
    console.log('Detected Codespaces, API URL:', apiUrl)
    return apiUrl
  }
  return 'http://localhost:3001'
}

const API_URL = getApiUrl()

console.log('Final API URL:', API_URL)

function getImageUrl(storagePath) {
  if (!storagePath) return ''
  return `${SUPABASE_URL}/storage/v1/object/public/reference-images/${storagePath}`
}

export default function Generate() {
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [uploadedImage, setUploadedImage] = useState(null)
  const [uploadedImageFilename, setUploadedImageFilename] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [toasts, setToasts] = useState([])

  // Reference images state
  const [referenceImages, setReferenceImages] = useState([])
  const [selectedImages, setSelectedImages] = useState([]) // Changed to array for multi-select
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('all')

  // Workflow parameters
  const [params, setParams] = useState({
    denoise: 0.75,
    cfg: 3.8,
    steps: 28,
    seed: -1,
    lora_strength: 0.65,
    variations: 1, // New: how many versions per image
    positive_prompt_suffix: 'bikini, professional photo, ultra detailed skin, sharp focus, 8k, photorealistic masterpiece',
    negative_prompt_suffix: 'blurry, deformed, bad anatomy'
  })

  // Fetch initial data
  useEffect(() => {
    fetchModels()
    fetchWorkflows()
    fetchJobs()
    fetchReferenceImages()
  }, [])

  // Auto-polling: refresh jobs every 5 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      const oldJobs = jobs
      await fetchJobs()

      // Check status of processing jobs
      jobs.filter(job => job.status === 'processing').forEach(job => {
        checkJobStatus(job.id)
      })

      // Show toast for newly completed jobs
      const newCompletedJobs = jobs.filter(job =>
        job.status === 'completed' &&
        !oldJobs.find(old => old.id === job.id && old.status === 'completed')
      )

      if (newCompletedJobs.length > 0) {
        showToast(`✅ ${newCompletedJobs.length} image${newCompletedJobs.length > 1 ? 's' : ''} generated!`, 'success')
      }
    }, 5000) // 5 seconds

    return () => clearInterval(interval)
  }, [jobs])

  // Toast notification helper
  function showToast(message, type = 'info') {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id))
    }, 4000)
  }

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

  async function fetchWorkflows() {
    try {
      const response = await fetch(`${API_URL}/api/workflows`)
      const data = await response.json()
      setWorkflows(data || [])
      if (data && data.length > 0) {
        setSelectedWorkflow(data[0])
      }
    } catch (error) {
      console.error('Failed to fetch workflows:', error)
    }
  }

  async function fetchReferenceImages() {
    try {
      const { data } = await supabase
        .from('reference_images')
        .select('*')
        .not('vision_description', 'is', null)
        .order('filename')

      setReferenceImages(data || [])

      // Extract unique categories
      const uniqueCategories = [...new Set((data || []).map(img => img.category))]
      setCategories(uniqueCategories)
    } catch (error) {
      console.error('Failed to fetch reference images:', error)
    }
  }

  // Filter reference images by category
  const filteredReferenceImages = selectedCategory === 'all'
    ? referenceImages
    : referenceImages.filter(img => img.category === selectedCategory)

  async function handleImageUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('image', file)

      const response = await fetch(`${API_URL}/api/upload-image`, {
        method: 'POST',
        body: formData
      })

      const result = await response.json()

      if (result.success) {
        setUploadedImage(URL.createObjectURL(file))
        setUploadedImageFilename(result.filename)
      } else {
        alert(`Upload failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Upload error: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function fetchJobs() {
    try {
      const response = await fetch(`${API_URL}/api/jobs`)
      const data = await response.json()
      setJobs(data || [])
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    }
  }

  async function handleGenerate() {
    if (!selectedModel || !selectedWorkflow || selectedImages.length === 0) {
      alert('Please select a model, workflow, and at least one reference image')
      return
    }

    setLoading(true)
    let totalJobs = 0
    let successfulJobs = 0

    try {
      // Process each selected image
      for (const selectedImage of selectedImages) {
        // Download reference image from Supabase Storage
        const { data: imageData, error: downloadError } = await supabase.storage
          .from('reference-images')
          .download(selectedImage.storage_path)

        if (downloadError) {
          console.error(`Failed to download ${selectedImage.filename}:`, downloadError)
          continue
        }

        // Upload to ComfyUI
        const formData = new FormData()
        formData.append('image', imageData, selectedImage.filename)

        const uploadResponse = await fetch(`${API_URL}/api/upload-image`, {
          method: 'POST',
          body: formData
        })

        const uploadResult = await uploadResponse.json()

        if (!uploadResult.success) {
          console.error(`Upload failed for ${selectedImage.filename}:`, uploadResult.error)
          continue
        }

        // Submit multiple variations for this image
        for (let i = 0; i < params.variations; i++) {
          totalJobs++

          const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              modelId: selectedModel.id,
              workflowSlug: selectedWorkflow.slug,
              uploadedImageFilename: uploadResult.filename,
              parameters: {
                ...params,
                seed: -1, // Always random seed for variations
                positive_prompt_suffix: selectedImage.vision_description || params.positive_prompt_suffix
              }
            })
          })

          const result = await response.json()

          if (result.success) {
            successfulJobs++
          } else {
            console.error(`Generation failed:`, result.error)
          }
        }
      }

      alert(`✅ Submitted ${successfulJobs}/${totalJobs} jobs!\n\n${selectedImages.length} images × ${params.variations} variations = ${totalJobs} total jobs`)
      fetchJobs()

    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function checkJobStatus(jobId) {
    try {
      const response = await fetch(`${API_URL}/api/jobs/${jobId}/check`, {
        method: 'POST'
      })
      const result = await response.json()

      if (result.status === 'completed' || result.status === 'failed') {
        fetchJobs()
      }

      return result
    } catch (error) {
      console.error('Failed to check job status:', error)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - Configuration */}
          <div className="lg:col-span-2 space-y-4">
            {/* Model Selection */}
            <section className="bg-gray-900/50 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-3">1. Select Model</h2>
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

            {/* Workflow Selection */}
            <section className="bg-gray-900/50 rounded-lg p-4">
              <h2 className="text-lg font-semibold mb-3">2. Select Workflow</h2>
              <div className="grid grid-cols-1 gap-2">
                {workflows.map(workflow => (
                  <button
                    key={workflow.id}
                    onClick={() => setSelectedWorkflow(workflow)}
                    className={`p-3 rounded-lg border-2 transition-all text-left ${
                      selectedWorkflow?.id === workflow.id
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
                    }`}
                  >
                    <h3 className="font-semibold">{workflow.name}</h3>
                    <p className="text-sm text-gray-400 mt-1">{workflow.description}</p>
                  </button>
                ))}
              </div>
            </section>

            {/* Category Filter & Reference Images */}
            {selectedModel && (
              <section className="bg-gray-900/50 rounded-lg p-4">
                <h2 className="text-lg font-semibold mb-3">3. Select Reference Image</h2>

                <div className="flex gap-1.5 flex-wrap mb-3">
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

                <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                  {filteredReferenceImages.map(image => {
                    const isSelected = selectedImages.some(img => img.id === image.id)
                    return (
                      <div
                        key={image.id}
                        onClick={() => {
                          if (isSelected) {
                            setSelectedImages(selectedImages.filter(img => img.id !== image.id))
                          } else {
                            setSelectedImages([...selectedImages, image])
                          }
                        }}
                        className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                          isSelected
                            ? 'border-blue-500 ring-2 ring-blue-500/50'
                            : 'border-transparent hover:border-gray-600'
                        }`}
                      >
                        <img
                          src={getImageUrl(image.storage_path)}
                          alt={image.filename}
                          className="w-full aspect-square object-cover"
                        />
                        {isSelected && (
                          <div className="absolute top-1 right-1 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Show selection summary */}
                {selectedImages.length > 0 && (
                  <div className="mt-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-sm font-semibold text-blue-400">
                        {selectedImages.length} image{selectedImages.length > 1 ? 's' : ''} selected
                      </h3>
                      <button
                        onClick={() => setSelectedImages([])}
                        className="text-xs text-gray-400 hover:text-white"
                      >
                        Clear all
                      </button>
                    </div>
                    {selectedImages.length === 1 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Grok Vision Caption:</p>
                        <p className="text-sm text-gray-300">{selectedImages[0].vision_description}</p>
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}

            {/* Parameters */}
            {selectedWorkflow && (
              <section className="bg-gray-900/50 rounded-lg p-4">
                <h2 className="text-lg font-semibold mb-3">4. Adjust Parameters</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Denoise Strength: {params.denoise}
                    </label>
                    <input
                      type="range"
                      min="0.5"
                      max="1.0"
                      step="0.05"
                      value={params.denoise}
                      onChange={(e) => setParams({...params, denoise: parseFloat(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      CFG Scale: {params.cfg}
                    </label>
                    <input
                      type="range"
                      min="1.0"
                      max="15.0"
                      step="0.1"
                      value={params.cfg}
                      onChange={(e) => setParams({...params, cfg: parseFloat(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Steps: {params.steps}
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="50"
                      step="1"
                      value={params.steps}
                      onChange={(e) => setParams({...params, steps: parseInt(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      LoRA Strength: {params.lora_strength}
                    </label>
                    <input
                      type="range"
                      min="0.3"
                      max="1.0"
                      step="0.05"
                      value={params.lora_strength}
                      onChange={(e) => setParams({...params, lora_strength: parseFloat(e.target.value)})}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Variations per image: {params.variations}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="5"
                      step="1"
                      value={params.variations}
                      onChange={(e) => setParams({...params, variations: parseInt(e.target.value)})}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {selectedImages.length} image{selectedImages.length !== 1 ? 's' : ''} × {params.variations} variation{params.variations !== 1 ? 's' : ''} = {selectedImages.length * params.variations} total jobs
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-1">
                      Seed (-1 for random)
                    </label>
                    <input
                      type="number"
                      value={params.seed}
                      onChange={(e) => setParams({...params, seed: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-800 rounded-lg border border-gray-700"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-1">
                      Additional Positive Prompt
                    </label>
                    <textarea
                      value={params.positive_prompt_suffix}
                      onChange={(e) => setParams({...params, positive_prompt_suffix: e.target.value})}
                      className="w-full px-3 py-2 bg-gray-800 rounded-lg border border-gray-700"
                      rows="2"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-1">
                      Additional Negative Prompt
                    </label>
                    <textarea
                      value={params.negative_prompt_suffix}
                      onChange={(e) => setParams({...params, negative_prompt_suffix: e.target.value})}
                      className="w-full px-3 py-2 bg-gray-800 rounded-lg border border-gray-700"
                      rows="2"
                    />
                  </div>
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={loading || !selectedModel || !selectedWorkflow || selectedImages.length === 0}
                  className="w-full mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Submitting...' : `🚀 Generate ${selectedImages.length * params.variations} Image${selectedImages.length * params.variations !== 1 ? 's' : ''}`}
                </button>
              </section>
            )}
          </div>

          {/* Right Column - Job Queue */}
          <div className="lg:col-span-1">
            <section className="bg-gray-900/50 rounded-lg p-4 sticky top-20">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold">Generation Queue</h2>
                <button
                  onClick={fetchJobs}
                  className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
                >
                  Refresh
                </button>
              </div>

              <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
                {jobs.length === 0 && (
                  <div className="text-center py-8 text-sm text-gray-500">
                    No jobs yet. Start generating!
                  </div>
                )}

                {jobs.map(job => (
                  <div
                    key={job.id}
                    className="bg-gray-800/50 rounded-lg p-3 border border-gray-700"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-semibold text-sm">{job.models?.name}</h3>
                        <p className="text-xs text-gray-400">{job.workflows?.name}</p>
                      </div>
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        job.status === 'processing' ? 'bg-blue-500/20 text-blue-400' :
                        job.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {job.status}
                      </span>
                    </div>

                    {job.reference_images?.storage_path && (
                      <img
                        src={getImageUrl(job.reference_images.storage_path)}
                        alt="Reference"
                        className="w-full aspect-square object-cover rounded mt-2"
                      />
                    )}

                    {job.result_image_url && (
                      <img
                        src={job.result_image_url}
                        alt="Generated"
                        className="w-full aspect-square object-cover rounded mt-2"
                      />
                    )}

                    {job.status === 'processing' && (
                      <button
                        onClick={() => checkJobStatus(job.id)}
                        className="w-full mt-2 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded"
                      >
                        Check Status
                      </button>
                    )}

                    {job.error_message && (
                      <p className="text-xs text-red-400 mt-2">{job.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>

        {/* Toast Notifications */}
        <div className="fixed bottom-4 right-4 z-50 space-y-2">
          {toasts.map(toast => (
            <div
              key={toast.id}
              className={`px-4 py-3 rounded-lg shadow-lg border backdrop-blur-sm animate-slide-in ${
                toast.type === 'success'
                  ? 'bg-green-900/90 border-green-500 text-green-100'
                  : toast.type === 'error'
                  ? 'bg-red-900/90 border-red-500 text-red-100'
                  : 'bg-blue-900/90 border-blue-500 text-blue-100'
              }`}
            >
              {toast.message}
            </div>
          ))}
        </div>
      </div>
  )
}
