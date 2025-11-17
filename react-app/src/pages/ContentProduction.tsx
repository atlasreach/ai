import { useState, useEffect } from 'react';
import { Upload, Sparkles, Download, Settings as SettingsIcon } from 'lucide-react';
import { supabase } from '../lib/supabase';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8003'
  : `https://vigilant-rotary-phone-7v5g5q99jpjjfw57w-8003.app.github.dev`;

interface Model {
  id: string;
  name: string;
  trigger_word: string;
  defining_features: Record<string, string>;
}

interface Dataset {
  id: string;
  name: string;
  dataset_type: string;
  lora_filename: string | null;
  training_status: string;
}

interface SourceImage {
  file: File;
  preview: string;
}

interface GeneratedImage {
  source_index: number;
  variation_index: number;
  url: string;
  parameters: any;
}

type Preset = 'conservative' | 'balanced' | 'aggressive';

export default function ContentProduction() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);

  // Source images
  const [sourceImages, setSourceImages] = useState<SourceImage[]>([]);

  // Generation settings
  const [preset, setPreset] = useState<Preset>('balanced');
  const [variationsPerImage, setVariationsPerImage] = useState(4);
  const [customSettings, setCustomSettings] = useState({
    denoise: 0.75,
    lora_strength: 0.8,
    cfg_scale: 4.5,
    steps: 30,
  });

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImages, setGeneratedImages] = useState<GeneratedImage[]>([]);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModel) {
      loadDatasets(selectedModel.id);
    }
  }, [selectedModel]);

  const loadModels = async () => {
    const { data } = await supabase.from('models').select('*').order('created_at', { ascending: false });
    if (data) setModels(data);
  };

  const loadDatasets = async (modelId: string) => {
    const { data } = await supabase
      .from('datasets')
      .select('*')
      .eq('model_id', modelId)
      .eq('training_status', 'trained')
      .order('created_at', { ascending: false });

    if (data) setDatasets(data);
  };

  const presets: Record<Preset, typeof customSettings> = {
    conservative: {
      denoise: 0.6,
      lora_strength: 0.7,
      cfg_scale: 3.5,
      steps: 25,
    },
    balanced: {
      denoise: 0.75,
      lora_strength: 0.85,
      cfg_scale: 4.5,
      steps: 30,
    },
    aggressive: {
      denoise: 0.9,
      lora_strength: 1.0,
      cfg_scale: 6,
      steps: 40,
    },
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newImages: SourceImage[] = files.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
    }));
    setSourceImages([...sourceImages, ...newImages]);
  };

  const generateContent = async () => {
    if (!selectedModel || !selectedDataset || sourceImages.length === 0) {
      alert('Please select model, dataset, and upload source images');
      return;
    }

    if (!selectedDataset.lora_filename) {
      alert('Selected dataset does not have a trained LoRA file');
      return;
    }

    setIsGenerating(true);
    setProgress({ current: 0, total: sourceImages.length * variationsPerImage });
    setGeneratedImages([]);

    try {
      // Upload source images first
      const uploadedUrls: string[] = [];

      for (const img of sourceImages) {
        const formData = new FormData();
        formData.append('file', img.file);

        const uploadResponse = await fetch(`${API_BASE}/api/upload-temp`, {
          method: 'POST',
          body: formData,
        });

        const uploadData = await uploadResponse.json();
        uploadedUrls.push(uploadData.url);
      }

      // Generate variations for each source image
      for (let i = 0; i < uploadedUrls.length; i++) {
        const sourceUrl = uploadedUrls[i];

        // Call batch generation API
        const response = await fetch(`${API_BASE}/api/comfyui/batch-generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model_id: selectedModel.id,
            dataset_id: selectedDataset.id,
            lora_filename: selectedDataset.lora_filename,
            trigger_word: selectedModel.trigger_word,
            defining_features: selectedModel.defining_features,
            source_image_url: sourceUrl,
            batch_size: variationsPerImage,
            parameters: customSettings,
          }),
        });

        const data = await response.json();

        if (data.job_id) {
          // Poll for completion
          await pollJobStatus(data.job_id, i);
        }
      }

      alert('Generation complete!');
    } catch (error) {
      console.error('Error generating content:', error);
      alert('Failed to generate content. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const pollJobStatus = async (jobId: string, sourceIndex: number) => {
    return new Promise<void>((resolve) => {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/api/comfyui/status/${jobId}`);
          const data = await response.json();

          if (data.status === 'completed') {
            clearInterval(interval);

            // Add generated images
            if (data.output_urls && Array.isArray(data.output_urls)) {
              const newImages: GeneratedImage[] = data.output_urls.map((url: string, idx: number) => ({
                source_index: sourceIndex,
                variation_index: idx,
                url,
                parameters: customSettings,
              }));

              setGeneratedImages((prev) => [...prev, ...newImages]);
              setProgress((prev) => ({ ...prev, current: prev.current + variationsPerImage }));
            }

            resolve();
          } else if (data.status === 'failed') {
            clearInterval(interval);
            console.error('Job failed:', data.error);
            resolve();
          }
          // Continue polling if status is 'processing'
        } catch (error) {
          console.error('Error polling job status:', error);
          clearInterval(interval);
          resolve();
        }
      }, 5000); // Poll every 5 seconds
    });
  };

  const downloadImage = (url: string, filename: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  const downloadAll = () => {
    generatedImages.forEach((img, i) => {
      downloadImage(img.url, `generated_${i + 1}.png`);
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Content Production</h1>
        <p className="text-slate-400 mt-1">Generate batch content using your trained models</p>
      </div>

      {/* Model & Dataset Selection */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Select Model</label>
          <select
            value={selectedModel?.id || ''}
            onChange={(e) => {
              const model = models.find((m) => m.id === e.target.value);
              setSelectedModel(model || null);
              setSelectedDataset(null);
            }}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Choose a model...</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Select Dataset/LoRA
          </label>
          <select
            value={selectedDataset?.id || ''}
            onChange={(e) => {
              const dataset = datasets.find((d) => d.id === e.target.value);
              setSelectedDataset(dataset || null);
            }}
            disabled={!selectedModel}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="">Choose a dataset...</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} ({dataset.dataset_type}) - {dataset.lora_filename || 'No LoRA'}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedDataset && (
        <>
          {/* Source Image Upload */}
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl">
            <h2 className="text-lg font-bold text-white mb-4">Source Images</h2>

            <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-slate-600 transition-colors mb-4">
              <Upload className="w-10 h-10 mx-auto text-slate-500 mb-3" />
              <p className="text-slate-300 mb-2">Upload source images for transformation</p>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                id="source-upload"
              />
              <label
                htmlFor="source-upload"
                className="inline-block px-6 py-2 bg-slate-800 text-slate-300 rounded-lg cursor-pointer hover:bg-slate-700"
              >
                Select Files
              </label>
            </div>

            {sourceImages.length > 0 && (
              <div className="grid grid-cols-6 gap-3">
                {sourceImages.map((img, i) => (
                  <div key={i} className="aspect-square rounded-lg overflow-hidden bg-slate-800">
                    <img src={img.preview} alt={`Source ${i + 1}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Generation Settings */}
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5" />
              Generation Settings
            </h2>

            {/* Variations Per Image */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Variations per image: {variationsPerImage}
              </label>
              <input
                type="range"
                min="3"
                max="5"
                value={variationsPerImage}
                onChange={(e) => setVariationsPerImage(parseInt(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-slate-500 mt-1">
                Total images: {sourceImages.length} × {variationsPerImage} ={' '}
                {sourceImages.length * variationsPerImage}
              </p>
            </div>

            {/* Presets */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">Preset</label>
              <div className="grid grid-cols-3 gap-3">
                {(['conservative', 'balanced', 'aggressive'] as Preset[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => {
                      setPreset(p);
                      setCustomSettings(presets[p]);
                    }}
                    className={`p-4 rounded-lg border transition-all ${
                      preset === p
                        ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <div className="font-medium capitalize">{p}</div>
                    <div className="text-xs mt-1 opacity-70">
                      {p === 'conservative' && 'Subtle changes'}
                      {p === 'balanced' && 'Recommended'}
                      {p === 'aggressive' && 'Strong effect'}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Advanced Settings */}
            <details className="group">
              <summary className="text-sm font-medium text-slate-300 cursor-pointer hover:text-white">
                Advanced Settings
              </summary>

              <div className="mt-4 space-y-4 pl-4 border-l-2 border-slate-700">
                {Object.entries(customSettings).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-sm text-slate-400 mb-1 capitalize">
                      {key.replace('_', ' ')}: {value}
                    </label>
                    <input
                      type="range"
                      min={key === 'steps' ? 20 : key === 'cfg_scale' ? 1 : 0}
                      max={key === 'steps' ? 50 : key === 'cfg_scale' ? 10 : key === 'lora_strength' ? 1.5 : 1}
                      step={key === 'steps' ? 1 : 0.05}
                      value={value}
                      onChange={(e) =>
                        setCustomSettings({ ...customSettings, [key]: parseFloat(e.target.value) })
                      }
                      className="w-full"
                    />
                  </div>
                ))}
              </div>
            </details>
          </div>

          {/* Generate Button */}
          <button
            onClick={generateContent}
            disabled={isGenerating || sourceImages.length === 0}
            className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-lg font-medium shadow-lg shadow-blue-500/20"
          >
            <Sparkles className="w-6 h-6" />
            {isGenerating ? (
              <>
                Generating... ({progress.current}/{progress.total})
              </>
            ) : (
              <>Generate {sourceImages.length * variationsPerImage} Images</>
            )}
          </button>
        </>
      )}

      {/* Generated Results */}
      {generatedImages.length > 0 && (
        <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">Generated Images</h2>
            <button
              onClick={downloadAll}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              <Download className="w-4 h-4" />
              Download All
            </button>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {generatedImages.map((img, i) => (
              <div key={i} className="group relative aspect-square rounded-lg overflow-hidden bg-slate-800">
                <img src={img.url} alt={`Generated ${i + 1}`} className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <button
                    onClick={() => downloadImage(img.url, `generated_${i + 1}.png`)}
                    className="p-2 bg-white rounded-full hover:bg-slate-200 transition-colors"
                  >
                    <Download className="w-5 h-5 text-slate-900" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
