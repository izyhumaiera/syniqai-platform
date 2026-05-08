import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  RefreshCw, 
  Database, 
  Activity, 
  CheckCircle, 
  XCircle, 
  Eye,
  Info,
  AlertCircle
} from 'lucide-react';

/**
 * CDC Streaming - Real-time Change Data Capture to Silver Layer
 * Monitors CDC topics from Debezium and streams to MinIO silver bucket
 * 
 * ALIGNED WITH BRONZE→SILVER PIPELINE:
 * - Uses same SilverTransformer (cleaning_rules.yaml)
 * - Uses same SilverQualityGate for validation
 * - Writes to same syniqai-silver bucket
 * - Same quality scoring and metadata
 * - No hardcoded values (reads from .env and config)
 */
export default function CDCStreaming() {
  const [topics, setTopics] = useState([]);
  const [status, setStatus] = useState(null);
  const [silverTables, setSilverTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTable, setSelectedTable] = useState(null);
  const [previewData, setPreviewData] = useState(null);

  // Load initial data
  useEffect(() => {
    loadTopics();
    loadStatus();
    loadSilverTables();
  }, []);

  // Auto-refresh status every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (status?.running) {
        loadStatus();
        loadSilverTables();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [status]);

  const loadTopics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/cdc-silver/topics');
      const data = await response.json();
      if (data.success) {
        setTopics(data.topics);
      }
    } catch (err) {
      console.error('Failed to load topics:', err);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/cdc-silver/status');
      const data = await response.json();
      if (data.success) {
        setStatus(data);
      }
    } catch (err) {
      console.error('Failed to load status:', err);
    }
  };

  const loadSilverTables = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/silver/cdc-tables');
      const data = await response.json();
      if (data.success) {
        // Filter out non-CDC tables (like jpg, png folders)
        const cdcTables = data.tables.filter(t => 
          !['jpg', 'png', 'gif', 'mp3', 'mp4', 'pdf'].includes(t.source.toLowerCase())
        );
        setSilverTables(cdcTables);
      }
    } catch (err) {
      console.error('Failed to load silver tables:', err);
    }
  };

  const startStreaming = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/cdc-silver/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_discover: true })
      });
      const data = await response.json();
      if (data.success) {
        await loadStatus();
      } else {
        setError(data.message || 'Failed to start streaming');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const stopStreaming = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/cdc-silver/stop', {
        method: 'POST'
      });
      const data = await response.json();
      if (data.success) {
        await loadStatus();
      } else {
        setError(data.message || 'Failed to stop streaming');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const previewTable = async (source, table) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/silver/cdc-preview/${source}/${table}?limit=10`);
      const data = await response.json();
      if (data.success) {
        setPreviewData(data);
        setSelectedTable({ source, table });
      } else {
        setError(data.message || 'Failed to load preview');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="h-full w-full p-6 overflow-auto bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CDC Streaming</h1>
            <p className="text-gray-600 mt-1">Real-time Change Data Capture to Silver Layer</p>
            <p className="text-sm text-blue-600 mt-1">
              ⚡ Aligned with Bronze→Silver pipeline • Same transformations • Same quality gates
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadTopics}
              disabled={loading}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            {status?.running ? (
              <button
                onClick={stopStreaming}
                disabled={loading}
                className="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 flex items-center gap-2"
              >
                <Square className="w-4 h-4" />
                Stop Streaming
              </button>
            ) : (
              <button
                onClick={startStreaming}
                disabled={loading}
                className="px-4 py-2 text-white bg-green-600 rounded-lg hover:bg-green-700 flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                Start Streaming
              </button>
            )}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Status Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Streaming Status
            </h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              status?.running 
                ? 'bg-green-100 text-green-800' 
                : 'bg-gray-100 text-gray-800'
            }`}>
              {status?.running ? (
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" />
                  Active
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <XCircle className="w-4 h-4" />
                  Stopped
                </span>
              )}
            </span>
          </div>

          {status?.running && status.active_streams?.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-gray-600 font-medium">
                Active Streams: {status.active_streams.length}
              </p>
              <div className="space-y-2">
                {status.active_streams.map((stream, idx) => (
                  <div key={idx} className="bg-gray-50 rounded p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{stream.table}</p>
                        <p className="text-gray-500 text-xs mt-1">Topic: {stream.topic}</p>
                      </div>
                      <span className="text-green-600 text-xs font-medium">
                        {stream.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!status?.running && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">Pipeline Alignment</p>
                <p className="text-sm text-blue-700 mt-1">
                  CDC→Silver uses the same transformation pipeline as Bronze→Silver:
                </p>
                <ul className="text-xs text-blue-600 mt-2 space-y-1 ml-4">
                  <li>✓ Same SilverTransformer (cleaning_rules.yaml)</li>
                  <li>✓ Same SilverQualityGate for validation</li>
                  <li>✓ Same MinIO bucket structure</li>
                  <li>✓ Same quality scoring logic</li>
                  <li>✓ No hardcoded values (reads from .env)</li>
                </ul>
                <p className="text-sm text-blue-700 mt-2">
                  Click "Start Streaming" to begin capturing CDC changes and processing them to Silver bucket.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Available Topics */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            Discovered CDC Topics ({topics.length})
          </h2>
          {topics.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {topics.map((topic, idx) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="font-medium text-gray-900 text-sm">{topic.full_name}</p>
                  <p className="text-gray-500 text-xs mt-1">Source: {topic.source}</p>
                  <p className="text-gray-400 text-xs mt-1 font-mono">{topic.topic}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No CDC topics discovered. Make sure Debezium connectors are configured.</p>
          )}
        </div>

        {/* Silver Tables */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Silver Layer Tables ({silverTables.length})
          </h2>
          {silverTables.length > 0 ? (
            <div className="space-y-3">
              {silverTables.map((table, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">{table.full_name}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                        <span>{table.file_count} files</span>
                        <span>•</span>
                        <span>{formatBytes(table.total_size_bytes)}</span>
                        <span>•</span>
                        <span>Updated: {formatDate(table.last_modified)}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => previewTable(table.source, table.table)}
                      className="px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg flex items-center gap-2 text-sm"
                    >
                      <Eye className="w-4 h-4" />
                      Preview
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
              <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 font-medium">No tables in Silver Layer yet</p>
              <p className="text-gray-500 text-sm mt-1">
                Start streaming and make changes to your database to see data appear here.
              </p>
            </div>
          )}
        </div>

        {/* Preview Modal */}
        {previewData && selectedTable && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      {selectedTable.source}.{selectedTable.table}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {previewData.total_rows} total rows • Showing {previewData.preview_rows} rows
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setPreviewData(null);
                      setSelectedTable(null);
                    }}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <XCircle className="w-6 h-6" />
                  </button>
                </div>
              </div>
              <div className="p-6 overflow-auto flex-1">
                {previewData.data && previewData.data.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          {previewData.columns.map((col, idx) => (
                            <th key={idx} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider whitespace-nowrap">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {previewData.data.map((row, rowIdx) => (
                          <tr key={rowIdx} className="hover:bg-gray-50">
                            {previewData.columns.map((col, colIdx) => (
                              <td key={colIdx} className="px-4 py-3 whitespace-nowrap text-gray-900">
                                {typeof row[col] === 'object' 
                                  ? JSON.stringify(row[col]).substring(0, 50) + '...'
                                  : String(row[col] ?? '').substring(0, 100)
                                }
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No data available</p>
                )}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
