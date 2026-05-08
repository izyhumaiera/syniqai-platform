import { useState, useEffect, useCallback } from 'react'
import { 
  FileText, Image, File, Scan, Type, Languages,
  Download, Upload, Copy, Check, AlertCircle, Eye,
  Search, ZoomIn, Grid3x3, RefreshCw
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'

export default function TextExtraction() {
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [extractionMethod, setExtractionMethod] = useState('ocr') // 'ocr', 'pdf', 'handwriting'
  const [extractedText, setExtractedText] = useState('')  // kept for legacy compat but not used for display
  const [liveDocuments, setLiveDocuments] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)

  // Live analysis data from AnalysisService + LLM
  const [analysisData, setAnalysisData] = useState(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingError, setProcessingError] = useState(null)
  const [jobProgress, setJobProgress] = useState(null)

  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true)
    try {
      const res = await fetch(`${API_BASE}/api/silver/assets?file_type=pdf&limit=20`)
      if (res.ok) {
        const data = await res.json()
        const mapped = (data.assets || []).map((r, i) => ({
          id: r.id,
          name: r.bronze_minio_key?.split('/').pop() || `document_${i}.pdf`,
          type: r.file_type || 'pdf',
          pages: null,
          status: r.extraction_status || 'pending',
          extracted: !!r.silver_minio_key,
          textLength: r.summary?.length || 0,
          language: 'Unknown',
          confidence: r.ai_confidence_score,
          text_preview: r.summary?.slice(0, 100) || '',
          is_corrupted: r.extraction_status === 'failed',
          assetId: r.id,
          silverKey: r.silver_minio_key,
          bronzePath: r.bronze_minio_key
        }))
        setLiveDocuments(mapped)
      }
    } catch (err) {
      console.warn('Could not fetch documents:', err)
    } finally {
      setHasFetched(true)
      setLoadingDocs(false)
    }
  }, [])

  const fetchAnalysis = useCallback(async (doc) => {
    if (!doc || !doc.silverKey) return
    setLoadingAnalysis(true)
    setAnalysisData(null)
    try {
      // Fetch the Silver JSON from MinIO
      const res = await fetch(`${API_BASE}/api/silver/assets?limit=1`) // Placeholder - would need a direct download endpoint
      if (res.ok) {
        const data = await res.json()
        const asset = data.assets?.find(a => a.id === doc.assetId)
        if (asset) {
          setAnalysisData({
            extracted_text: asset.summary || 'No text extracted',
            extracted_fields: [],
            confidence: asset.ai_confidence_score
          })
        }
      }
    } catch (err) { 
      console.warn('Could not fetch document analysis:', err) 
    } finally { 
      setLoadingAnalysis(false) 
    }
  }, [])

  // AI Processing trigger for PDF/document extraction
  const handleProcessDocument = useCallback(async () => {
    if (!selectedDocument || isProcessing) return
    
    setIsProcessing(true)
    setProcessingError(null)
    setJobProgress({ progress: 0, message: 'Queuing PDF processing job...' })
    
    // Derive domain and entity from bronze path
    let domain = 'general'
    let entity = 'documents'
    if (selectedDocument.bronzePath) {
      const parts = selectedDocument.bronzePath.split('/')
      if (parts.length >= 2) {
        domain = parts[0]
        entity = parts[1] || 'documents'
      }
    }
    
    try {
      const res = await fetch(`${API_BASE}/api/silver/unstructured/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_type: 'document',
          domain,
          entity,
          execution_mode: 'full',
          transforms: {
            extractText: true,
            ocrEnabled: extractionMethod === 'ocr',
            handwritingRecognition: extractionMethod === 'handwriting'
          },
          stage_to_bronze: false, // Files already in Bronze - just process them
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
      
      // Poll job status until completion
      let done = false
      while (!done) {
        await new Promise(r => setTimeout(r, 2000))
        const poll = await fetch(`${API_BASE}/api/silver/unstructured/jobs/${job_id}`)
        
        if (poll.ok) {
          const job = await poll.json()
          setJobProgress({ 
            progress: job.progress ?? 0, 
            message: job.message || job.status 
          })
          
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
      
      // Refresh analysis and document list
      await fetchAnalysis(selectedDocument)
      await fetchDocuments()
      
    } catch (err) {
      const msg = err?.message || String(err)
      setProcessingError(
        msg.includes('fetch') 
          ? 'Cannot reach the API server. Is the backend running on port 8000?' 
          : msg
      )
    } finally {
      setIsProcessing(false)
      setJobProgress(null)
    }
  }, [selectedDocument, isProcessing, extractionMethod, fetchAnalysis, fetchDocuments])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])
  useEffect(() => { if (selectedDocument) fetchAnalysis(selectedDocument) }, [selectedDocument, fetchAnalysis])

  const documents = liveDocuments

  // Live data – no hard-coded fallback
  const extractedFields = analysisData?.extracted_fields || []
  const extractedTextContent = analysisData?.extracted_text || ''

  const extractionMethods = [
    { id: 'ocr', label: 'OCR', icon: Scan, description: 'Image-based text extraction' },
    { id: 'pdf', label: 'PDF Parser', icon: FileText, description: 'Native PDF text extraction' },
    { id: 'handwriting', label: 'Handwriting', icon: Type, description: 'Handwritten text recognition' }
  ]

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
      <div className="bg-green-50 border-b border-green-200 px-6 py-3">
        <div className="flex items-center gap-2 text-sm">
          <FileText className="w-4 h-4 text-green-600" />
          <span className="font-medium text-green-900">Workflow:</span>
          <span className="text-green-700">
            1. Go to <strong>AI Processing</strong> tab to process documents → 
            2. Click <strong>"Process Document"</strong> to extract text with AI
          </span>
        </div>
      </div>
      
      <div className="flex-1 flex overflow-hidden">
      {/* Left Sidebar - Document List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-900">Documents {liveDocuments.length > 0 && <span className="text-xs text-green-600 font-normal ml-1">● live</span>}</h2>
            <div className="flex items-center gap-1">
              <button onClick={fetchDocuments} disabled={loadingDocs} className="p-1.5 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50">
                <RefreshCw className={`w-4 h-4 ${loadingDocs ? 'animate-spin' : ''}`} />
              </button>
              <button className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Upload className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Extraction Method Selector */}
          <div className="mb-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">Extraction Method</label>
            <select 
              value={extractionMethod}
              onChange={(e) => setExtractionMethod(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              {extractionMethods.map(method => (
                <option key={method.id} value={method.id}>{method.label}</option>
              ))}
            </select>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-3">
          {loadingDocs && !hasFetched ? (
            <div className="flex items-center justify-center h-32 text-gray-400 text-sm">Loading documents…</div>
          ) : documents.length === 0 && hasFetched ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-400">
              <FileText className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-xs text-center">No documents found. Go to AI Processing tab to process files.</p>
            </div>
          ) : null}
          {documents.map(doc => (
            <div
              key={doc.id}
              onClick={() => {
                setSelectedDocument(doc)
                // Analysis is fetched automatically via useEffect
              }}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedDocument?.id === doc.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-16 bg-gray-100 rounded flex items-center justify-center">
                  <FileText className="w-6 h-6 text-gray-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-gray-900 truncate">{doc.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(doc.status)}`}>
                      {doc.status}
                    </span>
                  </div>
                  {doc.pages && (
                    <p className="text-xs text-gray-600 mt-1">{doc.pages} pages</p>
                  )}
                  {doc.extracted && doc.confidence != null && (
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-600">
                      <span>{doc.textLength} chars</span>
                      <span>•</span>
                      <span>{(doc.confidence * 100).toFixed(0)}% confidence</span>
                    </div>
                  )}
                  {doc.progress && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div 
                          className="bg-blue-600 h-1.5 rounded-full transition-all"
                          style={{ width: `${doc.progress}%` }}
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
              <h1 className="text-xl font-bold text-gray-900">Text Extraction</h1>
              <p className="text-sm text-gray-600 mt-1">
                {selectedDocument ? selectedDocument.name : 'Select a document to extract text'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selectedDocument && (
                <>
                  <button 
                    onClick={handleProcessDocument}
                    disabled={isProcessing || selectedDocument.status === 'processing'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Scan className={`w-4 h-4 ${isProcessing ? 'animate-pulse' : ''}`} />
                    {isProcessing ? 'Processing...' : 'Process Document'}
                  </button>
                  <button 
                    onClick={() => {
                      if (extractedTextContent) {
                        navigator.clipboard.writeText(extractedTextContent)
                        alert('Text copied to clipboard!')
                      }
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                  >
                    <Copy className="w-4 h-4" />
                    Copy
                  </button>
                  <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                    <Download className="w-5 h-5 text-gray-600" />
                  </button>
                </>
              )}
            </div>
          </div>
          
          {/* Processing Progress */}
          {jobProgress && (
            <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Scan className="w-4 h-4 text-blue-600 animate-pulse" />
                <span className="text-sm font-medium text-blue-900">{jobProgress.message}</span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${jobProgress.progress}%` }}
                ></div>
              </div>
            </div>
          )}
          
          {/* Processing Error */}
          {processingError && (
            <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-900">Processing Failed</p>
                <p className="text-xs text-red-800 mt-1">{processingError}</p>
              </div>
            </div>
          )}
        </div>

        {/* Main Area */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Document Preview */}
          <div className="flex-1 p-6 overflow-auto">
            {selectedDocument ? (
              <div className="space-y-4">
                {/* Document Preview */}
                <div className="bg-white rounded-lg shadow-lg p-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Document Preview</h3>
                  <div className="bg-gray-100 rounded-lg aspect-[8.5/11] flex items-center justify-center">
                    <div className="text-center">
                      <FileText className="w-24 h-24 text-gray-300 mb-2" />
                      <p className="text-sm text-gray-600">{selectedDocument.name}</p>
                      {selectedDocument.pages && (
                        <p className="text-xs text-gray-500">{selectedDocument.pages} pages</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Extracted Text */}
                {(selectedDocument.extracted || extractedTextContent) && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-gray-900">Extracted Text</h3>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Languages className="w-4 h-4" />
                        <span>{analysisData?.detected_language || selectedDocument.language || 'en'}</span>
                        {selectedDocument.confidence != null && (
                          <><span>•</span>
                          <span className="text-green-600 font-medium">{(selectedDocument.confidence * 100).toFixed(1)}% confidence</span></>
                        )}
                      </div>
                    </div>
                    {loadingAnalysis ? (
                      <div className="flex items-center gap-2 text-gray-500 py-4">
                        <RefreshCw className="w-4 h-4 animate-spin" /><span>Loading extracted text…</span>
                      </div>
                    ) : extractedTextContent ? (
                      <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm whitespace-pre-wrap max-h-96 overflow-auto border border-gray-200">
                        {extractedTextContent}
                      </div>
                    ) : (
                      <div className="text-gray-400 text-sm text-center py-6">
                        No text extracted yet. Run a pipeline to process this document.
                      </div>
                    )}
                  </div>
                )}

                {/* Processing Status */}
                {selectedDocument.status === 'processing' && (
                  <div className="bg-white rounded-lg shadow-lg p-6">
                    <div className="flex items-center gap-3">
                      <div className="animate-spin">
                        <Scan className="w-6 h-6 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">Extracting text... {selectedDocument.progress}%</p>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${selectedDocument.progress}%` }}
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
                  <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No document selected</p>
                  <p className="text-sm mt-1">Choose a document to extract text</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar - Extraction Results */}
          <div className="w-96 bg-white border-l border-gray-200 overflow-auto">
            
            {/* Extracted Fields (live from AnalysisService + LLM entity extraction) */}
            {extractedFields.length > 0 && (
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-bold text-gray-900 mb-3">Extracted Fields</h3>
                <div className="space-y-2">
                  {extractedFields.map((field, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">{field.field}</span>
                        <span className="text-xs text-gray-500">{Math.round((field.confidence || 0) * 100)}%</span>
                      </div>
                      <p className="font-semibold text-gray-900">{field.value}</p>
                      <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                        <div className="bg-green-600 h-1 rounded-full"
                          style={{ width: `${(field.confidence || 0) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extraction Options */}
            <div className="p-4">
              <h3 className="font-bold text-gray-900 mb-3">Extraction Options</h3>
              <div className="space-y-3">
                <label className="flex items-center gap-2">
                  <input type="checkbox" defaultChecked className="rounded" />
                  <span className="text-sm text-gray-700">Auto-detect language</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" defaultChecked className="rounded" />
                  <span className="text-sm text-gray-700">Extract tables</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" className="rounded" />
                  <span className="text-sm text-gray-700">Preserve formatting</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" defaultChecked className="rounded" />
                  <span className="text-sm text-gray-700">Auto-correct errors</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" className="rounded" />
                  <span className="text-sm text-gray-700">Extract metadata</span>
                </label>
              </div>

              <div className="mt-6">
                <label className="text-sm font-medium text-gray-700 mb-2 block">Output Format</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option>Plain Text</option>
                  <option>JSON</option>
                  <option>Markdown</option>
                  <option>CSV</option>
                </select>
              </div>

              <div className="mt-6">
                <label className="text-sm font-medium text-gray-700 mb-2 block">Language</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                  <option>Auto-detect</option>
                  <option>English</option>
                  <option>Spanish</option>
                  <option>French</option>
                  <option>German</option>
                  <option>Chinese</option>
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
