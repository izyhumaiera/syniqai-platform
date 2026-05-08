import { useState, useEffect, useCallback } from 'react'
import { 
  Shield, AlertTriangle, CheckCircle, XCircle, 
  Image, Video, Music, FileText, TrendingUp,
  Settings, Play, Pause, Filter, Download, RefreshCw, Save
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function MediaQuality() {
  const [selectedDataset, setSelectedDataset] = useState('product_images')
  const [activeCategory, setActiveCategory] = useState('all')
  const [serverRules, setServerRules] = useState({})
  const [savingRules, setSavingRules] = useState(false)
  const [saveMsg, setSaveMsg] = useState(null)
  const [liveDatasets, setLiveDatasets] = useState([])
  const [liveRecentChecks, setLiveRecentChecks] = useState([])  
  const [hasFetchedDatasets, setHasFetchedDatasets] = useState(false)
  const [hasFetchedChecks, setHasFetchedChecks] = useState(false)
  const [runningChecks, setRunningChecks] = useState(false)
  const [checksMsg, setChecksMsg] = useState(null)

  // Live quality rules from PostgreSQL via QualityRulesEngine
  const [liveQualityRules, setLiveQualityRules] = useState([])
  // Live per-file quality issues from jobs tracker
  const [liveIssues, setLiveIssues] = useState([])

  const fetchServerRules = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/rules`)
      if (res.ok) {
        const data = await res.json()
        setServerRules(data.rules || {})
      }
    } catch (err) {
      console.warn('Could not fetch rules:', err)
    }
  }, [])

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/quality/datasets`)
      if (res.ok) {
        const data = await res.json()
        setLiveDatasets((data.datasets || []).map(d => ({ ...d, issues: d.issues ?? 0 })))
      } else {
        // Fallback to tables endpoint
        const r2 = await fetch(`${API_BASE}/api/silver/unstructured/tables`)
        if (r2.ok) {
          const data = await r2.json()
          const tables = data.tables || []
          const _EXT_TYPE = { images: 'Image', image: 'Image', videos: 'Video', video: 'Video', audio: 'Audio', documents: 'Document', document: 'Document' }
          setLiveDatasets(tables.map(t => {
            const name = t.table_name || t.prefix || 'unknown'
            const slug = name.split('.').pop() || name.split('/').pop() || ''
            const type = _EXT_TYPE[slug.toLowerCase()] || 'Media'
            const files = t.row_count || 0
            return { id: name, name: name.split('.').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '), type, files, issues: 0, score: files > 0 ? 100 : 0 }
          }))
        }
      }
    } catch (err) { console.warn('Could not fetch datasets:', err) }
    finally { setHasFetchedDatasets(true) }
  }, [])

  const fetchRecentChecks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/jobs?limit=4`)
      if (res.ok) {
        const data = await res.json()
        const jobs = data.jobs || []
        setLiveRecentChecks(jobs.map(job => ({
          id: job.job_id || job.id,
          dataset: job.table_name || job.entity || 'media',
          rule: `${job.cleaning_summary?.media_type || job.entity || 'media'} processing`,
          status: job.status === 'completed' ? 'passed' : job.status === 'failed' ? 'failed' : 'warning',
          time: job.started_at ? new Date(job.started_at).toLocaleString() : '—',
          files: job.row_count || 0,
        })))
      }
    } catch (err) { console.warn('Could not fetch checks:', err) }
    finally { setHasFetchedChecks(true) }
  }, [])

  const fetchQualityRules = useCallback(async (mediaType) => {
    try {
      const url = new URL(`${API_BASE}/api/silver/unstructured/quality/rules`)
      if (mediaType) url.searchParams.set('media_type', mediaType)
      const res = await fetch(url.toString())
      if (res.ok) {
        const data = await res.json()
        setLiveQualityRules(data.rules || [])
      }
    } catch (err) { console.warn('Could not fetch quality rules:', err) }
  }, [])

  const fetchQualityIssues = useCallback(async (mediaType) => {
    try {
      const url = new URL(`${API_BASE}/api/silver/unstructured/quality/issues`)
      url.searchParams.set('limit', '20')
      if (mediaType) url.searchParams.set('media_type', mediaType)
      const res = await fetch(url.toString())
      if (res.ok) {
        const data = await res.json()
        setLiveIssues(data.issues || [])
      }
    } catch (err) { console.warn('Could not fetch quality issues:', err) }
  }, [])

  useEffect(() => {
    fetchServerRules()
    fetchDatasets()
    fetchRecentChecks()
    fetchQualityRules()
    fetchQualityIssues()
  }, [fetchServerRules, fetchDatasets, fetchRecentChecks, fetchQualityRules, fetchQualityIssues])

  // Re-fetch rules and issues filtered by the selected dataset's media type
  useEffect(() => {
    if (liveDatasets.length === 0) return
    const ds = liveDatasets.find(d => d.id === selectedDataset) || liveDatasets[0]
    if (ds?.media_type) {
      fetchQualityRules(ds.media_type)
      fetchQualityIssues(ds.media_type)
    }
  }, [selectedDataset, liveDatasets, fetchQualityRules, fetchQualityIssues])

  const handleRunChecks = async () => {
    // Compute active dataset inline from state (avoids forward-reference to _activeDataset)
    const activeDs = liveDatasets.find(d => d.id === selectedDataset) || liveDatasets[0] || null
    if (!activeDs) return
    setRunningChecks(true)
    setChecksMsg(null)
    try {
      const mediaType = activeDs.media_type || 'image'
      // Derive domain/entity from dataset id (e.g. "syniq_iceberg.media.unstructured_image_files")
      const stripped = (activeDs.id || '').replace(/^syniq_iceberg\./, '')
      const parts = stripped.split('.')
      const domain = parts[0] || 'media'
      const rawEntity = parts[parts.length - 1] || 'assets'
      // Strip leading "unstructured_<type>_" prefix if present
      const entity = rawEntity.replace(new RegExp(`^unstructured_${mediaType}_`), '') || rawEntity

      const body = {
        media_type: mediaType,
        domain,
        entity,
        stage_to_bronze: false,
        rules: liveQualityRules
          .filter(r => !r.media_type || r.media_type === mediaType)
          .map(r => ({
            rule_key: r.rule_key,
            category: r.category || 'technical',
            severity: r.severity || 'medium',
            enabled: true,
          })),
      }

      const res = await fetch(`${API_BASE}/api/silver/unstructured/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (data.job_id) {
        setChecksMsg(`Running checks… (job: ${data.job_id})`)
        const poll = setInterval(async () => {
          try {
            const jr = await fetch(`${API_BASE}/api/silver/unstructured/jobs/${data.job_id}`)
            if (jr.ok) {
              const jd = await jr.json()
              if (jd.status === 'completed' || jd.status === 'failed' || jd.status === 'error') {
                clearInterval(poll)
                setRunningChecks(false)
                setChecksMsg(jd.status === 'completed' ? 'Checks completed successfully' : `Checks failed: ${jd.error_message || jd.message || ''}`)
                const mt = activeDs.media_type
                fetchQualityRules(mt)
                fetchQualityIssues(mt)
                fetchDatasets()
                fetchRecentChecks()
                setTimeout(() => setChecksMsg(null), 5000)
              }
            }
          } catch {}
        }, 2000)
      } else {
        setChecksMsg(data.detail || 'Failed to start checks')
        setRunningChecks(false)
      }
    } catch (err) {
      setChecksMsg(`Error: ${err}`)
      setRunningChecks(false)
    }
  }

  const saveRules = async (mediaType, updates) => {
    setSavingRules(true)
    setSaveMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/rules/${mediaType}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules: updates }),
      })
      if (res.ok) {
        setSaveMsg(`Rules saved for ${mediaType}`)
        fetchServerRules()
      } else {
        setSaveMsg('Failed to save rules')
      }
    } catch (err) {
      setSaveMsg(`Error: ${err}`)
    } finally {
      setSavingRules(false)
      setTimeout(() => setSaveMsg(null), 3000)
    }
  }

  // Enrich datasets: compute issues count from liveIssues, compute score from rules or ratio
  const datasets = liveDatasets.map(d => {
    const issueCount = liveIssues.filter(i => {
      const parts = d.id.split('.')
      return i.file === d.id || parts.some(part => part && i.file.includes(part))
    }).length

    let score = d.score
    if (score === null || score === undefined) {
      const rulesWithData = liveQualityRules.filter(r => (r.passed ?? 0) + (r.failed ?? 0) > 0)
      if (rulesWithData.length > 0) {
        const avg = rulesWithData.reduce((s, r) => {
          const p = r.passed ?? 0; const f = r.failed ?? 0
          return s + (p + f > 0 ? (p / (p + f)) * 100 : 100)
        }, 0) / rulesWithData.length
        score = Math.round(avg)
      } else {
        score = d.files > 0 ? Math.max(0, Math.round((d.files - issueCount) / d.files * 100)) : 100
      }
    }

    return { ...d, issues: d.issues ?? issueCount, score }
  })

  // Quality rules: use live data from PostgreSQL rules engine, no hard-coded rules
  const qualityRules = liveQualityRules.map((r, i) => ({
    id: r.id || i + 1,
    category: r.category || 'technical',
    rule: r.rule_label || r.rule_key,
    description: r.description || '',
    severity: r.severity || 'medium',
    passed: r.passed ?? 0,
    failed: r.failed ?? 0,
    passRate: r.pass_rate != null ? r.pass_rate : (r.passed + r.failed > 0 ? (r.passed / (r.passed + r.failed) * 100) : 0),
  }))

  const recentChecks = liveRecentChecks

  // Issue details: live from jobs tracker / quality issues endpoint
  const issueDetails = liveIssues

  const categories = [
    { id: 'all', label: 'All Rules', count: qualityRules.length },
    { id: 'technical', label: 'Technical', count: qualityRules.filter(r => r.category === 'technical').length },
    { id: 'content', label: 'Content', count: qualityRules.filter(r => r.category === 'content').length },
    { id: 'metadata', label: 'Metadata', count: qualityRules.filter(r => r.category === 'metadata').length },
    { id: 'compliance', label: 'Compliance', count: qualityRules.filter(r => r.category === 'compliance').length }
  ]

  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200'
      case 'medium': return 'text-orange-600 bg-orange-50 border-orange-200'
      case 'low': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getStatusColor = (status) => {
    switch(status) {
      case 'passed': return 'text-green-600 bg-green-50'
      case 'warning': return 'text-orange-600 bg-orange-50'
      case 'failed': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getScoreColor = (score) => {
    if (score >= 95) return 'text-green-600 bg-green-50'
    if (score >= 85) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const filteredRules = activeCategory === 'all' 
    ? qualityRules 
    : qualityRules.filter(r => r.category === activeCategory)

  const _activeDataset = datasets.find(d => d.id === selectedDataset) || datasets[0] || null

  return (
    <div className="h-full flex bg-gray-50">
      
      {/* Left Sidebar - Datasets */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-bold text-gray-900 mb-4">Datasets</h2>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-2">
          {!hasFetchedDatasets ? (
            <div className="text-center text-gray-400 text-sm py-8">Loading datasets…</div>
          ) : datasets.length === 0 ? (
            <div className="text-center text-gray-400 text-sm py-8">No datasets found.<br/>Run a pipeline to generate data.</div>
          ) : null}
          {datasets.map(dataset => (
            <div
              key={dataset.id}
              onClick={() => setSelectedDataset(dataset.id)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedDataset === dataset.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm text-gray-900">{dataset.name}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-bold ${getScoreColor(dataset.score)}`}>
                  {dataset.score}%
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-600">
                <span>{dataset.files.toLocaleString()} files</span>
                <span className="text-red-600 font-medium">{dataset.issues} issues</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                <div 
                  className={`h-1.5 rounded-full ${dataset.score >= 95 ? 'bg-green-500' : dataset.score >= 85 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${dataset.score}%` }}
                ></div>
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
              <h1 className="text-xl font-bold text-gray-900">Media Quality Monitoring</h1>
              <p className="text-sm text-gray-600 mt-1">Automated quality checks for unstructured data</p>
            </div>
            <div className="flex items-center gap-2">
              {checksMsg && (
                <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${checksMsg.includes('completed') ? 'bg-green-100 text-green-700' : checksMsg.startsWith('Running') ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}`}>
                  {checksMsg}
                </span>
              )}
              {saveMsg && (
                <span className={`px-3 py-1.5 rounded-lg text-sm font-medium ${saveMsg.startsWith('Rules saved') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {saveMsg}
                </span>
              )}
              <button
                onClick={() => {
                  const mt = liveDatasets.find(d => d.id === selectedDataset)?.media_type
                    || liveDatasets[0]?.media_type || 'image'
                  saveRules(mt, serverRules[mt] || {})
                }}
                disabled={savingRules}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {savingRules ? 'Saving…' : 'Save Rules'}
              </button>
              <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2">
                <Filter className="w-4 h-4" />
                Filter
              </button>
              <button
                onClick={handleRunChecks}
                disabled={runningChecks || !_activeDataset}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
              >
                {runningChecks ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {runningChecks ? 'Running…' : 'Run Checks'}
              </button>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex gap-2 mt-4">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activeCategory === cat.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                }`}
              >
                {cat.label} ({cat.count})
              </button>
            ))}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-6">
            
            {/* Quality Score Overview */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">Quality Score Overview</h2>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-50 mb-3">
                      <span className="text-3xl font-bold text-green-600">
                        {_activeDataset ? `${_activeDataset.score}%` : '—'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">Overall Score</p>
                    <p className="text-xs text-gray-600">Quality rating</p>
                  </div>
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-blue-50 mb-3">
                      <span className="text-3xl font-bold text-blue-600">
                        {_activeDataset?.files ?? '—'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">Total Files</p>
                    <p className="text-xs text-gray-600">In dataset</p>
                  </div>
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-red-50 mb-3">
                      <span className="text-3xl font-bold text-red-600">
                        {_activeDataset?.issues ?? '—'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">Issues Found</p>
                    <p className="text-xs text-gray-600">Need attention</p>
                  </div>
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-50 mb-3">
                      <span className="text-3xl font-bold text-green-600">
                        {_activeDataset ? _activeDataset.files - _activeDataset.issues : '—'}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900">Passed</p>
                    <p className="text-xs text-gray-600">Meeting standards</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Quality Rules Table */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">Quality Rules</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-700">Rule</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-700">Description</th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-gray-700">Severity</th>
                      <th className="text-right px-6 py-3 text-xs font-semibold text-gray-700">Passed</th>
                      <th className="text-right px-6 py-3 text-xs font-semibold text-gray-700">Failed</th>
                      <th className="text-right px-6 py-3 text-xs font-semibold text-gray-700">Pass Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredRules.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-400 italic">
                          No quality rules found for this dataset. Click Run Checks to evaluate rules.
                        </td>
                      </tr>
                    )}
                    {filteredRules.map(rule => (
                      <tr key={rule.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="font-semibold text-sm text-gray-900">{rule.rule}</div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{rule.description}</td>
                        <td className="px-6 py-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getSeverityColor(rule.severity)}`}>
                            {rule.severity}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right text-sm text-green-600 font-medium">
                          {rule.passed.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right text-sm text-red-600 font-medium">
                          {rule.failed.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div 
                                className={`h-2 rounded-full ${rule.passRate >= 95 ? 'bg-green-500' : rule.passRate >= 85 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                style={{ width: `${rule.passRate}%` }}
                              ></div>
                            </div>
                            <span className="text-sm font-semibold text-gray-900 w-12">{rule.passRate.toFixed(1)}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Issue Details */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold text-gray-900">Issue Details</h2>
                  <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">View All</button>
                </div>
              </div>
              <div className="divide-y divide-gray-200">
                {issueDetails.length === 0 && (
                  <p className="text-sm text-gray-400 italic text-center py-6">No issues found for this dataset.</p>
                )}
                {issueDetails.map(issue => (
                  <div key={issue.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-semibold text-gray-900">{issue.file}</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSeverityColor(issue.severity)}`}>
                            {issue.severity}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                            {issue.type}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 mb-1">{issue.issue}</p>
                        <p className="text-xs text-gray-500">Detected: {issue.detected}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                          View
                        </button>
                        <button className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                          Fix
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Server Transformation Rules */}
            {Object.keys(serverRules).length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="p-6 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-bold text-gray-900">Server Transformation Rules</h2>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{Object.keys(serverRules).length} media type(s)</span>
                      <button
                        onClick={() => fetchServerRules()}
                        className="p-1.5 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {Object.entries(serverRules).map(([mediaType, rules]) => (
                      <div key={mediaType} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-semibold text-gray-900 capitalize">{mediaType}</h3>
                          <button
                            onClick={() => saveRules(mediaType, rules)}
                            disabled={savingRules}
                            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                          >
                            <Save className="w-3 h-3" />
                            Save
                          </button>
                        </div>
                        <div className="space-y-1">
                          {Object.entries(rules).map(([key, value]) => (
                            <div key={key} className="flex items-center justify-between text-sm">
                              <span className="text-gray-600">{key}</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${value === true ? 'bg-green-100 text-green-700' : value === false ? 'bg-gray-100 text-gray-500' : 'bg-blue-100 text-blue-700'}`}>
                                {String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Recent Checks */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">Recent Quality Checks</h2>
              </div>
              <div className="divide-y divide-gray-200">
                {hasFetchedChecks && recentChecks.length === 0 && (
                  <p className="text-sm text-gray-400 italic text-center py-4">No recent quality checks. Run checks to see results here.</p>
                )}
                {recentChecks.map(check => (
                  <div key={check.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                    <div className="flex items-center gap-4">
                      {check.status === 'passed' && <CheckCircle className="w-5 h-5 text-green-600" />}
                      {check.status === 'warning' && <AlertTriangle className="w-5 h-5 text-orange-600" />}
                      {check.status === 'failed' && <XCircle className="w-5 h-5 text-red-600" />}
                      <div>
                        <p className="font-semibold text-sm text-gray-900">{check.rule}</p>
                        <p className="text-xs text-gray-600">{check.dataset} • {check.files.toLocaleString()} files</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(check.status)}`}>
                        {check.status}
                      </span>
                      <span className="text-xs text-gray-500 w-16 text-right">{check.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  )
}
