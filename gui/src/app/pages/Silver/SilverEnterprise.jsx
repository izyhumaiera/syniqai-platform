import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Play, Database, CheckCircle, XCircle, Clock, AlertTriangle,
  RefreshCw, Filter, Search, Code, Zap, Package, ChevronDown, ChevronUp,
  Info, TrendingUp, Server, Cpu, HardDrive, Activity, Shield, Target,
  BarChart3, GitBranch, Box, Layers, FileText, Eye, AlertCircle, X,
  ArrowUp, ArrowDown, ArrowLeft, Calendar, FileType, HelpCircle
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Help tooltip component
const HelpTooltip = ({ title, children }) => {
  const [show, setShow] = useState(false);
  
  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="ml-2 text-gray-400 hover:text-gray-600 transition-colors"
      >
        <HelpCircle size={16} />
      </button>
      {show && (
        <div className="absolute z-50 w-64 p-3 bg-gray-900 text-white text-sm rounded-lg shadow-lg -top-2 left-6">
          {title && <div className="font-semibold mb-1">{title}</div>}
          <div className="text-gray-200">{children}</div>
          <div className="absolute top-3 -left-1 w-2 h-2 bg-gray-900 transform rotate-45"></div>
        </div>
      )}
    </div>
  );
};

// Source type configuration
const SOURCE_CONFIG = {
  postgres: { 
    icon: Database, 
    color: 'blue', 
    label: 'PostgreSQL',
  },
  mariadb: { 
    icon: Database, 
    color: 'orange', 
    label: 'MariaDB',
  },
  mariadb_cloud: { 
    icon: Database, 
    color: 'orange', 
    label: 'MariaDB Cloud',
  },
  s3: { 
    icon: Layers, 
    color: 'purple', 
    label: 'Amazon S3',
  },
  mongodb: { 
    icon: FileText, 
    color: 'green', 
    label: 'MongoDB',
  }
};

/**
 * Enterprise Silver Layer Control Tower
 * Governed transformation engine powered by Spark + Iceberg
 */
const SilverEnterprise = () => {
  // ===== Tab State =====
  const [activeTab, setActiveTab] = useState('tables'); // 'tables' | 'transformation'
  
  // ===== Tables View State (Tab 1) =====
  const [silverTables, setSilverTables] = useState([]);
  const [selectedSilverTable, setSelectedSilverTable] = useState(null);
  const [tablesLoading, setTablesLoading] = useState(true);
  const [tablesError, setTablesError] = useState(null);
  
  // Search and filters for tables view
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [formatFilter, setFormatFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('all');
  const [sortBy, setSortBy] = useState('last_modified');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showFilters, setShowFilters] = useState(false);
  
  // Pagination for tables view
  const [listPage, setListPage] = useState(1);
  const [listPageSize, setListPageSize] = useState(50);
  const [listTotalPages, setListTotalPages] = useState(1);
  const [listTotalCount, setListTotalCount] = useState(0);
  
  // ===== Core State (Tab 2 - Transformation) =====
  const [bronzeTables, setBronzeTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tablePreview, setTablePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Transformation settings
  const [executionMode, setExecutionMode] = useState('full');
  const [watermarkColumn, setWatermarkColumn] = useState('');
  const [customSQL, setCustomSQL] = useState('');
  const [qualityMode, setQualityMode] = useState('strict'); // 'strict' | 'lenient'
  
  // Quality rules
  const [selectedRules, setSelectedRules] = useState([]);
  const [expandedCategories, setExpandedCategories] = useState(new Set(['Completeness']));
  
  // Iceberg & Performance
  const [snapshotHistory, setSnapshotHistory] = useState([]);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [sparkResources, setSparkResources] = useState({
    executors: 4,
    cores_per_executor: 4,
    memory_per_executor: '4GB',
    estimated_runtime: null
  });
  
  // Job tracking & logs
  const [currentJobId, setCurrentJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [transformationLogs, setTransformationLogs] = useState([]);
  const [executionProgress, setExecutionProgress] = useState(null);
  const [logFilter, setLogFilter] = useState('all'); // 'all' | 'info' | 'error' | 'success'
  const [autoScroll, setAutoScroll] = useState(true);
  
  // UI State
  const [summaryExpanded, setSummaryExpanded] = useState(true);
  const [showSQLEditor, setShowSQLEditor] = useState(false);
  
  const pollIntervalRef = useRef(null);
  const logsEndRef = useRef(null);

  // ===== QUALITY RULES CATALOG (Enhanced with Severity) =====
  const QUALITY_RULES_CATALOG = [
    // Completeness Rules
    { 
      id: 'not_null', 
      name: 'Not Null', 
      category: 'Completeness',
      severity: 'high',
      description: 'Field must not be null',
      params: ['column'],
      estimatedImpact: '5-10% quarantine',
      enabled: true
    },
    { 
      id: 'not_empty', 
      name: 'Not Empty', 
      category: 'Completeness',
      severity: 'high',
      description: 'String must not be empty',
      params: ['column'],
      estimatedImpact: '2-5% quarantine',
      enabled: true
    },
    { 
      id: 'required_fields', 
      name: 'Required Fields', 
      category: 'Completeness',
      severity: 'critical',
      description: 'Multiple fields must be present',
      params: ['columns'],
      estimatedImpact: '10-15% quarantine',
      enabled: true
    },
    
    // Validity Rules
    { 
      id: 'email_format', 
      name: 'Email Format', 
      category: 'Validity',
      severity: 'medium',
      description: 'Valid email address format',
      params: ['column'],
      estimatedImpact: '1-3% quarantine',
      enabled: true
    },
    { 
      id: 'phone_format', 
      name: 'Phone Format', 
      category: 'Validity',
      severity: 'medium',
      description: 'Valid phone number format',
      params: ['column'],
      estimatedImpact: '2-5% quarantine',
      enabled: true
    },
    { 
      id: 'date_format', 
      name: 'Date Format', 
      category: 'Validity',
      severity: 'high',
      description: 'Valid date format (YYYY-MM-DD)',
      params: ['column'],
      estimatedImpact: '1-2% quarantine',
      enabled: true
    },
    { 
      id: 'data_type', 
      name: 'Data Type', 
      category: 'Validity',
      severity: 'high',
      description: 'Value matches expected data type',
      params: ['column', 'expected_type'],
      estimatedImpact: '3-8% quarantine',
      enabled: true
    },
    { 
      id: 'regex_pattern', 
      name: 'Regex Pattern', 
      category: 'Validity',
      severity: 'medium',
      description: 'Matches custom regex pattern',
      params: ['column', 'pattern'],
      estimatedImpact: 'Variable',
      enabled: true
    },
    
    // Range Rules
    { 
      id: 'numeric_range', 
      name: 'Numeric Range', 
      category: 'Range',
      severity: 'medium',
      description: 'Number within min/max range',
      params: ['column', 'min', 'max'],
      estimatedImpact: '2-5% quarantine',
      enabled: true
    },
    { 
      id: 'positive_value', 
      name: 'Positive Value', 
      category: 'Range',
      severity: 'medium',
      description: 'Value must be positive',
      params: ['column'],
      estimatedImpact: '1-3% quarantine',
      enabled: true
    },
    { 
      id: 'length_check', 
      name: 'Length Check', 
      category: 'Range',
      severity: 'low',
      description: 'String length within range',
      params: ['column', 'min_length', 'max_length'],
      estimatedImpact: '<1% quarantine',
      enabled: true
    },
    
    // Consistency Rules
    { 
      id: 'unique_values', 
      name: 'Unique Values', 
      category: 'Consistency',
      severity: 'critical',
      description: 'Column values must be unique',
      params: ['column'],
      estimatedImpact: '5-15% quarantine',
      enabled: true
    },
    { 
      id: 'referential_integrity', 
      name: 'Referential Integrity', 
      category: 'Consistency',
      severity: 'high',
      description: 'Foreign key relationship valid',
      params: ['column', 'ref_table', 'ref_column'],
      estimatedImpact: '3-10% quarantine',
      enabled: true
    },
    { 
      id: 'consistent_case', 
      name: 'Consistent Case', 
      category: 'Consistency',
      severity: 'low',
      description: 'Text in consistent case (upper/lower)',
      params: ['column', 'case_type'],
      estimatedImpact: '<1% quarantine',
      enabled: true
    },
    
    // Accuracy Rules
    { 
      id: 'value_in_list', 
      name: 'Value in List', 
      category: 'Accuracy',
      severity: 'high',
      description: 'Value must be from allowed list',
      params: ['column', 'allowed_values'],
      estimatedImpact: '2-8% quarantine',
      enabled: true
    },
    { 
      id: 'threshold_check', 
      name: 'Threshold Check', 
      category: 'Accuracy',
      severity: 'medium',
      description: 'Value meets threshold',
      params: ['column', 'operator', 'threshold'],
      estimatedImpact: '1-5% quarantine',
      enabled: true
    },
    
    // Timeliness Rules
    { 
      id: 'recent_date', 
      name: 'Recent Date', 
      category: 'Timeliness',
      severity: 'medium',
      description: 'Date within recent timeframe',
      params: ['column', 'days'],
      estimatedImpact: '1-3% quarantine',
      enabled: true
    },
    { 
      id: 'future_date_check', 
      name: 'Future Date Check', 
      category: 'Timeliness',
      severity: 'high',
      description: 'Date not in future',
      params: ['column'],
      estimatedImpact: '<1% quarantine',
      enabled: true
    }
  ];

  // ===== Effects =====
  useEffect(() => {
    if (activeTab === 'tables') {
      loadSilverTables();
    } else {
      loadBronzeTables();
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [activeTab, searchQuery, sourceFilter, formatFilter, dateFilter, sortBy, sortOrder, listPage, listPageSize]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transformationLogs, autoScroll]);

  // ===== Utility Functions =====
  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  const getQualityBadge = (score) => {
    if (!score && score !== 0) return { text: 'N/A', className: 'bg-gray-100 text-gray-600' };
    if (score >= 95) return { text: `${score}%`, className: 'bg-green-100 text-green-800' };
    if (score >= 80) return { text: `${score}%`, className: 'bg-yellow-100 text-yellow-800' };
    return { text: `${score}%`, className: 'bg-red-100 text-red-800' };
  };

  const getTimeSince = (dateStr) => {
    if (!dateStr) return 'Unknown';
    const now = new Date();
    const past = new Date(dateStr);
    const seconds = Math.floor((now - past) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 86400)}d ago`;
    return past.toLocaleDateString();
  };

  // ===== API Functions =====
  const loadSilverTables = async () => {
    try {
      setTablesLoading(true);
      setTablesError(null);
      
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (sourceFilter) params.append('source_type', sourceFilter);
      if (formatFilter) params.append('format', formatFilter);
      if (dateFilter !== 'all') params.append('date_filter', dateFilter);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      params.append('page', listPage);
      params.append('page_size', listPageSize);
      
      const response = await axios.get(`${API_BASE}/silver/tables?${params}`);
      
      setSilverTables(response.data.tables || []);
      setListTotalCount(response.data.total || 0);
      setListTotalPages(Math.ceil((response.data.total || 0) / listPageSize));
      
      addLog('info', `Loaded ${response.data.tables?.length || 0} Silver tables`);
    } catch (error) {
      console.error('[Silver] Failed to load tables:', error);
      setTablesError('Failed to load Silver tables: ' + error.message);
      addLog('error', 'Failed to load Silver tables: ' + error.message);
      // Set mock data for demo
      setSilverTables([
        { 
          table_name: 'user_credit_card_transaction_cleaned',
          source: 'finance',
          source_type: 'postgres',
          format: 'iceberg',
          row_count: 2340567,
          total_size: 95678234,
          quality_score: 98,
          is_partitioned: true,
          last_modified: new Date(Date.now() - 1800000).toISOString()
        },
        {
          table_name: 'customer_profile_validated',
          source: 'crm',
          source_type: 'postgres',
          format: 'iceberg',
          row_count: 427500,
          total_size: 43218976,
          quality_score: 95,
          is_partitioned: false,
          last_modified: new Date(Date.now() - 82800000).toISOString()
        }
      ]);
      setListTotalCount(2);
      setListTotalPages(1);
    } finally {
      setTablesLoading(false);
    }
  };

  const loadBronzeTables = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/bronze/tables`);
      setBronzeTables(response.data || []);
      addLog('info', `Loaded ${response.data?.length || 0} Bronze tables`);
    } catch (error) {
      console.error('[Silver] Failed to load Bronze tables:', error);
      addLog('error', 'Failed to load Bronze tables: ' + error.message);
      // Set dummy data for demo
      setBronzeTables([
        { table_name: 'user_credit_card_transaction', source: 'finance', row_count: 2456789, size_mb: 100.5 },
        { table_name: 'customer_profile', source: 'crm', row_count: 450000, size_mb: 45.2 }
      ]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setListPage(1);
  };
  
  const handleSearch = (value) => {
    setSearchQuery(value);
    setListPage(1);
  };
  
  const clearFilters = () => {
    setSearchQuery('');
    setSourceFilter('');
    setFormatFilter('');
    setDateFilter('all');
    setListPage(1);
  };

  const loadTablePreview = async (table) => {
    try {
      setPreviewLoading(true);
      // API call to get preview (100 rows)
      // const response = await axios.get(`${API_BASE}/bronze/preview/${table.source}/${table.table_name}?limit=100`);
      // setTablePreview(response.data);
      
      // Mock preview for now
      setTablePreview({
        columns: ['transaction_id', 'user_id', 'amount', 'transaction_date', 'status'],
        sample_rows: 100,
        total_rows: table.row_count
      });
    } catch (error) {
      console.error('[Silver] Failed to load preview:', error);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleTableSelect = (table) => {
    setSelectedTable(table);
    loadTablePreview(table);
    if (table.source && table.table_name) {
      loadSnapshotHistory(table.source, table.table_name);
    }
    addLog('info', `Selected table: ${table.table_name} (${table.row_count?.toLocaleString()} rows)`);
    
    // Estimate runtime
    if (table.row_count) {
      const estimatedSec = Math.ceil(table.row_count / 50000); // ~50k rows/sec
      setSparkResources(prev => ({
        ...prev,
        estimated_runtime: `~${estimatedSec}s`
      }));
    }
  };

  const handleExecute = async () => {
    if (!selectedTable) {
      addLog('error', 'Please select a Bronze table');
      return;
    }

    try {
      setExecuting(true);
      setExecutionProgress({
        step: 1,
        total: 5,
        message: 'Initializing Spark session...'
      });
      addLog('info', `🚀 Starting transformation: ${selectedTable.table_name}`);
      
      // Prepare quality rules
      const rules = selectedRules.map(ruleId => {
        const ruleDef = QUALITY_RULES_CATALOG.find(r => r.id === ruleId);
        return {
          rule_type: ruleId,
          columns: ruleDef.params.includes('column') ? ['*'] : [],
          threshold: qualityMode === 'strict' ? 1.0 : 0.95,
          params: {}
        };
      });

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

      setExecutionProgress({
        step: 2,
        total: 5,
        message: 'Submitting job to Spark cluster...'
      });

      const response = await axios.post(
        `${API_BASE}/silver/process-spark`,
        requestBody,
        { headers: { 'Content-Type': 'application/json' } }
      );

      setCurrentJobId(response.data.job_id);
      addLog('success', `✅ Job queued: ${response.data.job_id}`);
      
      setExecutionProgress({
        step: 3,
        total: 5,
        message: 'Reading Bronze data...'
      });

      pollJobStatus(response.data.job_id);

    } catch (error) {
      console.error('[Silver] Execute failed:', error);
      addLog('error', `❌ Failed to start: ${error.message}`);
      setExecuting(false);
      setExecutionProgress(null);
    }
  };

  const pollJobStatus = (jobId) => {
    const startTime = Date.now();
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`${API_BASE}/silver/jobs/${jobId}`);
        const job = response.data;
        
        setJobStatus(job);
        
        // Update execution progress
        if (job.status === 'running') {
          const progress = job.progress || 0;
          let step = 3;
          let message = 'Processing data...';
          
          if (progress < 20) {
            step = 3;
            message = 'Reading Bronze data...';
          } else if (progress < 50) {
            step = 3;
            message = 'Applying quality rules...';
          } else if (progress < 80) {
            step = 4;
            message = 'Writing to Silver layer...';
          } else {
            step = 5;
            message = 'Finalizing Iceberg snapshot...';
          }
          
          setExecutionProgress({ step, total: 5, message, progress });
        }
        
        if (job.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          const duration = ((Date.now() - startTime) / 1000).toFixed(2);
          
          setExecutionProgress({
            step: 5,
            total: 5,
            message: 'Transformation completed',
            progress: 100
          });
          
          setPerformanceMetrics({
            duration: duration,
            row_count: job.row_count,
            quality_score: job.quality_score,
            records_per_sec: Math.floor(job.row_count / duration),
            quarantine_count: Math.floor(job.row_count * (1 - (job.quality_score || 1))),
            quarantine_pct: ((1 - (job.quality_score || 1)) * 100).toFixed(2)
          });
          
          addLog('success', `✅ Complete! ${job.row_count?.toLocaleString()} rows in ${duration}s (${Math.floor(job.row_count / duration)} rows/sec)`);
          setExecuting(false);
          
          // Load updated snapshots
          if (selectedTable) {
            setTimeout(() => loadSnapshotHistory(selectedTable.source, selectedTable.table_name), 1000);
          }
        } else if (job.status === 'failed') {
          clearInterval(pollIntervalRef.current);
          addLog('error', `❌ Failed: ${job.error_message || 'Unknown error'}`);
          setExecuting(false);
          setExecutionProgress(null);
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
      console.error('[Silver] Failed to load snapshots:', error);
      // Mock snapshot for demo
      setSnapshotHistory([
        {
          snapshot_id: 1234567890,
          committed_at: new Date().toISOString(),
          summary: { 'total-records': '2456789' },
          operation: 'append'
        }
      ]);
    }
  };

  const addLog = (level, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setTransformationLogs(prev => [
      { timestamp, level, message, id: Date.now() },
      ...prev.slice(0, 99)
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
      setSelectedRules(prev => prev.filter(id => !rulesInCategory.includes(id)));
    } else {
      setSelectedRules(prev => [...new Set([...prev, ...rulesInCategory])]);
    }
  };

  const toggleCategory = (category) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-300';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-300';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-300';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-300';
      default: return 'text-gray-600 bg-gray-50 border-gray-300';
    }
  };

  const getLogIcon = (level) => {
    switch(level) {
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'info': return <Info className="w-4 h-4 text-blue-500" />;
      default: return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  const filteredLogs = transformationLogs.filter(log => 
    logFilter === 'all' || log.level === logFilter
  );

  const categories = [...new Set(QUALITY_RULES_CATALOG.map(r => r.category))];
  
  const canExecute = selectedTable && !executing;
  const tooltipMessage = !selectedTable 
    ? 'No Bronze table selected' 
    : executing 
    ? 'Transformation in progress' 
    : 'Execute transformation';

  // Calculate transformation summary
  const transformationSummary = selectedTable ? {
    source_table: `bronze.${selectedTable.source}.${selectedTable.table_name}`,
    target_table: `silver.${selectedTable.source}.${selectedTable.table_name}_cleaned`,
    mode: executionMode === 'incremental' ? `Incremental (Watermark: ${watermarkColumn || 'N/A'})` : 'Full Load',
    rules_active: selectedRules.length,
    expected_output: selectedTable.row_count ? `~${(selectedTable.row_count * 0.95).toLocaleString(0)} rows` : 'Unknown',
    partitioned_by: 'transaction_date',
    estimated_runtime: sparkResources.estimated_runtime || 'Calculating...'
  } : null;

  // ===== Render =====
  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header - Industrial Design */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b-4 border-blue-500 shadow-2xl">
        <div className="px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-black text-white flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-lg shadow-lg">
                  <Zap className="w-8 h-8 text-white" />
                </div>
                Silver Layer Control Tower
              </h1>
              <p className="text-blue-200 mt-2 text-sm font-medium flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Governed transformation engine powered by Spark + Iceberg
                <span className="mx-2">•</span>
                Versioned, auditable, distributed processing
              </p>
            </div>
            
            {/* System Health Indicators */}
            <div className="flex items-center gap-4">
              <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
                <div className="flex items-center gap-2 text-green-400 text-sm font-semibold">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  Spark Cluster Online
                </div>
              </div>
              
              <button
                onClick={loadBronzeTables}
                disabled={loading}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 font-semibold shadow-lg transition-all hover:shadow-xl"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        
        {/* ===== TRANSFORMATION SUMMARY PANEL ===== */}
        <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200">
          <div 
            className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-slate-50 transition-colors"
            onClick={() => setSummaryExpanded(!summaryExpanded)}
          >
            <div className="flex items-center gap-3">
              <Target className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-bold text-slate-900">Transformation Summary</h2>
              {transformationSummary && (
                <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">
                  CONFIGURED
                </span>
              )}
            </div>
            {summaryExpanded ? <ChevronUp className="w-5 h-5 text-slate-600" /> : <ChevronDown className="w-5 h-5 text-slate-600" />}
          </div>
          
          {summaryExpanded && (
            <div className="px-6 pb-6 border-t border-slate-200">
              {transformationSummary ? (
                <div className="grid grid-cols-2 gap-6 mt-4">
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <Database className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Source Table</div>
                        <div className="text-sm font-mono font-bold text-slate-900 mt-1">{transformationSummary.source_table}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <Box className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Target Table</div>
                        <div className="text-sm font-mono font-bold text-green-700 mt-1">{transformationSummary.target_table}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <Activity className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Execution Mode</div>
                        <div className="text-sm font-semibold text-slate-900 mt-1">{transformationSummary.mode}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <Shield className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Quality Rules Active</div>
                        <div className="text-sm font-bold text-blue-700 mt-1">
                          {transformationSummary.rules_active} rules / {qualityMode === 'strict' ? 'STRICT' : 'LENIENT'} mode
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <TrendingUp className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Expected Output</div>
                        <div className="text-sm font-semibold text-slate-900 mt-1">{transformationSummary.expected_output}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-start gap-3">
                      <Clock className="w-5 h-5 text-slate-600 mt-0.5" />
                      <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Estimated Runtime</div>
                        <div className="text-sm font-semibold text-amber-600 mt-1">{transformationSummary.estimated_runtime}</div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-4 text-center py-8">
                  <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500 font-medium">Select a Bronze table to configure transformation</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ===== MAIN CONFIGURATION AREA ===== */}
        <div className="grid grid-cols-2 gap-6">
          
          {/* LEFT: Quality Rules + Table Selection */}
          <div className="space-y-6">
            
            {/* Bronze Table Selector */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200 p-6">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2 text-lg">
                <Database className="w-5 h-5 text-blue-600" />
                Select Bronze Table
              </h3>
              
              <select
                value={selectedTable?.table_name || ''}
                onChange={(e) => {
                  const table = bronzeTables.find(t => t.table_name === e.target.value);
                  if (table) handleTableSelect(table);
                }}
                className="w-full px-4 py-3 border-2 border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-semibold text-slate-900 bg-slate-50"
              >
                <option value="">-- Select a table --</option>
                {bronzeTables.map((table, idx) => (
                  <option key={idx} value={table.table_name}>
                    {table.table_name} ({table.row_count?.toLocaleString()} rows, {table.size_mb?.toFixed(1)} MB)
                  </option>
                ))}
              </select>
              
              {selectedTable && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-blue-900">Table Preview Available</span>
                    <button
                      onClick={() => loadTablePreview(selectedTable)}
                      disabled={previewLoading}
                      className="text-xs px-3 py-1 bg-blue-600 text-white rounded font-semibold hover:bg-blue-700 flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" />
                      {previewLoading ? 'Loading...' : 'View 100 Rows'}
                    </button>
                  </div>
                  
                  {tablePreview && (
                    <div className="text-xs text-blue-700 mt-2">
                      <div>Columns: {tablePreview.columns?.join(', ')}</div>
                      <div className="mt-1">Sample: {tablePreview.sample_rows} / {tablePreview.total_rows?.toLocaleString()} rows</div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Quality Rules */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-slate-900 flex items-center gap-2 text-lg">
                  <Shield className="w-5 h-5 text-blue-600" />
                  Quality Rules
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">
                    {selectedRules.length}
                  </span>
                </h3>
                
                {/* Strict/Lenient Mode Toggle */}
                <div className="flex items-center gap-2 bg-slate-100 rounded-lg p-1">
                  <button
                    onClick={() => setQualityMode('strict')}
                    className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                      qualityMode === 'strict' 
                        ? 'bg-red-600 text-white shadow' 
                        : 'text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    STRICT
                  </button>
                  <button
                    onClick={() => setQualityMode('lenient')}
                    className={`px-3 py-1 rounded text-xs font-bold transition-all ${
                      qualityMode === 'lenient' 
                        ? 'bg-green-600 text-white shadow' 
                        : 'text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    LENIENT
                  </button>
                </div>
              </div>
              
              <div className="text-xs text-slate-600 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <strong>Mode:</strong> {qualityMode === 'strict' ? 'Errors block execution' : 'Errors quarantined, execution continues'}
              </div>
              
              <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                {categories.map(category => {
                  const rulesInCategory = QUALITY_RULES_CATALOG.filter(r => r.category === category);
                  const selectedInCategory = rulesInCategory.filter(r => selectedRules.includes(r.id));
                  const isExpanded = expandedCategories.has(category);
                  
                  return (
                    <div key={category} className="border-2 border-slate-200 rounded-lg overflow-hidden">
                      {/* Category Header */}
                      <div 
                        className="bg-slate-100 px-4 py-3 cursor-pointer hover:bg-slate-200 transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3 flex-1" onClick={() => toggleCategory(category)}>
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                          <span className="font-bold text-slate-900">{category}</span>
                          <span className="text-xs text-slate-600">
                            {selectedInCategory.length}/{rulesInCategory.length} selected
                          </span>
                        </div>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            selectAllRulesInCategory(category);
                          }}
                          className="px-3 py-1 bg-blue-600 text-white text-xs font-bold rounded hover:bg-blue-700"
                        >
                          {selectedInCategory.length === rulesInCategory.length ? 'Deselect All' : 'Select All'}
                        </button>
                      </div>
                      
                      {/* Rules in Category */}
                      {isExpanded && (
                        <div className="p-2 space-y-1 bg-white">
                          {rulesInCategory.map(rule => {
                            const isSelected = selectedRules.includes(rule.id);
                            return (
                              <div
                                key={rule.id}
                                onClick={() => toggleRule(rule.id)}
                                className={`p-3 rounded cursor-pointer transition-all border-2 ${
                                  isSelected
                                    ? 'bg-blue-50 border-blue-400 shadow'
                                    : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                                }`}
                              >
                                <div className="flex items-start gap-3">
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => {}}
                                    className="mt-1 w-4 h-4"
                                  />
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-sm font-bold text-slate-900">{rule.name}</span>
                                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full border ${getSeverityColor(rule.severity)}`}>
                                        {rule.severity?.toUpperCase()}
                                      </span>
                                    </div>
                                    <div className="text-xs text-slate-600 mb-1">{rule.description}</div>
                                    <div className="text-xs text-slate-500 italic">Impact: {rule.estimatedImpact}</div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* RIGHT: Execution Configuration */}
          <div className="space-y-6">
            
            {/* Execution Settings */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200 p-6">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2 text-lg">
                <Server className="w-5 h-5 text-blue-600" />
                Execution Configuration
              </h3>
              
              {/* Spark Resources */}
              <div className="mb-6 p-4 bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-300 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Cpu className="w-5 h-5 text-orange-600" />
                  <span className="font-bold text-orange-900">Spark Cluster Resources</span>
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="bg-white p-2 rounded border border-orange-200">
                    <div className="text-orange-700 font-semibold">Executors</div>
                    <div className="text-lg font-bold text-orange-900">{sparkResources.executors}</div>
                  </div>
                  <div className="bg-white p-2 rounded border border-orange-200">
                    <div className="text-orange-700 font-semibold">Cores/Exec</div>
                    <div className="text-lg font-bold text-orange-900">{sparkResources.cores_per_executor}</div>
                  </div>
                  <div className="bg-white p-2 rounded border border-orange-200">
                    <div className="text-orange-700 font-semibold">Memory</div>
                    <div className="text-lg font-bold text-orange-900">{sparkResources.memory_per_executor}</div>
                  </div>
                </div>
              </div>
              
              {/* Execution Mode */}
              <div className="mb-4">
                <label className="block text-sm font-bold text-slate-700 mb-3">
                  Execution Mode
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className={`flex items-center justify-center gap-2 cursor-pointer p-3 rounded-lg border-2 transition-all ${
                    executionMode === 'full' 
                      ? 'bg-blue-50 border-blue-500 text-blue-900' 
                      : 'bg-slate-50 border-slate-300 text-slate-600 hover:border-slate-400'
                  }`}>
                    <input
                      type="radio"
                      value="full"
                      checked={executionMode === 'full'}
                      onChange={(e) => setExecutionMode(e.target.value)}
                      className="w-4 h-4"
                    />
                    <Database className="w-4 h-4" />
                    <span className="font-bold">Full Load</span>
                  </label>
                  <label className={`flex items-center justify-center gap-2 cursor-pointer p-3 rounded-lg border-2 transition-all ${
                    executionMode === 'incremental' 
                      ? 'bg-green-50 border-green-500 text-green-900' 
                      : 'bg-slate-50 border-slate-300 text-slate-600 hover:border-slate-400'
                  }`}>
                    <input
                      type="radio"
                      value="incremental"
                      checked={executionMode === 'incremental'}
                      onChange={(e) => setExecutionMode(e.target.value)}
                      className="w-4 h-4"
                    />
                    <TrendingUp className="w-4 h-4" />
                    <span className="font-bold">Incremental</span>
                  </label>
                </div>
              </div>

              {/* Watermark Column */}
              {executionMode === 'incremental' && (
                <div className="mb-4">
                  <label className="block text-sm font-bold text-slate-700 mb-2">
                    Watermark Column
                  </label>
                  <input
                    type="text"
                    value={watermarkColumn}
                    onChange={(e) => setWatermarkColumn(e.target.value)}
                    placeholder="e.g., updated_at, transaction_date"
                    className="w-full px-4 py-2 border-2 border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                  />
                </div>
              )}

              {/* Custom SQL Toggle */}
              <div className="mb-4">
                <button
                  onClick={() => setShowSQLEditor(!showSQLEditor)}
                  className="w-full flex items-center justify-between p-3 bg-slate-100 hover:bg-slate-200 rounded-lg border-2 border-slate-300 transition-colors"
                >
                  <span className="flex items-center gap-2 font-bold text-slate-900">
                    <Code className="w-4 h-4" />
                    Custom SQL Transformation
                  </span>
                  {showSQLEditor ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>

              {showSQLEditor && (
                <div className="mb-4">
                  <textarea
                    value={customSQL}
                    onChange={(e) => setCustomSQL(e.target.value)}
                    placeholder="-- Advanced SQL transformations&#10;SELECT *, &#10;  CASE WHEN amount > 1000 THEN 'HIGH' ELSE 'NORMAL' END as risk_level&#10;FROM {table}"
                    className="w-full h-32 p-3 font-mono text-xs border-2 border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none bg-slate-900 text-green-400"
                  />
                </div>
              )}

              {/* Performance Metrics */}
              {performanceMetrics && (
                <div className="mb-6 p-4 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <BarChart3 className="w-5 h-5 text-green-600" />
                    <span className="font-bold text-green-900">Last Execution Performance</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-white p-2 rounded border border-green-200">
                      <div className="text-green-700 font-semibold">Duration</div>
                      <div className="text-lg font-bold text-green-900">{performanceMetrics.duration}s</div>
                    </div>
                    <div className="bg-white p-2 rounded border border-green-200">
                      <div className="text-green-700 font-semibold">Throughput</div>
                      <div className="text-lg font-bold text-green-900">{performanceMetrics.records_per_sec?.toLocaleString()}/s</div>
                    </div>
                    <div className="bg-white p-2 rounded border border-green-200">
                      <div className="text-green-700 font-semibold">Rows Processed</div>
                      <div className="text-lg font-bold text-green-900">{performanceMetrics.row_count?.toLocaleString()}</div>
                    </div>
                    <div className="bg-white p-2 rounded border border-green-200">
                      <div className="text-green-700 font-semibold">Quarantined</div>
                      <div className="text-lg font-bold text-red-700">
                        {performanceMetrics.quarantine_count?.toLocaleString()} ({performanceMetrics.quarantine_pct}%)
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Execute Button */}
              <button
                onClick={handleExecute}
                disabled={!canExecute}
                title={tooltipMessage}
                className={`w-full py-4 rounded-xl font-black text-lg flex items-center justify-center gap-3 transition-all shadow-lg ${
                  canExecute
                    ? 'bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white hover:shadow-2xl hover:scale-105'
                    : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                }`}
              >
                {executing ? (
                  <>
                    <RefreshCw className="w-6 h-6 animate-spin" />
                    PROCESSING...
                  </>
                ) : (
                  <>
                    <Play className="w-6 h-6" />
                    EXECUTE TRANSFORMATION
                  </>
                )}
              </button>

              {/* Execution Progress */}
              {executionProgress && (
                <div className="mt-4 p-4 bg-blue-50 border-2 border-blue-300 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-blue-900">
                      Step {executionProgress.step}/{executionProgress.total}: {executionProgress.message}
                    </span>
                    {executionProgress.progress && (
                      <span className="text-sm font-bold text-blue-700">
                        {executionProgress.progress}%
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-blue-500 to-purple-600 h-full transition-all duration-500 rounded-full"
                      style={{ width: `${(executionProgress.step / executionProgress.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>

            {/* Iceberg Snapshots */}
            <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200 p-6">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2 text-lg">
                <GitBranch className="w-5 h-5 text-blue-600" />
                Iceberg Snapshots
                <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs font-bold rounded-full">
                  {snapshotHistory.length}
                </span>
              </h3>
              
              {snapshotHistory.length === 0 ? (
                <div className="text-center py-6 bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-200 rounded-lg">
                  <GitBranch className="w-10 h-10 text-purple-400 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-purple-900 mb-2">No Snapshots Yet</p>
                  <p className="text-xs text-purple-700 px-4">
                    Iceberg snapshots enable <strong>rollback</strong>, <strong>time travel</strong> & <strong>version control</strong>.
                    <br/>Execute a transformation to create your first snapshot.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {snapshotHistory.slice(0, 5).map((snapshot, idx) => (
                    <div key={idx} className="p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border-2 border-purple-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-purple-900">
                          Snapshot #{snapshot.snapshot_id}
                        </span>
                        <span className="text-xs text-purple-700">
                          {new Date(snapshot.committed_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-purple-700 font-semibold">Records:</span>{' '}
                          <span className="font-bold text-purple-900">{snapshot.summary?.['total-records']?.toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-purple-700 font-semibold">Operation:</span>{' '}
                          <span className="font-bold text-purple-900">{snapshot.operation}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ===== TRANSFORMATION BACKLOG (Full Width) ===== */}
        <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200">
          <div className="px-6 py-4 border-b-2 border-slate-200 flex items-center justify-between">
            <h3 className="font-bold text-slate-900 flex items-center gap-2 text-lg">
              <Activity className="w-5 h-5 text-blue-600" />
              Transformation Backlog
              <span className="px-2 py-0.5 bg-slate-200 text-slate-700 text-xs font-bold rounded-full">
                {filteredLogs.length}
              </span>
            </h3>
            
            <div className="flex items-center gap-3">
              {/* Filter */}
              <select
                value={logFilter}
                onChange={(e) => setLogFilter(e.target.value)}
                className="px-3 py-1 border-2 border-slate-300 rounded text-xs font-semibold bg-slate-50"
              >
                <option value="all">All Logs</option>
                <option value="info">Info Only</option>
                <option value="success">Success Only</option>
                <option value="error">Errors Only</option>
              </select>
              
              {/* Auto-scroll Toggle */}
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="w-4 h-4"
                />
                Auto-scroll
              </label>
            </div>
          </div>
          
          <div className="p-6">
            {filteredLogs.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm font-medium">No logs yet. Execute a transformation to see runtime logs.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredLogs.map((log) => (
                  <div
                    key={log.id}
                    className={`p-3 rounded-lg font-mono text-sm flex items-start gap-3 border-2 transition-all ${
                      log.level === 'error' ? 'bg-red-50 border-red-300 text-red-900' :
                      log.level === 'success' ? 'bg-green-50 border-green-300 text-green-900' :
                      'bg-blue-50 border-blue-300 text-blue-900'
                    }`}
                  >
                    {getLogIcon(log.level)}
                    <div className="flex-1 overflow-hidden">
                      <div className="mb-1">
                        <span className="text-slate-500 font-semibold">[{log.timestamp}]</span>
                      </div>
                      <div className="whitespace-pre-wrap break-words">
                        {log.message}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SilverEnterprise;
