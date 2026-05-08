import { useState, useEffect, useCallback, useRef } from 'react'
import { 
  Music, Play, Pause, SkipForward, Volume2, 
  Mic, MessageSquare, Download, Upload, Activity,
  Clock, Languages, User, Tag, FileAudio, RefreshCw
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function AudioAnalysis() {
  const [selectedAudio, setSelectedAudio] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [sliderValue, setSliderValue] = useState(0)  // visual slider pos while dragging
  const isDragging = useRef(false)
  const audioRef = useRef(null)
  const [analysisType, setAnalysisType] = useState('transcription') // 'transcription', 'sentiment', 'speaker'
  const [liveAudioFiles, setLiveAudioFiles] = useState([])
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)

  // Live analysis data for selected file
  const [analysisData, setAnalysisData] = useState(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)
  const [jobProgress, setJobProgress] = useState(null)

  // ML model list for ASR model selector
  const [audioModels, setAudioModels] = useState([])

  // Analysis toggle options
  const [analysisOptions, setAnalysisOptions] = useState({
    speakerDiarization: true,
    sentimentAnalysis: true,
    keywordExtraction: true,
    punctuation: true,
  })

  const fetchAudioFiles = useCallback(async () => {
    setLoadingFiles(true)
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/preview/audio?domain=media&entity=assets&limit=20`)
      if (res.ok) {
        const data = await res.json()
        const mapped = (data.records || []).map((r, i) => {
          const objectPath = r.bronze_path ||
            (r.s3_path || '').replace('s3a://syniqai-bronze/', '') ||
            (r.path || '').replace('s3a://syniqai-bronze/', '')
          return {
          id: r.file_name || i,
          name: r.file_name || `audio_${i}.wav`,
          objectPath,
          duration: r.duration_seconds ? `${Math.floor(r.duration_seconds / 60)}:${String(Math.round(r.duration_seconds % 60)).padStart(2, '0')}` : '—',
          thumbnail: '🎵',
          status: r.processing_status || 'pending',
          transcription: !!r.extracted_text,
          speakers: r.channels || 1,
          sentiment: r.sentiment_label || 'neutral',
          words: r.word_count || 0,
          confidence: r.confidence || null,
          sample_rate: r.sample_rate_hz,
          is_silent: r.is_silent,
          avg_volume: r.average_volume_db,
        }})
        setLiveAudioFiles(mapped)
      }
    } catch (err) {
      console.warn('Could not fetch audio preview:', err)
    } finally {
      setHasFetched(true)
      setLoadingFiles(false)
    }
  }, [])

  // Fetch per-file analysis from AnalysisService (LLM + ML)
  const fetchAnalysis = useCallback(async (audio) => {
    if (!audio) return
    setLoadingAnalysis(true)
    setAnalysisData(null)
    try {
      const params = new URLSearchParams({ file_id: audio.id, domain: 'media', entity: 'assets' })
      const res = await fetch(`${API_BASE}/api/silver/unstructured/analysis/audio?${params}`)
      if (res.ok) setAnalysisData(await res.json())
    } catch (err) {
      console.warn('Could not fetch audio analysis:', err)
    } finally {
      setLoadingAnalysis(false)
    }
  }, [])

  // Fetch ML models for ASR model selector
  const fetchAudioModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/models`)
      if (res.ok) {
        const data = await res.json()
        setAudioModels((data.models || []).filter(m =>
          (m.media_types || []).includes('audio') || m.category === 'transcription'
        ))
      }
    } catch (err) { console.warn('Could not fetch audio models:', err) }
  }, [])

  useEffect(() => { fetchAudioFiles(); fetchAudioModels() }, [fetchAudioFiles, fetchAudioModels])
  useEffect(() => {
    if (selectedAudio) {
      fetchAnalysis(selectedAudio)
      setIsPlaying(false)
      setCurrentTime(0)
      setDuration(0)
      setSliderValue(0)
    }
  }, [selectedAudio, fetchAnalysis])

  const audioFiles = liveAudioFiles

  // Build audio stream URL from MinIO via thumbnail proxy
  const audioUrl = selectedAudio?.objectPath
    ? `${API_BASE}/api/silver/unstructured/thumbnail/syniqai-bronze/${selectedAudio.objectPath}`
    : null

  // Audio player helpers
  const formatTime = (s) => {
    if (s == null || isNaN(s) || !isFinite(s) || s < 0) return '0:00'
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${String(sec).padStart(2, '0')}`
  }

  const updateDuration = () => {
    const el = audioRef.current
    if (!el) return
    const d = el.duration
    if (d && isFinite(d) && d > 0) setDuration(d)
  }

  const handlePlayPause = () => {
    const el = audioRef.current
    if (!el) return
    if (isPlaying) { el.pause() } else { el.play() }
  }

  // Seek: update visual slider while dragging, only seek audio on release
  const handleSliderChange = (e) => {
    setSliderValue(Number(e.target.value))
  }

  const handleSliderPointerDown = () => {
    isDragging.current = true
  }

  const handleSliderPointerUp = (e) => {
    isDragging.current = false
    const el = audioRef.current
    if (!el) return
    const pct = Number(e.target.value)
    const d = el.duration
    if (d && isFinite(d)) {
      el.currentTime = (pct / 100) * d
    }
  }
  const transcript = analysisData?.transcript || []
  const speakerAnalysis = analysisData?.speaker_analysis || []
  const keywords = analysisData?.keywords || []

  // Derived live data (no hard-coded fallback)
  const handleRunAnalysis = async () => {
    if (!selectedAudio) return
    setLoadingAnalysis(true)
    setAnalysisError(null)
    setJobProgress({ progress: 0, message: 'Queuing job…' })
    // Derive domain and entity from actual bronze path
    let domain = 'media'
    let entity = 'assets'
    if (selectedAudio.objectPath) {
      const parts = selectedAudio.objectPath.split('/')
      if (parts.length >= 3) {
        domain = parts[0]
        entity = parts[2]
      }
    }
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_type: 'audio',
          domain,
          entity,
          stage_to_bronze: false,
        }),
      })
      if (!res.ok) {
        let detail = `Server returned ${res.status}`
        try { const e = await res.json(); detail = e.detail || e.message || detail } catch (_) {}
        throw new Error(detail)
      }
      const { job_id } = await res.json()
      let done = false
      while (!done) {
        await new Promise(r => setTimeout(r, 1500))
        const poll = await fetch(`${API_BASE}/api/silver/unstructured/jobs/${job_id}`)
        if (poll.ok) {
          const job = await poll.json()
          setJobProgress({ progress: job.progress ?? 0, message: job.message || job.status })
          if (['completed', 'failed', 'error'].includes(job.status)) {
            if (job.status === 'failed' || job.status === 'error')
              throw new Error(job.error_message || `Job ${job.status}`)
            done = true
          }
        } else { done = true }
      }
      await fetchAnalysis(selectedAudio)
    } catch (err) {
      const msg = err?.message || String(err)
      setAnalysisError(msg.includes('fetch') ? 'Cannot reach the API server. Is the backend running on port 8000?' : msg)
    } finally {
      setLoadingAnalysis(false)
      setJobProgress(null)
    }
  }

  // Handle run analysis button

  const analysisTypes = [
    { id: 'transcription', label: 'Transcription', icon: MessageSquare },
    { id: 'sentiment', label: 'Sentiment', icon: Tag },
    { id: 'speaker', label: 'Speaker ID', icon: User }
  ]

  const getStatusColor = (status) => {
    switch(status) {
      case 'transcribed': return 'text-green-600 bg-green-50'
      case 'processing': return 'text-blue-600 bg-blue-50'
      case 'pending': return 'text-gray-600 bg-gray-50'
      case 'failed': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getSentimentColor = (sentiment) => {
    switch(sentiment) {
      case 'positive':
      case 'happy':
      case 'satisfied':
        return 'text-green-600 bg-green-50'
      case 'negative':
      case 'angry':
        return 'text-red-600 bg-red-50'
      case 'neutral':
        return 'text-gray-600 bg-gray-50'
      case 'concerned':
        return 'text-orange-600 bg-orange-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Workflow Info Banner */}
      <div className="bg-blue-50 border-b border-blue-200 px-6 py-3">
        <div className="flex items-center gap-2 text-sm">
          <Activity className="w-4 h-4 text-blue-600" />
          <span className="font-medium text-blue-900">Workflow:</span>
          <span className="text-blue-700">
            1. Go to <strong>AI Processing</strong> tab to process audio files → 
            2. Click <strong>"Run Analysis"</strong> to process audio with AI
          </span>
        </div>
      </div>
      
      <div className="flex-1 flex overflow-hidden">
      {/* Left Sidebar - Audio Files */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-900">Audio Files {liveAudioFiles.length > 0 && <span className="text-xs text-green-600 font-normal ml-1">● live</span>}</h2>
            <div className="flex items-center gap-1">
              <button onClick={fetchAudioFiles} disabled={loadingFiles} className="p-1.5 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50">
                <RefreshCw className={`w-4 h-4 ${loadingFiles ? 'animate-spin' : ''}`} />
              </button>
              <button className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Upload className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Analysis Type Selector */}
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">Analysis Type</label>
            <select 
              value={analysisType}
              onChange={(e) => setAnalysisType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              {analysisTypes.map(type => (
                <option key={type.id} value={type.id}>{type.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-3">
          {loadingFiles && !hasFetched ? (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">Loading audio files…</div>
          ) : audioFiles.length === 0 && hasFetched ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-400">
              <Music className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-xs text-center">No audio files found. Go to AI Processing tab to process audio files.</p>
            </div>
          ) : null}
          {audioFiles.map(audio => (
            <div
              key={audio.id}
              onClick={() => setSelectedAudio(audio)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedAudio?.id === audio.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-purple-500 to-pink-500 text-white text-xl">
                  🎵
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 truncate">{audio.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(audio.status)}`}>
                      {audio.status}
                    </span>
                    <span className="text-xs text-gray-600">{audio.duration}</span>
                  </div>
                  {audio.transcription && (
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-600">
                      <span>{audio.speakers} speakers</span>
                      <span>•</span>
                      <span>{audio.words} words</span>
                    </div>
                  )}
                  {audio.progress && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div 
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${audio.progress}%` }}
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
              <h1 className="text-xl font-bold text-gray-900">Audio Analysis & Transcription</h1>
              <p className="text-sm text-gray-600 mt-1">
                {selectedAudio ? selectedAudio.name : 'Select an audio file to analyze'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selectedAudio && (
                <>
                  <button
                    onClick={handleRunAnalysis}
                    disabled={loadingAnalysis}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loadingAnalysis ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                    {loadingAnalysis ? 'Running…' : 'Run Analysis'}
                  </button>
                  <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    <Download className="w-5 h-5 text-gray-600" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Main Area */}
        <div className="flex-1 flex overflow-hidden">

          {/* Transcript / Analysis Area */}
          <div className="flex-1 p-6 overflow-auto">
            {selectedAudio ? (
              <div className="space-y-4">
                {/* Audio Player Card */}
                <div className="bg-white rounded-lg shadow-lg p-6 w-full">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center text-white text-3xl flex-shrink-0">
                      {selectedAudio.thumbnail}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 truncate">{selectedAudio.name}</h3>
                      <p className="text-sm text-gray-600">Duration: {selectedAudio.duration}</p>
                      {analysisData && (
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                          {analysisData.language && <span>Language: <strong>{analysisData.language}</strong></span>}
                          {analysisData.overall_sentiment && (
                            <span className={`px-2 py-0.5 rounded-full ${getSentimentColor(analysisData.overall_sentiment)}`}>
                              {analysisData.overall_sentiment}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Hidden real audio element */}
                  {audioUrl && (
                    <audio
                      ref={audioRef}
                      src={audioUrl}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => { setIsPlaying(false); setSliderValue(0) }}
                      onTimeUpdate={() => {
                        const el = audioRef.current
                        if (!el) return
                        const t = el.currentTime
                        setCurrentTime(t)
                        if (!isDragging.current) {
                          const d = el.duration
                          if (d && isFinite(d) && d > 0) {
                            setDuration(d)
                            setSliderValue((t / d) * 100)
                          }
                        }
                        updateDuration()
                      }}
                      onLoadedMetadata={updateDuration}
                      onDurationChange={updateDuration}
                      preload="metadata"
                    />
                  )}
                  {/* Waveform placeholder */}
                  <div className="bg-gray-100 rounded-xl h-32 mb-5 flex items-center justify-center px-4 overflow-hidden">
                    <div className="flex items-end gap-0.5 w-full h-20">
                      {[...Array(80)].map((_, idx) => (
                        <div
                          key={idx}
                          className="flex-1 bg-blue-400 rounded-sm opacity-70 min-w-0"
                          style={{ height: `${20 + ((idx * 37 + 13) % 80)}%` }}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button onClick={handlePlayPause}
                      className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 flex-shrink-0"
                      disabled={!audioUrl}
                      title={audioUrl ? '' : 'Audio not available'}
                    >
                      {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                    </button>
                    <button className="p-2 text-gray-600 hover:text-gray-900 flex-shrink-0"><SkipForward className="w-5 h-5" /></button>
                    <div className="flex-1">
                      <input
                        type="range"
                        className="w-full accent-blue-600"
                        min="0"
                        max="100"
                        step="0.1"
                        value={sliderValue}
                        onPointerDown={handleSliderPointerDown}
                        onChange={handleSliderChange}
                        onPointerUp={handleSliderPointerUp}
                      />
                    </div>
                    <span className="text-sm text-gray-600 flex-shrink-0 tabular-nums">
                      {formatTime(currentTime)} / {duration > 0 ? formatTime(duration) : (selectedAudio.duration !== '—' ? selectedAudio.duration : '—')}
                    </span>
                    <button className="p-2 text-gray-600 hover:text-gray-900 flex-shrink-0"><Volume2 className="w-5 h-5" /></button>
                  </div>
                </div>

                {/* Job Progress */}
                {loadingAnalysis && jobProgress && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
                    <RefreshCw className="w-4 h-4 text-blue-600 animate-spin flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm text-blue-900 font-medium">{jobProgress.message} ({jobProgress.progress}%)</p>
                      <div className="w-full bg-blue-200 rounded-full h-1.5 mt-1">
                        <div className="bg-blue-600 h-1.5 rounded-full transition-all" style={{ width: `${jobProgress.progress}%` }} />
                      </div>
                    </div>
                  </div>
                )}

                {/* Analysis Error */}
                {analysisError && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                    <Activity className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-900">Analysis failed</p>
                      <p className="text-xs text-red-700 mt-0.5">{analysisError}</p>
                    </div>
                    <button onClick={() => setAnalysisError(null)} className="text-red-400 hover:text-red-600 text-lg leading-none">&times;</button>
                  </div>
                )}

                {/* Loading state */}
                {loadingAnalysis && !jobProgress && (
                  <div className="bg-white rounded-lg shadow p-4 flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
                    <span className="text-gray-600">Loading analysis from pipeline…</span>
                  </div>
                )}

                {/* Transcription Results */}
                {!loadingAnalysis && analysisData && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-900">Transcription</h3>
                      {analysisData.language && (
                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                          {analysisData.language.toUpperCase()}
                        </span>
                      )}
                    </div>
                    {analysisData.extracted_text ? (
                      <div className="space-y-3">
                        {/* Sentiment badge */}
                        {analysisData.overall_sentiment && analysisData.overall_sentiment !== 'neutral' && (
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(analysisData.overall_sentiment)}`}>
                            {analysisData.overall_sentiment}
                          </span>
                        )}
                        <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">{analysisData.extracted_text}</p>
                        {analysisData.summary && (
                          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                            <p className="text-xs font-semibold text-blue-900 mb-1">Summary</p>
                            <p className="text-sm text-blue-800">{analysisData.summary}</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <Mic className="w-10 h-10 mx-auto mb-2 opacity-40" />
                        <p className="font-medium text-sm">No transcription available yet</p>
                        <p className="text-xs mt-1 text-gray-400">Click <strong>Run Analysis</strong> to process this file and extract transcription through the Silver pipeline.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Segmented transcript (speaker diarization) if available */}
                {!loadingAnalysis && transcript.length > 0 && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-900">Speaker Segments</h3>
                      {selectedAudio.confidence != null && (
                        <span className="text-green-600 text-sm font-medium">
                          {(selectedAudio.confidence * 100).toFixed(1)}% confidence
                        </span>
                      )}
                    </div>
                    <div className="space-y-3 max-h-96 overflow-auto">
                      {transcript.map((line, i) => (
                        <div key={line.id || i} className="flex gap-3">
                          <div className="flex-shrink-0 w-24 text-right">
                            <span className="text-xs text-gray-500">{line.timestamp || ''}</span>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-sm text-gray-900">{line.speaker || 'Speaker'}</span>
                              {line.sentiment && (
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(line.sentiment)}`}>
                                  {line.sentiment}
                                </span>
                              )}
                            </div>
                            <p className="text-gray-700">{line.text}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Audio Metadata */}
                {analysisData && !loadingAnalysis && (
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { label: 'Duration', value: analysisData.duration != null ? formatTime(analysisData.duration) : null },
                      { label: 'Sample Rate', value: analysisData.sample_rate ? `${analysisData.sample_rate} Hz` : null },
                      { label: 'Channels', value: analysisData.channels },
                      { label: 'Avg Volume', value: analysisData.avg_volume_db != null ? `${analysisData.avg_volume_db.toFixed(1)} dB` : null },
                      { label: 'Language', value: analysisData.language },
                      { label: 'Sentiment', value: analysisData.overall_sentiment },
                    ].filter(m => m.value != null).map(m => (
                      <div key={m.label} className="bg-white rounded-lg shadow p-3 text-center">
                        <p className="text-xs text-gray-500">{m.label}</p>
                        <p className="font-semibold text-gray-900 text-sm mt-1">{m.value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Summary */}
                {analysisData?.summary && (
                  <div className="bg-white rounded-lg shadow p-4">
                    <h4 className="font-semibold text-gray-700 mb-1 text-sm">Summary</h4>
                    <p className="text-gray-600 text-sm">{analysisData.summary}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Music className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No audio selected</p>
                  <p className="text-sm mt-1">Choose an audio file from the sidebar to analyze</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar – Live Analysis Results */}
          <div className="w-80 bg-white border-l border-gray-200 overflow-auto">

            {/* Speaker Analysis (live from AnalysisService) */}
            {speakerAnalysis.length > 0 && (
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-bold text-gray-900 mb-3">Speaker Analysis</h3>
                <div className="space-y-3">
                  {speakerAnalysis.map((sp, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-gray-900">{sp.speaker}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(sp.sentiment)}`}>
                          {sp.sentiment}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div><p className="text-gray-500">Talk Time</p><p className="font-semibold text-gray-900">{sp.talkTime || '—'}</p></div>
                        <div><p className="text-gray-500">Words</p><p className="font-semibold text-gray-900">{sp.words}</p></div>
                      </div>
                      {sp.talkTime && (
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div className="bg-blue-600 h-2 rounded-full" style={{ width: sp.talkTime }} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Keywords (live from LLM service) */}
            {keywords.length > 0 && (
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-bold text-gray-900 mb-3">Keywords</h3>
                <div className="space-y-2">
                  {keywords.map((kw, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span className="font-medium text-gray-900">{kw.word}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">{kw.count}x</span>
                        <span className="text-xs text-gray-500">{Math.round((kw.relevance || 0) * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Analysis Options */}
            <div className="p-4">
              <h3 className="font-bold text-gray-900 mb-3">Analysis Options</h3>
              <div className="space-y-3">
                {[
                  ['speakerDiarization', 'Speaker diarization'],
                  ['sentimentAnalysis', 'Sentiment analysis'],
                  ['keywordExtraction', 'Keyword extraction'],
                  ['punctuation', 'Punctuation restoration'],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-center gap-2">
                    <input type="checkbox" checked={analysisOptions[key]}
                      onChange={(e) => setAnalysisOptions(prev => ({ ...prev, [key]: e.target.checked }))}
                      className="rounded" />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ))}
              </div>

              {/* ASR model selector (from ML registry) */}
              <div className="mt-6">
                <label className="text-sm font-medium text-gray-700 mb-2 block">ASR Model</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  {audioModels.length > 0
                    ? audioModels.map(m => <option key={m.id} value={m.id}>{m.name}</option>)
                    : <option>Whisper (default)</option>}
                </select>
              </div>
            </div>
          </div>

          </div>
        </div>
      </div>
    </div>
  )
}
