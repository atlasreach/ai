import { useState, useEffect } from 'react';
import { User, Plus, Loader, ArrowRight, ArrowLeft, Upload } from 'lucide-react';
import PersonaManager from './PersonaManager';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://${window.location.hostname.replace('5173', '8002')}`;

interface Model {
  id: string;
  name: string;
  first_name?: string;
  last_name?: string;
  thumbnail_url?: string;
  instagram_username?: string;
  tiktok_username?: string;
  onlyfans_username?: string;
  created_at: string;
}

export default function ModelManagerNew() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);

  // Multi-step form
  const [step, setStep] = useState(1);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [profileImage, setProfileImage] = useState<File | null>(null);
  const [profileImagePreview, setProfileImagePreview] = useState<string | null>(null);
  const [instagramUsername, setInstagramUsername] = useState('');
  const [tiktokUsername, setTiktokUsername] = useState('');
  const [onlyfansUsername, setOnlyfansUsername] = useState('');
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

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setProfileImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfileImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const resetForm = () => {
    setStep(1);
    setFirstName('');
    setLastName('');
    setProfileImage(null);
    setProfileImagePreview(null);
    setInstagramUsername('');
    setTiktokUsername('');
    setOnlyfansUsername('');
    setCreating(false);
    setEditingModel(null);
  };

  const createModel = async () => {
    if (!firstName || !lastName) return;

    setCreating(true);
    try {
      // Create model
      const modelData: any = {
        name: `${firstName} ${lastName}`.toLowerCase(),
        first_name: firstName,
        last_name: lastName,
        instagram_username: instagramUsername?.trim() || undefined,
        tiktok_username: tiktokUsername?.trim() || undefined,
        onlyfans_username: onlyfansUsername?.trim() || undefined,
      };

      const response = await fetch(`${API_BASE}/api/persona/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(modelData),
      });

      if (response.ok) {
        const newModel = await response.json();

        // Upload profile image if provided
        if (profileImage) {
          const formData = new FormData();
          formData.append('file', profileImage);

          await fetch(`${API_BASE}/api/persona/models/${newModel.id}/upload-thumbnail`, {
            method: 'POST',
            body: formData,
          });
        }

        setShowCreateModal(false);
        resetForm();
        fetchModels();

        // Navigate to persona manager for the new model
        setSelectedModelId(newModel.id);
      }
    } catch (error) {
      console.error('Failed to create model:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleEdit = (model: Model) => {
    setEditingModel(model);
    setFirstName(model.first_name || '');
    setLastName(model.last_name || '');
    setInstagramUsername(model.instagram_username || '');
    setTiktokUsername(model.tiktok_username || '');
    setOnlyfansUsername(model.onlyfans_username || '');
    setProfileImagePreview(model.thumbnail_url || null);
    setShowEditModal(true);
  };

  const updateModel = async () => {
    if (!editingModel || !firstName || !lastName) return;

    setCreating(true);
    try {
      const modelData: any = {
        name: `${firstName} ${lastName}`.toLowerCase(),
        first_name: firstName,
        last_name: lastName,
        instagram_username: instagramUsername?.trim() || undefined,
        tiktok_username: tiktokUsername?.trim() || undefined,
        onlyfans_username: onlyfansUsername?.trim() || undefined,
      };

      const response = await fetch(`${API_BASE}/api/persona/models/${editingModel.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(modelData),
      });

      if (response.ok) {
        // Upload profile image if provided
        if (profileImage) {
          const formData = new FormData();
          formData.append('file', profileImage);

          await fetch(`${API_BASE}/api/persona/models/${editingModel.id}/upload-thumbnail`, {
            method: 'POST',
            body: formData,
          });
        }

        setShowEditModal(false);
        resetForm();
        fetchModels();
      }
    } catch (error) {
      console.error('Failed to update model:', error);
    } finally {
      setCreating(false);
    }
  };

  const nextStep = () => {
    if (step === 1 && firstName && lastName) {
      setStep(2);
    }
  };

  const prevStep = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  // If a model is selected, show PersonaManager
  if (selectedModelId) {
    return (
      <PersonaManager
        modelId={selectedModelId}
        onBack={() => {
          setSelectedModelId(null);
          fetchModels();
        }}
      />
    );
  }

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
            <h1 className="text-3xl font-bold mb-2">Models</h1>
            <p className="text-slate-400">
              Manage your AI models
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {models.map((model) => (
              <div
                key={model.id}
                className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-colors group relative"
              >
                {/* Edit button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(model);
                  }}
                  className="absolute top-2 right-2 p-2 bg-slate-800/90 hover:bg-blue-600 rounded-lg transition-colors opacity-0 group-hover:opacity-100 z-10"
                  title="Edit model"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                    <path d="m15 5 4 4"/>
                  </svg>
                </button>

                <div
                  className="cursor-pointer"
                  onClick={() => setSelectedModelId(model.id)}
                >
                  {/* Profile Picture */}
                  <div className="aspect-square bg-slate-800 flex items-center justify-center">
                    {model.thumbnail_url ? (
                      <img
                        src={model.thumbnail_url}
                        alt={model.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User className="w-20 h-20 text-slate-600 group-hover:text-slate-500 transition-colors" />
                    )}
                  </div>

                  {/* Name */}
                  <div className="p-4 text-center">
                    <h3 className="text-lg font-semibold capitalize truncate">
                      {model.name || (model.first_name && model.last_name
                        ? `${model.first_name} ${model.last_name}`
                        : 'Unnamed Model')}
                    </h3>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Model Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full my-8 max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-bold mb-4">
              {step === 1 ? 'Create Model - Name & Photo' : 'Create Model - Socials'}
            </h2>

            <div className="overflow-y-auto flex-1 pr-2">
              {/* Step 1: Name & Photo */}
              {step === 1 && (
                <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    First Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g., Skylar"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Last Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g., Mae"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Profile Picture
                  </label>
                  <div className="flex flex-col items-center gap-4">
                    {profileImagePreview && (
                      <div className="w-32 h-32 rounded-lg overflow-hidden">
                        <img
                          src={profileImagePreview}
                          alt="Preview"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                    <label className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors cursor-pointer flex items-center justify-center gap-2">
                      <Upload className="w-4 h-4" />
                      {profileImage ? 'Change Photo' : 'Upload Photo'}
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageSelect}
                        className="hidden"
                      />
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Socials */}
            {step === 2 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Instagram Username
                  </label>
                  <input
                    type="text"
                    value={instagramUsername}
                    onChange={(e) => setInstagramUsername(e.target.value)}
                    placeholder="e.g., skylar_mae"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Optional - You can scrape Instagram data later from the Instagram Library page
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    TikTok Username
                  </label>
                  <input
                    type="text"
                    value={tiktokUsername}
                    onChange={(e) => setTiktokUsername(e.target.value)}
                    placeholder="e.g., skylar_mae"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    OnlyFans Username
                  </label>
                  <input
                    type="text"
                    value={onlyfansUsername}
                    onChange={(e) => setOnlyfansUsername(e.target.value)}
                    placeholder="e.g., skylar_mae"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            )}
            </div>

            {/* Navigation Buttons */}
            <div className="flex gap-3 mt-6 pt-4 border-t border-slate-800 flex-shrink-0">
              {step > 1 && (
                <button
                  onClick={prevStep}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </button>
              )}

              <button
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>

              {step === 1 ? (
                <button
                  onClick={nextStep}
                  disabled={!firstName || !lastName}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  Next
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={createModel}
                  disabled={creating}
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
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit Model Modal */}
      {showEditModal && editingModel && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full my-8 max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-bold mb-4">Edit Model</h2>

            <div className="space-y-4 overflow-y-auto flex-1 pr-2">
              <div>
                <label className="block text-sm font-medium mb-2">
                  First Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="e.g., Skylar"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Last Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="e.g., Mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Profile Picture
                </label>
                <div className="flex flex-col items-center gap-4">
                  {profileImagePreview && (
                    <div className="w-32 h-32 rounded-lg overflow-hidden">
                      <img
                        src={profileImagePreview}
                        alt="Preview"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  <label className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors cursor-pointer flex items-center justify-center gap-2">
                    <Upload className="w-4 h-4" />
                    {profileImage ? 'Change Photo' : 'Upload New Photo'}
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageSelect}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Instagram Username
                </label>
                <input
                  type="text"
                  value={instagramUsername}
                  onChange={(e) => setInstagramUsername(e.target.value)}
                  placeholder="e.g., skylar_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  TikTok Username
                </label>
                <input
                  type="text"
                  value={tiktokUsername}
                  onChange={(e) => setTiktokUsername(e.target.value)}
                  placeholder="e.g., skylar_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  OnlyFans Username
                </label>
                <input
                  type="text"
                  value={onlyfansUsername}
                  onChange={(e) => setOnlyfansUsername(e.target.value)}
                  placeholder="e.g., skylar_mae"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6 pt-4 border-t border-slate-800 flex-shrink-0">
              <button
                onClick={() => {
                  setShowEditModal(false);
                  resetForm();
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>

              <button
                onClick={updateModel}
                disabled={creating || !firstName || !lastName}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {creating ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  'Update Model'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
