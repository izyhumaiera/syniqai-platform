import { useState, useEffect } from 'react'
import { Play, Pause, RefreshCw, Clock, File, Video, Music, FileText, Image, AlertCircle, CheckCircle, } from 'lucide-react'
import axios from 'axios'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Alert from '../components/ui/Alert'

const API_BASE = 'http://localhost:8000/api'

// File type icon mapping
const FILE_TYPE_ICONS = {
  pdf: FileText,
  txt: FileText,
  image: Image,
  audio: Music,
  video: Video,
  unknown: File
}

const FILE_TYPE_COLORS = {
  pdf: 'text-red-600 bg-red-50',
  txt: 'text-gray-600 bg-gray-50',
  image: 'text-purple-600 bg-purple-50',
  audio: 'text-blue-600 bg-blue-50',
  video: 'text-green-600 bg-green-50',
  unknown: 'text-gray-400 bg-gray-50'
}

const BronzeReadyPanel = () => {
  const [emitterStatus, setEmitterStatus] = useState(null)
  const [readyItems, setReadyItems] = useState([])
  const [mediaPendingItems, setMediaPendingItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [selectedTab, setSelectedTab] = useState('ready') // 'ready' or 'pending'

  useEffect(() => {
    loadAllData()
    const interval = setInterval(loadAllData, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const loadAllData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Load status, ready items, and pending items in parallel
      const [statusRes, readyRes, pendingRes] = await Promise.all([
        axios.get(`${API_BASE}/bronze-ready/status`).catch(() => ({ data: { running: false } })),
        axios.get(`${API_BASE}/bronze-ready/items?limit=50`).catch(() => ({ data: { items: [] } })),
        axios.get(`${API_BASE}/bronze-ready/media-pending?limit=50`).catch(() => ({ data: { items: [] } }))
      ])
      
      setEmitterStatus(statusRes.data)
      setReadyItems(readyRes.data.items || [])
      setMediaPendingItems(pendingRes.data.items || [])
    } catch (err) {
      console.error('Error loading bronze ready data:', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStartEmitter = async () => {
    try {
      setActionLoading(true)
      setError(null)
      const response = await axios.post(`${API_BASE}/bronze-ready/start`)
      if (response.data.success) {
        await loadAllData()
      } else {
        setError(response.data.message)
      }
    } catch (err) {
      console.error('Error starting emitter:', err)
      setError(err.response?.data?.detail || 'Failed to start emitter')
    } finally {
      setActionLoading(false)
    }
  }

  const handleStopEmitter = async () => {
    try {
      setActionLoading(true)
      setError(null)
      const response = await axios.post(`${API_BASE}/bronze-ready/stop`)
      if (response.data.success) {
        await loadAllData()
      } else {
        setError(response.data.message)
      }
    } catch (err) {
      console.error('Error stopping emitter:', err)
      setError(err.response?.data?.detail || 'Failed to stop emitter')
    } finally {
      setActionLoading(false)
    }
  }

  const handleTriggerMedia = async (item) => {
    try {
      setActionLoading(true)
      setError(null)
      
      const response = await axios.post(`${API_BASE}/bronze-ready/trigger`, {
        object_key: item.object_key,
        file_type: item.file_type,
        source: item.source
      })
      
      if (response.data.success) {
        // Refresh data
        await loadAllData()
        alert(`✓ ${item.object_key} has been triggered for processing!`)
      }
    } catch (err) {
      console.error('Error triggering media:', err)
      setError(err.response?.data?.detail || 'Failed to trigger processing')
    } finally {
      setActionLoading(false)
    }
  }

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A'
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)
      
      if (minutes < 1) return 'Just now'
      if (minutes < 60) return `${minutes}m ago`
      if (hours < 24) return `${hours}h ago`
      return `${days}d ago`
    } catch {
      return timestamp
    }
  }

  const getFileIcon = (fileType) => {
    const Icon = FILE_TYPE_ICONS[fileType] || FILE_TYPE_ICONS.unknown
    return Icon
  }

  const renderItem = (item, isPending = false) => {
    const Icon = getFileIcon(item.file_type)
    const colorClass = FILE_TYPE_COLORS[item.file_type] || FILE_TYPE_COLORS.unknown

    return (
      <div
        key={item.object_key}
        className="bg-white border border-gray-200 rounded-lg p-4 hover:border-orange-300 hover:shadow-md transition-all"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <div className={`p-2 rounded-lg ${colorClass}`}>
                <Icon size={20} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">
                  {item.object_key.split('/').pop()}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {item.object_key}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-xs text-gray-600">
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {formatTimestamp(item.timestamp)}
              </span>
              <span className="px-2 py-0.5 bg-gray-100 rounded-full capitalize">
                {item.source}
              </span>
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full uppercase">
                {item.file_type}
              </span>
            </div>
          </div>

          {isPending && (
            <button
              onClick={() => handleTriggerMedia(item)}
              disabled={actionLoading}
              className="ml-4 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm font-medium"
            >
              <Play size={16} />
              Trigger
            </button>
          )}

          {!isPending && (
            <div className="ml-4 px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1">
              <CheckCircle size={14} />
              Ready
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Emitter Status Card */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-3 h-3 rounded-full ${emitterStatus?.running ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Bronze Ready Emitter</h3>
              <p className="text-sm text-gray-600">
                {emitterStatus?.running
                  ? `Running • PID: ${emitterStatus.pid} • Uptime: ${emitterStatus.uptime}`
                  : 'Not running'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadAllData}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>

            {emitterStatus?.running ? (
              <button
                onClick={handleStopEmitter}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <Pause size={16} />
                Stop
              </button>
            ) : (
              <button
                onClick={handleStartEmitter}
                disabled={actionLoading || !emitterStatus?.kafka_available}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <Play size={16} />
                Start
              </button>
            )}
          </div>
        </div>

        {!emitterStatus?.kafka_available && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-2">
            <AlertCircle size={18} className="text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Kafka is not available</p>
              <p className="text-yellow-700">Please start Kafka before running the emitter.</p>
            </div>
          </div>
        )}

        {error && (
          <Alert type="error" className="mt-4">
            {error}
          </Alert>
        )}
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="border-b border-gray-200 bg-gray-50">
          <div className="flex">
            <button
              onClick={() => setSelectedTab('ready')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                selectedTab === 'ready'
                  ? 'border-b-2 border-orange-500 text-orange-600 bg-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Ready Queue ({readyItems.length})
            </button>
            <button
              onClick={() => setSelectedTab('pending')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${
                selectedTab === 'pending'
                  ? 'border-b-2 border-orange-500 text-orange-600 bg-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              Media Pending ({mediaPendingItems.length})
            </button>
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <>
              {selectedTab === 'ready' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-lg font-semibold text-gray-900">Auto-Process Queue</h4>
                      <p className="text-sm text-gray-600">
                        Files ready for automatic AI processing (PDF, TXT, Images)
                      </p>
                    </div>
                  </div>

                  {readyItems.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <File size={48} className="mx-auto mb-4 text-gray-400" />
                      <p className="text-lg font-medium">No items in ready queue</p>
                      <p className="text-sm mt-1">Files will appear here when detected in Bronze layer</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {readyItems.map(item => renderItem(item, false))}
                    </div>
                  )}
                </div>
              )}

              {selectedTab === 'pending' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-lg font-semibold text-gray-900">Media Pending Queue</h4>
                      <p className="text-sm text-gray-600">
                        Audio/Video files awaiting manual trigger (requires user approval)
                      </p>
                    </div>
                  </div>

                  {mediaPendingItems.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Video size={48} className="mx-auto mb-4 text-gray-400" />
                      <p className="text-lg font-medium">No media files pending</p>
                      <p className="text-sm mt-1">Audio/Video files will appear here for manual approval</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {mediaPendingItems.map(item => renderItem(item, true))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default BronzeReadyPanel
