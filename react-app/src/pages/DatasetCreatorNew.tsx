import { useState, useEffect } from 'react';
import { Upload, Sparkles, Check, Download, Edit2, Save, X, Folder, ArrowLeft, Plus, Trash2, Copy, Instagram } from 'lucide-react';
import { supabase } from '../lib/supabase';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://vigilant-rotary-phone-7v5g5q99jpjjfw57w-8002.app.github.dev`;

interface Model {
  id: string;
  name: string;
  trigger_word: string;
  defining_features: Record<string, string>;
}

interface Dataset {
  id: string;
  model_id: string;
  name: string;
  dataset_type: string;
  description: string | null;
  image_count: number;
  training_status: string;
}

interface UploadedImage {
  file: File;
  preview: string;
  url?: string;
  caption?: string;
  id?: string;
}

type Step = 'list-datasets' | 'select-model' | 'analyze-features' | 'create-dataset' | 'scrape-instagram' | 'upload-images' | 'generate-captions';

interface DatasetCreatorProps {
  viewDatasetId?: string | null;
}

export default function DatasetCreatorNew({ viewDatasetId }: DatasetCreatorProps = {}) {
  const [step, setStep] = useState<Step>('list-datasets');
  const [models, setModels] = useState<Model[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [isNewModel, setIsNewModel] = useState(false);
  const [isLoadingDatasets, setIsLoadingDatasets] = useState(true);

  // Feature analysis
  const [analyzedFeatures, setAnalyzedFeatures] = useState<Record<string, string>>({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Dataset creation
  const [datasetName, setDatasetName] = useState('');
  const [datasetType, setDatasetType] = useState<'SFW' | 'NSFW'>('SFW');
  const [datasetDescription, setDatasetDescription] = useState('');
  const [currentDataset, setCurrentDataset] = useState<Dataset | null>(null);

  // Image upload
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedImages, setSelectedImages] = useState<Set<number>>(new Set());

  // Caption generation
  const [isGenerating, setIsGenerating] = useState(false);
  const [editingCaptionId, setEditingCaptionId] = useState<string | null>(null);
  const [editedCaption, setEditedCaption] = useState('');
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [regenerateFeedback, setRegenerateFeedback] = useState('');

  // Test captions for AI Toolkit
  const [testCaptions, setTestCaptions] = useState<string[]>([]);

  // Instagram scraping
  const [instagramUsername, setInstagramUsername] = useState('');
  const [numPosts, setNumPosts] = useState(20);
  const [isScraping, setIsScraping] = useState(false);
  const [createMethod, setCreateMethod] = useState<'upload' | 'instagram'>('upload');

  useEffect(() => {
    loadModels();
    loadDatasets();
  }, []);

  // Auto-load dataset when viewDatasetId is provided
  useEffect(() => {
    if (viewDatasetId) {
      loadDatasetById(viewDatasetId);
    }
  }, [viewDatasetId]);

  const loadDatasetById = async (datasetId: string) => {
    const { data: datasetData } = await supabase
      .from('datasets')
      .select('*')
      .eq('id', datasetId)
      .single();

    if (datasetData) {
      await openExistingDataset(datasetData);
    }
  };

  const loadModels = async () => {
    const { data } = await supabase.from('models').select('*').order('created_at', { ascending: false });
    if (data) setModels(data);
  };

  const loadDatasets = async () => {
    setIsLoadingDatasets(true);
    const { data } = await supabase
      .from('datasets')
      .select('*, models(name, trigger_word)')
      .order('created_at', { ascending: false });
    if (data) setDatasets(data as any);
    setIsLoadingDatasets(false);
  };

  const openExistingDataset = async (dataset: Dataset) => {
    // Load the model
    const { data: modelData } = await supabase
      .from('models')
      .select('*')
      .eq('id', dataset.model_id)
      .single();

    if (modelData) {
      setSelectedModel(modelData);
    }

    setCurrentDataset(dataset);

    // Load existing images
    const { data: imageData } = await supabase
      .from('dataset_images')
      .select('*')
      .eq('dataset_id', dataset.id)
      .order('display_order');

    if (imageData) {
      const loadedImages: UploadedImage[] = imageData.map((img) => ({
        file: null as any, // No file object for existing images
        preview: img.image_url,
        url: img.image_url,
        caption: img.caption,
        id: img.id,
      }));
      setImages(loadedImages);
    }

    // Go to caption generation step (where images are shown)
    setStep('generate-captions');
  };

  // Step 1: Select or Create Model
  const handleModelSelect = (model: Model) => {
    setSelectedModel(model);
    setAnalyzedFeatures(model.defining_features || {});
    setStep('create-dataset');
  };

  const handleNewModel = () => {
    setIsNewModel(true);
    setStep('upload-images');
  };

  // Step 2: Analyze Features (for new models)
  const analyzeFeatures = async () => {
    if (images.length === 0) {
      alert('Please upload at least 3-5 images first');
      return;
    }

    setIsAnalyzing(true);

    try {
      // Pick 3-5 sample images
      const sampleImages = images.slice(0, Math.min(5, images.length));
      const imageUrls = sampleImages.map(img => img.url).filter(Boolean);

      const response = await fetch(`${API_BASE}/api/analyze-features`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_urls: imageUrls }),
      });

      const data = await response.json();

      if (data.features) {
        setAnalyzedFeatures(data.features);
        setStep('analyze-features');
      }
    } catch (error) {
      console.error('Error analyzing features:', error);
      alert('Failed to analyze features. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const saveFeatures = async () => {
    if (!selectedModel) return;

    await supabase
      .from('models')
      .update({ defining_features: analyzedFeatures })
      .eq('id', selectedModel.id);

    setStep('create-dataset');
  };

  // Step 3: Create Dataset
  const createDataset = async () => {
    if (!datasetName || !selectedModel) {
      alert('Please fill in dataset name');
      return;
    }

    const { data, error } = await supabase
      .from('datasets')
      .insert([
        {
          model_id: selectedModel.id,
          name: datasetName,
          dataset_type: datasetType,
          description: datasetDescription || null,
          image_count: 0,
          training_status: 'preparing',
        },
      ])
      .select()
      .single();

    if (error) {
      alert('Error creating dataset: ' + error.message);
      return;
    }

    if (data) {
      setCurrentDataset(data);
      loadDatasets(); // Reload dataset list

      // Go to Instagram scraping or upload based on method
      if (createMethod === 'instagram') {
        setStep('scrape-instagram');
      } else {
        setStep('upload-images');
      }
    }
  };

  // Instagram scraping function
  const scrapeInstagram = async () => {
    if (!instagramUsername || !currentDataset || !selectedModel) {
      alert('Please enter an Instagram username');
      return;
    }

    setIsScraping(true);

    try {
      const response = await fetch(`${API_BASE}/api/scrape-instagram`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instagram_username: instagramUsername,
          model_id: selectedModel.id,
          dataset_name: currentDataset.name,
          num_posts: numPosts,
        }),
      });

      const data = await response.json();

      if (data.success) {
        alert(data.message);

        // Load the scraped images
        const { data: imageData } = await supabase
          .from('dataset_images')
          .select('*')
          .eq('dataset_id', currentDataset.id)
          .order('display_order');

        if (imageData) {
          const loadedImages: UploadedImage[] = imageData.map((img) => ({
            file: null as any,
            preview: img.image_url,
            url: img.image_url,
            caption: img.caption,
            id: img.id,
          }));
          setImages(loadedImages);
        }

        // Move to captions step
        setStep('generate-captions');
      } else {
        alert('Failed to scrape Instagram: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error scraping Instagram:', error);
      alert('Failed to scrape Instagram. Please try again.');
    } finally {
      setIsScraping(false);
    }
  };

  // Step 4: Upload Images
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    const newImages: UploadedImage[] = files.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
    }));

    setImages([...images, ...newImages]);
  };

  const uploadImages = async () => {
    if (!currentDataset || images.length === 0) return;

    setIsUploading(true);

    try {
      for (let i = 0; i < images.length; i++) {
        const img = images[i];
        if (img.url) continue; // Already uploaded

        // Upload to Supabase Storage
        const fileExt = img.file.name.split('.').pop();
        const fileName = `${currentDataset.id}/${Date.now()}_${i}.${fileExt}`;

        const { data: uploadData, error: uploadError } = await supabase.storage
          .from('training-images')
          .upload(fileName, img.file);

        if (uploadError) throw uploadError;

        // Get public URL
        const { data: urlData } = supabase.storage
          .from('training-images')
          .getPublicUrl(fileName);

        // Save to database
        const { data: imageRecord, error: dbError } = await supabase
          .from('dataset_images')
          .insert([
            {
              dataset_id: currentDataset.id,
              image_url: urlData.publicUrl,
              caption: '',
              display_order: i,
            },
          ])
          .select()
          .single();

        if (dbError) throw dbError;

        // Update local state
        const updatedImages = [...images];
        updatedImages[i] = { ...img, url: urlData.publicUrl, id: imageRecord.id };
        setImages(updatedImages);
      }

      // Update dataset image count
      await supabase
        .from('datasets')
        .update({ image_count: images.length, training_status: 'ready_to_train' })
        .eq('id', currentDataset.id);

      setStep('generate-captions');

      // Auto-generate captions after upload
      alert('Images uploaded! Automatically generating captions...');
      await generateCaptions();
    } catch (error) {
      console.error('Error uploading images:', error);
      alert('Failed to upload images. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  // Step 5: Generate Single Caption
  const generateSingleCaption = async (imageId: string, feedback?: string) => {
    if (!currentDataset || !selectedModel) return;

    try {
      // Get the image data
      const { data: imageData } = await supabase
        .from('dataset_images')
        .select('*')
        .eq('id', imageId)
        .single();

      if (!imageData) return;

      // Build caption prompt
      const trigger_word = selectedModel.trigger_word;
      const defining_features = selectedModel.defining_features || {};

      const feature_parts = [];
      for (const [key, value] of Object.entries(defining_features)) {
        if (key !== 'other' && value) {
          feature_parts.push(value);
        }
      }

      const base_template = feature_parts.length > 0
        ? `${trigger_word}, ${feature_parts.join(', ')}`
        : trigger_word;

      let prompt = `You are captioning training images for an AI model.

The character is: ${base_template}

Describe what's happening in this image in 10-15 words. Focus on:
- Pose/action
- Clothing/outfit
- Setting/background
- Lighting/mood

Format: "${base_template}, [your description]"

Be concise and factual. No commentary.`;

      // Add feedback if regenerating
      if (feedback && feedback.trim()) {
        prompt += `\n\nPrevious caption: "${imageData.caption}"\n\nUser feedback: ${feedback}\n\nGenerate a new caption addressing this feedback.`;
      }

      // Call Grok via our API endpoint
      const response = await fetch(`${API_BASE}/api/datasets/${currentDataset.id}/generate-caption/${imageId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (response.ok) {
        const data = await response.json();

        // Update local state
        const updatedImages = images.map((img) =>
          img.id === imageId ? { ...img, caption: data.caption } : img
        );
        setImages(updatedImages);

        // Clear regenerate state
        setRegeneratingId(null);
        setRegenerateFeedback('');
      }
    } catch (error) {
      console.error('Error generating caption:', error);
      alert('Failed to generate caption. Please try again.');
    }
  };

  // Step 5: Generate All Captions (only for images without captions)
  const generateCaptions = async () => {
    if (!currentDataset || !selectedModel) return;

    setIsGenerating(true);

    try {
      // Get images that don't have captions yet
      const { data: imageData } = await supabase
        .from('dataset_images')
        .select('*')
        .eq('dataset_id', currentDataset.id)
        .order('display_order');

      const imagesToCaption = imageData?.filter(img => !img.caption || img.caption.trim() === '') || [];

      if (imagesToCaption.length === 0) {
        alert('All images already have captions!');
        setIsGenerating(false);
        return;
      }

      alert(`Generating captions for ${imagesToCaption.length} images...`);

      const response = await fetch(`${API_BASE}/api/datasets/${currentDataset.id}/generate-all-captions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();

      if (data.success) {
        // Reload images with captions
        const { data: updatedImageData } = await supabase
          .from('dataset_images')
          .select('*')
          .eq('dataset_id', currentDataset.id)
          .order('display_order');

        if (updatedImageData) {
          const updatedImages = images.map((img, i) => ({
            ...img,
            caption: updatedImageData[i]?.caption || img.caption || '',
            id: updatedImageData[i]?.id || img.id,
          }));
          setImages(updatedImages);
        }

        // Set test captions
        if (data.test_captions && data.test_captions.length > 0) {
          setTestCaptions(data.test_captions);
        }

        alert(`Successfully generated ${data.updated_count} captions!${data.test_captions ? '\n\n10 test captions generated for AI Toolkit!' : ''}`);
      }
    } catch (error) {
      console.error('Error generating captions:', error);
      alert('Failed to generate captions. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const updateCaption = async (imageId: string, newCaption: string) => {
    await supabase
      .from('dataset_images')
      .update({ caption: newCaption })
      .eq('id', imageId);

    const updatedImages = images.map((img) =>
      img.id === imageId ? { ...img, caption: newCaption } : img
    );
    setImages(updatedImages);
    setEditingCaptionId(null);
  };

  const downloadDataset = async () => {
    if (!currentDataset) return;

    try {
      const response = await fetch(`${API_BASE}/api/datasets/${currentDataset.id}/download`);

      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get the blob from response
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentDataset.name}.zip`;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      alert('Failed to download dataset. Please try again.');
    }
  };

  const copyAllTestCaptions = () => {
    const text = testCaptions.join('\n');
    navigator.clipboard.writeText(text);
    alert('All test captions copied to clipboard!');
  };

  const copySingleCaption = (caption: string) => {
    navigator.clipboard.writeText(caption);
    alert('Caption copied!');
  };

  const deleteDataset = async (datasetId: string, datasetName: string) => {
    if (!confirm(`Are you sure you want to delete "${datasetName}"? This cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/datasets/${datasetId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Reload datasets list
        await loadDatasets();
        alert('Dataset deleted successfully!');
      } else {
        throw new Error('Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete dataset. Please try again.');
    }
  };

  const deleteImage = async (imageIndex: number) => {
    if (!confirm('Delete this image?')) {
      return;
    }

    const updatedImages = images.filter((_, i) => i !== imageIndex);
    setImages(updatedImages);

    // If image was already uploaded to database, delete it
    const imgToDelete = images[imageIndex];
    if (imgToDelete.id) {
      try {
        await supabase.table('dataset_images').delete().eq('id', imgToDelete.id);

        // Update dataset image count
        if (currentDataset) {
          await supabase
            .from('datasets')
            .update({ image_count: updatedImages.length })
            .eq('id', currentDataset.id);
        }
      } catch (error) {
        console.error('Error deleting image:', error);
      }
    }
  };

  const toggleImageSelection = (imageIndex: number) => {
    const newSelected = new Set(selectedImages);
    if (newSelected.has(imageIndex)) {
      newSelected.delete(imageIndex);
    } else {
      newSelected.add(imageIndex);
    }
    setSelectedImages(newSelected);
  };

  const selectAllImages = () => {
    const allIndices = new Set(images.map((_, i) => i));
    setSelectedImages(allIndices);
  };

  const deselectAllImages = () => {
    setSelectedImages(new Set());
  };

  const deleteSelectedImages = async () => {
    if (selectedImages.size === 0) {
      alert('No images selected');
      return;
    }

    if (!confirm(`Delete ${selectedImages.size} selected image(s)?`)) {
      return;
    }

    // Get indices to delete (sorted in descending order to avoid index issues)
    const indicesToDelete = Array.from(selectedImages).sort((a, b) => b - a);

    // Delete from database if already uploaded
    const imagesToDelete = indicesToDelete.map(i => images[i]).filter(img => img.id);
    if (imagesToDelete.length > 0) {
      try {
        const imageIds = imagesToDelete.map(img => img.id);
        await supabase.table('dataset_images').delete().in('id', imageIds);
      } catch (error) {
        console.error('Error deleting images from database:', error);
      }
    }

    // Filter out selected images
    const updatedImages = images.filter((_, i) => !selectedImages.has(i));
    setImages(updatedImages);

    // Update dataset image count
    if (currentDataset) {
      try {
        await supabase
          .from('datasets')
          .update({ image_count: updatedImages.length })
          .eq('id', currentDataset.id);
      } catch (error) {
        console.error('Error updating dataset count:', error);
      }
    }

    // Clear selection
    setSelectedImages(new Set());
    setIsMultiSelectMode(false);
  };

  return (
    <div className="space-y-6">
      {/* Header with Progress */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Dataset Creator</h1>
            <p className="text-slate-400 mt-1">Create training datasets with AI-powered captioning</p>
          </div>
          {step !== 'list-datasets' && (
            <button
              onClick={() => {
                setStep('list-datasets');
                setImages([]);
                setCurrentDataset(null);
                setSelectedModel(null);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Datasets
            </button>
          )}
        </div>

        {/* Progress Steps - Only show when not on list view */}
        {step !== 'list-datasets' && (
          <div className="mt-6 flex items-center gap-2">
            {(['select-model', 'create-dataset', 'upload-images', 'generate-captions'] as Step[]).map((s, i) => {
              const isActive = step === s;
              const isCompleted =
                (['select-model', 'create-dataset', 'upload-images', 'generate-captions'] as Step[]).indexOf(step) >
                i;

              return (
                <div key={s} className="flex items-center">
                  <div
                    className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    ${isCompleted
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : isActive
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'bg-slate-800 text-slate-500 border border-slate-700'
                    }
                  `}
                  >
                    {isCompleted ? <Check className="w-4 h-4" /> : i + 1}
                  </div>
                  {i < 3 && (
                    <div
                      className={`w-12 h-0.5 ${
                        isCompleted ? 'bg-green-500/30' : 'bg-slate-700'
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Step Content */}
      {step === 'list-datasets' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Your Datasets</h2>
            <button
              onClick={() => setStep('select-model')}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all duration-200 shadow-lg shadow-blue-500/20"
            >
              <Plus className="w-5 h-5" />
              Create New Dataset
            </button>
          </div>

          {isLoadingDatasets ? (
            <div className="text-center py-12 text-slate-400">Loading datasets...</div>
          ) : datasets.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {datasets.map((dataset) => (
                <div
                  key={dataset.id}
                  className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl hover:border-slate-700 transition-colors group relative"
                >
                  {/* Delete button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteDataset(dataset.id, dataset.name);
                    }}
                    className="absolute top-3 right-3 p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div
                    onClick={() => openExistingDataset(dataset)}
                    className="cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-3 pr-8">
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">
                          {dataset.name}
                        </h3>
                        <p className="text-sm text-slate-400 mt-1">
                          Model: {(dataset as any).models?.name || 'Unknown'}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded-full border ${
                          dataset.dataset_type === 'NSFW'
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : 'bg-green-500/10 text-green-400 border-green-500/30'
                        }`}
                      >
                        {dataset.dataset_type}
                      </span>
                    </div>

                  <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
                    <div className="flex items-center gap-1">
                      <Folder className="w-4 h-4" />
                      <span>{dataset.image_count} images</span>
                    </div>
                    <span
                      className={`px-2 py-0.5 text-xs rounded ${
                        dataset.training_status === 'trained'
                          ? 'bg-green-500/10 text-green-400'
                          : dataset.training_status === 'ready_to_train'
                          ? 'bg-blue-500/10 text-blue-400'
                          : 'bg-slate-500/10 text-slate-400'
                      }`}
                    >
                      {dataset.training_status.replace('_', ' ')}
                    </span>
                  </div>

                  {dataset.lora_filename && (
                    <div className="text-xs font-mono text-blue-400 bg-slate-800/50 px-2 py-1 rounded">
                      {dataset.lora_filename}
                    </div>
                  )}

                    {dataset.description && (
                      <p className="text-xs text-slate-500 mt-2 line-clamp-2">{dataset.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 border-2 border-dashed border-slate-700 rounded-xl">
              <Folder className="w-12 h-12 mx-auto text-slate-500 mb-3" />
              <p className="text-slate-400 mb-4">No datasets yet</p>
              <button
                onClick={() => setStep('select-model')}
                className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600"
              >
                Create Your First Dataset
              </button>
            </div>
          )}
        </div>
      )}

      {step === 'select-model' && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Select a Model</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => handleModelSelect(model)}
                className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl hover:border-slate-700 transition-colors text-left"
              >
                <h3 className="text-lg font-bold text-white">{model.name}</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Trigger: <span className="text-blue-400">{model.trigger_word}</span>
                </p>
              </button>
            ))}

            <button
              onClick={handleNewModel}
              className="p-6 bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl hover:border-blue-500/50 transition-colors"
            >
              <div className="text-blue-400 text-2xl mb-2">+</div>
              <h3 className="text-lg font-bold text-white">Create New Model</h3>
              <p className="text-sm text-slate-400 mt-1">Start with fresh dataset</p>
            </button>
          </div>
        </div>
      )}

      {step === 'analyze-features' && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Review Defining Features</h2>
          <p className="text-slate-400">Grok analyzed your images. Edit if needed:</p>

          <div className="space-y-3">
            {Object.entries(analyzedFeatures).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <input
                  type="text"
                  value={key}
                  readOnly
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 w-32"
                />
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setAnalyzedFeatures({ ...analyzedFeatures, [key]: e.target.value })}
                  className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                />
              </div>
            ))}
          </div>

          <button
            onClick={saveFeatures}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600"
          >
            Continue
          </button>
        </div>
      )}

      {step === 'create-dataset' && (
        <div className="max-w-2xl space-y-4">
          <h2 className="text-xl font-bold text-white">Create Dataset</h2>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Dataset Name</label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g., milan_instagram_v1"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Type</label>
            <div className="flex gap-3">
              {(['SFW', 'NSFW'] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setDatasetType(type)}
                  className={`px-6 py-2 rounded-lg border transition-colors ${
                    datasetType === type
                      ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Data Source</label>
            <div className="flex gap-3">
              <button
                onClick={() => setCreateMethod('upload')}
                className={`flex-1 p-4 rounded-lg border transition-colors text-left ${
                  createMethod === 'upload'
                    ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <Upload className="w-6 h-6 mb-2" />
                <div className="font-medium">Upload Files</div>
                <div className="text-xs opacity-75">Upload images from your device</div>
              </button>
              <button
                onClick={() => setCreateMethod('instagram')}
                className={`flex-1 p-4 rounded-lg border transition-colors text-left ${
                  createMethod === 'instagram'
                    ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                }`}
              >
                <Instagram className="w-6 h-6 mb-2" />
                <div className="font-medium">Scrape Instagram</div>
                <div className="text-xs opacity-75">Auto-import from Instagram account</div>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Description (Optional)</label>
            <textarea
              value={datasetDescription}
              onChange={(e) => setDatasetDescription(e.target.value)}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white h-24"
              placeholder="Notes about this dataset..."
            />
          </div>

          <button
            onClick={createDataset}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600"
          >
            Create & Continue
          </button>
        </div>
      )}

      {step === 'scrape-instagram' && (
        <div className="max-w-2xl space-y-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Instagram className="w-6 h-6 text-pink-500" />
            Scrape Instagram Account
          </h2>

          <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300">
              Enter an Instagram username to automatically import posts and images into your dataset.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Instagram Username</label>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">@</span>
              <input
                type="text"
                value={instagramUsername}
                onChange={(e) => setInstagramUsername(e.target.value)}
                placeholder="officialskylarmaexo"
                className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Number of Posts to Scrape
            </label>
            <input
              type="number"
              value={numPosts}
              onChange={(e) => setNumPosts(parseInt(e.target.value) || 20)}
              min="1"
              max="100"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
            <p className="text-xs text-slate-400 mt-1">
              Cost: ~${((numPosts / 1000) * 0.5).toFixed(3)} (using your free $5 credit)
            </p>
          </div>

          <button
            onClick={scrapeInstagram}
            disabled={isScraping || !instagramUsername}
            className="w-full px-6 py-3 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-lg hover:from-pink-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Instagram className="w-5 h-5" />
            {isScraping ? 'Scraping Instagram...' : `Scrape @${instagramUsername || 'username'}`}
          </button>

          {isScraping && (
            <div className="text-center text-sm text-slate-400">
              <p>This may take 10-30 seconds depending on the number of posts...</p>
            </div>
          )}
        </div>
      )}

      {step === 'upload-images' && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Upload Images</h2>

          <div className="border-2 border-dashed border-slate-700 rounded-xl p-12 text-center hover:border-slate-600 transition-colors">
            <Upload className="w-12 h-12 mx-auto text-slate-500 mb-4" />
            <p className="text-slate-300 mb-2">Drag & drop images or click to browse</p>
            <p className="text-sm text-slate-500 mb-4">Recommended: 20-30 images</p>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-block px-6 py-2 bg-slate-800 text-slate-300 rounded-lg cursor-pointer hover:bg-slate-700"
            >
              Select Files
            </label>
          </div>

          {images.length > 0 && (
            <>
              {/* Multi-select controls */}
              <div className="flex items-center justify-between p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      setIsMultiSelectMode(!isMultiSelectMode);
                      if (isMultiSelectMode) {
                        setSelectedImages(new Set());
                      }
                    }}
                    className={`px-3 py-1.5 rounded-lg transition-colors ${
                      isMultiSelectMode
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {isMultiSelectMode ? 'Exit Select Mode' : 'Select Multiple'}
                  </button>

                  {isMultiSelectMode && (
                    <>
                      <button
                        onClick={selectAllImages}
                        className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors"
                      >
                        Select All ({images.length})
                      </button>
                      <button
                        onClick={deselectAllImages}
                        className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors"
                      >
                        Deselect All
                      </button>
                    </>
                  )}
                </div>

                {isMultiSelectMode && selectedImages.size > 0 && (
                  <button
                    onClick={deleteSelectedImages}
                    className="flex items-center gap-2 px-4 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete Selected ({selectedImages.size})
                  </button>
                )}
              </div>

              <div className="grid grid-cols-4 gap-4">
                {images.map((img, i) => (
                  <div
                    key={i}
                    className={`relative aspect-square rounded-lg overflow-hidden bg-slate-800 group cursor-pointer transition-all ${
                      selectedImages.has(i) ? 'ring-4 ring-blue-500' : ''
                    }`}
                    onClick={() => isMultiSelectMode && toggleImageSelection(i)}
                  >
                    <img src={img.preview} alt={`Upload ${i + 1}`} className="w-full h-full object-cover" />

                    {/* Upload success checkmark */}
                    {img.url && !isMultiSelectMode && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                        <Check className="w-4 h-4 text-white" />
                      </div>
                    )}

                    {/* Multi-select checkbox */}
                    {isMultiSelectMode && (
                      <div className="absolute top-2 right-2">
                        <div className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all ${
                          selectedImages.has(i)
                            ? 'bg-blue-500 border-blue-500'
                            : 'bg-slate-700/80 border-slate-400'
                        }`}>
                          {selectedImages.has(i) && <Check className="w-4 h-4 text-white" />}
                        </div>
                      </div>
                    )}

                    {/* Individual delete button (only visible when NOT in multi-select mode) */}
                    {!isMultiSelectMode && (
                      <button
                        onClick={() => deleteImage(i)}
                        className="absolute top-2 left-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                        title="Delete image"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={uploadImages}
                disabled={isUploading}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 disabled:opacity-50"
              >
                {isUploading ? 'Uploading...' : `Upload ${images.length} Images`}
              </button>
            </>
          )}
        </div>
      )}

      {step === 'generate-captions' && (
        <div className="space-y-4">
          {/* Dataset Info Banner */}
          {currentDataset && (
            <div className="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-white">{currentDataset.name}</h3>
                  <div className="flex items-center gap-3 mt-1 text-sm text-slate-400">
                    <span>Model: {selectedModel?.name}</span>
                    <span>•</span>
                    <span>{currentDataset.dataset_type}</span>
                    <span>•</span>
                    <span>{images.length} images</span>
                    <span>•</span>
                    <span className="text-blue-400">
                      {images.filter(img => img.caption).length} captioned
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Generate Captions</h2>
            <div className="flex gap-3">
              {!isGenerating && images.some(img => img.caption) && (
                <button
                  onClick={downloadDataset}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  <Download className="w-4 h-4" />
                  Download Dataset
                </button>
              )}
              <button
                onClick={generateCaptions}
                disabled={isGenerating}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                {isGenerating ? 'Generating...' : 'Generate All Captions'}
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {images.map((img) => (
              <div key={img.id} className="flex gap-4 p-4 bg-slate-900/50 border border-slate-800 rounded-lg">
                <img src={img.preview} alt="" className="w-24 h-24 object-cover rounded-lg flex-shrink-0" />
                <div className="flex-1">
                  {editingCaptionId === img.id ? (
                    <div className="flex gap-2">
                      <textarea
                        value={editedCaption}
                        onChange={(e) => setEditedCaption(e.target.value)}
                        className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                        rows={3}
                      />
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => updateCaption(img.id!, editedCaption)}
                          className="p-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                        >
                          <Save className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingCaptionId(null)}
                          className="p-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ) : regeneratingId === img.id ? (
                    <div className="space-y-2">
                      <p className="text-slate-400 text-sm">Current: {img.caption || 'No caption'}</p>
                      <textarea
                        value={regenerateFeedback}
                        onChange={(e) => setRegenerateFeedback(e.target.value)}
                        placeholder="What didn't you like? (e.g., 'too generic', 'wrong clothing', 'missing background details')"
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm"
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => generateSingleCaption(img.id!, regenerateFeedback)}
                          className="flex items-center gap-1 px-3 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
                        >
                          <Sparkles className="w-4 h-4" />
                          Regenerate
                        </button>
                        <button
                          onClick={() => {
                            setRegeneratingId(null);
                            setRegenerateFeedback('');
                          }}
                          className="px-3 py-1 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-start justify-between">
                        <p className="text-slate-300 text-sm flex-1">{img.caption || 'No caption yet'}</p>
                        <div className="flex gap-2">
                          {img.id && (
                            <button
                              onClick={() => {
                                if (img.caption) {
                                  setRegeneratingId(img.id!);
                                  setRegenerateFeedback('');
                                } else {
                                  generateSingleCaption(img.id!);
                                }
                              }}
                              className="p-1 text-blue-400 hover:text-blue-300 flex items-center gap-1 text-xs"
                              title={img.caption ? "Regenerate with feedback" : "Generate caption"}
                            >
                              <Sparkles className="w-4 h-4" />
                              {img.caption ? 'Regenerate' : 'Generate'}
                            </button>
                          )}
                          {img.caption && (
                            <button
                              onClick={() => {
                                setEditingCaptionId(img.id!);
                                setEditedCaption(img.caption!);
                              }}
                              className="p-1 text-slate-400 hover:text-white"
                              title="Edit caption manually"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Test Captions for AI Toolkit */}
          {testCaptions.length > 0 && (
            <div className="mt-6 p-6 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-xl">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white">Test Captions for AI Toolkit</h3>
                  <p className="text-sm text-slate-400 mt-1">
                    10 synthetic captions generated for manual training
                  </p>
                </div>
                <button
                  onClick={copyAllTestCaptions}
                  className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors text-sm"
                >
                  Copy All
                </button>
              </div>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {testCaptions.map((caption, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 p-3 bg-slate-900/50 border border-slate-700 rounded-lg group"
                  >
                    <p className="text-sm text-slate-300 font-mono flex-1">{caption}</p>
                    <button
                      onClick={() => copySingleCaption(caption)}
                      className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded transition-colors opacity-0 group-hover:opacity-100"
                      title="Copy this caption"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
