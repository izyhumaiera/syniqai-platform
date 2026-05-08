import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Database, 
  TrendingUp, 
  Zap, 
  AlertCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  Shield,
  Download,
  FileText,
  Image,
  Music,
  Table as TableIcon,
  GitBranch,
  CheckCircle2
} from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export default function GoldDashboard() {
  const [goldAssets, setGoldAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [lineageData, setLineageData] = useState(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [totalAssets, setTotalAssets] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [fileTypeFilter, setFileTypeFilter] = useState('');
  const pageSize = 20;

  // Load gold assets from materialized view
  const loadGoldAssets = async (page = 0, fileType = '') => {
    try {
      setError(null);
      const offset = page * pageSize;
      const params = {
        limit: pageSize,
        offset: offset
      };
      if (fileType) {
        params.file_type = fileType;
      }
      
      const response = await axios.get(`${API_BASE}/gold/assets`, { params });
      setGoldAssets(response.data.assets || []);
      setTotalAssets(response.data.total || 0);
    } catch (err) {
      console.error('Error loading Gold assets:', err);
      setError(err.response?.data?.detail || 'Failed to load Gold assets');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Refresh materialized view
  const handleRefreshView = async () => {
    try {
      setRefreshing(true);
      const response = await axios.post(`${API_BASE}/gold/refresh`);
      console.log('Gold view refreshed:', response.data);
      
      // Show success message
      alert(`✅ Gold view refreshed!\nTotal assets: ${response.data.total_assets}\nNew assets: ${response.data.new_assets}`);
      
      // Reload assets
      await loadGoldAssets(currentPage, fileTypeFilter);
    } catch (err) {
      console.error('Error refreshing Gold view:', err);
      alert('❌ Failed to refresh Gold view: ' + (err.response?.data?.detail || err.message));
    } finally {
      setRefreshing(false);
    }
  };

  // Load lineage for selected asset
  const loadLineage = async (assetId) => {
    try {
      setLineageLoading(true);
      const response = await axios.get(`${API_BASE}/gold/lineage/${assetId}`);
      setLineageData(response.data);
    } catch (err) {
      console.error('Error loading lineage:', err);
      alert('Failed to load lineage: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLineageLoading(false);
    }
  };

  useEffect(() => {
    loadGoldAssets(currentPage, fileTypeFilter);
  }, [currentPage, fileTypeFilter]);

  // Get icon for file type
  const getFileTypeIcon = (fileType) => {
    switch(fileType?.toLowerCase()) {
      case 'pdf':
      case 'document':
        return <FileText className="text-red-600" size={20} />;
      case 'image':
      case 'png':
      case 'jpg':
      case 'jpeg':
        return <Image className="text-blue-600" size={20} />;
      case 'audio':
      case 'mp3':
      case 'wav':
        return <Music className="text-purple-600" size={20} />;
      default:
        return <Database className="text-gray-600" size={20} />;
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50">
        <div className="text-center">
          <Loader2 size={48} className="mx-auto text-blue-500 animate-spin mb-3" />
          <p className="text-gray-600">Loading Gold layer assets...</p>
        </div>
      </div>
    );
  }

  // Calculate statistics
  const avgConfidence = goldAssets.length > 0
    ? goldAssets.reduce((sum, a) => sum + (a.ai_confidence_score || 0), 0) / goldAssets.length
    : 0;
  
  const fileTypeCounts = goldAssets.reduce((acc, asset) => {
    const type = asset.file_type || 'unknown';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="w-full">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">Gold Layer - Promoted Assets</h1>
            <p className="text-sm text-gray-500 mt-1">
              Curated, high-quality assets from successful Silver extractions
            </p>
          </div>
          <button
            onClick={handleRefreshView}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            Refresh Gold View
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle size={20} className="text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-red-900">Failed to load Gold assets</p>
            <p className="text-sm text-red-800 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Total Assets */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="text-yellow-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalAssets}</p>
              <p className="text-sm text-gray-600">Total Gold Assets</p>
            </div>
          </div>
        </div>

        {/* Current Page Assets */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Database className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{goldAssets.length}</p>
              <p className="text-sm text-gray-600">Showing (Page {currentPage + 1})</p>
            </div>
          </div>
        </div>

        {/* Average Confidence */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Sparkles className="text-green-600" size={24} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{(avgConfidence * 100).toFixed(1)}%</p>
              <p className="text-sm text-gray-600">Avg AI Confidence</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="mb-4 flex items-center gap-4">
        <label className="text-sm font-medium text-gray-700">Filter by File Type:</label>
        <select
          value={fileTypeFilter}
          onChange={(e) => {
            setFileTypeFilter(e.target.value);
            setCurrentPage(0);
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Types</option>
          <option value="pdf">PDF</option>
          <option value="image">Image</option>
          <option value="audio">Audio</option>
          <option value="document">Document</option>
        </select>
      </div>

      {/* Assets Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Gold Assets</h2>
          <p className="text-sm text-gray-500 mt-1">
            Click any asset to view its complete lineage trail
          </p>
        </div>

        {goldAssets.length === 0 ? (
          <div className="p-12 text-center">
            <Database size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-600 mb-2">No Gold assets yet</p>
            <p className="text-sm text-gray-500">
              Assets will appear here after successful Silver processing
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Summary</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">AI Model</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Processed</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {goldAssets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getFileTypeIcon(asset.file_type)}
                        <span className="text-sm font-medium text-gray-900">{asset.file_type || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">{asset.source || 'N/A'}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 max-w-md truncate">
                        {asset.summary || 'No summary'}
                      </div>
                      {asset.content_tags && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {(Array.isArray(asset.content_tags) ? asset.content_tags : JSON.parse(asset.content_tags || '[]'))
                            .slice(0, 3)
                            .map((tag, idx) => (
                              <span key={idx} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                                {tag}
                              </span>
                            ))}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {asset.ai_model_used || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${(asset.ai_confidence_score || 0) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-900">
                          {((asset.ai_confidence_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(asset.processed_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => {
                          setSelectedAsset(asset);
                          loadLineage(asset.id);
                        }}
                        className="flex items-center gap-1 text-blue-600 hover:text-blue-700 font-medium"
                      >
                        <GitBranch size={16} />
                        Lineage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalAssets > pageSize && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {currentPage * pageSize + 1} to {Math.min((currentPage + 1) * pageSize, totalAssets)} of {totalAssets} assets
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                disabled={currentPage === 0}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(p => p + 1)}
                disabled={(currentPage + 1) * pageSize >= totalAssets}
                className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Lineage Side Panel */}
      {selectedAsset && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setSelectedAsset(null)}>
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Data Lineage Trail</h3>
                <p className="text-sm text-gray-500 mt-1">Asset ID: {selectedAsset.id.substring(0, 8)}...</p>
              </div>
              <button
                onClick={() => setSelectedAsset(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="text-2xl">&times;</span>
              </button>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(80vh-120px)]">
              {lineageLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="animate-spin text-blue-600" size={32} />
                </div>
              ) : lineageData ? (
                <div>
                  {/* Asset Info */}
                  <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">File Type:</span>
                        <span className="ml-2 font-medium text-gray-900">{lineageData.asset.file_type}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Source:</span>
                        <span className="ml-2 font-medium text-gray-900">{lineageData.asset.source}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500">Bronze Path:</span>
                        <span className="ml-2 font-mono text-xs text-gray-700">{lineageData.asset.bronze_minio_key}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-500">Silver Path:</span>
                        <span className="ml-2 font-mono text-xs text-gray-700">{lineageData.asset.silver_minio_key}</span>
                      </div>
                    </div>
                  </div>

                  {/* Lineage Timeline */}
                  <div className="space-y-4">
                    <h4 className="font-semibold text-gray-800">Transformation Events</h4>
                    {lineageData.lineage.length === 0 ? (
                      <p className="text-sm text-gray-500">No lineage events recorded yet</p>
                    ) : (
                      <div className="relative border-l-2 border-blue-300 pl-6 space-y-6">
                        {lineageData.lineage.map((event, idx) => (
                          <div key={idx} className="relative">
                            <div className="absolute -left-[29px] w-5 h-5 bg-blue-600 rounded-full border-4 border-white"></div>
                            <div className="bg-white border border-gray-200 rounded-lg p-4">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-semibold text-gray-800 capitalize">
                                  {event.event_type.replace('_', ' ')}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {formatDate(event.event_time)}
                                </span>
                              </div>
                              <div className="space-y-1 text-sm">
                                {event.model_used && (
                                  <div>
                                    <span className="text-gray-500">Model:</span>
                                    <span className="ml-2 text-gray-900">{event.model_used}</span>
                                  </div>
                                )}
                                {event.quality_score !== null && (
                                  <div>
                                    <span className="text-gray-500">Quality Score:</span>
                                    <span className="ml-2 text-gray-900">{(event.quality_score * 100).toFixed(1)}%</span>
                                  </div>
                                )}
                                {event.source_bucket && (
                                  <div>
                                    <span className="text-gray-500">From:</span>
                                    <span className="ml-2 font-mono text-xs text-gray-700">{event.source_bucket}</span>
                                  </div>
                                )}
                                {event.dest_bucket && (
                                  <div>
                                    <span className="text-gray-500">To:</span>
                                    <span className="ml-2 font-mono text-xs text-gray-700">{event.dest_bucket}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
