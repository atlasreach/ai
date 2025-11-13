import { useState } from 'react'
import axios from 'axios'
import './App.css'

// API configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface GenerationParams {
  prompt: string
  negative_prompt: string
  character: string
  width: number
  height: number
  num_inference_steps: number
  guidance_scale: number
  seed: number | null
  lora_strength: number
  init_image_base64: string | null
  strength: number
  num_images: number
  upscale_factor: number
}

interface GenerationResult {
  success: boolean
  image_base64?: string
  images_base64?: string[]
  error?: string
  generation_time?: number
  s3_input_url?: string
  s3_output_url?: string
  s3_metadata_url?: string
}

function App() {
  // State
  const [params, setParams] = useState<GenerationParams>({
    prompt: '',
    negative_prompt: 'blurry, low quality, distorted, deformed, disfigured',
    character: 'milan',
    width: 1024,
    height: 768,
    num_inference_steps: 30,
    guidance_scale: 4.0,
    seed: null,
    lora_strength: 0.8,
    init_image_base64: null,
    strength: 0.85,
    num_images: 1,
    upscale_factor: 1.5
  })

  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedImage, setGeneratedImage] = useState<string | null>(null)
  const [generationTime, setGenerationTime] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [grokCaption, setGrokCaption] = useState<string>('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [s3Urls, setS3Urls] = useState<{input?: string, output?: string, metadata?: string}>({})

  const models = [
    { value: 'milan', label: 'Milan' },
    { value: 'sara', label: 'Sara (Coming Soon)', disabled: true }
  ]

  // Analyze image with Grok Vision
  const analyzeImageWithGrok = async (base64Data: string) => {
    setIsAnalyzing(true)
    setGrokCaption('')

    try {
      const response = await axios.post(`${API_URL}/analyze-image`, {
        image_base64: base64Data,
        model_name: params.character
      })

      if (response.data.success && response.data.caption) {
        setGrokCaption(response.data.caption)
        // Auto-fill the prompt with Grok's caption - use functional update to avoid race condition
        setParams(prevParams => ({ ...prevParams, prompt: response.data.caption }))
      } else {
        console.error('Grok analysis failed:', response.data.error)
      }
    } catch (err) {
      console.error('Grok analysis error:', err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Handle image upload for IMG2IMG
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = () => {
      const base64 = reader.result as string
      const base64Data = base64.split(',')[1] // Remove data:image/...;base64, prefix
      setParams(prevParams => ({ ...prevParams, init_image_base64: base64Data }))
      setPreviewImage(base64) // For display

      // Analyze with Grok Vision
      analyzeImageWithGrok(base64Data)
    }
    reader.readAsDataURL(file)
  }

  // Remove uploaded image
  const clearImage = () => {
    setParams({ ...params, init_image_base64: null })
    setPreviewImage(null)
    setGrokCaption('')
  }

  // Generate image
  const handleGenerate = async () => {
    setIsGenerating(true)
    setError(null)
    setGeneratedImage(null)
    setGenerationTime(null)

    try {
      const response = await axios.post<GenerationResult>(
        `${API_URL}/generate`,
        params,
        { timeout: 600000 } // 10 minute timeout
      )

      if (response.data.success && response.data.image_base64) {
        setGeneratedImage(`data:image/png;base64,${response.data.image_base64}`)
        setGenerationTime(response.data.generation_time || null)
        setS3Urls({
          input: response.data.s3_input_url,
          output: response.data.s3_output_url,
          metadata: response.data.s3_metadata_url
        })
      } else {
        setError(response.data.error || 'Generation failed')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Generation failed')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="min-h-screen text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            AI Image Generator
          </h1>
          <p className="text-gray-400">Generate images with Milan LoRA using ComfyUI</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel - Controls */}
          <div className="space-y-6">
            {/* Model Selector */}
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Model Selection</h2>
              <select
                value={params.character}
                onChange={(e) => setParams({ ...params, character: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg p-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {models.map((model) => (
                  <option key={model.value} value={model.value} disabled={model.disabled}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Prompt */}
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Prompt</h2>
              <textarea
                className="w-full h-32 bg-slate-900 border border-slate-600 rounded-lg p-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Describe the image you want to generate..."
                value={params.prompt}
                onChange={(e) => setParams({ ...params, prompt: e.target.value })}
              />
            </div>

            {/* Negative Prompt */}
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Negative Prompt</h2>
              <textarea
                className="w-full h-24 bg-slate-900 border border-slate-600 rounded-lg p-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Things to avoid..."
                value={params.negative_prompt}
                onChange={(e) => setParams({ ...params, negative_prompt: e.target.value })}
              />
            </div>

            {/* IMG2IMG Upload */}
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">IMG2IMG (Optional)</h2>
              {!previewImage ? (
                <label className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-slate-600 rounded-lg cursor-pointer hover:border-purple-500 transition-colors">
                  <div className="text-center">
                    <p className="text-gray-400 mb-2">Click to upload image</p>
                    <p className="text-sm text-gray-500">Auto-analyzes with Grok Vision</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept="image/*"
                    onChange={handleImageUpload}
                  />
                </label>
              ) : (
                <div className="relative">
                  <img src={previewImage} alt="Preview" className="w-full h-48 object-cover rounded-lg" />
                  <button
                    onClick={clearImage}
                    className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-lg text-sm"
                  >
                    Remove
                  </button>
                  {/* Grok Caption */}
                  {isAnalyzing && (
                    <div className="mt-3 p-3 bg-blue-900/30 border border-blue-700 rounded-lg">
                      <p className="text-sm text-blue-300">🤖 Analyzing with Grok Vision...</p>
                    </div>
                  )}
                  {grokCaption && !isAnalyzing && (
                    <div className="mt-3 p-3 bg-green-900/30 border border-green-700 rounded-lg">
                      <p className="text-xs text-green-300 font-semibold mb-1">Grok Vision Caption:</p>
                      <p className="text-sm text-green-200">{grokCaption}</p>
                    </div>
                  )}

                  <div className="mt-3">
                    <label className="text-sm text-gray-400">IMG2IMG Strength</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={params.strength}
                      onChange={(e) => setParams({ ...params, strength: parseFloat(e.target.value) })}
                      className="w-full mt-2"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>0.0 (more creative)</span>
                      <span className="font-bold text-white">{params.strength}</span>
                      <span>1.0 (closer to input)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Parameters */}
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700 space-y-4">
              <h2 className="text-xl font-semibold mb-4">Parameters</h2>

              {/* LoRA Strength */}
              <div>
                <label className="text-sm text-gray-400">LoRA Strength</label>
                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.1"
                  value={params.lora_strength}
                  onChange={(e) => setParams({ ...params, lora_strength: parseFloat(e.target.value) })}
                  className="w-full mt-2"
                />
                <div className="text-right text-sm mt-1 text-white font-semibold">{params.lora_strength}</div>
              </div>

              {/* Steps */}
              <div>
                <label className="text-sm text-gray-400">Inference Steps</label>
                <input
                  type="range"
                  min="10"
                  max="50"
                  step="5"
                  value={params.num_inference_steps}
                  onChange={(e) => setParams({ ...params, num_inference_steps: parseInt(e.target.value) })}
                  className="w-full mt-2"
                />
                <div className="text-right text-sm mt-1 text-white font-semibold">{params.num_inference_steps}</div>
              </div>

              {/* CFG Scale */}
              <div>
                <label className="text-sm text-gray-400">Guidance Scale (CFG)</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={params.guidance_scale}
                  onChange={(e) => setParams({ ...params, guidance_scale: parseFloat(e.target.value) })}
                  className="w-full mt-2"
                />
                <div className="text-right text-sm mt-1 text-white font-semibold">{params.guidance_scale}</div>
              </div>

              {/* Dimensions */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-400">Width</label>
                  <input
                    type="number"
                    value={params.width}
                    onChange={(e) => setParams({ ...params, width: parseInt(e.target.value) })}
                    className="w-full mt-2 bg-slate-900 border border-slate-600 rounded-lg p-2 text-white"
                    step="64"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-400">Height</label>
                  <input
                    type="number"
                    value={params.height}
                    onChange={(e) => setParams({ ...params, height: parseInt(e.target.value) })}
                    className="w-full mt-2 bg-slate-900 border border-slate-600 rounded-lg p-2 text-white"
                    step="64"
                  />
                </div>
              </div>

              {/* Seed */}
              <div>
                <label className="text-sm text-gray-400">Seed (optional)</label>
                <input
                  type="number"
                  value={params.seed || ''}
                  onChange={(e) => setParams({ ...params, seed: e.target.value ? parseInt(e.target.value) : null })}
                  placeholder="Random"
                  className="w-full mt-2 bg-slate-900 border border-slate-600 rounded-lg p-2 text-white"
                />
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !params.prompt}
              className={`w-full py-4 rounded-xl font-semibold text-lg transition-all ${
                isGenerating || !params.prompt
                  ? 'bg-gray-700 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600'
              }`}
            >
              {isGenerating ? 'Generating... (~80s)' : 'Generate Image'}
            </button>
          </div>

          {/* Right Panel - Output */}
          <div className="space-y-6">
            <div className="bg-slate-800/50 backdrop-blur rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4">Generated Image</h2>

              {error && (
                <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-4">
                  <p className="text-red-200">{error}</p>
                </div>
              )}

              {isGenerating && (
                <div className="flex flex-col items-center justify-center h-96 bg-slate-900 rounded-lg">
                  <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500 mb-4"></div>
                  <p className="text-gray-400">Generating your image...</p>
                  <p className="text-sm text-gray-500 mt-2">This usually takes ~80 seconds</p>
                </div>
              )}

              {!isGenerating && !generatedImage && !error && (
                <div className="flex items-center justify-center h-96 bg-slate-900 rounded-lg">
                  <p className="text-gray-500">Your generated image will appear here</p>
                </div>
              )}

              {generatedImage && (
                <div>
                  <img
                    src={generatedImage}
                    alt="Generated"
                    className="w-full rounded-lg shadow-2xl"
                  />
                  {generationTime && (
                    <p className="text-sm text-gray-400 mt-3">
                      Generated in {generationTime.toFixed(1)}s
                    </p>
                  )}

                  {/* S3 URLs */}
                  {(s3Urls.input || s3Urls.output || s3Urls.metadata) && (
                    <div className="mt-3 p-3 bg-slate-900/50 border border-slate-600 rounded-lg">
                      <p className="text-xs text-gray-400 font-semibold mb-2">📦 Saved to S3:</p>
                      <div className="space-y-1 text-xs">
                        {s3Urls.input && (
                          <div>
                            <span className="text-gray-500">Input: </span>
                            <a href={s3Urls.input} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                              View
                            </a>
                          </div>
                        )}
                        {s3Urls.output && (
                          <div>
                            <span className="text-gray-500">Output: </span>
                            <a href={s3Urls.output} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                              View
                            </a>
                          </div>
                        )}
                        {s3Urls.metadata && (
                          <div>
                            <span className="text-gray-500">Metadata: </span>
                            <a href={s3Urls.metadata} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                              View JSON
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 mt-4">
                    <a
                      href={generatedImage}
                      download="generated-milan.png"
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2 rounded-lg text-center"
                    >
                      Download
                    </a>
                    <button
                      onClick={() => {
                        setGeneratedImage(null)
                        setGenerationTime(null)
                      }}
                      className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
