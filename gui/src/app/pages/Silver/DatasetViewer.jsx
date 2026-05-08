import React, { useState, useEffect } from 'react';
import { Table, Database, Download, RefreshCw, Filter, Eye, Code, BarChart3, History, ChevronDown, Play, Copy, CheckCircle, AlertCircle, Info, Shield, ArrowLeft } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';

/**
 * DatasetViewer - Detailed view of a specific dataset
 * Shows schema, sample data, statistics, and history
 */
export default function DatasetViewer({ dataset }) {
  const navigate = useNavigate();
  const { domain } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [activeTab, setActiveTab] = useState('preview'); // 'preview', 'schema', 'statistics', 'history', 'lineage'
  const [previewLimit, setPreviewLimit] = useState(100);
  const [showRawSQL, setShowRawSQL] = useState(false);
  const [schemaHistory, setSchemaHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  
  // Query validation state
  const [querySQL, setQuerySQL] = useState('');
  const [queryResults, setQueryResults] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Real data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [schemaData, setSchemaData] = useState([]);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [statisticsData, setStatisticsData] = useState([]);
  const [statisticsLoading, setStatisticsLoading] = useState(false);

  // Mock data - replace with actual API calls
  const defaultDataset = dataset || {
    name: 'finance_transactions',
    domain: 'finance',
    source: 'MariaDB',
    layer: 'bronze',
    rowCount: '2.4M',
    size: '1.2 GB',
    columns: 15
  };

  // Log the dataset to verify it's being passed correctly
  useEffect(() => {
    if (dataset) {
      console.log('DatasetViewer received dataset:', dataset);
      console.log('Using dataset for Check Quality:', {
        name: defaultDataset.name,
        domain: defaultDataset.domain,
        source: defaultDataset.source
      });
    }
  }, [dataset]);

  // Don't use hardcoded mock data anymore - these will be empty until fetched
  const schema = schemaData;
  const sampleData = previewData;
  const statistics = statisticsData;

  // Fetch schema history from Kafka CDC topics
  useEffect(() => {
    const fetchSchemaHistory = async () => {
      if (activeTab === 'history' && defaultDataset.name) {
        setHistoryLoading(true);
        setHistoryError(null);
        
        try {
          const response = await axios.get(`http://localhost:8000/api/bronze/schema-history/${defaultDataset.name}`, {
            params: {
              domain: defaultDataset.domain || 'finance',
              source: defaultDataset.source?.toLowerCase() || 'postgres',
              limit: 20
            }
          });
          
          if (response.data.success) {
            const history = response.data.history || [];
            setSchemaHistory(history);
            console.log(`Fetched ${history.length} schema history entries from Kafka CDC`);
          } else {
            setHistoryError('Failed to load schema history');
          }
        } catch (error) {
          console.error('Error fetching schema history:', error);
          setHistoryError(error.response?.data?.detail || 'Failed to connect to Kafka CDC backend');
          // Don't set fallback data - show the error to user
          setSchemaHistory([]);
        } finally {
          setHistoryLoading(false);
        }
      }
    };
    
    fetchSchemaHistory();
  }, [activeTab, defaultDataset.name, defaultDataset.domain, defaultDataset.source]);

  // Initialize query SQL when tab is opened
  useEffect(() => {
    if (activeTab === 'query' && !querySQL) {
      // Use a simple placeholder - will be replaced with S3 path during execution
      const normalizedSource = (defaultDataset.source || 'postgres').toLowerCase().replace('sql', '');
      const normalizedDomain = (defaultDataset.domain || 'finance').toLowerCase();
      const tableAlias = `syniqai_bronze_${normalizedDomain}_${normalizedSource}_${defaultDataset.name}`;
      setQuerySQL(`SELECT * FROM ${tableAlias} LIMIT 100;`);
    }
  }, [activeTab, defaultDataset.name, defaultDataset.source, defaultDataset.domain]);

  // Fetch preview data when Preview tab is opened
  useEffect(() => {
    const fetchPreviewData = async () => {
      if (activeTab === 'preview' && defaultDataset.name) {
        setPreviewLoading(true);
        try {
          const response = await axios.get(`http://localhost:8000/api/bronze-data/preview-data/${defaultDataset.name}`, {
            params: {
              domain: defaultDataset.domain || 'finance',
              source: defaultDataset.source?.toLowerCase() || 'postgres',
              limit: previewLimit
            }
          });
          if (response.data.success) {
            setPreviewData(response.data.rows || []);
            console.log(`Fetched ${response.data.rows?.length || 0} preview rows from MinIO`);
          }
        } catch (error) {
          console.error('Error fetching preview data:', error);
          setPreviewData([]);
        } finally {
          setPreviewLoading(false);
        }
      }
    };
    fetchPreviewData();
  }, [activeTab, defaultDataset.name, defaultDataset.domain, defaultDataset.source, previewLimit]);

  // Fetch schema when Schema tab is opened
  useEffect(() => {
    const fetchSchema = async () => {
      if (activeTab === 'schema' && defaultDataset.name) {
        setSchemaLoading(true);
        try {
          const response = await axios.get(`http://localhost:8000/api/bronze-data/schema/${defaultDataset.name}`, {
            params: {
              domain: defaultDataset.domain || 'finance',
              source: defaultDataset.source?.toLowerCase() || 'postgres'
            }
          });
          if (response.data.success) {
            setSchemaData(response.data.schema || []);
            console.log(`Fetched schema with ${response.data.schema?.length || 0} columns from MinIO`);
          }
        } catch (error) {
          console.error('Error fetching schema:', error);
          setSchemaData([]);
        } finally {
          setSchemaLoading(false);
        }
      }
    };
    fetchSchema();
  }, [activeTab, defaultDataset.name, defaultDataset.domain, defaultDataset.source]);

  // Fetch statistics when Statistics tab is opened
  useEffect(() => {
    const fetchStatistics = async () => {
      if (activeTab === 'statistics' && defaultDataset.name) {
        setStatisticsLoading(true);
        try {
          const response = await axios.get(`http://localhost:8000/api/bronze-data/statistics/${defaultDataset.name}`, {
            params: {
              domain: defaultDataset.domain || 'finance',
              source: defaultDataset.source?.toLowerCase() || 'postgres'
            }
          });
          if (response.data.success) {
            setStatisticsData(response.data.statistics || []);
            console.log(`Fetched statistics for ${response.data.statistics?.length || 0} columns from MinIO`);
          }
        } catch (error) {
          console.error('Error fetching statistics:', error);
          setStatisticsData([]);
        } finally {
          setStatisticsLoading(false);
        }
      }
    };
    fetchStatistics();
  }, [activeTab, defaultDataset.name, defaultDataset.domain, defaultDataset.source]);

  // Handle Run Query
  const handleRunQuery = async () => {
    setQueryLoading(true);
    setQueryError(null);
    
    try {
      // Normalize source name (PostgreSQL -> postgres)
      const normalizedSource = (defaultDataset.source || 'postgres').toLowerCase().replace('sql', '');
      const normalizedDomain = (defaultDataset.domain || 'finance').toLowerCase();
      const tableName = defaultDataset.name;
      
      // Construct S3 path (same as Preview tab)
      const s3Path = `s3://syniqai-bronze/${normalizedDomain}/${normalizedSource}/${tableName}/*.parquet`;
      
      console.log('🔍 Query Execution Details:', {
        tableName,
        s3Path,
        originalQuery: querySQL,
        dataset: defaultDataset
      });
      
      // Replace the table name in the query with the actual S3 path for direct DuckDB querying
      const modifiedQuery = querySQL.replace(
        /FROM\s+[\w_]+/i,
        `FROM '${s3Path}'`
      );
      
      console.log('📝 Modified Query (DuckDB style):', modifiedQuery);
      
      // Try to execute using DuckDB-compatible endpoint
      // If this fails, we'll create a simple execute endpoint
      const response = await axios.post('http://localhost:8000/api/bronze-data/execute-query', {
        query: modifiedQuery,
        table_name: tableName,
        domain: normalizedDomain,
        source: normalizedSource,
        limit: 1000
      });
      
      console.log('✅ Query Response:', response.data);
      
      if (response.data.success) {
        setQueryResults({
          success: true,
          columns: response.data.columns || [],
          rows: response.data.rows || [],
          row_count: response.data.row_count || response.data.rows?.length || 0,
          execution_time_ms: response.data.execution_time_ms || 0
        });
        console.log(`✅ Query executed successfully: ${response.data.rows?.length || 0} rows returned`);
      } else {
        const errorMsg = response.data.error || response.data.message || 'Query execution failed';
        console.error('❌ Query failed:', errorMsg);
        setQueryError(String(errorMsg)); // Ensure it's a string
      }
    } catch (error) {
      console.error('❌ Query execution error:', error);
      console.error('📋 Error response:', error.response?.data);
      
      // Extract error message and ensure it's a string
      let errorMsg = 'Failed to execute query. Check console for details.';
      
      if (error.response?.data) {
        const data = error.response.data;
        if (typeof data === 'string') {
          errorMsg = data;
        } else if (data.detail) {
          if (Array.isArray(data.detail)) {
            // FastAPI validation errors
            errorMsg = data.detail.map(err => `${err.loc?.join('.')}: ${err.msg}`).join(', ');
          } else {
            errorMsg = String(data.detail);
          }
        } else if (data.error) {
          errorMsg = String(data.error);
        } else if (data.message) {
          errorMsg = String(data.message);
        }
      } else if (error.message) {
        errorMsg = String(error.message);
      }
      
      setQueryError(errorMsg);
    } finally {
      setQueryLoading(false);
    }
  };

  // Handle Copy SQL
  const handleCopySQL = async () => {
    try {
      await navigator.clipboard.writeText(querySQL);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const tabs = [
    { id: 'preview', label: 'Data Preview', icon: Eye },
    { id: 'schema', label: 'Schema', icon: Database },
    { id: 'statistics', label: 'Statistics', icon: BarChart3 },
    { id: 'history', label: 'History', icon: History },
    { id: 'query', label: 'Query', icon: Code }
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={(e) => {
                e.preventDefault();
                setSearchParams({ tab: 'catalog' });
              }}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="Back to Catalog"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-3">
                <Table className="w-6 h-6 text-gray-600" />
                <h1 className="text-2xl font-bold text-gray-900">{defaultDataset.name}</h1>
                <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs font-medium">
                  {defaultDataset.layer}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-2">
                {defaultDataset.domain} • {defaultDataset.source} • {defaultDataset.rowCount} rows • {defaultDataset.size}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button 
              onClick={(e) => {
                e.preventDefault();
                console.log('Navigating to Check Quality with:', {
                  table: defaultDataset.name,
                  domain: defaultDataset.domain,
                  source: defaultDataset.source
                });
                // Update URL parameters to switch to quality tab
                setSearchParams({
                  tab: 'quality',
                  table: defaultDataset.name,
                  domain: defaultDataset.domain || 'finance',
                  source: defaultDataset.source || 'postgres'
                });
              }}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg text-sm font-medium hover:from-blue-700 hover:to-indigo-700 flex items-center gap-2 shadow-md"
              title={`Check Quality for ${defaultDataset.name}`}
            >
              <Shield className="w-4 h-4" />
              Check Quality
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="flex gap-1 px-6">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'preview' && (
          <div>
            <div className="bg-white rounded-lg shadow border border-gray-200">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Table Data Preview</h2>
                <div className="flex items-center gap-3">
                  {previewLoading && (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Loading...
                    </div>
                  )}
                  <label className="text-sm text-gray-600">Rows:</label>
                  <select
                    value={previewLimit}
                    onChange={(e) => setPreviewLimit(Number(e.target.value))}
                    className="border border-gray-300 rounded px-2 py-1 text-sm"
                  >
                    <option value={10}>10</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={500}>500</option>
                  </select>
                </div>
              </div>
              <div className="overflow-x-auto">
                {previewLoading ? (
                  <div className="text-center py-12 text-gray-500">
                    <RefreshCw className="w-8 h-8 mx-auto mb-3 text-gray-400 animate-spin" />
                    <p>Loading data from MinIO...</p>
                  </div>
                ) : sampleData.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Database className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                    <p>No data found</p>
                    <p className="text-sm mt-1">Table might be empty or not accessible</p>
                  </div>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        {Object.keys(sampleData[0] || {}).map(key => (
                          <th key={key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sampleData.map((row, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          {Object.values(row).map((value, cellIdx) => (
                            <td key={cellIdx} className="px-4 py-3 whitespace-nowrap text-gray-900">
                              {value === null ? <span className="text-gray-400 italic">null</span> : String(value)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'schema' && (
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Schema Definition from MinIO</h2>
              {schemaLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Loading...
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              {schemaLoading ? (
                <div className="text-center py-12 text-gray-500">
                  <RefreshCw className="w-8 h-8 mx-auto mb-3 text-gray-400 animate-spin" />
                  <p>Loading schema from MinIO...</p>
                </div>
              ) : schema.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Database className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>No schema found</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data Type</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nullable</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Key</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {schema.map((col, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{col.name}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                            {col.type}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {col.nullable ? (
                            <span className="text-gray-600">Yes</span>
                          ) : (
                            <span className="text-red-600 font-medium">No</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {col.primaryKey && (
                            <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-medium">
                              PRIMARY
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-gray-600">{col.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'statistics' && (
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Column Statistics from MinIO</h2>
              {statisticsLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Calculating...
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              {statisticsLoading ? (
                <div className="text-center py-12 text-gray-500">
                  <RefreshCw className="w-8 h-8 mx-auto mb-3 text-gray-400 animate-spin" />
                  <p>Calculating statistics from MinIO data...</p>
                  <p className="text-sm mt-1">This may take a moment...</p>
                </div>
              ) : statistics.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>No statistics available</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Distinct</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nulls</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Null %</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Min</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Max</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {statistics.map((stat, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{stat.column}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-600">{stat.type}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">{stat.distinct}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">{stat.nulls}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={stat.nullPercent > 5 ? 'text-red-600 font-medium' : 'text-gray-600'}>
                            {stat.nullPercent}%
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">{stat.min}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">{stat.max}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">{stat.avg}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Schema History from Kafka CDC</h2>
              {historyLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Loading from Kafka...
                </div>
              )}
            </div>
            
            {historyError && (
              <div className="p-4 bg-yellow-50 border-b border-yellow-100">
                <p className="text-sm text-yellow-800">
                  ⚠️ {historyError} - Showing fallback data
                </p>
              </div>
            )}
            
            <div className="p-6">
              {schemaHistory.length === 0 && !historyLoading ? (
                <div className="text-center py-8 text-gray-500">
                  <History className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>No schema history found</p>
                  <p className="text-sm mt-1">Enable CDC to track schema changes</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {schemaHistory.map((entry, idx) => (
                    <div key={idx} className="flex gap-4 pb-4 border-b border-gray-200 last:border-0">
                      <div className="flex-shrink-0">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          entry.change_type === 'mock' ? 'bg-gray-100' : 'bg-blue-50'
                        }`}>
                          <History className={`w-5 h-5 ${
                            entry.change_type === 'mock' ? 'text-gray-400' : 'text-blue-600'
                          }`} />
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-gray-900">{entry.version}</span>
                          <span className="text-sm text-gray-500">
                            • {entry.date?.includes('T') ? new Date(entry.date).toLocaleString() : entry.date}
                          </span>
                          {entry.change_type && entry.change_type !== 'mock' && (
                            <span className="px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded-full">
                              {entry.change_type}
                            </span>
                          )}
                          {entry.change_type === 'mock' && (
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                              sample data
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 mb-1">{entry.changes}</p>
                        <p className="text-xs text-gray-500">by {entry.author}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'query' && (
          <div className="space-y-4">
            {/* Header with explanation */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-blue-900 mb-1">Quick Validation & Testing</h3>
                  <p className="text-sm text-blue-800">
                    This interface is for <strong>quick data inspection and validation</strong> only. 
                    Use SELECT queries to check data quality, test assumptions, and verify transformations.
                  </p>
                  <p className="text-sm text-blue-700 mt-2">
                    💡 <strong>For data transformations</strong>, use the <strong>Transform</strong> button above with the full SQL editor (Monaco, templates, auto-complete).
                  </p>
                </div>
              </div>
            </div>

            {/* Step-by-step workflow */}
            <div className="bg-white rounded-lg shadow border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Validation Query Workflow</h2>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Step 1: Edit SQL */}
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                      1
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-2">Edit Your Validation Query</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Write a SELECT query to inspect your data. Examples: check nulls, count rows, find duplicates.
                    </p>
                    <div className="bg-gray-900 rounded-lg p-4">
                      <textarea
                        value={querySQL}
                        onChange={(e) => setQuerySQL(e.target.value)}
                        className="w-full bg-transparent text-white font-mono text-sm resize-none focus:outline-none"
                        rows={6}
                        placeholder="SELECT * FROM bronze.finance_transactions LIMIT 100;"
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      ⚠️ Only SELECT queries allowed. No INSERT/UPDATE/DELETE/DROP.
                    </p>
                  </div>
                </div>

                {/* Step 2: Run Query */}
                <div className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                      2
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-2">Execute & Review Results</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Run your query to see results. Verify data quality and test your assumptions.
                    </p>
                    <div className="flex gap-2">
                      <button 
                        onClick={handleRunQuery}
                        disabled={queryLoading || !querySQL.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
                      >
                        {queryLoading ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Running...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4" />
                            Run Query
                          </>
                        )}
                      </button>
                      <button 
                        onClick={handleCopySQL}
                        className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                      >
                        {copied ? (
                          <>
                            <CheckCircle className="w-4 h-4 text-green-600" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy SQL
                          </>
                        )}
                      </button>
                    </div>

                    {/* Query Error */}
                    {queryError && (
                      <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-red-900">Query Failed</p>
                          <p className="text-sm text-red-700">{queryError}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Step 3: Analyze Results */}
                {queryResults && (
                  <div className="flex gap-4">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-bold">
                        3
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900 mb-2">Analyze Results</h3>
                      
                      {/* Query Metadata */}
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-green-800">
                            <strong>✓ Success:</strong> {queryResults.message}
                          </span>
                          <span className="text-gray-600">
                            {queryResults.row_count} rows
                          </span>
                          <span className="text-gray-600">
                            {queryResults.execution_time_ms.toFixed(2)}ms
                          </span>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                            {queryResults.query_type}
                          </span>
                        </div>
                      </div>

                      {/* Results Table */}
                      {queryResults.rows && queryResults.rows.length > 0 ? (
                        <div className="border border-gray-200 rounded-lg overflow-hidden">
                          <div className="overflow-x-auto max-h-96">
                            <table className="w-full text-sm">
                              <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                  {queryResults.columns.map((col, idx) => (
                                    <th key={idx} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap border-b border-gray-200">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="bg-white divide-y divide-gray-200">
                                {queryResults.rows.map((row, rowIdx) => (
                                  <tr key={rowIdx} className="hover:bg-gray-50">
                                    {queryResults.columns.map((col, colIdx) => (
                                      <td key={colIdx} className="px-4 py-3 whitespace-nowrap text-gray-900">
                                        {row[col] === null ? (
                                          <span className="text-gray-400 italic">null</span>
                                        ) : typeof row[col] === 'object' ? (
                                          JSON.stringify(row[col])
                                        ) : (
                                          String(row[col])
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-8 text-gray-500 border border-gray-200 rounded-lg">
                          <Database className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                          <p>No results returned</p>
                          <p className="text-sm mt-1">Query executed successfully but returned 0 rows</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Help text when no results yet */}
                {!queryResults && !queryLoading && (
                  <div className="flex gap-4">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center font-bold">
                        3
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-500 mb-2">Analyze Results</h3>
                      <p className="text-sm text-gray-500">
                        Results will appear here after running your query.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick tips */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-2 text-sm">💡 Common Validation Queries</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button 
                  onClick={() => setQuerySQL(`SELECT COUNT(*) as total_rows FROM ${defaultDataset.layer}.${defaultDataset.name};`)}
                  className="text-left px-3 py-2 bg-white border border-gray-200 rounded hover:bg-gray-50"
                >
                  Count total rows
                </button>
                <button 
                  onClick={() => setQuerySQL(`SELECT * FROM ${defaultDataset.layer}.${defaultDataset.name} WHERE amount IS NULL;`)}
                  className="text-left px-3 py-2 bg-white border border-gray-200 rounded hover:bg-gray-50"
                >
                  Check for nulls
                </button>
                <button 
                  onClick={() => setQuerySQL(`SELECT status, COUNT(*) as count FROM ${defaultDataset.layer}.${defaultDataset.name} GROUP BY status;`)}
                  className="text-left px-3 py-2 bg-white border border-gray-200 rounded hover:bg-gray-50"
                >
                  Group by status
                </button>
                <button 
                  onClick={() => setQuerySQL(`SELECT MIN(amount) as min, MAX(amount) as max, AVG(amount) as avg FROM ${defaultDataset.layer}.${defaultDataset.name};`)}
                  className="text-left px-3 py-2 bg-white border border-gray-200 rounded hover:bg-gray-50"
                >
                  Statistical summary
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
