import { useState, useEffect } from 'react'
import { supabase } from '../supabase'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

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

export default function Models() {
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState(null)
  const [subModels, setSubModels] = useState([])
  const [selectedSubModel, setSelectedSubModel] = useState(null)
  const [contentTypes, setContentTypes] = useState([])
  const [loading, setLoading] = useState(true)

  // Modal states
  const [showSubModelModal, setShowSubModelModal] = useState(false)
  const [showContentTypeModal, setShowContentTypeModal] = useState(false)
  const [editingSubModel, setEditingSubModel] = useState(null)
  const [editingContentType, setEditingContentType] = useState(null)

  useEffect(() => {
    fetchModels()
  }, [])

  useEffect(() => {
    if (selectedModel) {
      fetchSubModels(selectedModel.id)
    }
  }, [selectedModel])

  useEffect(() => {
    if (selectedSubModel) {
      fetchContentTypes(selectedSubModel.id)
    }
  }, [selectedSubModel])

  async function fetchModels() {
    setLoading(true)
    const { data } = await supabase.from('models').select('*').order('name')
    setModels(data || [])
    if (data && data.length > 0) {
      setSelectedModel(data[0])
    }
    setLoading(false)
  }

  async function fetchSubModels(modelId) {
    const response = await fetch(`${API_URL}/api/models/${modelId}/sub-models`)
    const data = await response.json()
    setSubModels(data || [])
    setSelectedSubModel(null)
    setContentTypes([])
  }

  async function fetchContentTypes(subModelId) {
    const response = await fetch(`${API_URL}/api/sub-models/${subModelId}/content-types`)
    const data = await response.json()
    setContentTypes(data || [])
  }

  async function saveSubModel(formData) {
    const payload = { ...formData, model_id: selectedModel.id }

    if (editingSubModel) {
      await fetch(`${API_URL}/api/sub-models/${editingSubModel.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
    } else {
      await fetch(`${API_URL}/api/sub-models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
    }

    fetchSubModels(selectedModel.id)
    setShowSubModelModal(false)
    setEditingSubModel(null)
  }

  async function deleteSubModel(id) {
    if (confirm('Delete this sub-model?')) {
      await fetch(`${API_URL}/api/sub-models/${id}`, { method: 'DELETE' })
      fetchSubModels(selectedModel.id)
      if (selectedSubModel?.id === id) {
        setSelectedSubModel(null)
      }
    }
  }

  async function saveContentType(formData) {
    const payload = { ...formData, sub_model_id: selectedSubModel.id }

    if (editingContentType) {
      await fetch(`${API_URL}/api/content-types/${editingContentType.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
    } else {
      await fetch(`${API_URL}/api/content-types`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
    }

    fetchContentTypes(selectedSubModel.id)
    setShowContentTypeModal(false)
    setEditingContentType(null)
  }

  async function deleteContentType(id) {
    if (confirm('Delete this content type?')) {
      await fetch(`${API_URL}/api/content-types/${id}`, { method: 'DELETE' })
      fetchContentTypes(selectedSubModel.id)
    }
  }

  if (loading) {
    return <div className="p-6 text-center text-gray-400">Loading...</div>
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Models Management</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Models */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h2 className="text-xl font-semibold mb-4">Main Models</h2>
          <div className="space-y-2">
            {models.map(model => (
              <div
                key={model.id}
                onClick={() => setSelectedModel(model)}
                className={`p-3 rounded-lg cursor-pointer transition-all ${
                  selectedModel?.id === model.id
                    ? 'bg-blue-600'
                    : 'bg-gray-800 hover:bg-gray-700'
                }`}
              >
                <div className="font-semibold">{model.name}</div>
                <div className="text-xs text-gray-400">{model.trigger_word}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Sub-Models */}
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Sub-Models</h2>
            {selectedModel && (
              <button
                onClick={() => {
                  setEditingSubModel(null)
                  setShowSubModelModal(true)
                }}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              >
                + Add
              </button>
            )}
          </div>

          {!selectedModel ? (
            <div className="text-gray-500 text-sm text-center py-8">Select a main model</div>
          ) : subModels.length === 0 ? (
            <div className="text-gray-500 text-sm text-center py-8">No sub-models yet</div>
          ) : (
            <div className="space-y-2">
              {subModels.map(subModel => (
                <div
                  key={subModel.id}
                  onClick={() => setSelectedSubModel(subModel)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedSubModel?.id === subModel.id
                      ? 'bg-blue-600'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold">{subModel.name}</div>
                      {subModel.fanhub_account && (
                        <div className="text-xs text-gray-400">FanVue: {subModel.fanhub_account}</div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingSubModel(subModel)
                          setShowSubModelModal(true)
                        }}
                        className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                      >
                        Edit
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSubModel(subModel.id)
                        }}
                        className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded"
                      >
                        Del
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content Types */}
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Content Types</h2>
            {selectedSubModel && (
              <button
                onClick={() => {
                  setEditingContentType(null)
                  setShowContentTypeModal(true)
                }}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              >
                + Add
              </button>
            )}
          </div>

          {!selectedSubModel ? (
            <div className="text-gray-500 text-sm text-center py-8">Select a sub-model</div>
          ) : contentTypes.length === 0 ? (
            <div className="text-gray-500 text-sm text-center py-8">No content types yet</div>
          ) : (
            <div className="space-y-2">
              {contentTypes.map(contentType => (
                <div
                  key={contentType.id}
                  className="p-3 rounded-lg bg-gray-800"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold">{contentType.name}</div>
                      {contentType.instagram_account && (
                        <div className="text-xs text-gray-400">IG: {contentType.instagram_account}</div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => {
                          setEditingContentType(contentType)
                          setShowContentTypeModal(true)
                        }}
                        className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => deleteContentType(contentType.id)}
                        className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded"
                      >
                        Del
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sub-Model Modal */}
      {showSubModelModal && (
        <SubModelModal
          subModel={editingSubModel}
          onSave={saveSubModel}
          onClose={() => {
            setShowSubModelModal(false)
            setEditingSubModel(null)
          }}
        />
      )}

      {/* Content Type Modal */}
      {showContentTypeModal && (
        <ContentTypeModal
          contentType={editingContentType}
          onSave={saveContentType}
          onClose={() => {
            setShowContentTypeModal(false)
            setEditingContentType(null)
          }}
        />
      )}
    </div>
  )
}

function SubModelModal({ subModel, onSave, onClose }) {
  const [formData, setFormData] = useState({
    name: subModel?.name || '',
    face_image_url: subModel?.face_image_url || '',
    fanhub_account: subModel?.fanhub_account || '',
    description: subModel?.description || ''
  })
  const [uploading, setUploading] = useState(false)

  async function handleFileUpload(e) {
    const file = e.target.files[0]
    if (!file) return

    setUploading(true)
    try {
      const formDataUpload = new FormData()
      formDataUpload.append('image', file)

      const response = await fetch(`${API_URL}/api/upload-face`, {
        method: 'POST',
        body: formDataUpload
      })

      const result = await response.json()
      if (result.success) {
        setFormData({...formData, face_image_url: result.url})
      } else {
        alert('Upload failed: ' + result.error)
      }
    } catch (error) {
      alert('Upload error: ' + error.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 rounded-lg p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
        <h3 className="text-xl font-bold mb-4">{subModel ? 'Edit' : 'Add'} Sub-Model</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              placeholder="e.g., Hazel Ray"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Face Image</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              disabled={uploading}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
            {uploading && <p className="text-xs text-gray-400 mt-1">Uploading...</p>}
            {formData.face_image_url && (
              <div className="mt-2">
                <img src={formData.face_image_url} alt="Face preview" className="w-24 h-24 object-cover rounded" />
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">FanVue Account</label>
            <input
              type="text"
              value={formData.fanhub_account}
              onChange={e => setFormData({...formData, fanhub_account: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              placeholder="@username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              rows="3"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => onSave(formData)}
            disabled={uploading}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold disabled:opacity-50"
          >
            Save
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-semibold"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function ContentTypeModal({ contentType, onSave, onClose }) {
  const [formData, setFormData] = useState({
    name: contentType?.name || '',
    instagram_account: contentType?.instagram_account || '',
    description: contentType?.description || ''
  })

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 rounded-lg p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
        <h3 className="text-xl font-bold mb-4">{contentType ? 'Edit' : 'Add'} Content Type</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              placeholder="e.g., Bikini, Lingerie, Fitness"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Instagram Account</label>
            <input
              type="text"
              value={formData.instagram_account}
              onChange={e => setFormData({...formData, instagram_account: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              placeholder="@username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              className="w-full px-3 py-2 bg-gray-800 rounded border border-gray-700"
              rows="3"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => onSave(formData)}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold"
          >
            Save
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-semibold"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
