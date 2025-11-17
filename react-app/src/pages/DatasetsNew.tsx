import { useState, useEffect, useCallback } from 'react';
import { Plus, Loader, Database, Image as ImageIcon, Download, Trash2, Upload, Instagram, ArrowRight, ArrowLeft, Sparkles } from 'lucide-react';
// import DatasetEditor from './DatasetEditor'; // TODO: Add back dataset editor

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://${window.location.hostname.replace('5173', '8002')}`;

interface Model {
  id: string;
  name: string;
  first_name?: string;
  last_name?: string;
  thumbnail_url?: string;
}

interface Dataset {
  id: string;
  name: string;
  type: 'training' | 'content_generation';
  model_id: string;
  description?: string;
  image_count: number;
  created_at: string;
  updated_at: string;
}

interface InstagramPost {
  id: string;
  display_url: string;
  caption?: string;
  post_type: 'Image' | 'Video' | 'Sidecar';
}

export default function Datasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [filterModelId, setFilterModelId] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  // const [editingDatasetId, setEditingDatasetId] = useState<string | null>(null); // TODO: Add back when dataset editor is restored

  // Create wizard state
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [type, setType] = useState<'training' | 'content_generation'>('training');
  const [modelId, setModelId] = useState('');
  const [description, setDescription] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [instagramPosts, setInstagramPosts] = useState<InstagramPost[]>([]);
  const [selectedPostIds, setSelectedPostIds] = useState<Set<string>>(new Set());
  const [generating, setGenerating] = useState(false);
  const [captioning, setCaptioning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // ALL HOOKS MUST BE HERE - before any function definitions
  useEffect(() => {
    loadDatasets();
    loadModels();
  }, [filterModelId, filterType]);

  // Load Instagram posts when model is selected
  useEffect(() => {
    if (modelId && step === 3) {
      loadInstagramPosts(modelId);
    }
  }, [modelId, step]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setUploadedFiles(prev => [...prev, ...Array.from(files)]);
    }
  }, []);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      let url = `${API_BASE}/api/datasets`;
      const params = new URLSearchParams();
      if (filterModelId) params.append('model_id', filterModelId);
      if (filterType) params.append('type', filterType);
      if (params.toString()) url += `?${params.toString()}`;

      const response = await fetch(url);
      const data = await response.json();
      setDatasets(data);
    } catch (error) {
      console.error('Failed to load datasets:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/persona/models`);
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadInstagramPosts = async (modelId: string) => {
    setGenerating(true);
    try {
      const response = await fetch(`${API_BASE}/api/persona/models/${modelId}/instagram-posts`);
      const data = await response.json();

      if (data.success && data.posts) {
        const imagePosts = data.posts.filter((post: InstagramPost) =>
          post.post_type === 'Image' || post.post_type === 'Sidecar' || post.post_type === 'Video'
        );
        setInstagramPosts(imagePosts);
      } else {
        setInstagramPosts([]);
      }
    } catch (error) {
      console.error('Failed to load Instagram posts:', error);
      setInstagramPosts([]);
    } finally {
      setGenerating(false);
    }
  };

  const generateCaptions = async () => {
    setCaptioning(true);
    // TODO: Implement Grok captioning
    // For now, just wait a bit
    await new Promise(resolve => setTimeout(resolve, 1000));
    setCaptioning(false);
    // Move to next step after captioning
    createDataset();
  };

  const createDataset = async () => {
    if (!name || !modelId) return;

    // Check that we have images
    const hasImages = uploadedFiles.length > 0 || selectedPostIds.size > 0;
    if (!hasImages) {
      alert('Please add at least one image before creating the dataset');
      return;
    }

    setCreating(true);
    try {
      // Step 1: Create the dataset
      const createResponse = await fetch(`${API_BASE}/api/datasets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          type,
          model_id: modelId,
          description
        }),
      });

      if (!createResponse.ok) {
        throw new Error('Failed to create dataset');
      }

      const datasetData = await createResponse.json();
      const datasetId = datasetData.id;

      // Step 2: Upload files
      if (uploadedFiles.length > 0) {
        const formData = new FormData();
        uploadedFiles.forEach((file) => {
          if (file.name.endsWith('.zip')) {
            // It's a ZIP file
            formData.append('file', file);
          } else {
            // Regular image
            formData.append('files', file);
          }
        });

        // Check if we have a ZIP file
        const hasZip = uploadedFiles.some(f => f.name.endsWith('.zip'));

        if (hasZip) {
          // Upload ZIP
          const zipFile = uploadedFiles.find(f => f.name.endsWith('.zip'));
          const zipFormData = new FormData();
          zipFormData.append('file', zipFile!);

          await fetch(`${API_BASE}/api/datasets/${datasetId}/upload-zip`, {
            method: 'POST',
            body: zipFormData,
          });

          // Upload other images
          const imageFiles = uploadedFiles.filter(f => !f.name.endsWith('.zip'));
          if (imageFiles.length > 0) {
            const imageFormData = new FormData();
            imageFiles.forEach(f => imageFormData.append('files', f));

            await fetch(`${API_BASE}/api/datasets/${datasetId}/upload`, {
              method: 'POST',
              body: imageFormData,
            });
          }
        } else {
          // Just upload images
          await fetch(`${API_BASE}/api/datasets/${datasetId}/upload`, {
            method: 'POST',
            body: formData,
          });
        }
      }

      // Step 3: Add Instagram images if any
      if (selectedPostIds.size > 0) {
        const imagesToAdd = Array.from(selectedPostIds).map(postId => {
          const post = instagramPosts.find(p => p.id === postId);
          return {
            source: 'instagram',
            image_url: post!.display_url,
            instagram_post_id: postId,
            caption: post!.caption
          };
        });

        await fetch(`${API_BASE}/api/datasets/${datasetId}/images/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(imagesToAdd),
        });
      }

      // Success!
      setShowCreateModal(false);
      resetForm();
      loadDatasets();

    } catch (error) {
      console.error('Failed to create dataset:', error);
      alert('Failed to create dataset. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const deleteDataset = async (id: string, datasetName: string) => {
    if (!confirm(`Delete dataset "${datasetName}"? This will remove all images.`)) return;

    try {
      const response = await fetch(`${API_BASE}/api/datasets/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadDatasets();
      }
    } catch (error) {
      console.error('Failed to delete dataset:', error);
    }
  };

  const downloadDataset = async (id: string, datasetName: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/datasets/${id}/download`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${datasetName}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download dataset:', error);
      alert('Failed to download dataset');
    }
  };

  const resetForm = () => {
    setStep(1);
    setName('');
    setType('training');
    setModelId('');
    setDescription('');
    setUploadedFiles([]);
    setSelectedPostIds(new Set());
    setInstagramPosts([]);
  };

  const getModelName = (model_id: string) => {
    const model = models.find(m => m.id === model_id);
    if (!model) return 'Unknown Model';
    return model.first_name && model.last_name
      ? `${model.first_name} ${model.last_name}`
      : model.name;
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadedImageCount = uploadedFiles.filter(f => !f.name.endsWith('.zip')).length;
  const uploadedZipCount = uploadedFiles.filter(f => f.name.endsWith('.zip')).length;
  const totalFromUploads = uploadedImageCount + uploadedZipCount;
  const totalImageCount = totalFromUploads + selectedPostIds.size;

  // If editing a dataset, show the editor
  // TODO: Add back dataset editor functionality
  // if (editingDatasetId) {
  //   return (
  //     <DatasetEditor
  //       datasetId={editingDatasetId}
  //       onBack={() => {
  //         setEditingDatasetId(null);
  //         loadDatasets();
  //       }}
  //     />
  //   );
  // }

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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-2">Datasets</h1>
            <p className="text-slate-400">
              Manage training and content generation datasets
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Create Dataset
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-4">
          <select
            value={filterModelId}
            onChange={(e) => setFilterModelId(e.target.value)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
          >
            <option value="">All Models</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.first_name && model.last_name
                  ? `${model.first_name} ${model.last_name}`
                  : model.name}
              </option>
            ))}
          </select>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
          >
            <option value="">All Types</option>
            <option value="training">Training</option>
            <option value="content_generation">Content Generation</option>
          </select>
        </div>
      </div>

      {/* Datasets Grid */}
      <div className="max-w-7xl mx-auto">
        {datasets.length === 0 ? (
          <div className="text-center py-16">
            <Database className="w-16 h-16 mx-auto mb-4 text-slate-600" />
            <h3 className="text-xl font-semibold mb-2 text-slate-300">No datasets yet</h3>
            <p className="text-slate-400 mb-6">Create your first dataset to get started</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Create Your First Dataset
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {datasets.map((dataset) => (
              <div
                key={dataset.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors group relative"
              >
                <div className="absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-300">
                  {dataset.type === 'training' ? 'Training' : 'Content Gen'}
                </div>

                <div className="w-12 h-12 bg-slate-800 rounded-lg flex items-center justify-center mb-4">
                  {dataset.type === 'training' ? (
                    <Database className="w-6 h-6 text-blue-400" />
                  ) : (
                    <ImageIcon className="w-6 h-6 text-purple-400" />
                  )}
                </div>

                <h3 className="text-lg font-semibold mb-2 truncate">{dataset.name}</h3>

                <p className="text-sm text-slate-400 mb-3">
                  Model: {getModelName(dataset.model_id)}
                </p>

                {dataset.description && (
                  <p className="text-sm text-slate-500 mb-4 line-clamp-2">
                    {dataset.description}
                  </p>
                )}

                <div className="flex items-center gap-4 text-sm text-slate-400 mb-4">
                  <div className="flex items-center gap-1">
                    <ImageIcon className="w-4 h-4" />
                    <span>{dataset.image_count} images</span>
                  </div>
                </div>

                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => alert('Dataset editor temporarily disabled. Edit functionality coming soon!')}
                    className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm transition-colors"
                  >
                    Open
                  </button>
                  <button
                    onClick={() => downloadDataset(dataset.id, dataset.name)}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                    title="Download as ZIP"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteDataset(dataset.id, dataset.name)}
                    className="px-3 py-2 bg-slate-800 hover:bg-red-600 rounded-lg transition-colors"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal - 3-Step Wizard */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-4xl w-full max-h-[90vh] flex flex-col">
            <h2 className="text-xl font-bold mb-4">
              {step === 1 && 'Create Dataset - Basic Info'}
              {step === 2 && 'Upload Files'}
              {step === 3 && 'Add from Instagram (Optional)'}
              {step === 4 && 'Generate Captions'}
            </h2>

            {/* Progress Indicator */}
            <div className="flex gap-2 mb-6">
              <div className={`flex-1 h-1 rounded ${step >= 1 ? 'bg-blue-500' : 'bg-slate-700'}`} />
              <div className={`flex-1 h-1 rounded ${step >= 2 ? 'bg-blue-500' : 'bg-slate-700'}`} />
              <div className={`flex-1 h-1 rounded ${step >= 3 ? 'bg-blue-500' : 'bg-slate-700'}`} />
              <div className={`flex-1 h-1 rounded ${step >= 4 ? 'bg-blue-500' : 'bg-slate-700'}`} />
            </div>

            <div className="flex-1 overflow-y-auto">
              {/* Step 1: Basic Info */}
              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Dataset Name <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g., Milan Training Set V1"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Model <span className="text-red-400">*</span>
                    </label>
                    <select
                      value={modelId}
                      onChange={(e) => setModelId(e.target.value)}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Select a model</option>
                      {models.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.first_name && model.last_name
                            ? `${model.first_name} ${model.last_name}`
                            : model.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Type <span className="text-red-400">*</span>
                    </label>
                    <select
                      value={type}
                      onChange={(e) => setType(e.target.value as 'training' | 'content_generation')}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    >
                      <option value="training">Training</option>
                      <option value="content_generation">Content Generation</option>
                    </select>
                    <p className="text-xs text-slate-500 mt-1">
                      Training: For LoRA training | Content Gen: Reference images for generation
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Description (Optional)
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Describe this dataset..."
                      rows={3}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500 resize-none"
                    />
                  </div>
                </div>
              )}

              {/* Step 2: Upload Files */}
              {step === 2 && (
                <div className="space-y-6">
                  <div
                    className={`border-2 border-dashed rounded-xl p-12 transition-colors ${
                      dragActive
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-700 bg-slate-900/50'
                    }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                  >
                    <div className="flex flex-col items-center gap-4">
                      <Upload className="w-16 h-16 text-slate-500" />
                      <div className="text-center">
                        <p className="text-xl font-medium mb-2">
                          Drop images or ZIP files here
                        </p>
                        <p className="text-slate-500 mb-4">
                          Upload individual images or a ZIP file containing multiple images
                        </p>
                      </div>

                      <label className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer transition-colors text-lg">
                        <Upload className="w-5 h-5" />
                        Choose Files
                        <input
                          type="file"
                          multiple
                          accept="image/*,.zip"
                          onChange={(e) => e.target.files && setUploadedFiles(prev => [...prev, ...Array.from(e.target.files!)])}
                          className="hidden"
                        />
                      </label>
                    </div>
                  </div>

                  {/* Uploaded Files Preview */}
                  {uploadedFiles.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium mb-3">
                        Uploaded: {uploadedImageCount} image{uploadedImageCount !== 1 ? 's' : ''}
                        {uploadedZipCount > 0 && ` + ${uploadedZipCount} ZIP file${uploadedZipCount !== 1 ? 's' : ''}`}
                      </h3>
                      <div className="grid grid-cols-4 gap-3">
                        {uploadedFiles.map((file, index) => (
                          <div key={index} className="relative group">
                            {file.name.endsWith('.zip') ? (
                              <div className="aspect-square bg-purple-500/20 border border-purple-500/50 rounded-lg flex flex-col items-center justify-center p-3">
                                <Database className="w-8 h-8 text-purple-400 mb-2" />
                                <p className="text-xs text-center truncate w-full">{file.name}</p>
                              </div>
                            ) : (
                              <div className="aspect-square bg-slate-800 rounded-lg overflow-hidden">
                                <img
                                  src={URL.createObjectURL(file)}
                                  alt={file.name}
                                  className="w-full h-full object-cover"
                                />
                              </div>
                            )}
                            <button
                              onClick={() => removeFile(index)}
                              className="absolute -top-2 -right-2 p-1.5 bg-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: Instagram Selection */}
              {step === 3 && (
                <div className="space-y-6">
                  {generating ? (
                    <div className="text-center py-12">
                      <Loader className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
                      <p className="text-slate-400">Loading Instagram posts...</p>
                    </div>
                  ) : instagramPosts.length === 0 ? (
                    <div className="text-center py-12">
                      <Instagram className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                      <h3 className="text-lg font-semibold mb-2">No Instagram posts available</h3>
                      <p className="text-slate-400 mb-4">
                        This model doesn't have any scraped Instagram posts yet
                      </p>
                      <p className="text-sm text-slate-500">
                        You can skip this step and continue with the uploaded files
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-medium">Select Instagram Posts</h3>
                        <p className="text-sm text-slate-400">
                          {selectedPostIds.size} selected from {instagramPosts.length} posts
                        </p>
                      </div>
                      <div className="grid grid-cols-4 gap-3 max-h-96 overflow-y-auto">
                        {instagramPosts.map((post) => {
                          const isSelected = selectedPostIds.has(post.id);
                          return (
                            <div
                              key={post.id}
                              onClick={() => {
                                const newSelected = new Set(selectedPostIds);
                                if (isSelected) {
                                  newSelected.delete(post.id);
                                } else {
                                  newSelected.add(post.id);
                                }
                                setSelectedPostIds(newSelected);
                              }}
                              className={`relative aspect-square rounded-lg overflow-hidden cursor-pointer border-2 transition-all ${
                                isSelected
                                  ? 'border-pink-500 scale-95'
                                  : 'border-transparent hover:border-slate-600'
                              }`}
                            >
                              <img
                                src={post.display_url}
                                alt="Instagram post"
                                className="w-full h-full object-cover"
                              />
                              {isSelected && (
                                <div className="absolute inset-0 bg-pink-500/30 flex items-center justify-center">
                                  <div className="w-8 h-8 bg-pink-500 rounded-full flex items-center justify-center">
                                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Step 4: Generate Captions */}
              {step === 4 && (
                <div className="text-center py-12">
                  <Sparkles className="w-16 h-16 mx-auto mb-4 text-purple-500" />
                  <h3 className="text-2xl font-bold mb-2">Generate Captions with Grok</h3>
                  <p className="text-slate-400 mb-6">
                    Automatically generate training captions for {totalImageCount} images
                  </p>
                  <div className="max-w-md mx-auto bg-slate-800/50 rounded-lg p-6">
                    <p className="text-sm text-slate-300 mb-4">
                      Grok AI will analyze each image and generate descriptive captions for training
                    </p>
                    <div className="text-xs text-slate-500">
                      <p>✓ {totalFromUploads} from uploads</p>
                      <p>✓ {selectedPostIds.size} from Instagram</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer Buttons */}
            <div className="flex gap-3 mt-6 pt-4 border-t border-slate-800">
              {step > 1 && (
                <button
                  onClick={() => setStep(step - 1)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
                  disabled={creating || captioning}
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
                disabled={creating || captioning}
              >
                Cancel
              </button>

              {step === 1 && (
                <button
                  onClick={() => setStep(2)}
                  disabled={!name || !modelId}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  Next: Upload Files
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {step === 2 && (
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {totalFromUploads > 0 ? 'Next: Instagram (Optional)' : 'Skip to Instagram'}
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}

              {step === 3 && (
                <>
                  <button
                    onClick={() => setStep(4)}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {selectedPostIds.size > 0 ? 'Next: Generate Captions' : 'Skip to Captions'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </>
              )}

              {step === 4 && (
                <button
                  onClick={generateCaptions}
                  disabled={captioning || creating}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {captioning ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      Generating Captions...
                    </>
                  ) : creating ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      Creating Dataset...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Captions & Create
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
