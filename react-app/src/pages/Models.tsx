import { useState } from 'react'

export default function Models() {
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  const models = [
    {
      id: 'milan',
      name: 'Milan',
      description: 'Professional female model',
      lora_file: 'milan_000002000.safetensors',
      trigger_word: 'milan',
      training_images: 25,
      generations: 47,
      last_used: '2 hours ago',
      thumbnail: 'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/1.jpg',
      featured_images: [
        'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/1.jpg',
        'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/2.jpg',
        'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/3.jpg',
        'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/4.jpg',
        'https://ai-character-generations.s3.us-east-2.amazonaws.com/training-images/milan/5.jpg',
      ]
    },
    {
      id: 'skyler',
      name: 'Skyler',
      description: 'Professional female model',
      lora_file: 'skyler_000002000.safetensors',
      trigger_word: 'skyler',
      training_images: 18,
      generations: 23,
      last_used: '1 day ago',
      thumbnail: null,
      featured_images: []
    },
    {
      id: 'sara',
      name: 'Sara',
      description: 'Fashion model',
      lora_file: 'sara_000001500.safetensors',
      trigger_word: 'sara',
      training_images: 12,
      generations: 8,
      last_used: '3 days ago',
      thumbnail: null,
      featured_images: []
    },
  ]

  const selectedModelData = models.find(m => m.id === selectedModel)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Your Models</h1>
          <p className="text-gray-400">Manage your character models and training images</p>
        </div>
        <button className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg font-semibold hover:from-purple-600 hover:to-pink-600 transition-all">
          + Add New Model
        </button>
      </div>

      {/* Model Cards */}
      <div className="grid grid-cols-1 gap-6">
        {models.map((model) => (
          <div key={model.id} className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 overflow-hidden">
            <div className="p-6">
              <div className="flex gap-6">
                {/* Thumbnail */}
                <div className="w-32 h-32 bg-slate-700 rounded-lg overflow-hidden flex-shrink-0">
                  {model.thumbnail ? (
                    <img src={model.thumbnail} alt={model.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-5xl">
                      👤
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-2xl font-bold mb-1">{model.name}</h2>
                      <p className="text-gray-400 mb-3">{model.description}</p>

                      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                        <div>
                          <span className="text-gray-500">LoRA File:</span>
                          <p className="font-mono text-xs text-gray-300">{model.lora_file}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Trigger Word:</span>
                          <p className="font-semibold text-purple-400">{model.trigger_word}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Training Images:</span>
                          <p className="font-semibold">{model.training_images} images</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Used In:</span>
                          <p className="font-semibold">{model.generations} generations</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Last Used:</span>
                          <p className="font-semibold">{model.last_used}</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold">
                        ✏️ Edit
                      </button>
                      <button
                        onClick={() => setSelectedModel(selectedModel === model.id ? null : model.id)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-semibold"
                      >
                        {selectedModel === model.id ? '▲ Hide Gallery' : '▼ View Gallery'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Training Images Gallery */}
              {selectedModel === model.id && model.featured_images.length > 0 && (
                <div className="mt-6 pt-6 border-t border-slate-700">
                  <h3 className="font-semibold mb-4">Training Gallery ({model.training_images} images)</h3>
                  <div className="grid grid-cols-6 gap-3">
                    {model.featured_images.map((img, idx) => (
                      <div key={idx} className="aspect-square bg-slate-700 rounded-lg overflow-hidden hover:ring-2 hover:ring-purple-500 transition-all cursor-pointer">
                        <img src={img} alt={`Training ${idx + 1}`} className="w-full h-full object-cover" />
                      </div>
                    ))}
                    {model.training_images > model.featured_images.length && (
                      <div className="aspect-square bg-slate-700 rounded-lg flex items-center justify-center cursor-pointer hover:bg-slate-600 transition-all">
                        <div className="text-center">
                          <p className="text-2xl">+{model.training_images - model.featured_images.length}</p>
                          <p className="text-xs text-gray-400">more</p>
                        </div>
                      </div>
                    )}
                  </div>

                  <button className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold">
                    View All {model.training_images} Images →
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add New Model Card */}
      <div className="bg-slate-800/30 backdrop-blur rounded-xl border-2 border-dashed border-slate-600 hover:border-purple-500 transition-all cursor-pointer">
        <div className="p-12 text-center">
          <div className="text-6xl mb-4">➕</div>
          <h3 className="text-xl font-semibold mb-2">Add New Model</h3>
          <p className="text-gray-400 mb-4">Upload your trained LoRA file and training images</p>
          <button className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold">
            Get Started
          </button>
        </div>
      </div>

      {/* Info Section */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
        <h3 className="font-semibold mb-2 flex items-center gap-2">
          <span className="text-2xl">💡</span>
          How to Train Your Own Model
        </h3>
        <div className="text-sm text-gray-300 space-y-2 ml-8">
          <p>1. Collect 20-50 high-quality images of your subject</p>
          <p>2. Use a training service (like Replicate, Astria, or RunPod)</p>
          <p>3. Download your trained LoRA .safetensors file</p>
          <p>4. Upload it here along with training images</p>
        </div>
      </div>
    </div>
  )
}
