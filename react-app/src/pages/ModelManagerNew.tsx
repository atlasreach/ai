import { useState, useEffect } from 'react';
import { User, Plus, Loader, Users, Image, CheckCircle, Clock, AlertCircle } from 'lucide-react';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://${window.location.hostname.replace('5173', '8002')}`;

interface Model {
  id: string;
  name: string;
  description?: string;
  thumbnail_url?: string;
  training_status: 'not_started' | 'training' | 'complete';
  lora_url?: string;
  lora_trigger_word?: string;
  training_notes?: string;
  instagram_username?: string;
  tiktok_username?: string;
  onlyfans_username?: string;
  created_at: string;
  updated_at: string;
  persona_count: number;
  total_generated: number;
  total_posted: number;
}

export default function ModelManagerNew() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);

  // Form state
  const [newModelName, setNewModelName] = useState('');
  const [newModelDescription, setNewModelDescription] = useState('');
  const [newInstagramUsername, setNewInstagramUsername] = useState('');
  const [newTiktokUsername, setNewTiktokUsername] = useState('');
  const [newOnlyfansUsername, setNewOnlyfansUsername] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/persona/models`);
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    } finally {
      setLoading(false);
    }
  };

  const createModel = async () => {
    if (!newModelName) return;

    setCreating(true);
    try {
      const response = await fetch(`${API_BASE}/api/persona/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newModelName,
          description: newModelDescription || undefined,
          instagram_username: newInstagramUsername || undefined,
          tiktok_username: newTiktokUsername || undefined,
          onlyfans_username: newOnlyfansUsername || undefined,
        }),
      });

      if (response.ok) {
        setShowCreateModal(false);
        setNewModelName('');
        setNewModelDescription('');
        setNewInstagramUsername('');
        setNewTiktokUsername('');
        setNewOnlyfansUsername('');
        fetchModels();
      }
    } catch (error) {
      console.error('Failed to create model:', error);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return (
          <div className="flex items-center gap-1 text-green-400 text-xs">
            <CheckCircle className="w-3 h-3" />
            Trained
          </div>
        );
      case 'training':
        return (
          <div className="flex items-center gap-1 text-yellow-400 text-xs">
            <Clock className="w-3 h-3 animate-spin" />
            Training
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1 text-slate-400 text-xs">
            <AlertCircle className="w-3 h-3" />
            Not Started
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Model Manager</h1>
            <p className="text-slate-400">
              Manage your AI models and personas
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Create Model
          </button>
        </div>
      </div>

      {/* Models Grid */}
      <div className="max-w-7xl mx-auto">
        {models.length === 0 ? (
          <div className="text-center py-16">
            <User className="w-16 h-16 mx-auto mb-4 text-slate-600" />
            <h3 className="text-xl font-semibold mb-2 text-slate-300">No models yet</h3>
            <p className="text-slate-400 mb-6">Create your first model to get started</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Create Your First Model
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {models.map((model) => (
              <div
                key={model.id}
                className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-colors cursor-pointer"
                onClick={() => setSelectedModel(model)}
              >
                {/* Thumbnail */}
                <div className="aspect-video bg-slate-800 flex items-center justify-center">
                  {model.thumbnail_url ? (
                    <img
                      src={model.thumbnail_url}
                      alt={model.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User className="w-16 h-16 text-slate-600" />
                  )}
                </div>

                {/* Content */}
                <div className="p-5">
                  {/* Name & Status */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-lg font-semibold capitalize">{model.name}</h3>
                      {model.lora_trigger_word && (
                        <p className="text-xs text-slate-400 mt-1">
                          Trigger: {model.lora_trigger_word}
                        </p>
                      )}
                    </div>
                    {getStatusBadge(model.training_status)}
                  </div>

                  {/* Description */}
                  {model.description && (
                    <p className="text-sm text-slate-400 mb-4 line-clamp-2">
                      {model.description}
                    </p>
                  )}

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3 pt-4 border-t border-slate-800">
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                        <Users className="w-4 h-4" />
                      </div>
                      <div className="text-lg font-semibold">{model.persona_count}</div>
                      <div className="text-xs text-slate-500">Personas</div>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                        <Image className="w-4 h-4" />
                      </div>
                      <div className="text-lg font-semibold">{model.total_generated}</div>
                      <div className="text-xs text-slate-500">Generated</div>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center gap-1 text-green-400 mb-1">
                        <CheckCircle className="w-4 h-4" />
                      </div>
                      <div className="text-lg font-semibold">{model.total_posted}</div>
                      <div className="text-xs text-slate-500">Posted</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Model Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Create New Model</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Model Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newModelName}
                  onChange={(e) => setNewModelName(e.target.value)}
                  placeholder="e.g., Skyler Mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Instagram Username
                </label>
                <input
                  type="text"
                  value={newInstagramUsername}
                  onChange={(e) => setNewInstagramUsername(e.target.value)}
                  placeholder="e.g., skyler_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  For scraping training data (optional)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  TikTok Username
                </label>
                <input
                  type="text"
                  value={newTiktokUsername}
                  onChange={(e) => setNewTiktokUsername(e.target.value)}
                  placeholder="e.g., skyler_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  For scraping training data (optional)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  OnlyFans Username
                </label>
                <input
                  type="text"
                  value={newOnlyfansUsername}
                  onChange={(e) => setNewOnlyfansUsername(e.target.value)}
                  placeholder="e.g., skyler_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-slate-500 mt-1">
                  For scraping training data (optional)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Description
                </label>
                <textarea
                  value={newModelDescription}
                  onChange={(e) => setNewModelDescription(e.target.value)}
                  placeholder="Optional description..."
                  rows={3}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createModel}
                disabled={!newModelName || creating}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Model'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Model Detail Modal */}
      {selectedModel && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-2xl w-full">
            <h2 className="text-2xl font-bold mb-4 capitalize">{selectedModel.name}</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-400">Training Status</p>
                  <div className="mt-1">{getStatusBadge(selectedModel.training_status)}</div>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Trigger Word</p>
                  <p className="mt-1 font-mono text-sm">{selectedModel.lora_trigger_word || 'Not set'}</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800">
                <div>
                  <p className="text-sm text-slate-400">Personas</p>
                  <p className="text-2xl font-bold mt-1">{selectedModel.persona_count}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Generated</p>
                  <p className="text-2xl font-bold mt-1">{selectedModel.total_generated}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Posted</p>
                  <p className="text-2xl font-bold mt-1 text-green-400">{selectedModel.total_posted}</p>
                </div>
              </div>

              {selectedModel.description && (
                <div className="pt-4 border-t border-slate-800">
                  <p className="text-sm text-slate-400 mb-2">Description</p>
                  <p className="text-sm">{selectedModel.description}</p>
                </div>
              )}

              {selectedModel.lora_url && (
                <div className="pt-4 border-t border-slate-800">
                  <p className="text-sm text-slate-400 mb-2">LoRA URL</p>
                  <p className="text-xs font-mono bg-slate-800 p-2 rounded break-all">
                    {selectedModel.lora_url}
                  </p>
                </div>
              )}
            </div>

            <button
              onClick={() => setSelectedModel(null)}
              className="mt-6 w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
