import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

interface Model {
  id: string
  name: string
  thumbnail_url: string | null
}

interface LibraryImage {
  id: string
  url: string
  type: 'gallery' | 'generation'
  character_id?: string
}

export default function Tools() {
  const [selectedTool, setSelectedTool] = useState('face-swap')
  const [models, setModels] = useState<Model[]>([])
  const [selectedModel, setSelectedModel] = useState('')

  // Image selection mode
  const [targetMode, setTargetMode] = useState<'upload' | 'library'>('upload')
  const [sourceMode, setSourceMode] = useState<'upload' | 'library'>('upload')

  // File uploads
  const [targetFile, setTargetFile] = useState<File | null>(null)
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const [targetPreview, setTargetPreview] = useState<string | null>(null)
  const [sourcePreview, setSourcePreview] = useState<string | null>(null)

  // Library selection
  const [targetUrl, setTargetUrl] = useState<string | null>(null)
  const [sourceUrl, setSourceUrl] = useState<string | null>(null)
  const [libraryImages, setLibraryImages] = useState<LibraryImage[]>([])
  const [loadingLibrary, setLoadingLibrary] = useState(false)

  const [resultImage, setResultImage] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reel generation (from face swap)
  const [showReelCreator, setShowReelCreator] = useState(false)
  const [reelMode, setReelMode] = useState('standard')
  const [reelDuration, setReelDuration] = useState(5)
  const [reelPrompt, setReelPrompt] = useState('')
  const [reelNegativePrompt, setReelNegativePrompt] = useState('')
  const [generatingPrompts, setGeneratingPrompts] = useState(false)
  const [reelProcessing, setReelProcessing] = useState(false)
  const [reelResult, setReelResult] = useState<string | null>(null)

  // Standalone reel creator
  const [standaloneReelImage, setStandaloneReelImage] = useState<string | null>(null)
  const [standaloneReelMode, setStandaloneReelMode] = useState('standard')
  const [standaloneReelDuration, setStandaloneReelDuration] = useState(5)
  const [standaloneReelPrompt, setStandaloneReelPrompt] = useState('')
  const [standaloneReelNegativePrompt, setStandaloneReelNegativePrompt] = useState('')
  const [standaloneGeneratingPrompts, setStandaloneGeneratingPrompts] = useState(false)
  const [standaloneReelProcessing, setStandaloneReelProcessing] = useState(false)
  const [standaloneReelResult, setStandaloneReelResult] = useState<string | null>(null)

  // Fetch models directly from Supabase
  useEffect(() => {
    async function fetchModels() {
      try {
        const { data, error } = await supabase
          .from('characters')
          .select('id, name, thumbnail_url')
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

  // Fetch library images (gallery + generations)
  useEffect(() => {
    async function fetchLibraryImages() {
      if (targetMode !== 'library' && sourceMode !== 'library' && selectedTool !== 'reel-create') return

      setLoadingLibrary(true)
      try {
        const images: LibraryImage[] = []

        // Fetch gallery images
        const { data: galleryData, error: galleryError } = await supabase
          .from('character_gallery')
          .select('id, character_id, image_url')
          .order('created_at', { ascending: false })
          .limit(50)

        if (!galleryError && galleryData) {
          images.push(...galleryData.map(item => ({
            id: item.id,
            url: item.image_url,
            type: 'gallery' as const,
            character_id: item.character_id
          })))
        }

        // Fetch recent generations
        const { data: genData, error: genError } = await supabase
          .from('content_items')
          .select('id, character_id, face_swapped_url, original_file_url')
          .not('face_swapped_url', 'is', null)
          .order('created_at', { ascending: false })
          .limit(30)

        if (!genError && genData) {
          images.push(...genData.map(item => ({
            id: item.id,
            url: item.face_swapped_url || item.original_file_url,
            type: 'generation' as const,
            character_id: item.character_id
          })))
        }

        setLibraryImages(images)
      } catch (error) {
        console.error('Failed to load library images:', error)
      } finally {
        setLoadingLibrary(false)
      }
    }

    fetchLibraryImages()
  }, [targetMode, sourceMode, selectedTool])

  // Handle file selection and preview
  const handleTargetFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setTargetFile(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setTargetPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSourceFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSourceFile(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setSourcePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleFaceSwap = async () => {
    // Validate inputs based on mode
    const hasTarget = targetMode === 'upload' ? targetFile : targetUrl
    const hasSource = sourceMode === 'upload' ? sourceFile : sourceUrl

    if (!hasTarget || !hasSource || !selectedModel) {
      setError('Please select/upload both images and select a model')
      return
    }

    setProcessing(true)
    setError(null)
    setResultImage(null)

    try {
      let finalTargetUrl = targetUrl
      let finalSourceUrl = sourceUrl

      // Upload target image if in upload mode
      if (targetMode === 'upload' && targetFile) {
        const targetFormData = new FormData()
        targetFormData.append('file', targetFile)

        const targetUploadRes = await fetch('/api/upload', {
          method: 'POST',
          body: targetFormData
        })
        const targetUploadData = await targetUploadRes.json()

        if (!targetUploadData.success) {
          throw new Error('Failed to upload target image')
        }
        finalTargetUrl = targetUploadData.url
      }

      // Upload source image if in upload mode
      if (sourceMode === 'upload' && sourceFile) {
        const sourceFormData = new FormData()
        sourceFormData.append('file', sourceFile)

        const sourceUploadRes = await fetch('/api/upload', {
          method: 'POST',
          body: sourceFormData
        })
        const sourceUploadData = await sourceUploadRes.json()

        if (!sourceUploadData.success) {
          throw new Error('Failed to upload source image')
        }
        finalSourceUrl = sourceUploadData.url
      }

      // Call face swap with URLs
      const response = await fetch('/api/face-swap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input_image_url: finalTargetUrl,
          source_image_url: finalSourceUrl,
          character_id: selectedModel
        }),
      })

      const data = await response.json()

      if (data.success) {
        setResultImage(data.output_url)
      } else {
        setError(data.error || 'Face swap failed')
      }
    } catch (err) {
      setError('Failed to process face swap. Check if backend is running.')
      console.error('Face swap error:', err)
    } finally {
      setProcessing(false)
    }
  }

  const handleGeneratePrompts = async () => {
    if (!resultImage) {
      setError('Need result image first')
      return
    }

    setGeneratingPrompts(true)
    try {
      const response = await fetch('/api/generate-prompts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_url: resultImage,
          image_description: null
        }),
      })

      const data = await response.json()

      if (data.success) {
        setReelPrompt(data.positive_prompt)
        setReelNegativePrompt(data.negative_prompt)
      } else {
        setError('Failed to generate prompts')
      }
    } catch (err) {
      console.error('Error generating prompts:', err)
      setError('Failed to generate prompts')
    } finally {
      setGeneratingPrompts(false)
    }
  }

  const pollReelStatus = async (contentId: string) => {
    const maxAttempts = 60
    let attempts = 0

    const poll = async () => {
      try {
        const response = await fetch(`/api/content-status/${contentId}`)
        const data = await response.json()

        if (data.success) {
          if (data.status === 'ready') {
            setReelResult(data.video_url)
            setReelProcessing(false)
            setShowReelCreator(false)
            return
          } else if (data.status === 'failed') {
            setError('Reel generation failed on Replicate')
            setReelProcessing(false)
            return
          }
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 10000)
        } else {
          setError('Reel generation timed out')
          setReelProcessing(false)
        }
      } catch (err) {
        console.error('Error polling status:', err)
        setError('Failed to check status')
        setReelProcessing(false)
      }
    }

    poll()
  }

  const handleGenerateReel = async () => {
    if (!resultImage || !reelPrompt) {
      setError('Need face swap result and prompt')
      return
    }

    setReelProcessing(true)
    setError(null)

    try {
      const response = await fetch('/api/generate-reel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_image_url: resultImage,
          prompt: reelPrompt,
          negative_prompt: reelNegativePrompt,
          mode: reelMode,
          duration: reelDuration,
          character_id: selectedModel
        }),
      })

      const data = await response.json()

      if (data.success && data.content_item_id) {
        console.log(`Started reel generation: ${data.content_item_id}`)
        pollReelStatus(data.content_item_id)
      } else {
        setError(data.error || 'Failed to start reel generation')
        setReelProcessing(false)
      }
    } catch (err) {
      console.error('Reel generation error:', err)
      setError('Failed to generate reel')
      setReelProcessing(false)
    }
  }

  // Standalone reel handlers
  const handleStandaloneGeneratePrompts = async () => {
    if (!standaloneReelImage) {
      setError('Select an image first')
      return
    }

    setStandaloneGeneratingPrompts(true)
    try {
      const response = await fetch('/api/generate-prompts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_url: standaloneReelImage,
          image_description: null
        }),
      })

      const data = await response.json()

      if (data.success) {
        setStandaloneReelPrompt(data.positive_prompt)
        setStandaloneReelNegativePrompt(data.negative_prompt)
      } else {
        setError('Failed to generate prompts')
      }
    } catch (err) {
      console.error('Error generating prompts:', err)
      setError('Failed to generate prompts')
    } finally {
      setStandaloneGeneratingPrompts(false)
    }
  }

  const pollContentStatus = async (contentId: string) => {
    const maxAttempts = 60 // Poll for up to 10 minutes (60 * 10 seconds)
    let attempts = 0

    const poll = async () => {
      try {
        const response = await fetch(`/api/content-status/${contentId}`)
        const data = await response.json()

        if (data.success) {
          if (data.status === 'ready') {
            setStandaloneReelResult(data.video_url)
            setStandaloneReelProcessing(false)
            return
          } else if (data.status === 'failed') {
            setError('Reel generation failed on Replicate')
            setStandaloneReelProcessing(false)
            return
          }
        }

        // Still processing, poll again
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 10000) // Poll every 10 seconds
        } else {
          setError('Reel generation timed out')
          setStandaloneReelProcessing(false)
        }
      } catch (err) {
        console.error('Error polling status:', err)
        setError('Failed to check status')
        setStandaloneReelProcessing(false)
      }
    }

    poll()
  }

  const handleStandaloneGenerateReel = async () => {
    if (!standaloneReelImage || !standaloneReelPrompt) {
      setError('Need image and prompt')
      return
    }

    setStandaloneReelProcessing(true)
    setError(null)

    try {
      const response = await fetch('/api/generate-reel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_image_url: standaloneReelImage,
          prompt: standaloneReelPrompt,
          negative_prompt: standaloneReelNegativePrompt,
          mode: standaloneReelMode,
          duration: standaloneReelDuration,
          character_id: selectedModel
        }),
      })

      const data = await response.json()

      if (data.success && data.content_item_id) {
        // Job started! Now poll for completion
        console.log(`Started reel generation: ${data.content_item_id}`)
        pollContentStatus(data.content_item_id)
      } else {
        setError(data.error || 'Failed to start reel generation')
        setStandaloneReelProcessing(false)
      }
    } catch (err) {
      console.error('Reel generation error:', err)
      setError('Failed to generate reel')
      setStandaloneReelProcessing(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Tool Selector */}
      <div>
        <label className="block text-sm font-medium mb-2">Select Tool</label>
        <select
          value={selectedTool}
          onChange={(e) => setSelectedTool(e.target.value)}
          className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="face-swap">Face Swap</option>
          <option value="reel-create">Reel Create</option>
          <option value="video-generation" disabled>Video Generation (Coming Soon)</option>
          <option value="background-removal" disabled>Background Removal (Coming Soon)</option>
        </select>
      </div>

      {/* Face Swap Tool */}
      {selectedTool === 'face-swap' && (
        <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 p-6 space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">Face Swap</h2>
            <p className="text-gray-400">Upload two images to swap faces</p>
          </div>

          {/* Image Uploads Side by Side */}
          <div className="grid grid-cols-2 gap-4">
            {/* Target Image */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Target Image <span className="text-gray-500">(where face goes TO)</span>
              </label>

              {/* Mode Tabs */}
              <div className="flex gap-2 mb-3">
                <button
                  onClick={() => {
                    setTargetMode('upload')
                    setTargetUrl(null)
                  }}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                    targetMode === 'upload'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-gray-400 hover:bg-slate-600'
                  }`}
                >
                  Upload
                </button>
                <button
                  onClick={() => {
                    setTargetMode('library')
                    setTargetFile(null)
                    setTargetPreview(null)
                  }}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                    targetMode === 'library'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-gray-400 hover:bg-slate-600'
                  }`}
                >
                  Library
                </button>
              </div>

              {targetMode === 'upload' ? (
                <div className="border-2 border-dashed border-slate-600 rounded-lg p-4 text-center hover:border-purple-500 transition-all">
                  {targetPreview ? (
                    <div className="relative">
                      <img src={targetPreview} alt="Target preview" className="w-full h-48 object-cover rounded-lg mb-2" />
                      <button
                        onClick={() => {
                          setTargetFile(null)
                          setTargetPreview(null)
                        }}
                        className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <div className="py-8">
                      <div className="text-4xl mb-2">📸</div>
                      <p className="text-sm text-gray-400">Click to upload</p>
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleTargetFileChange}
                    className="hidden"
                    id="target-upload"
                  />
                  <label
                    htmlFor="target-upload"
                    className="mt-2 inline-block px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg cursor-pointer text-sm font-semibold transition-all"
                  >
                    {targetPreview ? 'Change' : 'Upload'}
                  </label>
                </div>
              ) : (
                <div className="border-2 border-slate-600 rounded-lg p-3 max-h-80 overflow-y-auto">
                  {loadingLibrary ? (
                    <div className="text-center py-8 text-gray-400">Loading library...</div>
                  ) : (
                    <div className="grid grid-cols-3 gap-2">
                      {libraryImages.map((img) => (
                        <div
                          key={img.id}
                          onClick={() => {
                            setTargetUrl(img.url)
                            setTargetPreview(img.url)
                          }}
                          className={`relative cursor-pointer rounded-lg overflow-hidden aspect-square ${
                            targetUrl === img.url ? 'ring-2 ring-purple-500' : 'hover:ring-2 hover:ring-purple-400'
                          }`}
                        >
                          <img src={img.url} alt="Library" className="w-full h-full object-cover" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Source Face */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Source Face <span className="text-gray-500">(face to swap IN)</span>
              </label>

              {/* Mode Tabs */}
              <div className="flex gap-2 mb-3">
                <button
                  onClick={() => {
                    setSourceMode('upload')
                    setSourceUrl(null)
                  }}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                    sourceMode === 'upload'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-gray-400 hover:bg-slate-600'
                  }`}
                >
                  Upload
                </button>
                <button
                  onClick={() => {
                    setSourceMode('library')
                    setSourceFile(null)
                    setSourcePreview(null)
                  }}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-semibold transition-all ${
                    sourceMode === 'library'
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-700 text-gray-400 hover:bg-slate-600'
                  }`}
                >
                  Library
                </button>
              </div>

              {sourceMode === 'upload' ? (
                <div className="border-2 border-dashed border-slate-600 rounded-lg p-4 text-center hover:border-purple-500 transition-all">
                  {sourcePreview ? (
                    <div className="relative">
                      <img src={sourcePreview} alt="Source preview" className="w-full h-48 object-cover rounded-lg mb-2" />
                      <button
                        onClick={() => {
                          setSourceFile(null)
                          setSourcePreview(null)
                        }}
                        className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <div className="py-8">
                      <div className="text-4xl mb-2">👤</div>
                      <p className="text-sm text-gray-400">Click to upload</p>
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleSourceFileChange}
                    className="hidden"
                    id="source-upload"
                  />
                  <label
                    htmlFor="source-upload"
                    className="mt-2 inline-block px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg cursor-pointer text-sm font-semibold transition-all"
                  >
                    {sourcePreview ? 'Change' : 'Upload'}
                  </label>
                </div>
              ) : (
                <div className="border-2 border-slate-600 rounded-lg p-3 max-h-80 overflow-y-auto">
                  {loadingLibrary ? (
                    <div className="text-center py-8 text-gray-400">Loading library...</div>
                  ) : (
                    <div className="grid grid-cols-3 gap-2">
                      {libraryImages.map((img) => (
                        <div
                          key={img.id}
                          onClick={() => {
                            setSourceUrl(img.url)
                            setSourcePreview(img.url)
                          }}
                          className={`relative cursor-pointer rounded-lg overflow-hidden aspect-square ${
                            sourceUrl === img.url ? 'ring-2 ring-purple-500' : 'hover:ring-2 hover:ring-purple-400'
                          }`}
                        >
                          <img src={img.url} alt="Library" className="w-full h-full object-cover" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Link to Model (optional)</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">Choose a model...</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-gray-500">
              Link this generation to a model to see it in Generations
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              {error}
            </div>
          )}

          {/* Run Button */}
          <button
            onClick={handleFaceSwap}
            disabled={processing || !targetFile || !sourceFile}
            className="w-full py-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg font-bold text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:from-purple-600 hover:to-pink-600"
          >
            {processing ? 'Processing...' : 'Run Face Swap'}
          </button>

          {/* Processing Indicator */}
          {processing && (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
              <p className="mt-4 text-gray-400">Swapping faces... This takes ~10-30 seconds</p>
            </div>
          )}

          {/* Result Display */}
          {resultImage && !processing && (
            <div className="space-y-4">
              <div className="border-t border-slate-700 pt-6">
                <h3 className="text-lg font-semibold mb-4">Result</h3>
                <div className="bg-slate-900 rounded-lg p-4">
                  <img
                    src={resultImage}
                    alt="Face swap result"
                    className="w-full rounded-lg"
                  />
                </div>
                <div className="mt-4 flex gap-2">
                  <a
                    href={resultImage}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-center font-semibold transition-all"
                  >
                    Open Full Size
                  </a>
                  <button
                    onClick={() => setShowReelCreator(true)}
                    className="flex-1 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-lg font-semibold transition-all"
                  >
                    Create Reel →
                  </button>
                  <button
                    onClick={() => {
                      setResultImage(null)
                      setTargetFile(null)
                      setSourceFile(null)
                      setTargetPreview(null)
                      setSourcePreview(null)
                      setError(null)
                      setShowReelCreator(false)
                      setReelResult(null)
                    }}
                    className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-semibold transition-all"
                  >
                    New Face Swap
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Reel Creator */}
          {showReelCreator && resultImage && (
            <div className="border-t border-slate-700 pt-6 space-y-4">
              <h3 className="text-lg font-semibold">Create Reel from Face Swap</h3>

              {/* Mode Selector */}
              <div>
                <label className="block text-sm font-medium mb-2">Quality Mode</label>
                <select
                  value={reelMode}
                  onChange={(e) => setReelMode(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="standard">Standard (720p, 24fps)</option>
                  <option value="pro">Pro (1080p, 24fps)</option>
                </select>
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium mb-2">Duration: {reelDuration}s</label>
                <input
                  type="range"
                  min="3"
                  max="10"
                  value={reelDuration}
                  onChange={(e) => setReelDuration(parseInt(e.target.value))}
                  className="w-full"
                />
              </div>

              {/* Prompt */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium">Prompt</label>
                  <button
                    onClick={handleGeneratePrompts}
                    disabled={generatingPrompts}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs font-semibold disabled:opacity-50"
                  >
                    {generatingPrompts ? 'Generating...' : '✨ Generate with Grok'}
                  </button>
                </div>
                <textarea
                  value={reelPrompt}
                  onChange={(e) => setReelPrompt(e.target.value)}
                  placeholder="Describe the motion/action..."
                  rows={3}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              {/* Negative Prompt */}
              <div>
                <label className="block text-sm font-medium mb-2">Negative Prompt</label>
                <textarea
                  value={reelNegativePrompt}
                  onChange={(e) => setReelNegativePrompt(e.target.value)}
                  placeholder="Things you don't want to see..."
                  rows={2}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              {/* Generate Button */}
              <div className="flex gap-2">
                <button
                  onClick={handleGenerateReel}
                  disabled={reelProcessing || !reelPrompt}
                  className="flex-1 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {reelProcessing ? 'Generating Reel...' : 'Generate Reel'}
                </button>
                <button
                  onClick={() => setShowReelCreator(false)}
                  className="px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-semibold"
                >
                  Cancel
                </button>
              </div>

              {reelProcessing && (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
                  <p className="mt-4 text-gray-400">Generating reel... This takes 2-5 minutes</p>
                </div>
              )}
            </div>
          )}

          {/* Reel Result */}
          {reelResult && !reelProcessing && (
            <div className="border-t border-slate-700 pt-6 space-y-4">
              <h3 className="text-lg font-semibold">Reel Generated!</h3>
              <div className="bg-slate-900 rounded-lg p-4">
                <video src={reelResult} controls className="w-full rounded-lg" />
              </div>
              <div className="flex gap-2">
                <a
                  href={reelResult}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-center font-semibold"
                >
                  Download Video
                </a>
                <button
                  onClick={() => {
                    setReelResult(null)
                    setShowReelCreator(true)
                  }}
                  className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-semibold"
                >
                  Create Another
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Standalone Reel Creator Tool */}
      {selectedTool === 'reel-create' && (
        <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 p-6 space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">Create Reel</h2>
            <p className="text-gray-400">Select an image and generate a video reel</p>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Link to Model (optional)</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">None</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          {/* Image Selection from Library */}
          <div>
            <label className="block text-sm font-medium mb-2">Select Image from Library</label>
            <div className="border-2 border-slate-600 rounded-lg p-4 max-h-96 overflow-y-auto">
              {loadingLibrary ? (
                <div className="text-center py-8 text-gray-400">Loading library...</div>
              ) : (
                <div className="grid grid-cols-4 gap-3">
                  {libraryImages.map((img) => (
                    <div
                      key={img.id}
                      onClick={() => setStandaloneReelImage(img.url)}
                      className={`relative cursor-pointer rounded-lg overflow-hidden aspect-square ${
                        standaloneReelImage === img.url ? 'ring-4 ring-purple-500' : 'hover:ring-2 hover:ring-purple-400'
                      }`}
                    >
                      <img src={img.url} alt="Library" className="w-full h-full object-cover" />
                      {standaloneReelImage === img.url && (
                        <div className="absolute inset-0 bg-purple-600/20 flex items-center justify-center">
                          <div className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center">
                            ✓
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Selected Image Preview */}
          {standaloneReelImage && (
            <div className="border border-slate-600 rounded-lg p-4">
              <label className="block text-sm font-medium mb-2">Selected Image</label>
              <img src={standaloneReelImage} alt="Selected" className="w-full max-w-md mx-auto rounded-lg" />
            </div>
          )}

          {/* Reel Settings */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Quality Mode</label>
              <select
                value={standaloneReelMode}
                onChange={(e) => setStandaloneReelMode(e.target.value)}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="standard">Standard (720p)</option>
                <option value="pro">Pro (1080p)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Duration: {standaloneReelDuration}s</label>
              <input
                type="range"
                min="3"
                max="10"
                value={standaloneReelDuration}
                onChange={(e) => setStandaloneReelDuration(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          </div>

          {/* Prompt with Grok Generation */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium">Prompt</label>
              <button
                onClick={handleStandaloneGeneratePrompts}
                disabled={standaloneGeneratingPrompts}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs font-semibold disabled:opacity-50"
              >
                {standaloneGeneratingPrompts ? 'Generating...' : '✨ Generate with Grok'}
              </button>
            </div>
            <textarea
              value={standaloneReelPrompt}
              onChange={(e) => setStandaloneReelPrompt(e.target.value)}
              placeholder="Describe the motion/action..."
              rows={3}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Negative Prompt */}
          <div>
            <label className="block text-sm font-medium mb-2">Negative Prompt</label>
            <textarea
              value={standaloneReelNegativePrompt}
              onChange={(e) => setStandaloneReelNegativePrompt(e.target.value)}
              placeholder="Things you don't want to see..."
              rows={2}
              className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Generate Button */}
          {error && (
            <div className="p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-200">
              {error}
            </div>
          )}

          <button
            onClick={handleStandaloneGenerateReel}
            disabled={standaloneReelProcessing || !standaloneReelImage || !standaloneReelPrompt}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {standaloneReelProcessing ? 'Generating Reel... (2-5 min)' : 'Generate Reel'}
          </button>

          {/* Result Video */}
          {standaloneReelResult && (
            <div className="border border-green-500 rounded-lg p-4 bg-green-500/10">
              <h3 className="text-lg font-bold mb-2 text-green-400">✓ Reel Generated!</h3>
              <video src={standaloneReelResult} controls className="w-full rounded-lg mb-4" />
              <div className="flex gap-2">
                <a
                  href={standaloneReelResult}
                  download
                  className="flex-1 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold text-center"
                >
                  Download Video
                </a>
                <button
                  onClick={() => {
                    setStandaloneReelResult(null)
                    setStandaloneReelImage(null)
                    setStandaloneReelPrompt('')
                    setStandaloneReelNegativePrompt('')
                  }}
                  className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-semibold"
                >
                  Create Another
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
