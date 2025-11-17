import { useState, useEffect } from 'react';
import { Plus, Edit2, Folder, CheckCircle, Clock, Trash2, ExternalLink, Database } from 'lucide-react';
import { supabase } from '../lib/supabase';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://vigilant-rotary-phone-7v5g5q99jpjjfw57w-8002.app.github.dev`;

interface Model {
  id: string;
  name: string;
  trigger_word: string;
  defining_features: Record<string, string>;
  huggingface_repo: string | null;
  is_active: boolean;
  created_at: string;
  dataset_count?: number;
}

interface Dataset {
  id: string;
  name: string;
  dataset_type: string;
  image_count: number;
  training_status: string;
  lora_filename: string | null;
}

interface Props {
  onNavigateToDatasets?: () => void;
  onNavigateToDataset?: (datasetId: string) => void;
}

export default function ModelManager({ onNavigateToDatasets, onNavigateToDataset }: Props) {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Form state for creating/editing
  const [formData, setFormData] = useState({
    name: '',
    trigger_word: '',
    huggingface_repo: '',
  });

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModel) {
      loadDatasets(selectedModel.id);
    }
  }, [selectedModel]);

  const loadModels = async () => {
    setIsLoading(true);
    const { data, error } = await supabase
      .from('models')
      .select('*')
      .order('created_at', { ascending: false });

    if (data) {
      // Get dataset counts for each model
      const modelsWithCounts = await Promise.all(
        data.map(async (model) => {
          const { count } = await supabase
            .from('datasets')
            .select('*', { count: 'exact', head: true })
            .eq('model_id', model.id);
          return { ...model, dataset_count: count || 0 };
        })
      );
      setModels(modelsWithCounts);
    }

    if (error) console.error('Error loading models:', error);
    setIsLoading(false);
  };

  const loadDatasets = async (modelId: string) => {
    const { data, error } = await supabase
      .from('datasets')
      .select('*')
      .eq('model_id', modelId)
      .order('created_at', { ascending: false });

    if (data) setDatasets(data);
    if (error) console.error('Error loading datasets:', error);
  };

  const createModel = async () => {
    if (!formData.name || !formData.trigger_word) {
      alert('Please fill in model name and trigger word');
      return;
    }

    const { data, error } = await supabase
      .from('models')
      .insert([
        {
          name: formData.name,
          trigger_word: formData.trigger_word.toLowerCase(),
          huggingface_repo: formData.huggingface_repo || null,
          defining_features: {},
          is_active: true,
        },
      ])
      .select()
      .single();

    if (error) {
      alert('Error creating model: ' + error.message);
      return;
    }

    if (data) {
      setModels([data, ...models]);
      setIsCreating(false);
      setFormData({ name: '', trigger_word: '', huggingface_repo: '' });
      setSelectedModel(data);
    }
  };

  const deleteModel = async (modelId: string, e: React.MouseEvent) => {
    console.log('Delete model clicked:', modelId);
    e.stopPropagation(); // Prevent selecting the model when clicking delete

    if (!confirm('Are you sure you want to delete this model? This will also delete all associated datasets and images.')) {
      console.log('Delete cancelled by user');
      return;
    }

    console.log('Sending DELETE request to:', `${API_BASE}/api/models/${modelId}`);

    try {
      const response = await fetch(`${API_BASE}/api/models/${modelId}`, {
        method: 'DELETE',
      });

      console.log('DELETE response status:', response.status);

      if (!response.ok) {
        throw new Error('Failed to delete model');
      }

      // Remove from state
      setModels(models.filter(m => m.id !== modelId));

      // Clear selection if deleted model was selected
      if (selectedModel?.id === modelId) {
        setSelectedModel(null);
        setDatasets([]);
      }

      alert('Model deleted successfully');
      console.log('Model deleted successfully');
    } catch (error) {
      console.error('Error deleting model:', error);
      alert('Failed to delete model: ' + (error as Error).message);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'trained':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'ready_to_train':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'training':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    return status === 'trained' ? CheckCircle : Clock;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-slate-400">Loading models...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Model Manager</h1>
          <p className="text-slate-400 mt-1">Manage your AI character models and datasets</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all duration-200 shadow-lg shadow-blue-500/20"
        >
          <Plus className="w-5 h-5" />
          Create New Model
        </button>
      </div>

      {/* Create Model Modal */}
      {isCreating && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-4">Create New Model</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Model Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Milan, Sara"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Trigger Word
                </label>
                <input
                  type="text"
                  value={formData.trigger_word}
                  onChange={(e) => setFormData({ ...formData, trigger_word: e.target.value })}
                  placeholder="e.g., milan, sara"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">Used in captions and prompts</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  HuggingFace Repo (Optional)
                </label>
                <input
                  type="text"
                  value={formData.huggingface_repo}
                  onChange={(e) => setFormData({ ...formData, huggingface_repo: e.target.value })}
                  placeholder="e.g., username/model-name"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setIsCreating(false)}
                className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createModel}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all"
              >
                Create Model
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {models.map((model) => (
          <div
            key={model.id}
            onClick={() => setSelectedModel(model)}
            className={`
              p-6 rounded-xl border cursor-pointer transition-all duration-200
              ${selectedModel?.id === model.id
                ? 'bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/30 shadow-lg shadow-blue-500/10'
                : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
              }
            `}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-white">{model.name}</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Trigger: <span className="text-blue-400 font-mono">{model.trigger_word}</span>
                </p>
              </div>
              <div className="flex items-center gap-2">
                {model.is_active && (
                  <span className="px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded-full border border-green-500/30">
                    Active
                  </span>
                )}
                <button
                  onClick={(e) => deleteModel(model.id, e)}
                  className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Delete model"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Defining Features */}
            {Object.keys(model.defining_features).length > 0 && (
              <div className="mb-4">
                <div className="text-xs font-medium text-slate-500 mb-2">Defining Features:</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(model.defining_features).slice(0, 3).map(([key, value]) => (
                    <span
                      key={key}
                      className="px-2 py-1 bg-slate-800 text-slate-300 text-xs rounded-md"
                    >
                      {value}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1 text-slate-400">
                <Folder className="w-4 h-4" />
                <span>{model.dataset_count || 0} datasets</span>
              </div>
              {model.huggingface_repo && (
                <a
                  href={`https://huggingface.co/${model.huggingface_repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>HuggingFace</span>
                </a>
              )}
            </div>
          </div>
        ))}

        {models.length === 0 && (
          <div className="col-span-2 text-center py-12 text-slate-400">
            <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No models yet. Create your first model to get started!</p>
          </div>
        )}
      </div>

      {/* Selected Model Details */}
      {selectedModel && (
        <div className="mt-8 p-6 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">
              {selectedModel.name} - Datasets
            </h2>
            <button
              onClick={() => onNavigateToDatasets?.()}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Dataset
            </button>
          </div>

          {datasets.length > 0 ? (
            <div className="space-y-3">
              {datasets.map((dataset) => {
                const StatusIcon = getStatusIcon(dataset.training_status);
                return (
                  <div
                    key={dataset.id}
                    onClick={() => onNavigateToDataset?.(dataset.id)}
                    className="p-4 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="font-medium text-white">{dataset.name}</h3>
                          <span className="px-2 py-0.5 bg-slate-700 text-slate-300 text-xs rounded">
                            {dataset.dataset_type}
                          </span>
                          <span
                            className={`px-2 py-0.5 text-xs rounded border ${getStatusColor(
                              dataset.training_status
                            )}`}
                          >
                            <StatusIcon className="w-3 h-3 inline mr-1" />
                            {dataset.training_status.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                          <span>{dataset.image_count} images</span>
                          {dataset.lora_filename && (
                            <span className="font-mono text-xs text-blue-400">
                              {dataset.lora_filename}
                            </span>
                          )}
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <Folder className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No datasets for this model yet.</p>
              <p className="text-sm mt-1">Create your first dataset to start training!</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
