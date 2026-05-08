import { useState, useEffect, useCallback } from 'react'
import { 
  Play, Square, RefreshCw, Zap, CheckCircle, Clock, 
  AlertCircle, Filter, Search, FileText, Image as ImageIcon,
  Music, Video, Layers, Settings, Download
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function AIProcessing() {
  const [bronzeFiles, setBronzeFiles] = useState([])
  const [selectedFiles, setSelectedFiles] = useState([])
  const [processingJobs, setProcessingJobs] = useState([])
  const [filterType, setFilterType] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [processingState, setProcessingState] = useState('idle') // idle, running, paused
  const [availableModels, setAvailableModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('default')
  const [routingConfig, setRoutingConfig] = useState(null)

  // Fetch Bronze files (not yet processed)
  const fetchBronzeFiles = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/bronze/files?limit=100`)
      if (res.ok) {
        const data = await res.json()
        setBronzeFiles(data.files || [])
      }
    } catch (err) {
      console.error('Failed to fetch Bronze files:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch AI processor status and job queue
  const fetchProcessingJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/processing/status`)
      if (res.ok) {
        const data = await res.json()
        setProcessingJobs(data.recent_jobs || [])
        setProcessingState(data.processor?.status || 'unknown')
      }
    } catch (err) {
      console.error('Failed to fetch processing jobs:', err)
    }
  }, [])

  // Fetch available models from routing config
  const fetchRoutingConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/processing/routing-config`)
      if (res.ok) {
        const data = await res.json()
        setRoutingConfig(data.config || {})
        
        // Extract unique models from routing config
        const models = new Set(['default'])
        if (data.config && data.config.routing_rules) {
          Object.values(data.config.routing_rules).forEach(rule => {
            if (rule.model) models.add(rule.model)
          })
        }
        setAvailableModels([...models])
      }
    } catch (err) {
      console.error('Failed to fetch routing config:', err)
      setAvailableModels(['default', 'qwen/qwen3-vl-8b-thinking', 'qwen/qwen3-8b', 'openai/gpt-audio-mini'])
    }
  }, [])

  // Initial load
  useEffect(() => {
    fetchBronzeFiles()
    fetchProcessingJobs()
    fetchRoutingConfig()
    
    // Poll processing jobs every 5 seconds
    const interval = setInterval(fetchProcessingJobs, 5000)
    return () => clearInterval(interval)
  }, [fetchBronzeFiles, fetchProcessingJobs, fetchRoutingConfig])

  // Trigger AI processing for selected files
  const handleProcessFiles = async () => {
    if (selectedFiles.length === 0) {
      alert('Please select files to process')
      return
    }

    try {
      const payload = {
        file_keys: selectedFiles,
        model_override: selectedModel === 'default' ? null : selectedModel,
        priority: 'normal'
      }

      const res = await fetch(`${API_BASE}/api/silver/processing/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        const data = await res.json()
        alert(`${data.jobs_created} processing jobs created`)
        setSelectedFiles([])
        fetchProcessingJobs()
        fetchBronzeFiles()
      } else {
        const error = await res.json()
        alert(`Failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (err) {
      alert(`Error: ${err.message}`)
    }
  }

  // Toggle file selection
  const toggleFileSelection = (fileKey) => {
    setSelectedFiles(prev => 
      prev.includes(fileKey) 
        ? prev.filter(k => k !== fileKey)
        : [...prev, fileKey]
    )
  }

  // Select all visible files
  const selectAllVisible = () => {
    const visibleKeys = filteredFiles.map(f => f.object_key)
    setSelectedFiles(visibleKeys)
  }

  // Clear selection
  const clearSelection = () => {
    setSelectedFiles([])
  }

  // Filter files
  const filteredFiles = bronzeFiles.filter(file => {
    const matchesType = filterType === 'all' || file.file_type === filterType
    const matchesSearch = searchQuery === '' || 
      file.object_key.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesType && matchesSearch
  })

  // Get file type icon
  const getFileIcon = (type) => {
    switch(type) {
      case 'image':
      case 'jpg':
      case 'png':
      case 'gif':
        return <ImageIcon className="w-5 h-5 text-green-600" />
      case 'pdf':
      case 'document':
        return <FileText className="w-5 h-5 text-blue-600" />
      case 'audio':
      case 'mp3':
        return <Music className="w-5 h-5 text-purple-600" />
      case 'video':
      case 'mp4':
        return <Video className="w-5 h-5 text-red-600" />
      default:
        return <Layers className="w-5 h-5 text-gray-600" />
    }
  }

  // Get job status badge
  const getStatusBadge = (status) => {
    const colors = {
      pending: 'bg-gray-100 text-gray-700',
      processing: 'bg-blue-100 text-blue-700',
      success: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700'
    }
    
    const icons = {
      pending: <Clock className="w-3 h-3" />,
      processing: <Zap className="w-3 h-3 animate-pulse" />,
      success: <CheckCircle className="w-3 h-3" />,
      failed: <AlertCircle className="w-3 h-3" />
    }

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
        {icons[status]}
        {status}
      </span>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header with AI Processor Status */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">AI Processing Control Center</h2>
              <p className="text-sm text-gray-600 mt-1">
                Process Bronze layer files with OpenRouter AI models (qwen-8b, qwen-vl, gpt-audio)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-gray-600">AI Processor Status</p>
              <div className="flex items-center gap-2 mt-1">
                {processingState === 'running' ? (
                  <>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-semibold text-green-700">Running</span>
                  </>
                ) : processingState === 'stopped' ? (
                  <>
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span className="text-sm font-semibold text-red-700">Stopped</span>
                  </>
                ) : (
                  <>
                    <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                    <span className="text-sm font-semibold text-gray-700">Unknown</span>
                  </>
                )}
              </div>
            </div>
            <button
              onClick={() => { fetchBronzeFiles(); fetchProcessingJobs(); fetchRoutingConfig(); }}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pending Files</p>
              <p className="text-2xl font-bold text-gray-900">{bronzeFiles.length}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Layers className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Processing</p>
              <p className="text-2xl font-bold text-gray-900">
                {processingJobs.filter(j => j.status === 'processing').length}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6 text-purple-600 animate-pulse" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-gray-900">
                {processingJobs.filter(j => j.status === 'success').length}
              </p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Selected</p>
              <p className="text-2xl font-bold text-gray-900">{selectedFiles.length}</p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <Settings className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Quick workflow guide */}
      <div className="bg-white rounded-lg p-4 border border-blue-200">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 mb-2">How AI Processing Works</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="font-medium text-gray-900 mb-1">1. Select Files</p>
                <p className="text-gray-600">Choose files from Bronze layer below</p>
              </div>
              <div>
                <p className="font-medium text-gray-900 mb-1">2. Choose Model</p>
                <p className="text-gray-600">Auto-routing by file type or override</p>
              </div>
              <div>
                <p className="font-medium text-gray-900 mb-1">3. Process</p>
                <p className="text-gray-600">AI extracts text, detects objects, transcribes audio</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg w-64"
            />
          </div>

          {/* Filter by type */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg"
          >
            <option value="all">All Types</option>
            <option value="image">Images</option>
            <option value="pdf">PDFs</option>
            <option value="document">Documents</option>
            <option value="audio">Audio</option>
            <option value="video">Video</option>
          </select>

          {/* Model selection */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">AI Model:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg"
            >
              {availableModels.map(model => (
                <option key={model} value={model}>
                  {model === 'default' ? 'Auto (Default)' : model.split('/').pop()}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedFiles.length > 0 && (
            <>
              <span className="text-sm text-gray-600">
                {selectedFiles.length} selected
              </span>
              <button
                onClick={clearSelection}
                className="px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Clear
              </button>
              <button
                onClick={handleProcessFiles}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                Process {selectedFiles.length} Files
              </button>
            </>
          )}
          {selectedFiles.length === 0 && filteredFiles.length > 0 && (
            <button
              onClick={selectAllVisible}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Select All ({filteredFiles.length})
            </button>
          )}
        </div>
      </div>

      {/* Bronze Files Table */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Bronze Files Ready for Processing
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {filteredFiles.length} files waiting in Bronze layer
          </p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading files...</div>
        ) : filteredFiles.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No files found in Bronze layer
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    <input
                      type="checkbox"
                      checked={selectedFiles.length === filteredFiles.length && filteredFiles.length > 0}
                      onChange={(e) => e.target.checked ? selectAllVisible() : clearSelection()}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">File Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uploaded</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredFiles.map((file) => (
                  <tr 
                    key={file.object_key}
                    className={`hover:bg-gray-50 ${selectedFiles.includes(file.object_key) ? 'bg-blue-50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedFiles.includes(file.object_key)}
                        onChange={() => toggleFileSelection(file.object_key)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="px-4 py-3">
                      {getFileIcon(file.file_type)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-md">
                        {file.object_key.split('/').pop()}
                      </div>
                      <div className="text-xs text-gray-500 truncate max-w-md">
                        {file.object_key}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {file.size_bytes ? `${(file.size_bytes / 1024 / 1024).toFixed(2)} MB` : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {file.uploaded_at ? new Date(file.uploaded_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        {file.source || 'CDC'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Processing Jobs */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent Processing Jobs</h3>
          <p className="text-sm text-gray-600 mt-1">Last 10 jobs from ai_processor.py</p>
        </div>

        {processingJobs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No processing jobs yet. Start the ai_processor.py to begin processing.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">File</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model Used</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Processed At</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {processingJobs.slice(0, 10).map((job, idx) => (
                  <tr key={job.id || idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {getStatusBadge(job.extraction_status || job.status || 'pending')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-md">
                        {job.file_key?.split('/').pop() || job.file_type || 'Processing...'}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {job.ai_model_used ? job.ai_model_used.split('/').pop() : job.model_used || 'Auto'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {job.processed_at ? new Date(job.processed_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {job.duration_seconds ? `${job.duration_seconds}s` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
