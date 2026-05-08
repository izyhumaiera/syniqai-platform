import { useState } from 'react'
import { Upload, FileText, Link, Database, X } from 'lucide-react'
import Alert from '../components/ui/Alert'

export default function ManualInput() {
  const [activeTab, setActiveTab] = useState('files') // files | text | url | query
  const [files, setFiles] = useState([])
  const [textContent, setTextContent] = useState('')
  const [textLabel, setTextLabel] = useState('user_input')
  const [contentType, setContentType] = useState('text')
  const [urlInput, setUrlInput] = useState('')
  const [queryConfig, setQueryConfig] = useState({
    source_type: 'postgresql',
    connection_id: 'default',
    query: ''
  })
  const [uploadProgress, setUploadProgress] = useState([])
  const [message, setMessage] = useState(null)

  const tabs = [
    { id: 'files', name: 'File Upload', icon: Upload },
    { id: 'text', name: 'Text/JSON', icon: FileText },
    { id: 'url', name: 'URL Fetch', icon: Link },
    { id: 'query', name: 'Database Query', icon: Database }
  ]

  const handleFilesDrop = (e) => {
    e.preventDefault()
    const droppedFiles = Array.from(e.dataTransfer?.files || e.target.files || [])
    
    const newFiles = droppedFiles.map(file => ({
      file,
      routeTo: 'unstructured',
      model: 'default',
      domain: 'general',
      status: 'pending'
    }))
    
    setFiles([...files, ...newFiles])
  }

  const updateFileConfig = (index, field, value) => {
    const updated = [...files]
    updated[index][field] = value
    setFiles(updated)
  }

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  const handleIngestFiles = async () => {
    if (files.length === 0) return

    setMessage(null)
    const formData = new FormData()

    files.forEach(({ file, routeTo, model, domain }) => {
      formData.append('files', file)
      formData.append('route_to', routeTo)
      formData.append('model_override', model === 'default' ? 'none' : model)
      formData.append('domain', domain)
    })

    try {
      const response = await fetch('/api/ingest/manual/files', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setMessage({ type: 'success', text: data.message })
        setFiles([])
      } else {
        setMessage({ type: 'error', text: `Failed: ${data.errors.join(', ')}` })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Request failed: ${error.message}` })
    }
  }

  const handleIngestText = async () => {
    if (!textContent.trim()) return

    setMessage(null)

    try {
      const response = await fetch('/api/ingest/manual/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: textContent,
          label: textLabel,
          route_to: 'unstructured',
          model_override: null,
          domain: 'general',
          content_type: contentType
        })
      })

      const data = await response.json()

      if (data.success) {
        setMessage({ type: 'success', text: data.message })
        setTextContent('')
        setTextLabel('user_input')
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Request failed: ${error.message}` })
    }
  }

  const handleIngestURL = async () => {
    if (!urlInput.trim()) return

    setMessage(null)

    try {
      const response = await fetch('/api/ingest/manual/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: urlInput,
          route_to: 'unstructured',
          model_override: null,
          domain: 'general'
        })
      })

      const data = await response.json()

      if (data.success) {
        setMessage({ type: 'success', text: data.message })
        setUrlInput('')
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Request failed: ${error.message}` })
    }
  }

  const handleIngestQuery = async () => {
    setMessage({ type: 'info', text: 'Database query ingestion coming soon...' })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Manual Data Input</h2>
        <p className="text-gray-600 mt-1">
          Upload files, paste text, fetch from URLs, or query existing databases
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                {tab.name}
              </button>
            )
          })}
        </nav>
      </div>

      {message && (
        <Alert type={message.type}>{message.text}</Alert>
      )}

      {/* File Upload Tab */}
      {activeTab === 'files' && (
        <div className="space-y-4">
          <div
            onDrop={handleFilesDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-400 transition-colors"
          >
            <CloudArrowUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-lg text-gray-700 font-medium mb-2">
              Drop files here or click to browse
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supports all file types: images, documents, PDFs, audio, video, CSV, JSON
            </p>
            <input
              type="file"
              multiple
              onChange={handleFilesDrop}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="btn-primary cursor-pointer">
              Select Files
            </label>
          </div>

          {/* Files List */}
          {files.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                <h3 className="font-semibold text-gray-900">{files.length} file(s) ready</h3>
                <button onClick={handleIngestFiles} className="btn-primary">
                  Ingest All
                </button>
              </div>

              <div className="divide-y divide-gray-200">
                {files.map((item, index) => (
                  <div key={index} className="p-4 grid grid-cols-6 gap-4 items-center">
                    <div className="col-span-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(item.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>

                    <select
                      value={item.routeTo}
                      onChange={(e) => updateFileConfig(index, 'routeTo', e.target.value)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      <option value="unstructured">Unstructured (AI)</option>
                      <option value="structured">Structured (SQL)</option>
                    </select>

                    <select
                      value={item.model}
                      onChange={(e) => updateFileConfig(index, 'model', e.target.value)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                      disabled={item.routeTo === 'structured'}
                    >
                      <option value="default">Default</option>
                      <option value="qwen/qwen-2-vl-72b-instruct">Qwen Vision</option>
                      <option value="qwen/qwen-2.5-72b-instruct">Qwen Text</option>
                    </select>

                    <select
                      value={item.domain}
                      onChange={(e) => updateFileConfig(index, 'domain', e.target.value)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      <option value="general">General</option>
                      <option value="finance">Finance</option>
                      <option value="healthcare">Healthcare</option>
                    </select>

                    <button
                      onClick={() => removeFile(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Text/JSON Tab */}
      {activeTab === 'text' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Label
              </label>
              <input
                type="text"
                value={textLabel}
                onChange={(e) => setTextLabel(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
                placeholder="e.g., user_note, transaction_data"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Content Type
              </label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="text"
                    checked={contentType === 'text'}
                    onChange={(e) => setContentType(e.target.value)}
                    className="mr-2"
                  />
                  Plain Text
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="json"
                    checked={contentType === 'json'}
                    onChange={(e) => setContentType(e.target.value)}
                    className="mr-2"
                  />
                  JSON
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Content
              </label>
              <textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                rows={12}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 font-mono text-sm"
                placeholder={contentType === 'json' 
                  ? '{\n  "key": "value"\n}'
                  : 'Paste your text content here...'
                }
              />
            </div>

            <div className="flex justify-end">
              <button onClick={handleIngestText} className="btn-primary">
                Ingest Text
              </button>
            </div>
          </div>
        </div>
      )}

      {/* URL Tab */}
      {activeTab === 'url' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL to Fetch
              </label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-4 py-2"
                placeholder="https://example.com/data.json"
              />
              <p className="text-xs text-gray-500 mt-1">
                Server will fetch the content and ingest it. Supports images, documents, JSON, etc.
              </p>
            </div>

            <div className="flex justify-end">
              <button onClick={handleIngestURL} className="btn-primary">
                Fetch and Ingest
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Query Tab */}
      {activeTab === 'query' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="text-center py-12">
              <Database className="w-16 h-16 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Database Query Ingestion
              </h3>
              <p className="text-gray-600 mb-4">
                Execute queries against your connected databases and ingest the results
              </p>
              <p className="text-sm text-blue-600 font-medium">
                Coming soon in the next update
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
