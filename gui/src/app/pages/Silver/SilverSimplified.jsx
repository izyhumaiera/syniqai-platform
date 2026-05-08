import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Play, Database, CheckCircle, XCircle, Clock, AlertTriangle,
  RefreshCw, Filter, Search, Code, Zap, Package
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

/**
 * Simplified Silver Layer UI
 * Focus: Basic transformation, Quality rules, Incremental, SQL, Iceberg, Benchmarking
 */
const SilverSimplified = () => {
  // ===== Core State =====
  const [bronzeTables, setBronzeTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  
  // Transformation settings
  const [executionMode, setExecutionMode] = useState('full'); // 'full' | 'incremental'
  const [watermarkColumn, setWatermarkColumn] = useState('');
  const [customSQL, setCustomSQL] = useState('');
  
  // Quality rules
  const [selectedRules, setSelectedRules] = useState([]);
  
  // Iceberg & Performance
  const [snapshotHistory, setSnapshotHistory] = useState([]);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  
  // Job tracking & logs
  const [currentJobId, setCurrentJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [transformationLogs, setTransformationLogs] = useState([]);
  
  const pollIntervalRef = useRef(null);

  // ===== QUALITY RULES CATALOG =====
  const QUALITY_RULES_CATALOG = [
    // Completeness Rules
    { 
      id: 'not_null', 
      name: 'Not Null', 
      category: 'Completeness',
      description: 'Field must not be null',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'not_empty', 
      name: 'Not Empty', 
      category: 'Completeness',
      description: 'String must not be empty',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'required_fields', 
      name: 'Required Fields', 
      category: 'Completeness',
      description: 'Multiple fields must be present',
      params: ['columns'],
      enabled: true
    },
    
    // Validity Rules
    { 
      id: 'email_format', 
      name: 'Email Format', 
      category: 'Validity',
      description: 'Valid email address format',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'phone_format', 
      name: 'Phone Format', 
      category: 'Validity',
      description: 'Valid phone number format',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'date_format', 
      name: 'Date Format', 
      category: 'Validity',
      description: 'Valid date format (YYYY-MM-DD)',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'data_type', 
      name: 'Data Type', 
      category: 'Validity',
      description: 'Value matches expected data type',
      params: ['column', 'expected_type'],
      enabled: true
    },
    { 
      id: 'regex_pattern', 
      name: 'Regex Pattern', 
      category: 'Validity',
      description: 'Matches custom regex pattern',
      params: ['column', 'pattern'],
      enabled: true
    },
    
    // Range Rules
    { 
      id: 'numeric_range', 
      name: 'Numeric Range', 
      category: 'Range',
      description: 'Number within min/max range',
      params: ['column', 'min', 'max'],
      enabled: true
    },
    { 
      id: 'positive_value', 
      name: 'Positive Value', 
      category: 'Range',
      description: 'Value must be positive',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'length_check', 
      name: 'Length Check', 
      category: 'Range',
      description: 'String length within range',
      params: ['column', 'min_length', 'max_length'],
      enabled: true
    },
    
    // Consistency Rules
    { 
      id: 'unique_values', 
      name: 'Unique Values', 
      category: 'Consistency',
      description: 'Column values must be unique',
      params: ['column'],
      enabled: true
    },
    { 
      id: 'referential_integrity', 
      name: 'Referential Integrity', 
      category: 'Consistency',
      description: 'Foreign key relationship valid',
      params: ['column', 'ref_table', 'ref_column'],
      enabled: true
    },
    { 
      id: 'consistent_case', 
      name: 'Consistent Case', 
      category: 'Consistency',
      description: 'Text in consistent case (upper/lower)',
      params: ['column', 'case_type'],
      enabled: true
    },
    
    // Accuracy Rules
    { 
      id: 'value_in_list', 
      name: 'Value in List', 
      category: 'Accuracy',
      description: 'Value must be from allowed list',
      params: ['column', 'allowed_values'],
      enabled: true
    },
    { 
      id: 'threshold_check', 
      name: 'Threshold Check', 
      category: 'Accuracy',
      description: 'Value meets threshold',
      params: ['column', 'operator', 'threshold'],
      enabled: true
    },
    
    // Timeliness Rules
    { 
      id: 'recent_date', 
      name: 'Recent Date', 
      category: 'Timeliness',
      description: 'Date within recent timeframe',
      params: ['column', 'days'],
      enabled: true
    },
    { 
      id: 'future_date_check', 
      name: 'Future Date Check', 
      category: 'Timeliness',
      description: 'Date not in future',
      params: ['column'],
      enabled: true
    }
  ];

  // ===== Effects =====
  useEffect(() => {
    loadBronzeTables();
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // ===== API Functions =====
  const loadBronzeTables = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/bronze/tables`);
      setBronzeTables(response.data || []);
    } catch (error) {
      console.error('[Silver] Failed to load Bronze tables:', error);
      addLog('error', 'Failed to load Bronze tables: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedTable) {
      addLog('error', 'Please select a Bronze table');
      return;
    }

    try {
      setExecuting(true);
      addLog('info', `Starting Spark transformation for ${selectedTable.table_name}...`);
      
      // Prepare quality rules
      const rules = selectedRules.map(ruleId => {
        const ruleDef = QUALITY_RULES_CATALOG.find(r => r.id === ruleId);
        return {
          rule_type: ruleId,
          columns: ruleDef.params.includes('column') ? ['*'] : [],
          threshold: 0.95,
          params: {}
        };
      });

      // Build request for Spark endpoint
      const requestBody = {
        source: selectedTable.source || 'finance',
        entity: selectedTable.table_name,
        domain: selectedTable.domain || 'finance',
        execution_mode: executionMode,
        use_spark: true,
        watermark_column: executionMode === 'incremental' ? watermarkColumn : null,
        rules: rules,
        custom_sql: customSQL || null
      };

      console.log('[Silver] Request body:', requestBody);

      const response = await axios.post(
        `${API_BASE}/silver/process-spark`,
        requestBody,
        { headers: { 'Content-Type': 'application/json' } }
      );

      setCurrentJobId(response.data.job_id);
      addLog('success', `Job ${response.data.job_id} queued`);
      
      // Start polling
      pollJobStatus(response.data.job_id);

    } catch (error) {
      console.error('[Silver] Execute failed:', error);
      addLog('error', `Failed to start transformation: ${error.message}`);
      setExecuting(false);
    }
  };

  const pollJobStatus = (jobId) => {
    const startTime = Date.now();
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/silver/jobs/${jobId}`);
        const job = response.data;
        
        setJobStatus(job);
        
        if (job.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          const duration = ((Date.now() - startTime) / 1000).toFixed(2);
          setPerformanceMetrics({
            duration: duration,
            row_count: job.row_count,
            quality_score: job.quality_score
          });
          addLog('success', `✅ Transformation completed in ${duration}s - ${job.row_count} rows`);
          setExecuting(false);
          
          // Load Iceberg snapshots
          if (selectedTable) {
            loadSnapshotHistory(selectedTable.source, selectedTable.table_name);
          }
        } else if (job.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          addLog('error', `❌ Transformation failed: ${job.error_message || 'Unknown error'}`);
          setExecuting(false);
        } else if (job.status === 'running') {
          addLog('info', `⚡ Processing... ${job.progress || 0}%`);
        }
      } catch (error) {
        console.error('[Silver] Poll failed:', error);
      }
    }, 2000);
  };

  const loadSnapshotHistory = async (source, entity) => {
    try {
      const response = await axios.get(
        `${API_BASE}/silver/iceberg-table/${source}/${entity}/history`
      );
      setSnapshotHistory(response.data.snapshots || []);
    } catch (error) {
      console.error('[Silver] Failed to load snapshot history:', error);
    }
  };

  const addLog = (level, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setTransformationLogs(prev => [
      { timestamp, level, message },
      ...prev.slice(0, 99) // Keep last 100 logs
    ]);
  };

  const toggleRule = (ruleId) => {
    setSelectedRules(prev => 
      prev.includes(ruleId) 
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  const selectAllRulesInCategory = (category) => {
    const rulesInCategory = QUALITY_RULES_CATALOG
      .filter(r => r.category === category)
      .map(r => r.id);
    
    const allSelected = rulesInCategory.every(id => selectedRules.includes(id));
    
    if (allSelected) {
      // Deselect all in category
      setSelectedRules(prev => prev.filter(id => !rulesInCategory.includes(id)));
    } else {
      // Select all in category
      setSelectedRules(prev => [...new Set([...prev, ...rulesInCategory])]);
    }
  };

  // ===== Render =====
  const categories = [...new Set(QUALITY_RULES_CATALOG.map(r => r.category))];

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Zap className="w-6 h-6 text-yellow-500" />
              Silver Layer - Spark + Iceberg
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Data quality transformation with distributed processing
            </p>
          </div>
          <button
            onClick={loadBronzeTables}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Tables
          </button>
        </div>
      </div>

      {/* Main Layout: 3 Columns */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* LEFT: Table Selection + Quality Rules */}
        <div className="w-1/4 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
          {/* Table Selection */}
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Database className="w-4 h-4" />
              Bronze Tables ({bronzeTables.length})
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {bronzeTables.map((table, idx) => (
                <div
                  key={idx}
                  onClick={() => setSelectedTable(table)}
                  className={`p-3 rounded cursor-pointer transition-colors ${
                    selectedTable?.table_name === table.table_name
                      ? 'bg-blue-50 border-2 border-blue-500'
                      : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <div className="font-medium text-sm text-gray-900">
                    {table.table_name}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {table.source} • {table.row_count?.toLocaleString() || '0'} rows
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quality Rules */}
          <div className="flex-1 overflow-hidden flex flex-col p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Filter className="w-4 h-4" />
              Quality Rules ({selectedRules.length} selected)
            </h3>
            
            <div className="flex-1 overflow-y-auto space-y-4">
              {categories.map(category => {
                const rulesInCategory = QUALITY_RULES_CATALOG.filter(r => r.category === category);
                const selectedInCategory = rulesInCategory.filter(r => selectedRules.includes(r.id)).length;
                
                return (
                  <div key={category} className="border border-gray-200 rounded-lg">
                    {/* Category Header */}
                    <div 
                      onClick={() => selectAllRulesInCategory(category)}
                      className="bg-gray-50 px-3 py-2 cursor-pointer hover:bg-gray-100 flex justify-between items-center rounded-t-lg"
                    >
                      <span className="font-medium text-sm text-gray-900">{category}</span>
                      <span className="text-xs text-gray-600">
                        {selectedInCategory}/{rulesInCategory.length}
                      </span>
                    </div>
                    
                    {/* Rules in Category */}
                    <div className="p-2 space-y-1">
                      {rulesInCategory.map(rule => (
                        <div
                          key={rule.id}
                          onClick={() => toggleRule(rule.id)}
                          className={`p-2 rounded cursor-pointer transition-colors ${
                            selectedRules.includes(rule.id)
                              ? 'bg-blue-50 border border-blue-300'
                              : 'bg-white border border-gray-200 hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              checked={selectedRules.includes(rule.id)}
                              onChange={() => {}}
                              className="mt-1"
                            />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900">
                                {rule.name}
                              </div>
                              <div className="text-xs text-gray-600 mt-1">
                                {rule.description}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* CENTER: Configuration + SQL Editor */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          {/* Configuration Panel */}
          <div className="p-6 border-b border-gray-200 space-y-4">
            <h3 className="font-semibold text-gray-900 mb-4">Transformation Configuration</h3>
            
            {/* Execution Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Execution Mode
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="full"
                    checked={executionMode === 'full'}
                    onChange={(e) => setExecutionMode(e.target.value)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-gray-900">Full Load</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="incremental"
                    checked={executionMode === 'incremental'}
                    onChange={(e) => setExecutionMode(e.target.value)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-gray-900">Incremental</span>
                </label>
              </div>
            </div>

            {/* Watermark Column (for incremental) */}
            {executionMode === 'incremental' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Watermark Column
                </label>
                <input
                  type="text"
                  value={watermarkColumn}
                  onChange={(e) => setWatermarkColumn(e.target.value)}
                  placeholder="e.g., updated_at, created_at"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Performance Metrics (if available) */}
            {performanceMetrics && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-semibold text-green-900 mb-2">Last Execution</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-green-700">Duration</div>
                    <div className="font-bold text-green-900">{performanceMetrics.duration}s</div>
                  </div>
                  <div>
                    <div className="text-green-700">Rows Processed</div>
                    <div className="font-bold text-green-900">{performanceMetrics.row_count?.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-green-700">Quality Score</div>
                    <div className="font-bold text-green-900">{(performanceMetrics.quality_score * 100).toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            )}

            {/* Execute Button */}
            <button
              onClick={handleExecute}
              disabled={!selectedTable || executing}
              className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {executing ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Execute Transformation
                </>
              )}
            </button>

            {/* Job Status */}
            {jobStatus && (
              <div className={`p-3 rounded-lg border ${
                jobStatus.status === 'completed' ? 'bg-green-50 border-green-200' :
                jobStatus.status === 'failed' ? 'bg-red-50 border-red-200' :
                jobStatus.status === 'running' ? 'bg-blue-50 border-blue-200' :
                'bg-gray-50 border-gray-200'
              }`}>
                <div className="text-sm font-medium">
                  Status: {jobStatus.status} {jobStatus.progress ? `(${jobStatus.progress}%)` : ''}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  {jobStatus.message}
                </div>
              </div>
            )}
          </div>

          {/* SQL Editor */}
          <div className="flex-1 flex flex-col p-6 overflow-hidden">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Code className="w-4 h-4" />
              Custom SQL Transformation (Optional)
            </h3>
            <textarea
              value={customSQL}
              onChange={(e) => setCustomSQL(e.target.value)}
              placeholder="-- Write custom SQL for advanced transformations&#10;-- Example:&#10;SELECT *, &#10;  CASE WHEN amount > 1000 THEN 'HIGH' ELSE 'NORMAL' END as risk_level&#10;FROM {table}"
              className="flex-1 w-full p-4 font-mono text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none"
            />
            <div className="text-xs text-gray-500 mt-2">
              Use <code className="bg-gray-100 px-1 py-0.5 rounded">{'{table}'}</code> as placeholder for the source table name
            </div>
          </div>
        </div>

        {/* RIGHT: Logs + Iceberg Snapshots */}
        <div className="w-1/3 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
          {/* Transformation Logs */}
          <div className="flex-1 flex flex-col overflow-hidden p-4">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Package className="w-4 h-4" />
              Transformation Backlog ({transformationLogs.length})
            </h3>
            <div className="flex-1 overflow-y-auto space-y-2 bg-gray-50 rounded-lg p-3">
              {transformationLogs.length === 0 ? (
                <div className="text-sm text-gray-500 text-center py-8">
                  No logs yet. Execute a transformation to see logs here.
                </div>
              ) : (
                transformationLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`p-2 rounded text-sm font-mono ${
                      log.level === 'error' ? 'bg-red-50 text-red-900 border border-red-200' :
                      log.level === 'success' ? 'bg-green-50 text-green-900 border border-green-200' :
                      'bg-blue-50 text-blue-900 border border-blue-200'
                    }`}
                  >
                    <div className="mb-1">
                      <span className="text-gray-500">[{log.timestamp}]</span>
                    </div>
                    <div className="whitespace-pre-wrap break-words">
                      {log.message}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Iceberg Snapshots */}
          <div className="flex-1 flex flex-col overflow-hidden p-4 border-t border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Iceberg Snapshots ({snapshotHistory.length})
            </h3>
            <div className="flex-1 overflow-y-auto space-y-2">
              {snapshotHistory.length === 0 ? (
                <div className="text-sm text-gray-500 text-center py-4">
                  No snapshots yet. Complete a transformation to see snapshot history.
                </div>
              ) : (
                snapshotHistory.map((snapshot, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="text-xs text-gray-600">
                      {new Date(snapshot.committed_at).toLocaleString()}
                    </div>
                    <div className="text-sm font-medium text-gray-900 mt-1">
                      Snapshot {snapshot.snapshot_id}
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {snapshot.summary?.['total-records']} records
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SilverSimplified;
