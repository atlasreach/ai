import { useState, useEffect } from 'react';
import {
  User, Plus, Loader, ArrowLeft, Instagram, Video, Sparkles,
  Upload, X, Image as ImageIcon, CheckCircle, Clock, Tag
} from 'lucide-react';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://${window.location.hostname.replace('5173', '8002')}`;

interface Model {
  id: string;
  name: string;
  description?: string;
  thumbnail_url?: string;
  training_status: string;
  lora_url?: string;
  lora_trigger_word?: string;
  instagram_username?: string;
  tiktok_username?: string;
  onlyfans_username?: string;
}

interface Persona {
  id: string;
  name: string;
  description?: string;
  niche?: string;
  thumbnail_url?: string;
  model_id: string;
  reference_library_id?: string;
  target_face_url: string;
  target_face_thumbnail?: string;
  target_face_name?: string;
  instagram_username?: string;
  instagram_bio?: string;
  instagram_connected: boolean;
  tiktok_username?: string;
  onlyfans_username?: string;
  default_prompt_prefix?: string;
  default_negative_prompt?: string;
  default_strength: number;
  total_generated: number;
  total_posted: number;
  created_at: string;
}

interface ReferenceLibrary {
  id: string;
  name: string;
  niche: string;
  description?: string;
  thumbnail_url?: string;
  image_count: number;
}

interface PersonaManagerProps {
  modelId: string;
  onBack: () => void;
}

export default function PersonaManager({ modelId, onBack }: PersonaManagerProps) {
  const [model, setModel] = useState<Model | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [libraries, setLibraries] = useState<ReferenceLibrary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);

  // Create persona form state
  const [newPersonaName, setNewPersonaName] = useState('');
  const [newPersonaNiche, setNewPersonaNiche] = useState('');
  const [newPersonaDescription, setNewPersonaDescription] = useState('');
  const [newPersonaTargetFaceName, setNewPersonaTargetFaceName] = useState('');
  const [newPersonaInstagram, setNewPersonaInstagram] = useState('');
  const [newPersonaTiktok, setNewPersonaTiktok] = useState('');
  const [newPersonaOnlyfans, setNewPersonaOnlyfans] = useState('');
  const [newPersonaLibraryId, setNewPersonaLibraryId] = useState('');
  const [newPersonaPromptPrefix, setNewPersonaPromptPrefix] = useState('');
  const [newPersonaStrength, setNewPersonaStrength] = useState(0.75);
  const [targetFaceFile, setTargetFaceFile] = useState<File | null>(null);
  const [targetFacePreview, setTargetFacePreview] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const niches = [
    'Gaming', 'Fitness', 'Yoga', 'Fashion', 'Travel',
    'Cooking', 'Beauty', 'Tech', 'Music', 'Art', 'Other'
  ];

  useEffect(() => {
    loadModelAndPersonas();
    loadReferenceLibraries();
  }, [modelId]);

  const loadModelAndPersonas = async () => {
    setLoading(true);
    try {
      // Load model details
      const modelResponse = await fetch(`${API_BASE}/api/persona/models/${modelId}`);
      const modelData = await modelResponse.json();
      setModel(modelData);

      // Load personas for this model
      const personasResponse = await fetch(`${API_BASE}/api/persona/models/${modelId}/personas`);
      const personasData = await personasResponse.json();
      setPersonas(personasData);
    } catch (error) {
      console.error('Failed to load model and personas:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadReferenceLibraries = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/persona/reference-libraries`);
      const data = await response.json();
      setLibraries(data);
    } catch (error) {
      console.error('Failed to load reference libraries:', error);
    }
  };

  const handleTargetFaceUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setTargetFaceFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setTargetFacePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const createPersona = async () => {
    if (!newPersonaName || !targetFaceFile) {
      alert('Please provide a persona name and target face image');
      return;
    }

    setCreating(true);
    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append('model_id', modelId);
      formData.append('name', newPersonaName);
      formData.append('target_face', targetFaceFile);

      if (newPersonaDescription) formData.append('description', newPersonaDescription);
      if (newPersonaNiche) formData.append('niche', newPersonaNiche);
      if (newPersonaLibraryId) formData.append('reference_library_id', newPersonaLibraryId);
      if (newPersonaTargetFaceName) formData.append('target_face_name', newPersonaTargetFaceName);
      if (newPersonaInstagram) formData.append('instagram_username', newPersonaInstagram);
      if (newPersonaTiktok) formData.append('tiktok_username', newPersonaTiktok);
      if (newPersonaOnlyfans) formData.append('onlyfans_username', newPersonaOnlyfans);
      if (newPersonaPromptPrefix) formData.append('default_prompt_prefix', newPersonaPromptPrefix);
      formData.append('default_strength', newPersonaStrength.toString());

      const response = await fetch(`${API_BASE}/api/persona/personas`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create persona');
      }

      // Reset form and refresh
      setShowCreateModal(false);
      resetForm();
      loadModelAndPersonas();
    } catch (error) {
      console.error('Failed to create persona:', error);
      alert('Failed to create persona: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setNewPersonaName('');
    setNewPersonaNiche('');
    setNewPersonaDescription('');
    setNewPersonaTargetFaceName('');
    setNewPersonaInstagram('');
    setNewPersonaTiktok('');
    setNewPersonaOnlyfans('');
    setNewPersonaLibraryId('');
    setNewPersonaPromptPrefix('');
    setNewPersonaStrength(0.75);
    setTargetFaceFile(null);
    setTargetFacePreview(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!model) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400">Model not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6 md:mb-8">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 md:mb-6 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Models
        </button>

        <div className="flex flex-col lg:flex-row items-start justify-between gap-4">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 w-full lg:w-auto">
            {/* Model Thumbnail */}
            <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl overflow-hidden bg-slate-800 flex-shrink-0">
              {model.thumbnail_url ? (
                <img src={model.thumbnail_url} alt={model.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <User className="w-10 h-10 sm:w-12 sm:h-12 text-slate-600" />
                </div>
              )}
            </div>

            {/* Model Info */}
            <div className="flex-1">
              <h1 className="text-2xl sm:text-3xl font-bold mb-2 capitalize">{model.name}</h1>
              {model.description && (
                <p className="text-slate-400 mb-3 text-sm sm:text-base">{model.description}</p>
              )}
              <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm">
                {model.lora_trigger_word && (
                  <div className="flex items-center gap-2">
                    <Tag className="w-4 h-4 text-slate-500" />
                    <span className="font-mono text-slate-300">{model.lora_trigger_word}</span>
                  </div>
                )}
                {model.instagram_username && (
                  <div className="flex items-center gap-2 text-pink-400">
                    <Instagram className="w-4 h-4" />
                    @{model.instagram_username}
                  </div>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-lg transition-all shadow-lg hover:shadow-blue-500/50 whitespace-nowrap"
          >
            <Plus className="w-5 h-5" />
            <span className="hidden sm:inline">Create Persona</span>
            <span className="sm:hidden">Create</span>
          </button>
        </div>
      </div>

      {/* Personas Grid */}
      <div className="max-w-7xl mx-auto">
        <div className="mb-4 md:mb-6">
          <h2 className="text-lg md:text-xl font-semibold mb-2">
            Personas ({personas.length})
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm">
            Each persona uses the base {model.name} model with a different target face and identity
          </p>
        </div>

        {personas.length === 0 ? (
          <div className="text-center py-12 md:py-16 bg-slate-900 border border-slate-800 rounded-xl">
            <Sparkles className="w-12 h-12 md:w-16 md:h-16 mx-auto mb-4 text-slate-600" />
            <h3 className="text-lg md:text-xl font-semibold mb-2 text-slate-300">No personas yet</h3>
            <p className="text-slate-400 mb-6 text-sm md:text-base px-4">
              Create your first persona to start generating content
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-2.5 md:py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-lg transition-all text-sm md:text-base"
            >
              Create First Persona
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
            {personas.map((persona) => (
              <div
                key={persona.id}
                className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-all cursor-pointer hover:shadow-lg hover:shadow-blue-500/10"
                onClick={() => setSelectedPersona(persona)}
              >
                {/* Thumbnail */}
                <div className="aspect-square bg-slate-800 flex items-center justify-center relative">
                  {persona.target_face_thumbnail || persona.target_face_url ? (
                    <img
                      src={persona.target_face_thumbnail || persona.target_face_url}
                      alt={persona.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User className="w-20 h-20 text-slate-600" />
                  )}
                  {/* Niche badge */}
                  {persona.niche && (
                    <div className="absolute top-3 right-3 px-3 py-1 bg-purple-600/90 backdrop-blur-sm rounded-full text-xs font-medium">
                      {persona.niche}
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="p-5">
                  {/* Name */}
                  <h3 className="text-lg font-semibold mb-2">{persona.name}</h3>
                  {persona.target_face_name && (
                    <p className="text-xs text-slate-400 mb-3">
                      Face: {persona.target_face_name}
                    </p>
                  )}

                  {/* Description */}
                  {persona.description && (
                    <p className="text-sm text-slate-400 mb-4 line-clamp-2">
                      {persona.description}
                    </p>
                  )}

                  {/* Social accounts */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {persona.instagram_username && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-pink-600/20 text-pink-400 rounded text-xs">
                        <Instagram className="w-3 h-3" />
                        @{persona.instagram_username}
                      </div>
                    )}
                    {persona.tiktok_username && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-slate-700 text-slate-300 rounded text-xs">
                        <Video className="w-3 h-3" />
                        @{persona.tiktok_username}
                      </div>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-800">
                    <div className="text-center">
                      <div className="text-xl font-bold text-blue-400">{persona.total_generated}</div>
                      <div className="text-xs text-slate-500">Generated</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-green-400">{persona.total_posted}</div>
                      <div className="text-xs text-slate-500">Posted</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Persona Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-2 sm:p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 sm:p-6 max-w-4xl w-full my-4 sm:my-8 max-h-[95vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4 sm:mb-6 sticky top-0 bg-slate-900 z-10 pb-2">
              <h2 className="text-xl sm:text-2xl font-bold">Create New Persona</h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5 sm:w-6 sm:h-6" />
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
              {/* Left Column: Target Face */}
              <div className="space-y-3 sm:space-y-4">
                <div>
                  <label className="block text-xs sm:text-sm font-medium mb-2">
                    Target Face Image <span className="text-red-400">*</span>
                  </label>
                  <div className="border-2 border-dashed border-slate-700 rounded-xl p-4 sm:p-6 hover:border-slate-600 transition-colors">
                    {targetFacePreview ? (
                      <div className="relative">
                        <img
                          src={targetFacePreview}
                          alt="Target face preview"
                          className="w-full h-48 sm:h-64 object-cover rounded-lg"
                        />
                        <button
                          onClick={() => {
                            setTargetFaceFile(null);
                            setTargetFacePreview(null);
                          }}
                          className="absolute top-2 right-2 p-1.5 sm:p-2 bg-red-600 hover:bg-red-700 rounded-full"
                        >
                          <X className="w-3 h-3 sm:w-4 sm:h-4" />
                        </button>
                      </div>
                    ) : (
                      <label className="cursor-pointer block text-center">
                        <Upload className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-2 sm:mb-3 text-slate-600" />
                        <p className="text-xs sm:text-sm text-slate-400 mb-1 sm:mb-2">
                          Click to upload target face
                        </p>
                        <p className="text-xs text-slate-500">
                          This face will be swapped onto generated images
                        </p>
                        <input
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handleTargetFaceUpload}
                        />
                      </label>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium mb-2">
                    Target Face Name
                  </label>
                  <input
                    type="text"
                    value={newPersonaTargetFaceName}
                    onChange={(e) => setNewPersonaTargetFaceName(e.target.value)}
                    placeholder="e.g., Edgy Gamer Face"
                    className="w-full px-3 sm:px-4 py-2 text-sm sm:text-base bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">Optional nickname for this face</p>
                </div>
              </div>

              {/* Right Column: Persona Details */}
              <div className="space-y-3 sm:space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Persona Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={newPersonaName}
                    onChange={(e) => setNewPersonaName(e.target.value)}
                    placeholder="e.g., SkylerGamerGirl"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Niche
                  </label>
                  <select
                    value={newPersonaNiche}
                    onChange={(e) => setNewPersonaNiche(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Select niche...</option>
                    {niches.map((niche) => (
                      <option key={niche} value={niche}>
                        {niche}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Reference Library
                  </label>
                  <select
                    value={newPersonaLibraryId}
                    onChange={(e) => setNewPersonaLibraryId(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    <option value="">No library (generate from scratch)</option>
                    {libraries
                      .filter((lib) => !newPersonaNiche || lib.niche === newPersonaNiche)
                      .map((lib) => (
                        <option key={lib.id} value={lib.id}>
                          {lib.name} ({lib.image_count} images)
                        </option>
                      ))}
                  </select>
                  <p className="text-xs text-slate-500 mt-1">
                    Optional: Use reference poses for generation
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Description
                  </label>
                  <textarea
                    value={newPersonaDescription}
                    onChange={(e) => setNewPersonaDescription(e.target.value)}
                    placeholder="Brief description of this persona..."
                    rows={2}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Default Prompt Prefix
                  </label>
                  <input
                    type="text"
                    value={newPersonaPromptPrefix}
                    onChange={(e) => setNewPersonaPromptPrefix(e.target.value)}
                    placeholder="e.g., gaming setup, RGB lighting,"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">Added to all generations for this persona</p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Default Strength: {newPersonaStrength.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={newPersonaStrength}
                    onChange={(e) => setNewPersonaStrength(parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    How much to use reference image (if library selected)
                  </p>
                </div>
              </div>
            </div>

            {/* Social Accounts Section */}
            <div className="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t border-slate-800">
              <h3 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">Social Media Accounts</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Instagram className="w-4 h-4 inline mr-1" />
                    Instagram
                  </label>
                  <input
                    type="text"
                    value={newPersonaInstagram}
                    onChange={(e) => setNewPersonaInstagram(e.target.value)}
                    placeholder="username"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Video className="w-4 h-4 inline mr-1" />
                    TikTok
                  </label>
                  <input
                    type="text"
                    value={newPersonaTiktok}
                    onChange={(e) => setNewPersonaTiktok(e.target.value)}
                    placeholder="username"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    OnlyFans
                  </label>
                  <input
                    type="text"
                    value={newPersonaOnlyfans}
                    onChange={(e) => setNewPersonaOnlyfans(e.target.value)}
                    placeholder="username"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-2">
                These accounts will be used for posting generated content
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 mt-4 sm:mt-6 sticky bottom-0 bg-slate-900 pt-4">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
                className="flex-1 px-4 py-2.5 sm:py-3 text-sm sm:text-base bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createPersona}
                disabled={!newPersonaName || !targetFaceFile || creating}
                className="flex-1 px-4 py-2.5 sm:py-3 text-sm sm:text-base bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 rounded-lg transition-all flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <Loader className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                    <span>Creating...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
                    <span>Create Persona</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Persona Detail Modal */}
      {selectedPersona && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-3xl w-full">
            <div className="flex items-start gap-6 mb-6">
              {/* Target Face */}
              <div className="w-48 h-48 rounded-xl overflow-hidden bg-slate-800 flex-shrink-0">
                {selectedPersona.target_face_thumbnail || selectedPersona.target_face_url ? (
                  <img
                    src={selectedPersona.target_face_thumbnail || selectedPersona.target_face_url}
                    alt={selectedPersona.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <User className="w-20 h-20 text-slate-600" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">{selectedPersona.name}</h2>
                    {selectedPersona.niche && (
                      <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm">
                        <Tag className="w-4 h-4" />
                        {selectedPersona.niche}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setSelectedPersona(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                {selectedPersona.target_face_name && (
                  <p className="text-sm text-slate-400 mb-2">
                    Target Face: {selectedPersona.target_face_name}
                  </p>
                )}

                {selectedPersona.description && (
                  <p className="text-slate-300 mb-4">{selectedPersona.description}</p>
                )}

                {/* Social accounts */}
                <div className="flex flex-wrap gap-3 mb-4">
                  {selectedPersona.instagram_username && (
                    <a
                      href={`https://instagram.com/${selectedPersona.instagram_username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-3 py-2 bg-pink-600/20 text-pink-400 hover:bg-pink-600/30 rounded-lg transition-colors"
                    >
                      <Instagram className="w-4 h-4" />
                      @{selectedPersona.instagram_username}
                    </a>
                  )}
                  {selectedPersona.tiktok_username && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-slate-700 text-slate-300 rounded-lg">
                      <Video className="w-4 h-4" />
                      @{selectedPersona.tiktok_username}
                    </div>
                  )}
                  {selectedPersona.onlyfans_username && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-blue-600/20 text-blue-400 rounded-lg">
                      @{selectedPersona.onlyfans_username}
                    </div>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">{selectedPersona.total_generated}</div>
                    <div className="text-xs text-slate-400 mt-1">Generated</div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{selectedPersona.total_posted}</div>
                    <div className="text-xs text-slate-400 mt-1">Posted</div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">
                      {selectedPersona.default_strength.toFixed(2)}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">Strength</div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">
                      {selectedPersona.instagram_connected ? (
                        <CheckCircle className="w-6 h-6 inline" />
                      ) : (
                        <Clock className="w-6 h-6 inline" />
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">Connected</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Generation Settings */}
            {selectedPersona.default_prompt_prefix && (
              <div className="bg-slate-800 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Default Prompt Prefix</h3>
                <p className="text-sm font-mono text-slate-300">{selectedPersona.default_prompt_prefix}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center justify-center gap-2">
                <Sparkles className="w-5 h-5" />
                Generate Content
              </button>
              <button className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors flex items-center justify-center gap-2">
                <ImageIcon className="w-5 h-5" />
                View Gallery
              </button>
              <button
                onClick={() => setSelectedPersona(null)}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
