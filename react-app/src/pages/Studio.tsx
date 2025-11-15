import { useState } from 'react'

type Step = 'upload' | 'select-model' | 'processing' | 'review' | 'complete'

export default function Studio() {
  const [step, setStep] = useState<Step>('upload')
  const [targetImage, setTargetImage] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)

  const models = [
    {
      id: 'milan',
      name: 'Milan',
      thumbnail: 'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/1.jpg'
    },
    { id: 'skyler', name: 'Skyler', thumbnail: null },
    { id: 'sara', name: 'Sara', thumbnail: null },
  ]

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Create local preview URL
      const previewUrl = URL.createObjectURL(file)
      setTargetImage(previewUrl)

      // Upload file to backend
      const formData = new FormData()
      formData.append('file', file)

      try {
        const response = await fetch('http://localhost:8002/upload', {
          method: 'POST',
          body: formData,
        })

        const data = await response.json()

        if (data.success) {
          // Store the actual URL for API calls, keep preview for display
          setTargetImage(data.file_url)
          setStep('select-model')
        } else {
          alert('Failed to upload file: ' + (data.error || 'Unknown error'))
        }
      } catch (error) {
        console.error('Error uploading file:', error)
        alert('Failed to upload file. Make sure the backend is running on port 8002.')
      }
    }
  }

  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId)
  }

  const handleStartSwap = async () => {
    setStep('processing')
    setProcessing(true)

    try {
      // Call the actual face-swap API
      const response = await fetch('http://localhost:8002/face-swap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character_id: selectedModel,
          input_image_url: targetImage,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setResultImage(data.output_url)
        setProcessing(false)
        setStep('review')
      } else {
        console.error('Face swap failed:', data.error)
        alert('Face swap failed: ' + (data.error || 'Unknown error'))
        setProcessing(false)
        setStep('select-model')
      }
    } catch (error) {
      console.error('Error calling face-swap API:', error)
      alert('Failed to connect to face-swap API. Make sure the backend is running on port 8002.')
      setProcessing(false)
      setStep('select-model')
    }
  }

  const handleAccept = () => {
    setStep('complete')
  }

  const handleReject = () => {
    setStep('select-model')
    setResultImage(null)
  }

  const handleStartOver = () => {
    setStep('upload')
    setTargetImage(null)
    setSelectedModel(null)
    setResultImage(null)
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {['Upload', 'Select Model', 'Face Swap', 'Review'].map((label, idx) => {
            const stepKeys: Step[] = ['upload', 'select-model', 'processing', 'review']
            const currentIdx = stepKeys.indexOf(step)
            const isActive = idx <= currentIdx
            const isCurrent = idx === currentIdx

            return (
              <div key={label} className="flex items-center flex-1">
                <div className="flex items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white'
                      : 'bg-slate-700 text-gray-400'
                  } ${isCurrent ? 'ring-4 ring-blue-500/30' : ''}`}>
                    {idx + 1}
                  </div>
                  <span className={`ml-3 font-semibold ${isActive ? 'text-white' : 'text-gray-500'}`}>
                    {label}
                  </span>
                </div>
                {idx < 3 && (
                  <div className={`flex-1 h-1 mx-4 rounded transition-all ${
                    idx < currentIdx ? 'bg-gradient-to-r from-blue-500 to-cyan-500' : 'bg-slate-700'
                  }`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
          <h2 className="text-2xl font-bold mb-4">Upload Target Image</h2>
          <p className="text-gray-400 mb-6">This is the image where the face will be swapped</p>

          <div className="border-2 border-dashed border-slate-600 rounded-xl p-16 text-center hover:border-blue-500 transition-all">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
              id="upload"
            />
            <label htmlFor="upload" className="cursor-pointer">
              <div className="text-7xl mb-4">📸</div>
              <p className="text-xl mb-2 font-semibold">Drop image here or click to browse</p>
              <p className="text-sm text-gray-500">Supports JPG, PNG</p>
            </label>
          </div>

          <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-2">📚 Or choose from your library:</p>
            <button className="text-blue-400 hover:text-blue-300 text-sm font-semibold">
              Browse Existing Images →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Select Model */}
      {step === 'select-model' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-bold mb-4">Your Target Image</h2>
            <div className="relative inline-block">
              <img src={targetImage!} alt="Target" className="max-h-64 rounded-lg" />
              <button
                onClick={handleStartOver}
                className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 px-3 py-1 rounded-lg text-sm font-semibold"
              >
                Change
              </button>
            </div>
          </div>

          <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-bold mb-4">Select Model Face</h2>
            <p className="text-gray-400 mb-6">Which model's face should be swapped in?</p>

            <div className="grid grid-cols-3 gap-4">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleModelSelect(model.id)}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    selectedModel === model.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <div className="aspect-square bg-slate-700 rounded-lg mb-3 overflow-hidden">
                    {model.thumbnail ? (
                      <img src={model.thumbnail} alt={model.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-4xl">👤</div>
                    )}
                  </div>
                  <h3 className="font-semibold text-center">{model.name}</h3>
                </button>
              ))}
            </div>

            {selectedModel && (
              <button
                onClick={handleStartSwap}
                className="w-full mt-6 py-4 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 rounded-xl font-bold text-lg transition-all"
              >
                Start Face Swap →
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Processing */}
      {step === 'processing' && (
        <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
          <h2 className="text-2xl font-bold mb-6 text-center">Face Swap in Progress</h2>

          <div className="flex justify-center gap-8 mb-8">
            <div className="text-center">
              <div className="w-32 h-32 bg-slate-700 rounded-lg overflow-hidden mb-2">
                <img src={targetImage!} alt="Original" className="w-full h-full object-cover" />
              </div>
              <p className="text-sm text-gray-400">Original</p>
            </div>

            <div className="flex items-center">
              <div className="text-4xl animate-pulse">→</div>
            </div>

            <div className="text-center">
              <div className="w-32 h-32 bg-slate-700 rounded-lg overflow-hidden mb-2 flex items-center justify-center">
                <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"></div>
              </div>
              <p className="text-sm text-gray-400">Swapping...</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span>Processing face swap</span>
              <span className="text-blue-400">~10 seconds</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full rounded-full animate-pulse" style={{width: '60%'}}></div>
            </div>
          </div>

          <div className="mt-6 text-center text-sm text-gray-400">
            <p>Using Replicate cdingram/face-swap model</p>
            <p>Cost: $0.01</p>
          </div>
        </div>
      )}

      {/* Step 4: Review */}
      {step === 'review' && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
            <h2 className="text-2xl font-bold mb-6 text-center">Review Result</h2>

            <div className="grid grid-cols-2 gap-6 mb-8">
              <div>
                <p className="text-sm text-gray-400 mb-2 text-center">Before</p>
                <div className="bg-slate-700 rounded-lg overflow-hidden">
                  <img src={targetImage!} alt="Before" className="w-full" />
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-400 mb-2 text-center">After</p>
                <div className="bg-slate-700 rounded-lg overflow-hidden ring-2 ring-blue-500">
                  <img src={resultImage!} alt="After" className="w-full" />
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={handleReject}
                className="flex-1 py-4 bg-slate-700 hover:bg-slate-600 rounded-xl font-bold text-lg transition-all"
              >
                ❌ Reject & Try Again
              </button>
              <button
                onClick={handleAccept}
                className="flex-1 py-4 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 rounded-xl font-bold text-lg transition-all"
              >
                ✅ Accept Result
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Complete - What to do next */}
      {step === 'complete' && (
        <div className="bg-slate-800 rounded-2xl p-8 border border-slate-700">
          <div className="text-center mb-8">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-3xl font-bold mb-2">Face Swap Complete!</h2>
            <p className="text-gray-400">What would you like to do next?</p>
          </div>

          <div className="mb-8">
            <img src={resultImage!} alt="Final" className="max-h-96 mx-auto rounded-lg" />
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <button className="p-6 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 hover:from-blue-500/30 hover:to-cyan-500/30 border border-blue-500/30 rounded-xl transition-all text-left">
              <div className="text-3xl mb-2">🎬</div>
              <h3 className="font-bold mb-1">Make Video</h3>
              <p className="text-sm text-gray-400">Turn this into a 5-10s video reel</p>
            </button>

            <button className="p-6 bg-gradient-to-br from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 border border-purple-500/30 rounded-xl transition-all text-left">
              <div className="text-3xl mb-2">✂️</div>
              <h3 className="font-bold mb-1">Remove Background</h3>
              <p className="text-sm text-gray-400">Get transparent PNG</p>
            </button>

            <button className="p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 hover:from-green-500/30 hover:to-emerald-500/30 border border-green-500/30 rounded-xl transition-all text-left">
              <div className="text-3xl mb-2">💬</div>
              <h3 className="font-bold mb-1">Generate Caption</h3>
              <p className="text-sm text-gray-400">AI-powered caption with hashtags</p>
            </button>

            <button className="p-6 bg-gradient-to-br from-orange-500/20 to-red-500/20 hover:from-orange-500/30 hover:to-red-500/30 border border-orange-500/30 rounded-xl transition-all text-left">
              <div className="text-3xl mb-2">📅</div>
              <h3 className="font-bold mb-1">Schedule Post</h3>
              <p className="text-sm text-gray-400">Schedule to Instagram, TikTok, etc</p>
            </button>
          </div>

          <div className="flex gap-4">
            <button className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl font-semibold transition-all">
              ⬇️ Download Image
            </button>
            <button className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 rounded-xl font-semibold transition-all">
              💾 Save to Library
            </button>
            <button
              onClick={handleStartOver}
              className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl font-semibold transition-all"
            >
              🔄 Start New
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
