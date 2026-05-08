import { useState, useEffect, useCallback } from 'react'
import { 
  Image, Video, Scan, Tag, Play, Pause, 
  ZoomIn, Download, Upload, Settings, Eye,
  Grid3x3, Box, AlertCircle, CheckCircle, Layers, RefreshCw
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function ObjectDetection() {
  const [selectedMedia, setSelectedMedia] = useState(null)
  const [detectionMode, setDetectionMode] = useState('objects') // 'objects', 'faces', 'text', 'scenes'
  const [isProcessing, setIsProcessing] = useState(false)
  const [liveMediaItems, setLiveMediaItems] = useState([])
  const [loadingMedia, setLoadingMedia] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)

  // Live ML model registry (replaces hard-coded models array)
  const [liveModels, setLiveModels] = useState([])

  // Per-image analysis data from AnalysisService
  const [analysisData, setAnalysisData] = useState(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [detectionError, setDetectionError] = useState(null)

  const fetchMediaItems = useCallback(async () => {
    setLoadingMedia(true)
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/preview/image?domain=media&entity=assets&limit=20`)
      if (res.ok) {
        const data = await res.json()
        const mapped = (data.records || []).map((r, i) => {
          const objectPath = r.bronze_path ||
            (r.s3_path || '').replace('s3a://syniqai-bronze/', '') ||
            (r.path || '').replace('s3a://syniqai-bronze/', '')
          const thumbnailUrl = objectPath
            ? `${API_BASE}/api/silver/unstructured/thumbnail/syniqai-bronze/${objectPath}`
            : null
          return {
          id: `item_${i}_${objectPath || r.file_name || 'unknown'}`,
          name: r.file_name || `image_${i}.jpg`,
          type: 'image',
          thumbnailUrl,
          objectPath,
          status: r.processing_status || 'pending',
          detections: [],
          processed: r.last_modified || null,
          width: r.width,
          height: r.height,
          format: r.format,
          blur_score: r.blur_score,
          brightness: r.brightness_avg,
        }})
        setLiveMediaItems(mapped)
      }
    } catch (err) {
      console.warn('Could not fetch image preview:', err)
    } finally {
      setHasFetched(true)
      setLoadingMedia(false)
    }
  }, [])

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/models`)
      if (res.ok) {
        const data = await res.json()
        setLiveModels((data.models || []).filter(m =>
          (m.media_types || []).some(t => ['image', 'video'].includes(t)) &&
          m.category === 'detection'
        ))
      }
    } catch (err) { console.warn('Could not fetch models:', err) }
  }, [])

  const fetchAnalysis = useCallback(async (item) => {
    if (!item) return
    setLoadingAnalysis(true)
    setAnalysisData(null)
    try {
      // Derive entity from the actual object path (e.g. media/s3/image_files/10.jpg → image_files)
      let domain = 'media'
      let entity = 'assets'
      if (item.objectPath) {
        const parts = item.objectPath.split('/')
        if (parts.length >= 3) { domain = parts[0]; entity = parts[2] }
      }
      const params = new URLSearchParams({ file_id: item.id, domain, entity })
      const res = await fetch(`${API_BASE}/api/silver/unstructured/analysis/image?${params}`)
      if (res.ok) setAnalysisData(await res.json())
    } catch (err) { console.warn('Could not fetch image analysis:', err) }
    finally { setLoadingAnalysis(false) }
  }, [])

  const [jobProgress, setJobProgress] = useState(null) // null | { progress, message }

  const runDetection = useCallback(async () => {
    if (!selectedMedia || isProcessing) return
    setIsProcessing(true)
    setDetectionError(null)
    setJobProgress({ progress: 0, message: 'Queuing job…' })
    const transformMap = {
      objects: { objectDetection: true },
      faces:   { objectDetection: true },
      text:    { extractText: true },
      scenes:  { objectDetection: true },
    }
    // Derive domain and entity from the actual bronze path
    // objectPath looks like: media/s3/image_files/10.jpg
    let domain = 'media'
    let entity = 'assets'
    if (selectedMedia.objectPath) {
      const parts = selectedMedia.objectPath.split('/')
      if (parts.length >= 3) {
        domain = parts[0]   // e.g. 'media'
        entity = parts[2]   // e.g. 'image_files'
      }
    }
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_type: 'image',
          domain,
          entity,
          execution_mode: 'full',
          transforms: transformMap[detectionMode] || { objectDetection: true },
          stage_to_bronze: false,
        }),
      })
      if (!res.ok) {
        let detail = `Server returned ${res.status}`
        try {
          const errBody = await res.json()
          detail = errBody.detail || errBody.message || detail
        } catch (_) {}
        throw new Error(detail)
      }
      const { job_id } = await res.json()
      // Poll until done
      let done = false
      while (!done) {
        await new Promise(r => setTimeout(r, 1500))
        const poll = await fetch(`${API_BASE}/api/silver/unstructured/jobs/${job_id}`)
        if (poll.ok) {
          const job = await poll.json()
          setJobProgress({ progress: job.progress ?? 0, message: job.message || job.status })
          if (['completed', 'failed', 'error'].includes(job.status)) {
            if (job.status === 'failed' || job.status === 'error') {
              throw new Error(job.error_message || `Job ${job.status}`)
            }
            done = true
          }
        } else {
          done = true
        }
      }
      // Refresh analysis for selected image
      await fetchAnalysis(selectedMedia)
      await fetchMediaItems()
    } catch (err) {
      const msg = err?.message || String(err)
      setDetectionError(msg.includes('fetch') ? 'Cannot reach the API server. Is the backend running on port 8000?' : msg)
    } finally {
      setIsProcessing(false)
      setJobProgress(null)
    }
  }, [selectedMedia, isProcessing, detectionMode, fetchAnalysis, fetchMediaItems])

  useEffect(() => { fetchMediaItems(); fetchModels() }, [fetchMediaItems, fetchModels])
  useEffect(() => { if (selectedMedia) fetchAnalysis(selectedMedia) }, [selectedMedia, fetchAnalysis])

  const mediaItems = liveMediaItems

  // Use live models from registry; fall back to empty list (no hard-coding)
  const models = liveModels

  const detectionTypes = [
    { id: 'objects', label: 'Objects', icon: Box, description: 'Detect common objects' },
    { id: 'faces', label: 'Faces', icon: Eye, description: 'Face detection & recognition' },
    { id: 'text', label: 'Text', icon: Tag, description: 'OCR text extraction' },
    { id: 'scenes', label: 'Scenes', icon: Layers, description: 'Scene classification' }
  ]

  // Use analysis data detections (no hard-coded fallback)
  const detectedObjects = analysisData?.detections || analysisData?.detected_objects || selectedMedia?.detections || []
  // Summarise what the pipeline produced even when no bbox detections are available
  const pipelineFlags = analysisData ? [
    analysisData.object_detected != null && { label: 'Object Detection', value: analysisData.object_detected ? 'detected' : 'not detected', positive: analysisData.object_detected },
    analysisData.edge_detected != null && { label: 'Edge Detection', value: analysisData.edge_detected ? 'applied' : 'not applied', positive: null },
    analysisData.is_grayscale != null && { label: 'Grayscale', value: analysisData.is_grayscale ? 'yes' : 'no', positive: null },
    analysisData.is_corrupted != null && { label: 'Corrupted', value: analysisData.is_corrupted ? 'yes' : 'no', positive: !analysisData.is_corrupted },
  ].filter(Boolean) : []

  const getStatusColor = (status) => {
    switch(status) {
      case 'processed': return 'text-green-600 bg-green-50'
      case 'processing': return 'text-blue-600 bg-blue-50'
      case 'pending': return 'text-gray-600 bg-gray-50'
      case 'failed': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Workflow Info Banner */}
      <div className="bg-purple-50 border-b border-purple-200 px-6 py-3">
        <div className="flex items-center gap-2 text-sm">
          <Layers className="w-4 h-4 text-purple-600" />
          <span className="font-medium text-purple-900">Workflow:</span>
          <span className="text-purple-700">
            1. Go to <strong>AI Processing</strong> tab to process images → 
            2. Click <strong>"Run Detection"</strong> to process with AI models
          </span>
        </div>
      </div>
      
      <div className="flex-1 flex overflow-hidden">
      {/* Left Sidebar - Media Gallery */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-900">Media Library {liveMediaItems.length > 0 && <span className="text-xs text-green-600 font-normal ml-1">● live</span>}</h2>
            <div className="flex items-center gap-1">
              <button onClick={fetchMediaItems} disabled={loadingMedia} className="p-1.5 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50">
                <RefreshCw className={`w-4 h-4 ${loadingMedia ? 'animate-spin' : ''}`} />
              </button>
              <button className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Upload className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Detection Mode Selector */}
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">Detection Type</label>
            <div className="grid grid-cols-2 gap-2">
              {detectionTypes.map(type => {
                const Icon = type.icon
                return (
                  <button
                    key={type.id}
                    onClick={() => setDetectionMode(type.id)}
                    className={`p-2 rounded-lg border text-left ${
                      detectionMode === type.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-4 h-4 mb-1" />
                    <div className="text-xs font-medium">{type.label}</div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-3">
          {loadingMedia && !hasFetched ? (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">Loading media…</div>
          ) : mediaItems.length === 0 && hasFetched ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-400">
              <Image className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-xs text-center">No media found. Go to AI Processing tab to process images or videos.</p>
            </div>
          ) : null}
          {mediaItems.map(item => (
            <div
              key={item.id}
              onClick={() => setSelectedMedia(item)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedMedia?.id === item.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-16 h-16 bg-gray-100 rounded overflow-hidden flex items-center justify-center text-3xl flex-shrink-0">
                  {item.thumbnailUrl ? (
                    <img
                      src={item.thumbnailUrl}
                      alt={item.name}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                    />
                  ) : null}
                  <div
                    className="w-full h-full items-center justify-center"
                    style={{ display: item.thumbnailUrl ? 'none' : 'flex' }}
                  >
                    <Image className="w-8 h-8 text-gray-400" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 truncate">{item.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                      {item.status}
                    </span>
                    {item.type === 'video' && item.duration && (
                      <span className="text-xs text-gray-600">{item.duration}</span>
                    )}
                  </div>
                  {item.detections && item.detections.length > 0 && (
                    <p className="text-xs text-gray-600 mt-1">
                      {item.detections.length} objects detected
                    </p>
                  )}
                  {item.progress && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div 
                          className="bg-blue-600 h-1.5 rounded-full"
                          style={{ width: `${item.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Toolbar */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Object Detection & Analysis</h1>
              <p className="text-sm text-gray-600 mt-1">
                {selectedMedia ? selectedMedia.name : 'Select media to analyze'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selectedMedia && (
                <>
                  <button
                    onClick={runDetection}
                    disabled={isProcessing}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    <Scan className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
                    {isProcessing ? 'Running…' : 'Run Detection'}
                  </button>
                  <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    <Download className="w-5 h-5 text-gray-600" />
                  </button>
                  <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    <Settings className="w-5 h-5 text-gray-600" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Main Canvas Area */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Canvas/Preview Area */}
          <div className="flex-1 p-6 overflow-auto">
            {selectedMedia ? (
              <div className="bg-white rounded-lg shadow-lg p-6">
                {/* Media Display with Bounding Boxes */}
                <div className="relative bg-gray-100 rounded-lg aspect-video flex items-center justify-center overflow-hidden">
                  {selectedMedia.thumbnailUrl ? (
                    <img
                      src={selectedMedia.thumbnailUrl}
                      alt={selectedMedia.name}
                      className="w-full h-full object-contain"
                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
                    />
                  ) : null}
                  <div
                    className="w-full h-full items-center justify-center"
                    style={{ display: selectedMedia.thumbnailUrl ? 'none' : 'flex' }}
                  >
                    <Image className="w-24 h-24 text-gray-300" />
                  </div>
                  
                  {/* Bounding Boxes Overlay */}
                  {selectedMedia.detections && selectedMedia.detections.length > 0 && (
                    <svg className="absolute inset-0 w-full h-full">
                      {selectedMedia.detections.map((detection, idx) => (
                        <g key={idx}>
                          <rect
                            x={`${(detection.bbox[0] / 800) * 100}%`}
                            y={`${(detection.bbox[1] / 600) * 100}%`}
                            width={`${((detection.bbox[2] - detection.bbox[0]) / 800) * 100}%`}
                            height={`${((detection.bbox[3] - detection.bbox[1]) / 600) * 100}%`}
                            fill="none"
                            stroke="#3b82f6"
                            strokeWidth="3"
                            rx="4"
                          />
                          <text
                            x={`${(detection.bbox[0] / 800) * 100}%`}
                            y={`${(detection.bbox[1] / 600) * 100 - 1}%`}
                            className="text-xs fill-white"
                          >
                            <tspan className="font-semibold">{detection.label}</tspan>
                            <tspan className="opacity-80"> {(detection.confidence * 100).toFixed(0)}%</tspan>
                          </text>
                        </g>
                      ))}
                    </svg>
                  )}
                </div>

                {/* Video Controls (if video) */}
                {selectedMedia.type === 'video' && (
                  <div className="mt-4 flex items-center gap-4">
                    <button className="p-2 bg-blue-600 text-white rounded-full hover:bg-blue-700">
                      <Play className="w-5 h-5" />
                    </button>
                    <div className="flex-1">
                      <input type="range" className="w-full" min="0" max="100" defaultValue="0" />
                    </div>
                    <span className="text-sm text-gray-600">0:00 / {selectedMedia.duration}</span>
                  </div>
                )}

                {/* Job Progress Bar */}
                {isProcessing && jobProgress && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="animate-spin">
                        <Scan className="w-5 h-5 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900">{jobProgress.message} ({jobProgress.progress}%)</p>
                        <div className="w-full bg-blue-200 rounded-full h-2 mt-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${jobProgress.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Detection Error */}
                {detectionError && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-900">Detection failed</p>
                      <p className="text-xs text-red-700 mt-1">{detectionError}</p>
                    </div>
                    <button onClick={() => setDetectionError(null)} className="text-red-400 hover:text-red-600 text-lg leading-none">&times;</button>
                  </div>
                )}

                {/* Analysis Metadata */}
                {analysisData && !isProcessing && (
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    {[
                      { label: 'Dimensions', value: analysisData.width && analysisData.height ? `${analysisData.width}×${analysisData.height}` : null },
                      { label: 'Format', value: analysisData.format },
                      { label: 'Status', value: analysisData.processing_status },
                      { label: 'Blur Score', value: analysisData.blur_score != null ? analysisData.blur_score.toFixed(2) : null },
                      { label: 'Brightness', value: analysisData.brightness_avg != null ? analysisData.brightness_avg.toFixed(1) : null },
                      { label: 'Detections', value: analysisData.detection_count != null ? analysisData.detection_count : 0 },
                    ].filter(m => m.value != null).map(m => (
                      <div key={m.label} className="bg-gray-50 rounded-lg p-3 text-center">
                        <p className="text-xs text-gray-500">{m.label}</p>
                        <p className="font-semibold text-gray-900 text-sm mt-1">{m.value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Processing Status */}
                {selectedMedia.status === 'processing' && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="animate-spin">
                        <Scan className="w-5 h-5 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900">Processing... {selectedMedia.progress}%</p>
                        <div className="w-full bg-blue-200 rounded-full h-2 mt-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${selectedMedia.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Image className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No media selected</p>
                  <p className="text-sm mt-1">Choose an image or video to start detection</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar - Detections & Models */}
          <div className="w-80 bg-white border-l border-gray-200 overflow-auto">
            
            {/* Detected Objects */}
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-bold text-gray-900 mb-3">Detected Objects</h3>
              {loadingAnalysis && (
                <div className="text-center py-6 text-gray-400 text-xs">Loading analysis…</div>
              )}
              {!loadingAnalysis && detectedObjects.length > 0 ? (
                <div className="space-y-2">
                  {detectedObjects.map((obj, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-gray-900">{obj.label}</span>
                        <span className="text-sm text-gray-600">{(obj.confidence * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div className="bg-green-600 h-1.5 rounded-full" style={{ width: `${obj.confidence * 100}%` }} />
                      </div>
                      {obj.bbox && (
                        <p className="text-xs text-gray-500 mt-1">BBox: [{obj.bbox.join(', ')}]</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : !loadingAnalysis && pipelineFlags.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500 mb-2 italic">No bounding-box detections — showing pipeline results:</p>
                  {pipelineFlags.map((f, i) => (
                    <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm">
                      <span className="text-gray-700">{f.label}</span>
                      <span className={`font-medium text-xs px-2 py-0.5 rounded-full ${
                        f.positive === true ? 'bg-green-100 text-green-700'
                        : f.positive === false ? 'bg-red-100 text-red-700'
                        : 'bg-gray-200 text-gray-600'
                      }`}>{f.value}</span>
                    </div>
                  ))}
                </div>
              ) : !loadingAnalysis ? (
                <div className="text-center py-8 text-gray-500">
                  <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No detections yet</p>
                  <p className="text-xs text-gray-400 mt-1">Run Detection to analyse this image</p>
                </div>
              ) : null}
            </div>

            {/* ML Models */}
            <div className="p-4">
              <h3 className="font-bold text-gray-900 mb-3">Detection Models</h3>
              <div className="space-y-2">
                {models.map(model => (
                  <div key={model.id} className="p-3 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer transition-colors">
                    <p className="font-semibold text-gray-900">{model.name}</p>
                    <p className="text-xs text-gray-600 mt-1">{model.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs">
                      <span className="text-gray-600">Accuracy: <strong>{model.accuracy}</strong></span>
                      <span className="text-gray-600">Speed: <strong>{model.speed}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

        </div>
      </div>
    </div>
    </div>
  )
}
