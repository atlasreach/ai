import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://vigilant-rotary-phone-7v5g5q99jpjjfw57w-8002.app.github.dev`;

interface Dataset {
  id: string;
  name: string;
  character_id: string;
  image_count: number;
  training_status?: string;
  training_progress?: number;
  runpod_job_id?: string;
  huggingface_url?: string;
  lora_download_url?: string;
  validation_prompts?: string[];
  created_at: string;
}

interface TrainingImage {
  id: string;
  image_url: string;
  caption: string;
  display_order: number;
}

interface TrainingConfig {
  gpu_type: 'rtx6000' | '5090';
  rank: 16 | 32;
  steps: number;
  lr: number;
  save_every_n_steps: number;
}

export default function Training() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [trainingImages, setTrainingImages] = useState<TrainingImage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Training config
  const [config, setConfig] = useState<TrainingConfig>({
    gpu_type: 'rtx6000', // Hardcoded - only one training pod
    rank: 16,
    steps: 2000,
    lr: 0.0002,
    save_every_n_steps: 500
  });

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Status polling
  const [statusData, setStatusData] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    loadDatasets();

    // Reload datasets when returning to this page
    const intervalId = setInterval(() => {
      loadDatasets();
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(intervalId);
  }, []);

  // Load training images when dataset is selected
  useEffect(() => {
    if (selectedDataset) {
      loadTrainingImages(selectedDataset.id);
    } else {
      setTrainingImages([]);
    }
  }, [selectedDataset]);

  // Poll for training status
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isPolling && selectedDataset?.runpod_job_id) {
      interval = setInterval(() => {
        checkTrainingStatus(selectedDataset.runpod_job_id!);
      }, 10000); // Poll every 10s
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPolling, selectedDataset]);

  const loadDatasets = async () => {
    const { data, error } = await supabase
      .from('training_datasets')
      .select('*')
      .gte('image_count', 1) // Show all datasets with at least 1 image
      .order('created_at', { ascending: false });

    if (data && !error) {
      setDatasets(data);
    }
  };

  const loadTrainingImages = async (datasetId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/datasets/${datasetId}/images`);
      const data = await response.json();
      if (data.success) {
        setTrainingImages(data.images || []);
      }
    } catch (err) {
      console.error('Failed to load training images:', err);
    }
  };

  const startTraining = async () => {
    if (!selectedDataset) return;

    setIsLoading(true);
    setError(null);

    try {
      console.log('🚀 Starting training...', {
        dataset_id: selectedDataset.id,
        config
      });

      const response = await fetch(`${API_BASE}/api/training/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDataset.id,
          ...config
        })
      });

      const responseText = await response.text();
      console.log('📥 Response:', response.status, responseText);

      if (response.ok) {
        const data = JSON.parse(responseText);
        console.log('✅ Training started!', data);

        // Start polling
        setIsPolling(true);

        // Reload datasets to get updated status
        await loadDatasets();

        // Select the dataset that's now training
        const updatedDataset = await supabase
          .from('training_datasets')
          .select('*')
          .eq('id', selectedDataset.id)
          .single();

        if (updatedDataset.data) {
          setSelectedDataset(updatedDataset.data);
        }
      } else {
        const errorMsg = `Training failed to start (${response.status}):\n\n${responseText}`;
        console.error('❌', errorMsg);
        setError(errorMsg);
      }
    } catch (error: any) {
      const errorMsg = `Error starting training: ${error.message}\n\nCheck console for details.`;
      console.error('❌ Exception:', error);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const checkTrainingStatus = async (jobId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/training/status/${jobId}`);

      if (response.ok) {
        const data = await response.json();
        setStatusData(data);

        // Stop polling if uploaded or failed (keep polling for uploading)
        if (data.status === 'uploaded' || data.status === 'failed') {
          setIsPolling(false);
          await loadDatasets();
        }
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const downloadLora = async (datasetId: string) => {
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/training/download/${datasetId}`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        alert(`✅ LoRA ready!\n\nHugging Face: ${data.huggingface_url}\n\nDirect Download: ${data.download_url}`);
        window.open(data.huggingface_url, '_blank');

        await loadDatasets();
      } else {
        const error = await response.text();
        alert(`❌ Download failed:\n${error}`);
      }
    } catch (error) {
      console.error('Error downloading LoRA:', error);
      alert(`Error: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'running': return 'text-yellow-400';
      case 'completed': return 'text-green-400';
      case 'uploading': return 'text-purple-400';
      case 'uploaded': return 'text-blue-400';
      case 'failed': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'running': return '⏳';
      case 'completed': return '✅';
      case 'uploading': return '📤';
      case 'uploaded': return '🎉';
      case 'failed': return '❌';
      default: return '⚪';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 text-white">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-2">
            LoRA Training
          </h1>
          <p className="text-gray-400">Train FLUX.1-dev LoRAs on Runpod with Kohya</p>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Left: Datasets List */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-purple-500/20 shadow-2xl">
            <h2 className="text-2xl font-bold mb-6">Datasets</h2>

            <div className="space-y-3">
              {datasets.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">📦</div>
                  <p>No datasets found</p>
                  <p className="text-sm mt-2">Create a dataset in Dataset Creator first</p>
                </div>
              ) : (
                datasets.map(ds => (
                  <button
                    key={ds.id}
                    onClick={() => {
                      setSelectedDataset(ds);
                      if (ds.runpod_job_id && (ds.training_status === 'running' || ds.training_status === 'uploading')) {
                        setIsPolling(true);
                        checkTrainingStatus(ds.runpod_job_id);
                      }
                    }}
                    className={`w-full p-4 rounded-xl border-2 transition text-left ${
                      selectedDataset?.id === ds.id
                        ? 'border-purple-500 bg-purple-500/20'
                        : 'border-gray-700 bg-slate-800/50 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-bold text-lg">{ds.name}</div>
                        <div className="text-sm text-gray-400 mt-1">
                          Character: <span className="font-mono">{ds.character_id}</span>
                        </div>
                        <div className="text-sm text-gray-400">
                          Images: {ds.image_count}
                        </div>
                      </div>
                      <div className={`text-2xl ${getStatusColor(ds.training_status)}`}>
                        {getStatusIcon(ds.training_status)}
                      </div>
                    </div>
                    <div className={`text-sm font-semibold mt-2 ${getStatusColor(ds.training_status)}`}>
                      {ds.training_status || 'not_started'}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right: Training Panel */}
          <div className="space-y-6">
            {!selectedDataset ? (
              <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-12 border border-purple-500/20 shadow-2xl text-center">
                <div className="text-6xl mb-4">👈</div>
                <p className="text-xl text-gray-400">Select a dataset to begin training</p>
              </div>
            ) : (
              <>
                {/* Dataset Info */}
                <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-purple-500/20 shadow-2xl">
                  <h2 className="text-2xl font-bold mb-4">{selectedDataset.name}</h2>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">Character</div>
                      <div className="font-mono font-bold">{selectedDataset.character_id}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Images</div>
                      <div className="font-bold">{selectedDataset.image_count}</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Status</div>
                      <div className={`font-bold ${getStatusColor(selectedDataset.training_status)}`}>
                        {selectedDataset.training_status || 'not_started'}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-400">Progress</div>
                      <div className="font-bold">{selectedDataset.training_progress || 0}%</div>
                    </div>
                  </div>

                  {/* Validation Prompts */}
                  {selectedDataset.validation_prompts && selectedDataset.validation_prompts.length > 0 && (
                    <div className="mt-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                      <div className="text-sm font-semibold mb-2">🎯 Validation Prompts:</div>
                      <div className="space-y-1">
                        {selectedDataset.validation_prompts.map((prompt, idx) => (
                          <div key={idx} className="text-xs text-gray-300">• {prompt}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Training Images Gallery */}
                {trainingImages.length > 0 && (
                  <details className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-purple-500/20 shadow-2xl">
                    <summary className="text-xl font-bold mb-4 cursor-pointer hover:text-purple-400 transition">
                      📸 Training Images ({trainingImages.length})
                    </summary>
                    <div className="mt-4 grid grid-cols-2 gap-4 max-h-[500px] overflow-y-auto">
                      {trainingImages.map((img) => (
                        <div key={img.id} className="bg-slate-900/50 rounded-lg overflow-hidden border border-gray-700">
                          <img
                            src={img.image_url}
                            alt={`Training ${img.display_order}`}
                            className="w-full aspect-square object-cover"
                          />
                          <div className="p-3">
                            <p className="text-xs text-gray-300 line-clamp-3">{img.caption}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                )}

                {/* Training Config */}
                {(!selectedDataset.training_status || selectedDataset.training_status === 'not_started' || selectedDataset.training_status === 'failed') && (
                  <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-purple-500/20 shadow-2xl">
                    <h3 className="text-xl font-bold mb-4">Training Configuration</h3>

                    {error && (
                      <div className="mb-4 p-4 bg-red-900/50 border border-red-500 rounded-lg">
                        <div className="font-bold text-red-300 mb-2">❌ Error</div>
                        <pre className="text-xs text-red-200 whitespace-pre-wrap">{error}</pre>
                      </div>
                    )}

                    <div className="space-y-4">
                      <div className="p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                        <div className="text-sm">
                          <span className="font-semibold">GPU:</span> RTX 6000 (Training Pod)
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-semibold mb-2">Training Steps</label>
                        <input
                          type="number"
                          value={config.steps}
                          onChange={(e) => setConfig({...config, steps: parseInt(e.target.value)})}
                          className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700"
                          min={100}
                          max={5000}
                          step={100}
                        />
                        <p className="text-xs text-gray-500 mt-1">Recommended: 2000-3000 steps</p>
                      </div>

                      <div>
                        <label className="block text-sm font-semibold mb-2">LoRA Rank</label>
                        <select
                          value={config.rank}
                          onChange={(e) => setConfig({...config, rank: parseInt(e.target.value) as any})}
                          className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700"
                        >
                          <option value={16}>16 (Faster, smaller file)</option>
                          <option value={32}>32 (Slower, more detail)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-semibold mb-2">Learning Rate</label>
                        <input
                          type="number"
                          value={config.lr}
                          onChange={(e) => setConfig({...config, lr: parseFloat(e.target.value)})}
                          className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700"
                          min={0.00001}
                          max={0.001}
                          step={0.00001}
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-semibold mb-2">Save Checkpoint Every</label>
                        <select
                          value={config.save_every_n_steps}
                          onChange={(e) => setConfig({...config, save_every_n_steps: parseInt(e.target.value)})}
                          className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700"
                        >
                          <option value={250}>250 steps</option>
                          <option value={500}>500 steps (Recommended)</option>
                          <option value={1000}>1000 steps</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">How often to save model checkpoints</p>
                      </div>

                      <button
                        onClick={startTraining}
                        disabled={isLoading}
                        className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl font-bold text-lg transition shadow-lg disabled:opacity-50"
                      >
                        {isLoading ? '🚀 Starting Training...' : '🚀 Start Training'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Training Progress */}
                {selectedDataset.training_status === 'running' && (
                  <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-yellow-500/20 shadow-2xl">
                    <h3 className="text-xl font-bold mb-4">🔥 Training in Progress</h3>

                    {statusData && (
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm mb-2">
                            <span>Progress</span>
                            <span className="font-bold">{statusData.progress}%</span>
                          </div>
                          <div className="h-4 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-500"
                              style={{ width: `${statusData.progress}%` }}
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <div className="text-gray-400">Current Step</div>
                            <div className="font-bold text-lg">{statusData.current_step}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">Total Steps</div>
                            <div className="font-bold text-lg">{statusData.total_steps}</div>
                          </div>
                        </div>

                        {statusData.logs && (
                          <div>
                            <div className="text-sm font-semibold mb-2">Latest Logs:</div>
                            <div className="bg-slate-900 p-3 rounded-lg font-mono text-xs text-green-400 max-h-32 overflow-y-auto">
                              {statusData.logs}
                            </div>
                          </div>
                        )}

                        <div className="text-xs text-gray-500 text-center">
                          Auto-refreshing every 10 seconds...
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Completed - Download */}
                {selectedDataset.training_status === 'completed' && (
                  <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-green-500/20 shadow-2xl">
                    <h3 className="text-xl font-bold mb-4">✅ Training Complete!</h3>

                    <p className="text-gray-300 mb-4">
                      Your LoRA model has finished training. Click below to download it and upload to Hugging Face.
                    </p>

                    <button
                      onClick={() => downloadLora(selectedDataset.id)}
                      disabled={isLoading}
                      className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl font-bold text-lg transition shadow-lg disabled:opacity-50"
                    >
                      {isLoading ? '📥 Downloading & Uploading...' : '📥 Download LoRA & Upload to HuggingFace'}
                    </button>
                  </div>
                )}

                {/* Uploaded - Links */}
                {selectedDataset.training_status === 'uploaded' && selectedDataset.huggingface_url && (
                  <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-6 border border-blue-500/20 shadow-2xl">
                    <h3 className="text-xl font-bold mb-4">🎉 LoRA Ready!</h3>

                    <div className="space-y-3">
                      <a
                        href={selectedDataset.huggingface_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block w-full py-3 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 rounded-lg font-semibold text-center transition"
                      >
                        🤗 View on Hugging Face
                      </a>

                      {selectedDataset.lora_download_url && (
                        <a
                          href={selectedDataset.lora_download_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-lg font-semibold text-center transition"
                        >
                          ⬇️ Direct Download (.safetensors)
                        </a>
                      )}
                    </div>

                    {/* Checkpoint Comparison View */}
                    {selectedDataset.checkpoints && selectedDataset.checkpoints.length > 1 && (
                      <div className="mt-6">
                        <h4 className="text-lg font-bold mb-4">📊 Checkpoint Comparison</h4>
                        <p className="text-sm text-gray-400 mb-4">
                          {selectedDataset.checkpoints.length} checkpoints saved during training
                        </p>

                        <div className="grid grid-cols-1 gap-4">
                          {selectedDataset.checkpoints.map((checkpoint: any) => (
                            <div
                              key={checkpoint.step}
                              className="bg-slate-900/50 p-4 rounded-xl border border-gray-700"
                            >
                              <div className="flex items-center justify-between mb-3">
                                <div>
                                  <span className="text-purple-400 font-bold">Step {checkpoint.step}</span>
                                  <span className="text-gray-500 text-sm ml-2">({checkpoint.size_mb} MB)</span>
                                </div>
                                <a
                                  href={`${selectedDataset.huggingface_url}/resolve/main/${checkpoint.filename}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm"
                                >
                                  Download
                                </a>
                              </div>

                              {/* Validation Images */}
                              {selectedDataset.validation_images && (
                                <div className="grid grid-cols-5 gap-2">
                                  {selectedDataset.validation_images
                                    .filter((img: any) => img.checkpoint_step === checkpoint.step)
                                    .map((img: any, idx: number) => (
                                      <div key={idx} className="relative group">
                                        <img
                                          src={img.image_url}
                                          alt={`Validation ${idx + 1}`}
                                          className="w-full aspect-square object-cover rounded border border-gray-700"
                                        />
                                        <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition p-2 rounded">
                                          <p className="text-xs text-white line-clamp-3">{img.prompt}</p>
                                        </div>
                                      </div>
                                    ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
