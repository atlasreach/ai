import { useState, useEffect } from 'react'
import { supabase } from '../supabase'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

// Detect API URL for Codespaces
function getApiUrl() {
  const url = window.location.origin
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  if (url.includes('app.github.dev')) {
    return url.replace('-5173.app.github.dev', '-3001.app.github.dev')
  }
  return 'http://localhost:3001'
}

const API_URL = getApiUrl()

export default function Gallery() {
  const [jobs, setJobs] = useState([])
  const [filteredJobs, setFilteredJobs] = useState([])
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('all')
  const [lightboxJob, setLightboxJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [newImagesCount, setNewImagesCount] = useState(0)
  const [showStarredOnly, setShowStarredOnly] = useState(false)
  const [showFaceSwappedOnly, setShowFaceSwappedOnly] = useState(false)
  const [faceSwapping, setFaceSwapping] = useState(false)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedImages, setSelectedImages] = useState([])
  const [showDetails, setShowDetails] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editModalType, setEditModalType] = useState(null) // 'edit' or 'variations'
  const [editPrompt, setEditPrompt] = useState('')
  const [numVariations, setNumVariations] = useState(4)
  const [processing, setProcessing] = useState(false)
  const [enhancedPrompt, setEnhancedPrompt] = useState('')
  const [enhancing, setEnhancing] = useState(false)
  const [showRegenerateModal, setShowRegenerateModal] = useState(false)
  const [regenerateParams, setRegenerateParams] = useState({
    denoise: 0.75,
    cfg: 3.8,
    steps: 10,
    loraStrength: 0.65,
    seed: -1,
    positivePrompt: '',
    negativePrompt: ''
  })
  const [showSmartBlendModal, setShowSmartBlendModal] = useState(false)
  const [smartBlendInstruction, setSmartBlendInstruction] = useState('')
  const [smartBlendVariations, setSmartBlendVariations] = useState(1)
  const [smartBlending, setSmartBlending] = useState(false)
  const [activeTab, setActiveTab] = useState('all') // 'originals', 'edited', 'all'
  const [showEditDropdown, setShowEditDropdown] = useState(false)
  const [showEditWithReferenceModal, setShowEditWithReferenceModal] = useState(false)
  const [editWithReferencePrompt, setEditWithReferencePrompt] = useState('')
  const [showCarouselModal, setShowCarouselModal] = useState(false)
  const [carouselNumImages, setCarouselNumImages] = useState(3)
  const [carouselPrompt, setCarouselPrompt] = useState('')

  useEffect(() => {
    fetchData()
  }, [showStarredOnly])

  useEffect(() => {
    filterJobs()
  }, [jobs, selectedModel, showFaceSwappedOnly])

  // Auto-refresh polling every 10 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      // Silently fetch new images
      const response = await fetch(`${API_URL}/api/gallery-images`)
      const imagesData = await response.json()

      if (imagesData && imagesData.length > jobs.length) {
        setNewImagesCount(imagesData.length - jobs.length)
        setJobs(imagesData)

        // Clear the notification after 3 seconds
        setTimeout(() => setNewImagesCount(0), 3000)
      }
    }, 10000)

    return () => clearInterval(interval)
  }, [jobs.length])

  async function fetchData() {
    setLoading(true)

    // Fetch all gallery images from generated_images table
    const url = showStarredOnly ? `${API_URL}/api/gallery-images?starred=true` : `${API_URL}/api/gallery-images`
    const response = await fetch(url)
    const imagesData = await response.json()
    setJobs(imagesData || [])

    // Fetch models
    const { data: modelsData } = await supabase.from('models').select('*').order('name')
    setModels(modelsData || [])

    setLoading(false)
  }

  async function toggleStar(image) {
    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${image.id}/star`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ starred: !image.is_starred })
      })

      if (response.ok) {
        // Update local state
        setJobs(jobs.map(j => j.id === image.id ? { ...j, is_starred: !image.is_starred } : j))
        if (lightboxJob && lightboxJob.id === image.id) {
          setLightboxJob({ ...lightboxJob, is_starred: !lightboxJob.is_starred })
        }
      }
    } catch (error) {
      alert(`Failed to star image: ${error.message}`)
    }
  }

  async function deleteImage(image) {
    if (!confirm('Delete this image? It will be moved to trash.')) return

    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${image.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Remove from local state
        setJobs(jobs.filter(j => j.id !== image.id))
        closeLightbox()
        alert('Image deleted successfully')
      }
    } catch (error) {
      alert(`Failed to delete image: ${error.message}`)
    }
  }

  async function faceSwap(image) {
    if (!confirm('Face swap this image with your source face?')) return

    setFaceSwapping(true)
    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${image.id}/face-swap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })

      const result = await response.json()

      if (result.success) {
        alert('Face swap completed! New image will appear in gallery shortly.')
        fetchData()
        closeLightbox()
      } else {
        alert(`Face swap failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Face swap error: ${error.message}`)
    } finally {
      setFaceSwapping(false)
    }
  }

  async function faceSwapGroup(image) {
    const groupType = image.group_id ? 'group' : 'batch'
    if (!confirm(`Face swap ALL images in this ${groupType}? This will process multiple images.`)) return

    setFaceSwapping(true)
    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${image.id}/face-swap-group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })

      const result = await response.json()

      if (result.success) {
        alert(`Face swap complete! ${result.succeeded} images processed successfully. ${result.failed > 0 ? `${result.failed} failed.` : ''} New images will appear in gallery shortly.`)
        fetchData()
        closeLightbox()
      } else {
        alert(`Face swap failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Face swap error: ${error.message}`)
    } finally {
      setFaceSwapping(false)
    }
  }

  function openEditModal(type) {
    setEditModalType(type)
    setEditPrompt('')
    setNumVariations(4)
    setShowEditModal(true)
    setShowEditDropdown(false)
  }

  function closeEditModal() {
    setShowEditModal(false)
    setEditModalType(null)
    setEditPrompt('')
    setEnhancedPrompt('')
  }

  function openEditWithReferenceModal() {
    setEditWithReferencePrompt('')
    setShowEditWithReferenceModal(true)
    setShowEditDropdown(false)
  }

  function closeEditWithReferenceModal() {
    setShowEditWithReferenceModal(false)
    setEditWithReferencePrompt('')
  }

  function closeCarouselModal() {
    setShowCarouselModal(false)
    setCarouselPrompt('')
    setCarouselNumImages(3)
  }

  async function submitCarouselVariations() {
    setProcessing(true)
    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${lightboxJob.id}/carousel-variations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numImages: carouselNumImages,
          variationPrompt: carouselPrompt.trim() || 'different camera angle, facial expression, and pose'
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Server error:', errorText)
        alert(`Server error (${response.status}): ${errorText.substring(0, 200)}`)
        return
      }

      const result = await response.json()

      if (result.success) {
        alert(`Carousel variations complete! ${carouselNumImages} images created.`)
        fetchData()
        closeLightbox()
        closeCarouselModal()
      } else {
        alert(`Carousel failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Carousel variations error:', error)
      alert(`Error: ${error.message}`)
    } finally {
      setProcessing(false)
    }
  }

  async function submitEditWithReference() {
    if (!editWithReferencePrompt.trim()) {
      alert('Please enter what to change')
      return
    }

    setProcessing(true)
    try {
      const response = await fetch(`${API_URL}/api/gallery-images/${lightboxJob.id}/edit-with-reference`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ editPrompt: editWithReferencePrompt })
      })

      // Check if response is OK
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Server error:', errorText)
        alert(`Server error (${response.status}): ${errorText.substring(0, 200)}`)
        return
      }

      const result = await response.json()

      if (result.success) {
        alert('Edit complete! New image will appear in gallery shortly.')
        fetchData()
        closeLightbox()
        closeEditWithReferenceModal()
      } else {
        alert(`Edit failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Edit with reference error:', error)
      alert(`Error: ${error.message}`)
    } finally {
      setProcessing(false)
    }
  }

  async function enhancePrompt() {
    if (!editPrompt.trim()) {
      alert('Please enter a prompt first')
      return
    }

    setEnhancing(true)
    try {
      const response = await fetch(`${API_URL}/api/enhance-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: editPrompt })
      })

      const result = await response.json()
      if (result.enhanced) {
        setEnhancedPrompt(result.enhanced)
        setEditPrompt(result.enhanced)
      }
    } catch (error) {
      alert(`Failed to enhance prompt: ${error.message}`)
    } finally {
      setEnhancing(false)
    }
  }

  function openRegenerateModal() {
    if (!lightboxJob) return

    // Pre-fill with current image parameters
    setRegenerateParams({
      denoise: lightboxJob.parameters?.denoise || 0.75,
      cfg: lightboxJob.parameters?.cfg || 3.8,
      steps: lightboxJob.parameters?.steps || 10,
      loraStrength: lightboxJob.parameters?.lora_strength || 0.65,
      seed: lightboxJob.parameters?.seed || -1,
      positivePrompt: lightboxJob.prompt_used || '',
      negativePrompt: lightboxJob.negative_prompt_used || ''
    })
    setShowRegenerateModal(true)
  }

  function closeRegenerateModal() {
    setShowRegenerateModal(false)
  }

  async function submitRegenerate() {
    setProcessing(true)
    try {
      // Get the original uploaded image from parameters
      const originalImage = lightboxJob.parameters?.uploaded_image

      if (!originalImage) {
        alert('Cannot regenerate: original image not found')
        return
      }

      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_slug: lightboxJob.model_slug,
          uploaded_image: originalImage,
          prompt: regenerateParams.positivePrompt,
          negative_prompt: regenerateParams.negativePrompt,
          cfg: regenerateParams.cfg,
          steps: regenerateParams.steps,
          denoise: regenerateParams.denoise,
          lora_strength: regenerateParams.loraStrength,
          seed: regenerateParams.seed,
          variations: 1
        })
      })

      const result = await response.json()

      if (result.success) {
        alert('Regeneration started! New image will appear in gallery shortly.')
        fetchData()
        closeLightbox()
        closeRegenerateModal()
      } else {
        alert(`Regeneration failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setProcessing(false)
    }
  }

  function openSmartBlendModal() {
    if (selectedImages.length !== 2) {
      alert('Please select exactly 2 images for Smart Blend')
      return
    }
    setSmartBlendInstruction('')
    setSmartBlendVariations(1)
    setShowSmartBlendModal(true)
  }

  function closeSmartBlendModal() {
    setShowSmartBlendModal(false)
    setSmartBlendInstruction('')
  }

  async function submitSmartBlend() {
    if (!smartBlendInstruction.trim()) {
      alert('Please enter what to transfer from image 2 to image 1')
      return
    }

    // Start the process without waiting
    fetch(`${API_URL}/api/smart-blend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sourceImageId: selectedImages[0],
        referenceImageId: selectedImages[1],
        instruction: smartBlendInstruction,
        numVariations: smartBlendVariations
      })
    }).catch(error => {
      console.error('Smart Blend error:', error)
    })

    // Immediately close and notify user
    alert(`Smart Blend started! ${smartBlendVariations} variation(s) will appear in gallery when ready (check back in ~30 sec).`)
    setSelectedImages([])
    setSelectionMode(false)
    closeSmartBlendModal()
  }

  async function submitEdit() {
    if (!editPrompt.trim() && editModalType === 'edit') {
      alert('Please enter an edit instruction')
      return
    }

    setProcessing(true)
    try {
      if (editModalType === 'edit') {
        const response = await fetch(`${API_URL}/api/gallery-images/${lightboxJob.id}/wavespeed-edit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ editPrompt })
        })

        const result = await response.json()

        if (result.success) {
          alert('Edit completed! New image will appear in gallery shortly.')
          fetchData()
          closeLightbox()
          closeEditModal()
        } else {
          alert(`Edit failed: ${result.error}`)
        }
      } else if (editModalType === 'variations') {
        const response = await fetch(`${API_URL}/api/gallery-images/${lightboxJob.id}/wavespeed-variations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            variationPrompt: editPrompt.trim() || undefined,
            numImages: numVariations
          })
        })

        const result = await response.json()

        if (result.success) {
          alert(`${result.count} variations created! They will appear in gallery shortly.`)
          fetchData()
          closeLightbox()
          closeEditModal()
        } else {
          alert(`Variations failed: ${result.error}`)
        }
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    } finally {
      setProcessing(false)
    }
  }

  function filterJobs() {
    let filtered = jobs

    // Filter by model
    if (selectedModel !== 'all') {
      filtered = filtered.filter(job => job.model_id === parseInt(selectedModel))
    }

    // Filter by face swapped
    if (showFaceSwappedOnly) {
      filtered = filtered.filter(job => job.edit_type === 'face_swap')
    }

    setFilteredJobs(filtered)
  }

  function toggleImageSelection(imageId) {
    setSelectedImages(prev =>
      prev.includes(imageId)
        ? prev.filter(id => id !== imageId)
        : [...prev, imageId]
    )
  }

  function selectAll() {
    setSelectedImages(filteredJobs.map(job => job.id))
  }

  function deselectAll() {
    setSelectedImages([])
  }

  async function bulkDelete() {
    if (selectedImages.length === 0) return
    if (!confirm(`Delete ${selectedImages.length} images?`)) return

    try {
      await Promise.all(
        selectedImages.map(id =>
          fetch(`${API_URL}/api/gallery-images/${id}`, { method: 'DELETE' })
        )
      )

      setJobs(jobs.filter(j => !selectedImages.includes(j.id)))
      setSelectedImages([])
      setSelectionMode(false)
      alert(`Deleted ${selectedImages.length} images`)
    } catch (error) {
      alert(`Failed to delete images: ${error.message}`)
    }
  }

  async function groupSelected() {
    if (selectedImages.length < 2) {
      alert('Please select at least 2 images to group')
      return
    }

    try {
      const response = await fetch(`${API_URL}/api/gallery-images/group`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageIds: selectedImages })
      })

      const result = await response.json()

      if (result.success) {
        alert(`Grouped ${selectedImages.length} images together!`)
        fetchData()
        setSelectedImages([])
        setSelectionMode(false)
      } else {
        alert(`Failed to group images: ${result.error}`)
      }
    } catch (error) {
      alert(`Error grouping images: ${error.message}`)
    }
  }

  async function bulkFaceSwap() {
    if (selectedImages.length === 0) return
    if (!confirm(`Face swap ${selectedImages.length} images? This may take a while.`)) return

    setFaceSwapping(true)
    try {
      // Use allSettled to process all images even if some fail
      const results = await Promise.allSettled(
        selectedImages.map(async (id) => {
          const response = await fetch(`${API_URL}/api/gallery-images/${id}/face-swap`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          })
          const data = await response.json()
          return { id, success: data.success, error: data.error }
        })
      )

      const succeeded = results.filter(r => r.status === 'fulfilled' && r.value.success).length
      const failed = results.length - succeeded

      setSelectedImages([])
      setSelectionMode(false)

      if (failed > 0) {
        alert(`Face swap: ${succeeded} succeeded, ${failed} failed. Successful swaps will appear in gallery shortly.`)
      } else {
        alert(`Started face swapping ${succeeded} images! They will appear in gallery shortly.`)
      }

      fetchData()
    } catch (error) {
      alert(`Face swap error: ${error.message}`)
    } finally {
      setFaceSwapping(false)
    }
  }

  // Group images by batch_id
  function openLightbox(job) {
    setLightboxJob(job)
    setShowDetails(false)
  }

  function closeLightbox() {
    setLightboxJob(null)
    setShowDetails(false)
  }

  function groupByBatch(images) {
    const batches = {}
    const ungrouped = []

    // First pass: Create a map of image_id to batch_id/group_id for parent lookups
    const imageToBatch = {}
    images.forEach(img => {
      // Prefer manual group_id, then batch_id
      if (img.group_id) {
        imageToBatch[img.id] = img.group_id
      } else if (img.batch_id) {
        imageToBatch[img.id] = img.batch_id
      }
    })

    // Second pass: Group images, including children with their parent's batch/group
    images.forEach(img => {
      // Prefer manual group_id over batch_id
      let groupId = img.group_id || img.batch_id

      // If no group/batch but has parent_image_id, use parent's group/batch
      if (!groupId && img.parent_image_id) {
        groupId = imageToBatch[img.parent_image_id]
      }

      if (groupId) {
        if (!batches[groupId]) {
          batches[groupId] = []
        }
        batches[groupId].push(img)
      } else {
        ungrouped.push(img)
      }
    })

    return { batches, ungrouped }
  }

  function getFilteredByTab(images) {
    if (activeTab === 'all') return images
    if (activeTab === 'originals') {
      // Show only images without edit_type (base generations)
      return images.filter(img => !img.edit_type && !img.parent_image_id)
    }
    if (activeTab === 'edited') {
      // Show only images with edit_type or parent_image_id
      return images.filter(img => img.edit_type || img.parent_image_id)
    }
    if (activeTab === 'groups') {
      // Show only images that have a manual group_id (custom groups)
      return images.filter(img => img.group_id && img.group_id.startsWith('manual_group_'))
    }
    return images
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* New Images Notification */}
      {newImagesCount > 0 && (
        <div className="mb-4 bg-green-500/20 border border-green-500 rounded-lg px-4 py-2 text-green-400 text-sm">
          ✨ {newImagesCount} new image{newImagesCount !== 1 ? 's' : ''} added to gallery!
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 flex gap-4 items-center flex-wrap">
        <div>
          <label className="block text-sm font-medium mb-1">Model</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="px-4 py-2 bg-gray-800 rounded-lg border border-gray-700"
          >
            <option value="all">All Models</option>
            {models.map(model => (
              <option key={model.id} value={model.id}>{model.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Filters</label>
          <div className="flex gap-2">
            <button
              onClick={() => setShowStarredOnly(!showStarredOnly)}
              className={`px-3 py-2 rounded-lg border text-sm ${
                showStarredOnly
                  ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                  : 'bg-gray-800 border-gray-700 hover:bg-gray-700'
              }`}
            >
              {showStarredOnly ? '⭐ Starred' : '⭐'}
            </button>
            <button
              onClick={() => setShowFaceSwappedOnly(!showFaceSwappedOnly)}
              className={`px-3 py-2 rounded-lg border text-sm ${
                showFaceSwappedOnly
                  ? 'bg-blue-500/20 border-blue-500 text-blue-400'
                  : 'bg-gray-800 border-gray-700 hover:bg-gray-700'
              }`}
            >
              {showFaceSwappedOnly ? '👤 Face Swapped' : '👤'}
            </button>
          </div>
        </div>


        <div className="ml-auto flex items-center gap-4">
          {selectionMode && (
            <>
              <button
                onClick={selectedImages.length === filteredJobs.length ? deselectAll : selectAll}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
              >
                {selectedImages.length === filteredJobs.length ? 'Deselect All' : 'Select All'}
              </button>
              <button
                onClick={bulkFaceSwap}
                disabled={selectedImages.length === 0 || faceSwapping}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm"
              >
                👤 Face Swap ({selectedImages.length})
              </button>
              {selectedImages.length === 2 && (
                <button
                  onClick={openSmartBlendModal}
                  className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
                >
                  🎨 Smart Blend
                </button>
              )}
              {selectedImages.length >= 2 && (
                <button
                  onClick={groupSelected}
                  className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium"
                >
                  📁 Group Selected
                </button>
              )}
              <button
                onClick={bulkDelete}
                disabled={selectedImages.length === 0}
                className="px-3 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm"
              >
                🗑️ Delete ({selectedImages.length})
              </button>
            </>
          )}
          <button
            onClick={() => {
              setSelectionMode(!selectionMode)
              setSelectedImages([])
            }}
            className={`px-3 py-2 rounded-lg text-sm ${
              selectionMode
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {selectionMode ? '✓ Done' : '☑ Select'}
          </button>
          <button
            onClick={() => fetchData()}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
          >
            🔄 Refresh
          </button>
          <div className="text-sm text-gray-400">
            {filteredJobs.length} image{filteredJobs.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b border-gray-700">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'all'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setActiveTab('originals')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'originals'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Originals
          </button>
          <button
            onClick={() => setActiveTab('edited')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'edited'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Edited
          </button>
          <button
            onClick={() => setActiveTab('groups')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'groups'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            Groups
          </button>
        </div>

      {/* Gallery Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : filteredJobs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          No images found with the selected filters
        </div>
      ) : (
        (() => {
          // Apply tab filtering
          const displayJobs = getFilteredByTab(filteredJobs)
          const { batches, ungrouped } = groupByBatch(displayJobs)

          return (
            <div className="space-y-6">
                {/* Batched variations */}
                {Object.entries(batches).map(([batchId, batchImages]) => (
                  <div key={batchId} className="bg-gray-800/30 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-gray-400">Variations</span>
                      <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">
                        {batchImages.length} images
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                      {batchImages.map(job => (
                        <div
                          key={job.id}
                          onClick={() => selectionMode ? toggleImageSelection(job.id) : openLightbox(job)}
                          className={`relative aspect-square bg-gray-800 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all group ${
                            selectedImages.includes(job.id) ? 'ring-2 ring-green-500' : ''
                          }`}
                        >
                          {selectionMode && (
                            <div className="absolute top-2 left-2 z-10">
                              <input
                                type="checkbox"
                                checked={selectedImages.includes(job.id)}
                                onChange={() => toggleImageSelection(job.id)}
                                className="w-5 h-5"
                                onClick={(e) => e.stopPropagation()}
                              />
                            </div>
                          )}
                          {job.image_url ? (
                            <>
                              <img
                                src={job.image_url}
                                alt={`Generated by ${job.model_name}`}
                                className="w-full h-full object-cover"
                              />
                              {/* Edit Type Badge */}
                              {job.edit_type && (
                                <div className="absolute top-2 right-2 z-10">
                                  {job.edit_type === 'face_swap' && (
                                    <span className="px-2 py-1 bg-blue-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                      👤
                                    </span>
                                  )}
                                  {job.edit_type === 'wavespeed_edit' && (
                                    <span className="px-2 py-1 bg-purple-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                      ✏️
                                    </span>
                                  )}
                                  {job.edit_type === 'wavespeed_variation' && (
                                    <span className="px-2 py-1 bg-green-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                      🎨
                                    </span>
                                  )}
                                  {job.edit_type === 'smart_blend' && (
                                    <span className="px-2 py-1 bg-purple-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                      🎨✨
                                    </span>
                                  )}
                                  {job.edit_type === 'edit_with_reference' && (
                                    <span className="px-2 py-1 bg-orange-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                      🖼️
                                    </span>
                                  )}
                                  {job.edit_type === 'carousel_variation' && (
                                    <span className="px-2 py-1 bg-blue-500/90 backdrop-blur-sm rounded text-xs font-medium">
                                      📸
                                    </span>
                                  )}
                                </div>
                              )}
                              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <div className="text-center px-2">
                                  <div className="text-sm font-semibold">{job.model_name}</div>
                                  <div className="text-xs text-gray-300 mt-1">{selectionMode ? 'Click to select' : 'Click to view'}</div>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="flex items-center justify-center h-full">
                              <div className="text-xs text-gray-500">No image</div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {/* Ungrouped individual images */}
                {ungrouped.length > 0 && (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                    {ungrouped.map(job => (
                      <div
                        key={job.id}
                        onClick={() => selectionMode ? toggleImageSelection(job.id) : openLightbox(job)}
                        className={`relative aspect-square bg-gray-800 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all group ${
                          selectedImages.includes(job.id) ? 'ring-2 ring-green-500' : ''
                        }`}
                      >
                        {selectionMode && (
                          <div className="absolute top-2 left-2 z-10">
                            <input
                              type="checkbox"
                              checked={selectedImages.includes(job.id)}
                              onChange={() => toggleImageSelection(job.id)}
                              className="w-5 h-5"
                              onClick={(e) => e.stopPropagation()}
                            />
                          </div>
                        )}
                        {job.image_url ? (
                          <>
                            <img
                              src={job.image_url}
                              alt={`Generated by ${job.model_name}`}
                              className="w-full h-full object-cover"
                            />
                            {/* Edit Type Badge */}
                            {job.edit_type && (
                              <div className="absolute top-2 right-2 z-10">
                                {job.edit_type === 'face_swap' && (
                                  <span className="px-2 py-1 bg-blue-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                    👤
                                  </span>
                                )}
                                {job.edit_type === 'wavespeed_edit' && (
                                  <span className="px-2 py-1 bg-purple-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                    ✏️
                                  </span>
                                )}
                                {job.edit_type === 'wavespeed_variation' && (
                                  <span className="px-2 py-1 bg-green-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                    🎨
                                  </span>
                                )}
                                {job.edit_type === 'smart_blend' && (
                                  <span className="px-2 py-1 bg-purple-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                    🎨✨
                                  </span>
                                )}
                                {job.edit_type === 'edit_with_reference' && (
                                  <span className="px-2 py-1 bg-orange-600/90 backdrop-blur-sm rounded text-xs font-medium">
                                    🖼️
                                  </span>
                                )}
                                {job.edit_type === 'carousel_variation' && (
                                  <span className="px-2 py-1 bg-blue-500/90 backdrop-blur-sm rounded text-xs font-medium">
                                    📸
                                  </span>
                                )}
                              </div>
                            )}
                            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                              <div className="text-center px-2">
                                <div className="text-sm font-semibold">{job.model_name}</div>
                                <div className="text-xs text-gray-300 mt-1">{selectionMode ? 'Click to select' : 'Click to view details'}</div>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-xs text-gray-500 text-center px-4">
                              No image
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
            </div>
          )
        })()
      )}

      {/* Lightbox Modal */}
      {lightboxJob && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={closeLightbox}
        >
          <div
            className="bg-gray-900 rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              {/* Close Button */}
              <button
                onClick={closeLightbox}
                className="float-right text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              <h2 className="text-2xl font-bold mb-4">{lightboxJob.model_name}</h2>

              {/* Generated Image */}
              <div className="mb-6 relative">
                {lightboxJob.image_url ? (
                  <>
                    <img
                      src={lightboxJob.image_url}
                      alt="Generated"
                      className="w-full rounded-lg max-h-[60vh] object-contain"
                    />
                    {lightboxJob.edit_type && (
                      <div className="absolute top-3 left-3 flex gap-2">
                        {lightboxJob.edit_type === 'face_swap' && (
                          <span className="px-3 py-1.5 bg-blue-600/90 backdrop-blur-sm rounded-lg text-sm font-medium">
                            👤 Face Swapped
                          </span>
                        )}
                        {lightboxJob.edit_type === 'wavespeed_edit' && (
                          <span className="px-3 py-1.5 bg-purple-600/90 backdrop-blur-sm rounded-lg text-sm font-medium">
                            ✏️ Edited
                          </span>
                        )}
                        {lightboxJob.edit_type === 'wavespeed_variation' && (
                          <span className="px-3 py-1.5 bg-green-600/90 backdrop-blur-sm rounded-lg text-sm font-medium">
                            🎨 Variation
                          </span>
                        )}
                        {lightboxJob.edit_type === 'carousel_variation' && (
                          <span className="px-3 py-1.5 bg-blue-500/90 backdrop-blur-sm rounded-lg text-sm font-medium">
                            📸 Carousel
                          </span>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="aspect-square bg-gray-800 rounded-lg flex items-center justify-center">
                    <span className="text-gray-500">No image</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 mb-6 flex-wrap">
                <button
                  onClick={() => toggleStar(lightboxJob)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    lightboxJob.is_starred
                      ? 'bg-yellow-500/20 border border-yellow-500 text-yellow-400'
                      : 'bg-gray-800 border border-gray-700 hover:bg-gray-700'
                  }`}
                >
                  {lightboxJob.is_starred ? '⭐ Starred' : '☆ Star'}
                </button>

                <button
                  onClick={() => faceSwap(lightboxJob)}
                  disabled={faceSwapping}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium"
                >
                  {faceSwapping ? '⏳ Face Swapping...' : '👤 Face Swap'}
                </button>

                {(lightboxJob.batch_id || lightboxJob.group_id) && (
                  <button
                    onClick={() => faceSwapGroup(lightboxJob)}
                    disabled={faceSwapping}
                    className="px-4 py-2 bg-blue-700 hover:bg-blue-800 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-medium"
                  >
                    {faceSwapping ? '⏳ Swapping...' : '👥 Face Swap All in Group'}
                  </button>
                )}

                {/* Edit Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setShowEditDropdown(!showEditDropdown)}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium flex items-center gap-2"
                  >
                    ✏️ Edit
                    <span className="text-xs">▼</span>
                  </button>

                  {showEditDropdown && (
                    <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10 min-w-[200px]">
                      {/* Edit with Reference */}
                      {(lightboxJob.reference_filename || lightboxJob.parameters?.uploaded_image) && (
                        <button
                          onClick={openEditWithReferenceModal}
                          className="w-full px-4 py-2 text-left hover:bg-gray-700 text-sm flex items-center gap-2 rounded-t-lg"
                        >
                          🖼️ Edit with Reference
                        </button>
                      )}

                      {/* Create Variations */}
                      <button
                        onClick={() => openEditModal('variations')}
                        className="w-full px-4 py-2 text-left hover:bg-gray-700 text-sm flex items-center gap-2"
                      >
                        🎨 Create Variations
                      </button>

                      {/* Create Carousel Variations */}
                      <button
                        onClick={() => {
                          setShowCarouselModal(true)
                          setShowEditDropdown(false)
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-gray-700 text-sm flex items-center gap-2"
                      >
                        📸 Carousel Variations
                      </button>

                      {/* Quick Edit */}
                      <button
                        onClick={() => openEditModal('edit')}
                        className="w-full px-4 py-2 text-left hover:bg-gray-700 text-sm flex items-center gap-2 rounded-b-lg"
                      >
                        ✏️ Quick Edit
                      </button>
                    </div>
                  )}
                </div>

                <button
                  onClick={openRegenerateModal}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm font-medium"
                >
                  🔄 Regenerate
                </button>

                {lightboxJob.image_url && (
                  <a
                    href={lightboxJob.image_url}
                    download
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm font-medium"
                  >
                    📥 Download
                  </a>
                )}

                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium"
                >
                  {showDetails ? '📷 Hide Details' : '📋 View Details'}
                </button>

                <button
                  onClick={() => deleteImage(lightboxJob)}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium ml-auto"
                >
                  🗑️ Delete
                </button>
              </div>

              {/* Details Section (Collapsible) */}
              {showDetails && (
                <>
                  {/* Reference Image and Metadata Side-by-Side */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Reference Image */}
                <div>
                  <h3 className="text-lg font-semibold mb-2">Reference Image</h3>
                  {(lightboxJob.reference_filename || lightboxJob.parameters?.uploaded_image) ? (
                    <div>
                      <img
                        src={lightboxJob.reference_filename
                          ? `${SUPABASE_URL}/storage/v1/object/public/reference-images/${lightboxJob.reference_filename}`
                          : `https://4bpau787p5p1t6-3001.proxy.runpod.net/view?filename=${lightboxJob.parameters.uploaded_image}&subfolder=&type=input`
                        }
                        alt="Reference"
                        className="w-full rounded-lg"
                        onError={(e) => {
                          e.target.style.display = 'none'
                          e.target.nextElementSibling.style.display = 'flex'
                        }}
                      />
                      <div className="aspect-square bg-gray-800 rounded-lg flex items-center justify-center" style={{display: 'none'}}>
                        <span className="text-gray-500 text-sm">Reference image unavailable</span>
                      </div>
                      {lightboxJob.reference_caption && (
                        <div className="mt-2 bg-gray-800 p-3 rounded-lg">
                          <h4 className="text-xs font-semibold mb-1 text-gray-400">Grok Vision Caption</h4>
                          <p className="text-xs text-gray-300">{lightboxJob.reference_caption}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="aspect-square bg-gray-800 rounded-lg flex items-center justify-center">
                      <span className="text-gray-500">No reference image</span>
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Model</h3>
                    <p className="text-gray-300">{lightboxJob.model_name}</p>
                  </div>

                  {/* Edit History */}
                  {(lightboxJob.edit_type || lightboxJob.parent_image_id) && (
                    <div>
                      <h3 className="text-lg font-semibold mb-2">Edit History</h3>
                      <div className="bg-gray-800 p-3 rounded text-sm space-y-2">
                        {lightboxJob.edit_type && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Edit Type:</span>
                            <span className="text-gray-200 capitalize">{lightboxJob.edit_type.replace('_', ' ')}</span>
                          </div>
                        )}
                        {lightboxJob.parent_image_id && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Created From:</span>
                            <span className="text-blue-400">Image #{lightboxJob.parent_image_id}</span>
                          </div>
                        )}
                        {lightboxJob.face_swap_source && (
                          <div className="flex justify-between">
                            <span className="text-gray-400">Face Source:</span>
                            <span className="text-gray-200">{lightboxJob.face_swap_source}</span>
                          </div>
                        )}
                        {lightboxJob.parameters?.wavespeed_edit_prompt && (
                          <div>
                            <span className="text-gray-400 block mb-1">Edit Instruction:</span>
                            <p className="text-gray-200 text-xs bg-gray-700 p-2 rounded">{lightboxJob.parameters.wavespeed_edit_prompt}</p>
                          </div>
                        )}
                        {lightboxJob.parameters?.wavespeed_variation_prompt && (
                          <div>
                            <span className="text-gray-400 block mb-1">Variation Style:</span>
                            <p className="text-gray-200 text-xs bg-gray-700 p-2 rounded">{lightboxJob.parameters.wavespeed_variation_prompt}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div>
                    <h3 className="text-lg font-semibold mb-2">Positive Prompt</h3>
                    <p className="text-sm text-gray-300 bg-gray-800 p-3 rounded">{lightboxJob.prompt_used}</p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold mb-2">Negative Prompt</h3>
                    <p className="text-sm text-gray-300 bg-gray-800 p-3 rounded">{lightboxJob.negative_prompt_used}</p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold mb-2">Parameters</h3>
                    <div className="bg-gray-800 p-3 rounded text-sm space-y-1">
                      {lightboxJob.parameters && Object.entries(lightboxJob.parameters).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-400">{key}:</span>
                          <span className="text-gray-200">{JSON.stringify(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold mb-2">Timestamps</h3>
                    <div className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Created:</span>
                        <span className="text-gray-200">{new Date(lightboxJob.created_at).toLocaleString()}</span>
                      </div>
                      {lightboxJob.generated_at && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Generated:</span>
                          <span className="text-gray-200">{new Date(lightboxJob.generated_at).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit/Variations Modal */}
      {showEditModal && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={closeEditModal}
        >
          <div
            className="bg-gray-900 rounded-lg max-w-lg w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold mb-4">
              {editModalType === 'edit' ? '✏️ Edit Image' : '🎨 Create Variations'}
            </h2>

            {editModalType === 'edit' ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Edit Instruction</label>
                  <textarea
                    value={editPrompt}
                    onChange={(e) => {
                      setEditPrompt(e.target.value)
                      setEnhancedPrompt('')
                    }}
                    placeholder="e.g., 'remove tattoos', 'change hair to brunette', 'remove text from image'"
                    className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none min-h-[100px]"
                  />
                  <div className="flex items-center justify-between mt-1">
                    <p className="text-xs text-gray-400">Describe what you want to change in the image</p>
                    <button
                      onClick={enhancePrompt}
                      disabled={enhancing || !editPrompt.trim()}
                      className="text-xs px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded"
                    >
                      {enhancing ? '✨ Enhancing...' : '✨ Enhance with AI'}
                    </button>
                  </div>
                  {enhancedPrompt && (
                    <div className="mt-2 p-2 bg-green-900/30 border border-green-700 rounded text-xs">
                      <strong>Enhanced:</strong> {enhancedPrompt}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Number of Variations: {numVariations}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="8"
                    value={numVariations}
                    onChange={(e) => setNumVariations(parseInt(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-400 mt-1">Generate {numVariations} coherent variations (Cost: ${(numVariations * 0.027).toFixed(2)})</p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Variation Style (Optional)</label>
                  <textarea
                    value={editPrompt}
                    onChange={(e) => setEditPrompt(e.target.value)}
                    placeholder="e.g., 'different poses', 'various backgrounds', or leave blank for subtle variations"
                    className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none min-h-[80px]"
                  />
                  <p className="text-xs text-gray-400 mt-1">Optional: Describe the style of variations you want</p>
                </div>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button
                onClick={closeEditModal}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitEdit}
                disabled={processing}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium"
              >
                {processing ? '⏳ Processing...' : editModalType === 'edit' ? 'Apply Edit' : `Generate ${numVariations}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regenerate Modal */}
      {showRegenerateModal && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4 overflow-y-auto"
          onClick={closeRegenerateModal}
        >
          <div
            className="bg-gray-900 rounded-lg max-w-2xl w-full p-6 my-8"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold mb-4">🔄 Regenerate with Adjustments</h2>
            <p className="text-sm text-gray-400 mb-6">Adjust parameters and regenerate from the original source image</p>

            <div className="space-y-6">
              {/* Denoise */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  Denoise Strength: {regenerateParams.denoise}
                  <span
                    className="text-xs text-gray-400 cursor-help"
                    title="How much the AI can change from original. Higher = more creative, lower = closer to source"
                  >
                    ⓘ
                  </span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={regenerateParams.denoise}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, denoise: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-400 mt-1">Higher = more creative, lower = closer to source</p>
              </div>

              {/* CFG Scale */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  CFG Scale: {regenerateParams.cfg}
                  <span
                    className="text-xs text-gray-400 cursor-help"
                    title="Prompt adherence. Higher = follows prompt strictly, lower = more creative freedom"
                  >
                    ⓘ
                  </span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.1"
                  value={regenerateParams.cfg}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, cfg: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-400 mt-1">Higher = follows prompt strictly, lower = more creative</p>
              </div>

              {/* Steps */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  Steps: {regenerateParams.steps}
                  <span
                    className="text-xs text-gray-400 cursor-help"
                    title="Quality/detail level. More steps = higher quality but slower"
                  >
                    ⓘ
                  </span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="1"
                  value={regenerateParams.steps}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, steps: parseInt(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-400 mt-1">More steps = higher quality but slower</p>
              </div>

              {/* LoRA Strength */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  LoRA Strength: {regenerateParams.loraStrength}
                  <span
                    className="text-xs text-gray-400 cursor-help"
                    title="How strongly your model's features are applied. Higher = more like your model"
                  >
                    ⓘ
                  </span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={regenerateParams.loraStrength}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, loraStrength: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-400 mt-1">Higher = stronger model features, lower = more general</p>
              </div>

              {/* Seed */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  Seed: {regenerateParams.seed === -1 ? 'Random' : regenerateParams.seed}
                  <span
                    className="text-xs text-gray-400 cursor-help"
                    title="Random seed. Use -1 for random, or same seed for reproducible results"
                  >
                    ⓘ
                  </span>
                </label>
                <input
                  type="number"
                  value={regenerateParams.seed}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, seed: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                  placeholder="-1 for random"
                />
                <p className="text-xs text-gray-400 mt-1">-1 = random, same seed = reproducible</p>
              </div>

              {/* Positive Prompt */}
              <div>
                <label className="block text-sm font-medium mb-2">Positive Prompt</label>
                <textarea
                  value={regenerateParams.positivePrompt}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, positivePrompt: e.target.value })}
                  className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none min-h-[80px]"
                  placeholder="Describe what you want..."
                />
              </div>

              {/* Negative Prompt */}
              <div>
                <label className="block text-sm font-medium mb-2">Negative Prompt</label>
                <textarea
                  value={regenerateParams.negativePrompt}
                  onChange={(e) => setRegenerateParams({ ...regenerateParams, negativePrompt: e.target.value })}
                  className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none min-h-[60px]"
                  placeholder="What to avoid..."
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={closeRegenerateModal}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitRegenerate}
                disabled={processing}
                className="flex-1 px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium"
              >
                {processing ? '⏳ Processing...' : '🔄 Regenerate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Smart Blend Modal */}
      {showSmartBlendModal && (() => {
        const image1 = jobs.find(j => j.id === selectedImages[0])
        const image2 = jobs.find(j => j.id === selectedImages[1])

        return (
          <div
            className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
            onClick={closeSmartBlendModal}
          >
            <div
              className="bg-gray-900 rounded-lg max-w-4xl w-full p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-2xl font-bold mb-4">🎨 Smart Blend</h2>
              <p className="text-sm text-gray-400 mb-4">Transfer elements from Image 2 to Image 1</p>

              {/* Side-by-side images */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <div className="text-sm font-medium mb-2 text-center">Image 1 (Base)</div>
                  {image1?.image_url && (
                    <img
                      src={image1.image_url}
                      alt="Base image"
                      className="w-full h-64 object-cover rounded-lg border-2 border-blue-500"
                    />
                  )}
                </div>
                <div>
                  <div className="text-sm font-medium mb-2 text-center">Image 2 (Reference)</div>
                  {image2?.image_url && (
                    <img
                      src={image2.image_url}
                      alt="Reference image"
                      className="w-full h-64 object-cover rounded-lg border-2 border-purple-500"
                    />
                  )}
                </div>
              </div>

              <div className="space-y-4">
                {/* Transfer instruction */}
                <div>
                  <label className="block text-sm font-medium mb-2">What to transfer from Image 2 to Image 1?</label>
                  <textarea
                    value={smartBlendInstruction}
                    onChange={(e) => setSmartBlendInstruction(e.target.value)}
                    placeholder="e.g., 'use phone color from image 2' or 'copy facial angle from image 2'"
                    className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none min-h-[100px]"
                  />
                  <p className="text-xs text-gray-400 mt-1">Be specific about what to transfer</p>
                </div>

                {/* Number of variations */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Number of variations: {smartBlendVariations}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="8"
                    value={smartBlendVariations}
                    onChange={(e) => setSmartBlendVariations(parseInt(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    Generate {smartBlendVariations} variation(s) (Cost: ${(smartBlendVariations * 0.027).toFixed(2)})
                  </p>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={closeSmartBlendModal}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={submitSmartBlend}
                  disabled={smartBlending || !smartBlendInstruction.trim()}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium"
                >
                  {smartBlending ? '⏳ Processing...' : `🎨 Blend (${smartBlendVariations})`}
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Edit with Reference Modal */}
      {showEditWithReferenceModal && lightboxJob && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={closeEditWithReferenceModal}
        >
          <div
            className="bg-gray-900 rounded-lg max-w-5xl w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold mb-4">🖼️ Edit with Reference</h2>
            <p className="text-sm text-gray-400 mb-4">Edit generated image by comparing to original reference</p>

            {/* Side-by-side images */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* Reference Image (Original) */}
              <div>
                <div className="text-sm font-medium mb-2 text-center">Original Reference</div>
                {(lightboxJob.reference_filename || lightboxJob.parameters?.uploaded_image) ? (
                  <img
                    src={lightboxJob.reference_filename
                      ? `${SUPABASE_URL}/storage/v1/object/public/reference-images/${lightboxJob.reference_filename}`
                      : `https://4bpau787p5p1t6-3001.proxy.runpod.net/view?filename=${lightboxJob.parameters.uploaded_image}&subfolder=&type=input`
                    }
                    alt="Original reference"
                    className="w-full h-80 object-contain rounded-lg border-2 border-blue-500 bg-gray-800"
                  />
                ) : (
                  <div className="w-full h-80 bg-gray-800 rounded-lg border-2 border-gray-700 flex items-center justify-center">
                    <span className="text-gray-500">No reference image</span>
                  </div>
                )}
              </div>

              {/* Generated Image */}
              <div>
                <div className="text-sm font-medium mb-2 text-center">Generated Image</div>
                <img
                  src={lightboxJob.image_url}
                  alt="Generated"
                  className="w-full h-80 object-contain rounded-lg border-2 border-purple-500 bg-gray-800"
                />
              </div>
            </div>

            {/* Edit instruction */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">What to change?</label>
                <textarea
                  value={editWithReferencePrompt}
                  onChange={(e) => setEditWithReferencePrompt(e.target.value)}
                  placeholder="e.g., 'use phone case from reference' or 'match background to reference' or 'remove text from generated image'"
                  className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none min-h-[100px]"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Compare both images and describe what you want to change in the generated image
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={closeEditWithReferenceModal}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitEditWithReference}
                disabled={processing || !editWithReferencePrompt.trim()}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium"
              >
                {processing ? '⏳ Processing...' : '✨ Apply Edit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Carousel Variations Modal */}
      {showCarouselModal && lightboxJob && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={closeCarouselModal}
        >
          <div
            className="bg-gray-900 rounded-lg max-w-lg w-full p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold mb-4">📸 Create Carousel Variations</h2>
            <p className="text-sm text-gray-400 mb-4">
              Generate consistent images perfect for Instagram carousels - same background, outfit, and style with slightly different poses.
            </p>

            {/* Preview current image */}
            <div className="mb-6">
              <div className="text-sm font-medium mb-2">Starting Image:</div>
              <img
                src={lightboxJob.image_url}
                alt="Starting image"
                className="w-full h-48 object-contain rounded-lg border-2 border-blue-500 bg-gray-800"
              />
            </div>

            <div className="space-y-4">
              {/* Number of carousel images */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Number of Images: {carouselNumImages}
                </label>
                <input
                  type="range"
                  min="2"
                  max="7"
                  value={carouselNumImages}
                  onChange={(e) => setCarouselNumImages(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Generate {carouselNumImages} nearly-identical images with minimal variations
                </p>
              </div>

              {/* Optional variation prompt */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  What to vary? (optional)
                </label>
                <input
                  type="text"
                  value={carouselPrompt}
                  onChange={(e) => setCarouselPrompt(e.target.value)}
                  placeholder="e.g., 'different facial expressions' or 'hand positions'"
                  className="w-full px-4 py-2 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Default: "different camera angle, facial expression, and pose"
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={closeCarouselModal}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitCarouselVariations}
                disabled={processing}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium"
              >
                {processing ? '⏳ Generating...' : `📸 Generate ${carouselNumImages}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
