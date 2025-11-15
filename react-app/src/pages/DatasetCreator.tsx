import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

// Backend API only used for Grok caption generation (requires API key)
// All other operations use Supabase directly
const API_BASE = 'http://localhost:8002';

// Preset constraint templates
const CONSTRAINT_PRESETS = {
  hair_color: {
    label: 'Hair Color',
    options: ['blonde', 'brunette', 'black', 'red', 'auburn', 'platinum blonde', 'dark brown', 'light brown']
  },
  hair_length: {
    label: 'Hair Length',
    options: ['short', 'medium', 'long', 'very long', 'shoulder-length']
  },
  skin_tone: {
    label: 'Skin Tone',
    options: ['fair skin', 'tan skin', 'olive skin', 'dark skin', 'pale skin', 'medium skin tone']
  },
  eye_color: {
    label: 'Eye Color',
    options: ['blue eyes', 'brown eyes', 'green eyes', 'hazel eyes', 'gray eyes', 'amber eyes']
  },
  facial_features: {
    label: 'Facial Features',
    options: ['freckles', 'dimples', 'beauty mark', 'high cheekbones', 'full lips', 'defined jawline'],
    multi: true
  }
};

interface Character {
  id: string;
  name: string;
  trigger_word: string;
  character_constraints?: {
    constants: Array<{
      key: string;
      value: string;
      type: string;
    }>;
  };
}

interface Dataset {
  id: string;
  character_id: string;
  name: string;
  dataset_type: string;
  description?: string;
  image_count: number;
  created_at: string;
}

interface TrainingImage {
  id: string;
  image_url: string;
  caption: string;
  display_order: number;
}

export default function DatasetCreator() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [currentStep, setCurrentStep] = useState<'select' | 'constraints' | 'dataset' | 'upload' | 'captions'>('select');

  // New character creation
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [newCharacterName, setNewCharacterName] = useState('');
  const [newCharacterTrigger, setNewCharacterTrigger] = useState('');

  // Constraint editing with presets
  const [editingConstraints, setEditingConstraints] = useState<Array<{ key: string; value: string; type: string }>>([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [customConstraintKey, setCustomConstraintKey] = useState('');
  const [customConstraintValue, setCustomConstraintValue] = useState('');

  // Dataset creation
  const [datasetName, setDatasetName] = useState('');
  const [datasetType, setDatasetType] = useState<'SFW' | 'NSFW'>('SFW');
  const [datasetDescription, setDatasetDescription] = useState('');
  const [currentDataset, setCurrentDataset] = useState<Dataset | null>(null);

  // Image upload
  const [uploadedImages, setUploadedImages] = useState<File[]>([]);
  const [uploadedImageUrls, setUploadedImageUrls] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Caption generation
  const [images, setImages] = useState<TrainingImage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [captionFormat, setCaptionFormat] = useState('');
  const [editingCaptionId, setEditingCaptionId] = useState<string | null>(null);
  const [editingCaptionText, setEditingCaptionText] = useState('');

  useEffect(() => {
    loadCharacters();
  }, []);

  useEffect(() => {
    if (selectedCharacter) {
      loadCharacterDatasets(selectedCharacter.id);
      setEditingConstraints(selectedCharacter.character_constraints?.constants || []);
    }
  }, [selectedCharacter]);

  const loadCharacters = async () => {
    const { data, error } = await supabase
      .from('characters')
      .select('*')
      .eq('is_active', true);

    if (data && !error) {
      setCharacters(data);
    }
  };

  const loadCharacterDatasets = async (characterId: string) => {
    try {
      const { data, error } = await supabase
        .from('training_datasets')
        .select('*')
        .eq('character_id', characterId)
        .order('created_at', { ascending: false });

      if (data && !error) {
        setDatasets(data);
      }
    } catch (error) {
      console.error('Error loading datasets:', error);
    }
  };

  const createNewCharacter = async () => {
    console.log('🚀 Create character called', { newCharacterName, newCharacterTrigger });

    if (!newCharacterName || !newCharacterTrigger) {
      console.log('❌ Missing name or trigger');
      return;
    }

    try {
      const newCharacter = {
        id: newCharacterTrigger.toLowerCase().replace(/\s+/g, '_'),
        name: newCharacterName,
        trigger_word: newCharacterTrigger.toLowerCase(),
        character_constraints: { constants: [] },
        is_active: true,
        lora_file: 'pending_training.safetensors', // Placeholder until training is complete
        lora_strength: 0.8,
        comfyui_workflow: 'workflows/qwen/instagram_single.json'
      };

      console.log('📤 Inserting character:', newCharacter);

      const { data, error } = await supabase
        .from('characters')
        .insert([newCharacter])
        .select()
        .single();

      console.log('📥 Response:', { data, error });

      if (error) {
        console.error('❌ Supabase error:', error);
        alert(`Error creating character: ${error.message}`);
        return;
      }

      if (data) {
        console.log('✅ Character created successfully');
        setCharacters([...characters, data]);
        setSelectedCharacter(data);
        setIsCreatingCharacter(false);
        setCurrentStep('constraints');
        setNewCharacterName('');
        setNewCharacterTrigger('');
      }
    } catch (error) {
      console.error('❌ Exception creating character:', error);
      alert(`Exception: ${error}`);
    }
  };

  const addConstraintFromPreset = async (presetKey: string, value: string) => {
    if (!selectedCharacter || !value) return;

    try {
      // Get current constraints
      const currentConstraints = selectedCharacter.character_constraints?.constants || [];

      // Check if constraint already exists, update it, otherwise add
      const existingIndex = currentConstraints.findIndex(c => c.key === presetKey);
      const updatedConstraints = existingIndex >= 0
        ? currentConstraints.map((c, idx) => idx === existingIndex ? { key: presetKey, value, type: 'physical' } : c)
        : [...currentConstraints, { key: presetKey, value, type: 'physical' }];

      // Update character in Supabase
      const { data, error } = await supabase
        .from('characters')
        .update({
          character_constraints: { constants: updatedConstraints }
        })
        .eq('id', selectedCharacter.id)
        .select()
        .single();

      if (data && !error) {
        setSelectedCharacter(data);
        setEditingConstraints(data.character_constraints?.constants || []);
        setSelectedPreset('');
      }
    } catch (error) {
      console.error('Error adding constraint:', error);
    }
  };

  const addCustomConstraint = async () => {
    if (!selectedCharacter || !customConstraintKey || !customConstraintValue) return;

    try {
      // Get current constraints
      const currentConstraints = selectedCharacter.character_constraints?.constants || [];

      // Add new custom constraint
      const updatedConstraints = [...currentConstraints, {
        key: customConstraintKey,
        value: customConstraintValue,
        type: 'physical'
      }];

      // Update character in Supabase
      const { data, error } = await supabase
        .from('characters')
        .update({
          character_constraints: { constants: updatedConstraints }
        })
        .eq('id', selectedCharacter.id)
        .select()
        .single();

      if (data && !error) {
        setSelectedCharacter(data);
        setEditingConstraints(data.character_constraints?.constants || []);
        setCustomConstraintKey('');
        setCustomConstraintValue('');
      }
    } catch (error) {
      console.error('Error adding constraint:', error);
    }
  };

  const removeConstraint = async (key: string) => {
    if (!selectedCharacter) return;

    try {
      // Get current constraints and filter out the one to remove
      const currentConstraints = selectedCharacter.character_constraints?.constants || [];
      const updatedConstraints = currentConstraints.filter(c => c.key !== key);

      // Update character in Supabase
      const { data, error } = await supabase
        .from('characters')
        .update({
          character_constraints: { constants: updatedConstraints }
        })
        .eq('id', selectedCharacter.id)
        .select()
        .single();

      if (data && !error) {
        setSelectedCharacter(data);
        setEditingConstraints(data.character_constraints?.constants || []);
      }
    } catch (error) {
      console.error('Error removing constraint:', error);
    }
  };

  const createDataset = async () => {
    if (!selectedCharacter || !datasetName) return;

    try {
      // Create dataset in Supabase
      const { data, error } = await supabase
        .from('training_datasets')
        .insert([{
          character_id: selectedCharacter.id,
          name: datasetName,
          dataset_type: datasetType,
          description: datasetDescription,
          dataset_constraints: {
            rules: [
              { key: 'clothing', value: datasetType === 'SFW' ? 'required' : 'optional' }
            ]
          },
          image_count: 0
        }])
        .select()
        .single();

      if (data && !error) {
        setCurrentDataset(data);
        setCurrentStep('upload');
        // Build caption format locally
        buildCaptionFormatLocal(selectedCharacter, data);
      }
    } catch (error) {
      console.error('Error creating dataset:', error);
    }
  };

  const buildCaptionFormatLocal = (character: Character, dataset: Dataset) => {
    const trigger = character.trigger_word || character.id;
    const constraints = character.character_constraints?.constants || [];

    // Build format: trigger, character_description, [VARIABLE_ELEMENTS], dataset_rules
    let format = `${trigger}`;

    if (constraints.length > 0) {
      const constantDesc = constraints.map(c => c.value).join(', ');
      format += `, a woman with ${constantDesc}`;
    }

    format += ', [describe pose, clothing, setting, expression]';

    const datasetRules = dataset.dataset_constraints?.rules || [];
    if (datasetRules.length > 0) {
      const rulesDesc = datasetRules.map(r => `${r.key}: ${r.value}`).join(', ');
      format += ` (${rulesDesc})`;
    }

    setCaptionFormat(format);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setUploadedImages(files);
  };

  const uploadImagesToS3 = async () => {
    if (!uploadedImages.length || !currentDataset) return;

    setIsUploading(true);
    const urls: string[] = [];

    try {
      for (let i = 0; i < uploadedImages.length; i++) {
        const file = uploadedImages[i];
        const fileExt = file.name.split('.').pop();
        const fileName = `${currentDataset.id}/${Date.now()}_${i}.${fileExt}`;

        // Upload to Supabase Storage
        const { data: uploadData, error: uploadError } = await supabase.storage
          .from('training-images')
          .upload(fileName, file);

        if (uploadData && !uploadError) {
          // Get public URL
          const { data: { publicUrl } } = supabase.storage
            .from('training-images')
            .getPublicUrl(fileName);

          urls.push(publicUrl);

          // Insert into training_images table
          await supabase
            .from('training_images')
            .insert([{
              dataset_id: currentDataset.id,
              image_url: publicUrl,
              caption: '', // Will be generated later
              display_order: i
            }]);
        }
      }

      setUploadedImageUrls(urls);

      // Update dataset image count
      await supabase
        .from('training_datasets')
        .update({ image_count: urls.length })
        .eq('id', currentDataset.id);

      setCurrentStep('captions');
    } catch (error) {
      console.error('Error uploading images:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const generateCaptions = async () => {
    if (!currentDataset || !uploadedImageUrls.length) return;

    setIsGenerating(true);

    try {
      const response = await fetch(
        `${API_BASE}/api/datasets/${currentDataset.id}/generate-captions-batch`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            dataset_id: currentDataset.id,
            image_urls: uploadedImageUrls
          })
        }
      );

      const data = await response.json();
      if (data.success) {
        loadDatasetImages(currentDataset.id);
      }
    } catch (error) {
      console.error('Error generating captions:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const loadDatasetImages = async (datasetId: string) => {
    try {
      const { data, error } = await supabase
        .from('training_images')
        .select('*')
        .eq('dataset_id', datasetId)
        .order('display_order', { ascending: true });

      if (data && !error) {
        setImages(data);
      }
    } catch (error) {
      console.error('Error loading images:', error);
    }
  };

  const updateCaption = async (imageId: string, newCaption: string) => {
    try {
      const { error } = await supabase
        .from('training_images')
        .update({ caption: newCaption })
        .eq('id', imageId);

      if (!error) {
        setImages(images.map(img =>
          img.id === imageId ? { ...img, caption: newCaption } : img
        ));
        setEditingCaptionId(null);
      }
    } catch (error) {
      console.error('Error updating caption:', error);
    }
  };

  const goBack = () => {
    const steps = ['select', 'constraints', 'dataset', 'upload', 'captions'] as const;
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1]);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 text-white">
      <div className="max-w-6xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-2">
            Dataset Creator
          </h1>
          <p className="text-gray-400">Create training datasets for LoRA models with AI-powered captioning</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            {['Select Character', 'Define Traits', 'Create Dataset', 'Upload Images', 'Generate Captions'].map((label, idx) => {
              const steps = ['select', 'constraints', 'dataset', 'upload', 'captions'];
              const currentIdx = steps.indexOf(currentStep);
              const isActive = idx === currentIdx;
              const isComplete = idx < currentIdx;

              return (
                <div key={idx} className="flex-1 flex items-center">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                      isActive ? 'bg-gradient-to-r from-purple-500 to-pink-500 scale-110' :
                      isComplete ? 'bg-green-500' :
                      'bg-gray-700'
                    }`}>
                      {isComplete ? '✓' : idx + 1}
                    </div>
                    <div className={`text-xs mt-2 text-center ${isActive ? 'text-white font-semibold' : 'text-gray-500'}`}>
                      {label}
                    </div>
                  </div>
                  {idx < 4 && (
                    <div className={`h-1 flex-1 mx-2 rounded transition-all ${
                      isComplete ? 'bg-green-500' : 'bg-gray-700'
                    }`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Back Button */}
        {currentStep !== 'select' && (
          <button
            onClick={goBack}
            className="mb-4 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition flex items-center gap-2"
          >
            ← Back
          </button>
        )}

        {/* Step 1: Select/Create Character */}
        {currentStep === 'select' && (
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 border border-purple-500/20 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-3xl font-bold">Select Character</h2>
              <button
                onClick={() => setIsCreatingCharacter(true)}
                className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 rounded-xl font-semibold transition shadow-lg"
              >
                + Create New Character
              </button>
            </div>

            {isCreatingCharacter && (
              <div className="mb-8 bg-slate-900/50 p-6 rounded-xl border border-green-500/20">
                <h3 className="text-xl font-bold mb-4">New Character</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Character Name</label>
                    <input
                      type="text"
                      value={newCharacterName}
                      onChange={(e) => setNewCharacterName(e.target.value)}
                      placeholder="e.g., SeaDream"
                      className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Trigger Word</label>
                    <input
                      type="text"
                      value={newCharacterTrigger}
                      onChange={(e) => setNewCharacterTrigger(e.target.value)}
                      placeholder="e.g., seadream (lowercase, no spaces)"
                      className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                    />
                    <p className="text-xs text-gray-500 mt-1">This word will be the first word in all captions</p>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={createNewCharacter}
                      disabled={!newCharacterName || !newCharacterTrigger}
                      className="px-6 py-3 bg-green-600 hover:bg-green-500 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Create Character
                    </button>
                    <button
                      onClick={() => setIsCreatingCharacter(false)}
                      className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-4">
              {characters.map(char => (
                <button
                  key={char.id}
                  onClick={() => {
                    setSelectedCharacter(char);
                    setCurrentStep('constraints');
                  }}
                  className="p-6 bg-gradient-to-br from-purple-900/40 to-pink-900/40 hover:from-purple-800/60 hover:to-pink-800/60 rounded-xl border border-purple-500/30 transition transform hover:scale-105 shadow-lg"
                >
                  <div className="text-2xl font-bold mb-2">{char.name}</div>
                  <div className="text-sm text-gray-400">
                    <span className="font-mono bg-purple-500/20 px-2 py-1 rounded">{char.trigger_word}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    {char.character_constraints?.constants?.length || 0} constraints
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Edit Character Constraints (continued in next file due to length) */}
        {currentStep === 'constraints' && selectedCharacter && (
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 border border-purple-500/20 shadow-2xl">
            <h2 className="text-3xl font-bold mb-6">
              Define Character Traits: <span className="text-purple-400">{selectedCharacter.name}</span>
            </h2>

            {/* Trigger Word Display */}
            <div className="mb-8 bg-purple-900/20 p-4 rounded-xl border border-purple-500/30">
              <div className="text-sm text-gray-400 mb-2">Trigger Word (first in all captions):</div>
              <div className="text-2xl font-mono font-bold text-purple-400">{selectedCharacter.trigger_word}</div>
            </div>

            {/* Current Constraints */}
            <div className="mb-8">
              <h3 className="text-xl font-semibold mb-4">Current Traits:</h3>
              <div className="grid grid-cols-2 gap-3">
                {editingConstraints.length === 0 ? (
                  <div className="col-span-2 text-center py-8 text-gray-500">
                    No traits defined yet. Add some below!
                  </div>
                ) : (
                  editingConstraints.map(constraint => (
                    <div key={constraint.key} className="flex items-center justify-between bg-slate-800/50 p-4 rounded-lg border border-gray-700">
                      <div>
                        <span className="text-purple-400 font-semibold">{constraint.key.replace(/_/g, ' ')}:</span>{' '}
                        <span className="text-white">{constraint.value}</span>
                      </div>
                      <button
                        onClick={() => removeConstraint(constraint.key)}
                        className="text-red-400 hover:text-red-300 font-bold text-lg"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Add Constraints - Preset Templates */}
            <div className="mb-8 bg-slate-900/50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold mb-4">Add Trait (Quick Select):</h3>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(CONSTRAINT_PRESETS).map(([key, preset]) => (
                  <div key={key} className="space-y-2">
                    <label className="block text-sm font-semibold text-gray-300">{preset.label}</label>
                    <select
                      onChange={(e) => {
                        if (e.target.value) {
                          addConstraintFromPreset(key, e.target.value);
                          e.target.value = '';
                        }
                      }}
                      className="w-full bg-slate-800 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                      defaultValue=""
                    >
                      <option value="">Select {preset.label.toLowerCase()}...</option>
                      {preset.options.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>

            {/* Add Custom Constraint */}
            <div className="mb-8 bg-slate-900/50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold mb-4">Add Custom Trait:</h3>
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Trait name (e.g., facial_expression)"
                  value={customConstraintKey}
                  onChange={(e) => setCustomConstraintKey(e.target.value)}
                  className="flex-1 bg-slate-800 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Value (e.g., smiling)"
                  value={customConstraintValue}
                  onChange={(e) => setCustomConstraintValue(e.target.value)}
                  className="flex-1 bg-slate-800 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                />
                <button
                  onClick={addCustomConstraint}
                  disabled={!customConstraintKey || !customConstraintValue}
                  className="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
            </div>

            <button
              onClick={() => setCurrentStep('dataset')}
              className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-xl font-bold text-lg transition shadow-lg"
            >
              Continue to Dataset Creation →
            </button>
          </div>
        )}

        {/* Remaining steps (dataset, upload, captions) - keeping previous logic but with better styling */}
        {/* ... rest of the component continues below ... */}

        {/* Step 3: Create Dataset */}
        {currentStep === 'dataset' && selectedCharacter && (
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 border border-purple-500/20 shadow-2xl">
            <h2 className="text-3xl font-bold mb-6">Create New Dataset</h2>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold mb-2 text-gray-300">Dataset Name</label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder={`${selectedCharacter.id}_${datasetType.toLowerCase()}_v1`}
                  className="w-full bg-slate-800 p-4 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none text-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-3 text-gray-300">Dataset Type</label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setDatasetType('SFW')}
                    className={`p-6 rounded-xl border-2 transition ${
                      datasetType === 'SFW'
                        ? 'border-blue-500 bg-blue-500/20'
                        : 'border-gray-700 bg-slate-800/50 hover:border-gray-600'
                    }`}
                  >
                    <div className="text-2xl mb-2">👕</div>
                    <div className="font-bold text-lg">SFW</div>
                    <div className="text-sm text-gray-400 mt-1">Clothed / Safe for work</div>
                  </button>
                  <button
                    onClick={() => setDatasetType('NSFW')}
                    className={`p-6 rounded-xl border-2 transition ${
                      datasetType === 'NSFW'
                        ? 'border-pink-500 bg-pink-500/20'
                        : 'border-gray-700 bg-slate-800/50 hover:border-gray-600'
                    }`}
                  >
                    <div className="text-2xl mb-2">🔞</div>
                    <div className="font-bold text-lg">NSFW</div>
                    <div className="text-sm text-gray-400 mt-1">Nude / Adult content</div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2 text-gray-300">Description (optional)</label>
                <textarea
                  value={datasetDescription}
                  onChange={(e) => setDatasetDescription(e.target.value)}
                  placeholder="Beach photoshoot series, summer vibes..."
                  className="w-full bg-slate-800 p-4 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none h-24"
                />
              </div>

              <button
                onClick={createDataset}
                disabled={!datasetName}
                className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl font-bold text-lg transition shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Dataset & Continue →
              </button>
            </div>
          </div>
        )}

        {/* Steps 4 & 5 continue with similar improved styling... */}
        {/* Keeping upload and caption steps with same logic but better visual design */}

        {currentStep === 'upload' && currentDataset && (
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 border border-purple-500/20 shadow-2xl">
            <h2 className="text-3xl font-bold mb-6">Upload Training Images</h2>

            <div className="mb-6 bg-purple-900/20 p-4 rounded-xl border border-purple-500/30">
              <div className="text-sm text-gray-400 mb-2">Caption Preview:</div>
              <div className="font-mono text-sm text-green-400">{captionFormat}</div>
            </div>

            <div className="mb-6">
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                id="image-upload"
              />
              <label
                htmlFor="image-upload"
                className="block w-full p-16 border-2 border-dashed border-purple-500/50 rounded-2xl text-center cursor-pointer hover:border-purple-400 hover:bg-purple-500/5 transition"
              >
                <div className="text-6xl mb-4">📤</div>
                <div className="text-2xl font-bold mb-2">Click to upload images</div>
                <div className="text-gray-400">Select 20-30 high-quality images for best results</div>
              </label>
            </div>

            {uploadedImages.length > 0 && (
              <div>
                <div className="text-lg font-semibold mb-4">Selected: {uploadedImages.length} images</div>
                <div className="grid grid-cols-6 gap-3 mb-6">
                  {uploadedImages.map((file, idx) => (
                    <div key={idx} className="aspect-square bg-slate-700 rounded-lg overflow-hidden border border-gray-600">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Upload ${idx + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ))}
                </div>

                <button
                  onClick={uploadImagesToS3}
                  disabled={isUploading}
                  className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-xl font-bold text-lg transition shadow-lg disabled:opacity-50"
                >
                  {isUploading ? 'Uploading...' : `Upload ${uploadedImages.length} Images & Continue →`}
                </button>
              </div>
            )}
          </div>
        )}

        {currentStep === 'captions' && currentDataset && (
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 border border-purple-500/20 shadow-2xl">
            <h2 className="text-3xl font-bold mb-6">Generate & Review Captions</h2>

            {uploadedImageUrls.length > 0 && images.length === 0 && (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🤖</div>
                <button
                  onClick={generateCaptions}
                  disabled={isGenerating}
                  className="px-8 py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl font-bold text-lg transition shadow-lg disabled:opacity-50"
                >
                  {isGenerating ? '✨ Generating captions with Grok AI...' : 'Generate Captions with AI'}
                </button>
                <p className="text-gray-400 mt-4">This may take a few minutes...</p>
              </div>
            )}

            {images.length > 0 && (
              <div className="space-y-4">
                {images.map((img) => (
                  <div key={img.id} className="bg-slate-800/50 p-4 rounded-xl border border-gray-700 flex gap-4">
                    <img
                      src={img.image_url}
                      alt="Training"
                      className="w-40 h-40 object-cover rounded-lg"
                    />
                    <div className="flex-1">
                      {editingCaptionId === img.id ? (
                        <div>
                          <textarea
                            value={editingCaptionText}
                            onChange={(e) => setEditingCaptionText(e.target.value)}
                            className="w-full bg-slate-900 p-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none mb-3"
                            rows={4}
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => updateCaption(img.id, editingCaptionText)}
                              className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-semibold"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingCaptionId(null)}
                              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <p className="text-sm text-gray-300 mb-3">{img.caption}</p>
                          <button
                            onClick={() => {
                              setEditingCaptionId(img.id);
                              setEditingCaptionText(img.caption);
                            }}
                            className="text-purple-400 hover:text-purple-300 text-sm font-semibold"
                          >
                            ✏️ Edit Caption
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                <div className="mt-8 p-6 bg-gradient-to-br from-green-900/40 to-emerald-900/40 rounded-xl border border-green-500/30">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="text-4xl">✅</div>
                    <div>
                      <div className="font-bold text-xl">Dataset Ready!</div>
                      <div className="text-sm text-gray-300">{images.length} images with AI-generated captions</div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-300 space-y-2">
                    <p className="font-semibold">Next Steps:</p>
                    <ol className="list-decimal list-inside space-y-1 ml-2">
                      <li>Download dataset as ZIP (feature coming soon)</li>
                      <li>Upload to AI Toolkit / Kohya / Allura</li>
                      <li>Train LoRA model (recommended: 2000-3000 steps)</li>
                      <li>Upload .safetensors file to your ComfyUI loras/ folder</li>
                      <li>Use ComfyUI integration to generate!</li>
                    </ol>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
