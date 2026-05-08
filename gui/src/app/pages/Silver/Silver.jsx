import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Database, Play, Eye, Clock, CheckCircle, AlertTriangle, Search, ChevronDown, ChevronRight, TrendingUp, RefreshCw, FileText, Activity, Layers, ArrowLeft, Filter, Award, BarChart3 } from 'lucide-react';
import { RULE_CATEGORIES } from '../../constants/rulesCatalogue';
import { EXECUTION_MODES, PIPELINE_STEPS } from '../../constants/executionModes';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

const API_BASE = 'http://localhost:8000/api';

// Transform type colors (visual hierarchy)
const TRANSFORM_COLORS = {
  'type_conversion': '#b088ff', // purple
  'string_cleanup': '#10b981',  // green  
  'business_logic': '#f59e0b',  // yellow
  'computed': '#3b82f6'         // blue
};

// Color scheme for pipeline status
const LAYER_COLORS = {
  bronze: '#CD7F32',
  silver: '#6B7280',
  gold: '#B8860B',
  green: '#10b981'
};

// Tooltip Component for pipeline
const InfoTooltip = ({ text }) => {
  const [show, setShow] = React.useState(false);
  
  return (
    <div className="relative inline-block ml-1">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        style={{
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          backgroundColor: '#E5E7EB',
          border: '1px solid #D1D5DB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#6B7280',
          fontSize: '10px',
          cursor: 'pointer',
          transition: 'background-color 0.2s'
        }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#D1D5DB'}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#E5E7EB'}
      >
        ?
      </button>
      {show && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          marginBottom: '8px',
          width: '256px',
          backgroundColor: '#1F2937',
          color: 'white',
          fontSize: '12px',
          borderRadius: '8px',
          padding: '12px',
          zIndex: 50,
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
        }}>
          {text}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginTop: '-4px',
            borderWidth: '4px',
            borderStyle: 'solid',
            borderColor: '#1F2937 transparent transparent transparent'
          }}></div>
        </div>
      )}
    </div>
  );
};

// Pipeline Status Banner
const PipelineStatus = () => {
  return (
    <div className="layer-header-card" style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(205,127,50,0.15)',
            border: '2px solid #CD7F32'
          }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: LAYER_COLORS.bronze }}>B</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ fontWeight: 600, fontSize: '14px', color: LAYER_COLORS.bronze }}>Bronze Layer</div>
              <InfoTooltip text="The Bronze layer stores raw data exactly as ingested from source systems. No transformations are applied - data is preserved in its original format. This ensures full historical traceability and allows reprocessing if needed." />
            </div>
            <div style={{ fontSize: '12px', color: '#6B7280' }}>Raw ingestion</div>
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: LAYER_COLORS.green }}>Done</div>
        </div>
        
        <div style={{ color: '#D1D5DB', fontSize: '20px' }}>›</div>
        
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(168,180,192,0.12)',
            border: '2px solid #6B7280'
          }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: LAYER_COLORS.silver }}>S</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ fontWeight: 600, fontSize: '14px', color: LAYER_COLORS.silver }}>Silver Layer</div>
              <InfoTooltip text="The Silver layer contains cleaned and validated data. Transformations include type casting, deduplication, validation rules, and quality checks. Data is structured and ready for analytics." />
            </div>
            <div style={{ fontSize: '12px', color: '#6B7280' }}>Cleaned · Validated</div>
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: LAYER_COLORS.silver }}>Ready</div>
        </div>
        
        <div style={{ color: '#D1D5DB', fontSize: '20px' }}>›</div>
        
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(184,134,11,0.08)',
            border: '2px solid #B8860B'
          }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: LAYER_COLORS.gold }}>G</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <div style={{ fontWeight: 600, fontSize: '14px', color: LAYER_COLORS.gold }}>Gold Layer</div>
              <InfoTooltip text="The Gold layer contains curated, business-ready data products. Data is aggregated, analyzed, and optimized for reporting and analytics use cases. Includes EDA reports, KPIs, and data marts." />
            </div>
            <div style={{ fontSize: '12px', color: '#6B7280' }}>Aggregated · Curated</div>
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#9CA3AF' }}>Next</div>
        </div>
      </div>
    </div>
  );
};

/**
 * Silver - Transformation Studio with 2-Stage Flow
 * Stage 1: Table Selection | Stage 2: Transformation Studio
 */
export default function Silver() {
  const { domain } = useParams();
  
  // ===== TWO-STAGE FLOW =====
  const [view, setView] = useState('selection'); // 'selection' or 'studio'
  const [bronzeTables, setBronzeTables] = useState([]);
  const [silverTables, setSilverTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('last_modified');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterSource, setFilterSource] = useState('');
  const [filterFormat, setFilterFormat] = useState('');
  const [filterStatus, setFilterStatus] = useState(''); // 'bronze' or 'cleaned'
  const [filterDataType, setFilterDataType] = useState(''); // 'structured' or 'unstructured'
  const [showFilters, setShowFilters] = useState(false);
  
  // ===== STUDIO STATE =====
  const [selectedTable, setSelectedTable] = useState(null);
  const [activeTab, setActiveTab] = useState('transform'); // 'transform' | 'quality' | 'monitor'
  const [dataType, setDataType] = useState('structured'); // 'structured' or 'unstructured'
  const [unstructuredType, setUnstructuredType] = useState('image'); // 'image' | 'video' | 'audio'
  const [executionMode, setExecutionMode] = useState('incremental');
  const [watermarkColumn, setWatermarkColumn] = useState('created_at');
  const [customSQL, setCustomSQL] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionStatus, setExecutionStatus] = useState('');
  
  // Unstructured data transformation options
  const [imageTransforms, setImageTransforms] = useState({
    removeCorrupted: true,
    resize: false,
    resizeWidth: 224,
    resizeHeight: 224,
    formatConversion: '',
    convertToRGB: false,
    normalizePixels: false,
    fixedAspectRatio: false,
    standardNaming: false,
    standardMetadata: false,
    grayscale: false,
    edgeDetection: false,
    objectDetection: false,
    augmentation: []
  });
  const [videoTransforms, setVideoTransforms] = useState({
    removeCorrupted: true,
    formatConversion: '',
    standardizeResolution: false,
    normalizeFPS: false,
    targetFPS: 30,
    removeSilent: false,
    compression: false,
    reduceBitrate: false,
    trimUnnecessary: false,
    audioConversion: ''
  });
  const [audioTransforms, setAudioTransforms] = useState({
    formatConversion: '',
    channelConfig: '',
    normalizeVolume: false
  });
  
  // ===== SPARK + PERFORMANCE STATE =====
  const [useSparkEngine, setUseSparkEngine] = useState(true); // Spark-first architecture
  const [datasetSizeInfo, setDatasetSizeInfo] = useState(null);
  const [checkingSizeLoading, setCheckingSizeLoading] = useState(false);
  const [runBenchmark, setRunBenchmark] = useState(false); // Optional: Run both Pandas & Spark for comparison
  const [performanceMetrics, setPerformanceMetrics] = useState(null); // Stores Pandas vs Spark comparison
  const [showSnapshotViewer, setShowSnapshotViewer] = useState(false);
  const [snapshotHistory, setSnapshotHistory] = useState([]);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  
  // SQL Preview state
  const [sqlPreviewResults, setSqlPreviewResults] = useState(null);
  const [sqlPreviewLoading, setSqlPreviewLoading] = useState(false);
  const [sqlPreviewError, setSqlPreviewError] = useState(null);
  const [sqlPreviewUsingMock, setSqlPreviewUsingMock] = useState(false);
  
  // Rule state
  const [activeRules, setActiveRules] = useState({});
  const [expandedCategories, setExpandedCategories] = useState({
    basic_completeness: true
  });
  const [expandedRules, setExpandedRules] = useState({});
  
  // Rule execution results (mock data - represents actual DQ check results)
  const [ruleResults, setRuleResults] = useState({
    'COMP-001': { passed: 2398850, failed: 1150, action: 'quarantine', threshold: '0 nulls allowed', samples: ['row 1247: user_id=NULL', 'row 2891: email=NULL'] },
    'COMP-002': { passed: 2399900, failed: 100, action: 'transform', threshold: 'trim empty strings', samples: ['row 445: name=""', 'row 1203: description=""'] },
    'VAL-001': { passed: 2400000, failed: 0, action: 'pass', threshold: 'match schema types', samples: [] },
    'VAL-002': { passed: 2399913, failed: 87, action: 'reject', threshold: 'valid date format', samples: ['row 332: date="99-99-9999"', 'row 1847: date="invalid"'] },
    'VAL-003': { passed: 2399995, failed: 5, action: 'quarantine', threshold: 'amount > 0', samples: ['row 5421: amount=-150.50', 'row 8932: amount=-2.00'] },
    'UNQ-001': { passed: 2400000, failed: 0, action: 'pass', threshold: 'unique transaction_id', samples: [] },
    'UNQ-002': { passed: 2399659, failed: 341, action: 'transform', threshold: 'remove duplicates', samples: ['341 duplicate rows removed'] },
    'FMT-001': { passed: 2400000, failed: 0, action: 'transform', threshold: 'trim whitespace', samples: [] },
    'FMT-002': { passed: 2400000, failed: 0, action: 'pass', threshold: 'standardize case', samples: [] },
    'FMT-003': { passed: 2400000, failed: 0, action: 'pass', threshold: 'remove special chars', samples: [] },
    'CON-001': { passed: 2399998, failed: 2, action: 'quarantine', threshold: 'start_date < end_date', samples: ['row 823: start=2026-03-05, end=2026-03-01'] },
    'CON-002': { passed: 2400000, failed: 0, action: 'pass', threshold: 'within expected range', samples: [] }
  });
  
  // Threshold editing state
  const [editingThreshold, setEditingThreshold] = useState(null);
  const [thresholdInput, setThresholdInput] = useState('');
  
  // Per-dimension DQ trends (last 5 runs)
  const [dimensionTrends, setDimensionTrends] = useState({
    completeness: [92, 93, 92, 94, 94],
    conformity: [85, 86, 87, 88, 88],
    uniqueness: [98, 99, 99, 99, 99],
    validity: [78, 80, 79, 78, 76]
  });
  
  // Quarantine & Rejection data
  const [showQuarantineViewer, setShowQuarantineViewer] = useState(false);
  const [showRejectionViewer, setShowRejectionViewer] = useState(false);
  const [quarantineData, setQuarantineData] = useState([
    { row_id: 1247, rule: 'COMP-001', column: 'user_id', value: 'NULL', reason: 'NULL value in critical column', timestamp: '2026-03-02T14:22:15Z' },
    { row_id: 2891, rule: 'COMP-001', column: 'email', value: 'NULL', reason: 'NULL value in critical column', timestamp: '2026-03-02T14:22:15Z' },
    { row_id: 5421, rule: 'VAL-003', column: 'amount', value: '-150.50', reason: 'Negative value not allowed', timestamp: '2026-03-02T14:22:16Z' },
    { row_id: 8932, rule: 'VAL-003', column: 'amount', value: '-2.00', reason: 'Negative value not allowed', timestamp: '2026-03-02T14:22:16Z' }
  ]);
  const [rejectionData, setRejectionData] = useState([
    { row_id: 332, rule: 'VAL-002', column: 'transaction_date', value: '99-99-9999', reason: 'Invalid date format', timestamp: '2026-03-02T14:22:15Z' },
    { row_id: 1847, rule: 'VAL-002', column: 'transaction_date', value: 'invalid', reason: 'Invalid date format', timestamp: '2026-03-02T14:22:15Z' },
    { row_id: 3421, rule: 'VAL-002', column: 'created_at', value: '2099-12-31', reason: 'Future date not allowed', timestamp: '2026-03-02T14:22:16Z' }
  ]);
  
  // Real Silver job data
  const [silverJob, setSilverJob] = useState(null);
  const [silverJobLoading, setSilverJobLoading] = useState(false);
  
  // Watermark state
  const [watermarkState, setWatermarkState] = useState({
    column: 'created_at',
    lastValue: '2026-03-02T08:30:00Z',
    nextRunWillProcess: '> 2026-03-02T08:30:00Z',
    rowsSinceLastRun: 12483
  });
  
  // Schema drift state
  const [schemaDrift, setSchemaDrift] = useState({
    status: 'stable', // 'stable', 'warning', 'error'
    lastChecked: '2026-03-02T14:20:00Z',
    changes: [] // e.g., [{type: 'added', column: 'new_col', detected: '...'}]
  });
  
  // Active pipeline step filter
  const [activePipelineFilter, setActivePipelineFilter] = useState(null);
  
  // Transformation backlog & real-time logs
  const [transformationLogs, setTransformationLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentOperation, setCurrentOperation] = useState(null);
  
  // Failure viewer
  const [showAllFailuresModal, setShowAllFailuresModal] = useState(false);
  const [selectedRuleForFailures, setSelectedRuleForFailures] = useState(null);
  
  // Enterprise features
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [savedConfigurations, setSavedConfigurations] = useState([]);
  const [showTemplateLibrary, setShowTemplateLibrary] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showHelp, setShowHelp] = useState(false);
  
  // NEW: Schema Evolution & Mapping
  const [schemaEvolutionMode, setSchemaEvolutionMode] = useState('strict'); // 'strict' or 'flexible'
  const [showSchemaMapping, setShowSchemaMapping] = useState(true);
  
  // NEW: Data Quality Constraints (Great Expectations style)
  const [columnConstraints, setColumnConstraints] = useState({
    // Column-level constraints
    // transaction_id: { notNull: true, unique: true, isPrimaryKey: true },
    // email: { notNull: false, unique: false, regex: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$' }
  });
  
  // NEW: Transformation Preview
  const [showPreview, setShowPreview] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState({
    before: [],
    after: [],
    columns: []
  });
  
  // NEW: Performance Tuning
  const [partitionColumns, setPartitionColumns] = useState(['transaction_date']);
  const [zOrderColumns, setZOrderColumns] = useState([]);
  const [useLiquidClustering, setUseLiquidClustering] = useState(false);
  const [clusteringColumns, setClusteringColumns] = useState([]);
  
  // Pipeline state with metrics
  const [pipelineSteps, setPipelineSteps] = useState([
    { id: 'clean', label: 'Clean', status: 'completed', rows: 2400000, time: '2.1s' },
    { id: 'cast', label: 'Type Cast', status: 'completed', rows: 2400000, time: '1.8s' },
    { id: 'dedup', label: 'Dedup', status: 'completed', rows: 341, time: '3.2s' },
    { id: 'validate', label: 'Validate', status: 'active', rows: null, time: null },
    { id: 'quarantine', label: 'Quarantine', status: 'pending', rows: null, time: null },
    { id: 'enrich', label: 'Enrich', status: 'pending', rows: null, time: null },
    { id: 'write', label: 'Write', status: 'pending', rows: null, time: null }
  ]);
  
  // DQ Metrics with trend (will be populated from real job data)
  const [dqScore, setDqScore] = useState(null);
  const [dqTrend, setDqTrend] = useState([]); // Last 5 runs
  const [qualityMetrics, setQualityMetrics] = useState({
    completeness: null,
    conformity: null,
    uniqueness: null,
    validity: null
  });
  
  // Column mappings with transform types
  const [columnMappings, setColumnMappings] = useState([
    { source: 'transaction_id', sourceType: 'VARCHAR(50)', target: 'transaction_id', targetType: 'VARCHAR(50)', transform: 'TRIM', transformType: 'string_cleanup' },
    { source: 'amount', sourceType: 'DECIMAL(10,2)', target: 'amount', targetType: 'DECIMAL(12,2)', transform: 'ABS→CAST', transformType: 'type_conversion' },
    { source: 'currency_code', sourceType: 'VARCHAR(3)', target: 'currency_code', targetType: 'VARCHAR(3)', transform: 'UPPER+TRIM', transformType: 'string_cleanup' },
    { source: 'status', sourceType: 'VARCHAR(20)', target: 'status', targetType: 'VARCHAR(20)', transform: 'ENUM MAP', transformType: 'business_logic' },
    { source: '-', sourceType: '-', target: 'transaction_type', targetType: 'VARCHAR(10)', transform: 'COMPUTED', transformType: 'computed' }
  ]);
  
  // Preview summary stats (different from transformation preview)
  const [previewSummary, setPreviewSummary] = useState({
    rows_input: null,
    rows_output: null,
    rows_quarantined: null,
    duplicates_removed: null,
    rows_rejected: null
  });

  // ===== CDC STREAMING STATE =====
  const [cdcStatus, setCdcStatus] = useState({}); // CDC streaming status per table
  const [cdcMetrics, setCdcMetrics] = useState({}); // Real-time CDC metrics
  const [cdcLoading, setCdcLoading] = useState(false);
  const [cdcEnabledTables, setCdcEnabledTables] = useState([]); // Tables with CDC capability

  // ===== LIFECYCLE =====
  useEffect(() => {
    loadBronzeTables();
    loadCDCStatus(); // Load CDC streaming status
    
    // Auto-refresh CDC status every 10 seconds
    const cdcRefreshInterval = setInterval(() => {
      if (view === 'selection') {
        loadCDCStatus();
      }
    }, 10000);
    
    return () => clearInterval(cdcRefreshInterval);
  }, [domain, view]);
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+K or Cmd+K - Command Palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(true);
      }
      // Ctrl+S or Cmd+S - Save configuration
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSaveConfiguration();
      }
      // Esc - Close modals
      if (e.key === 'Escape') {
        setShowCommandPalette(false);
        setShowQuickActions(false);
        setShowTemplateLibrary(false);
        setShowHelp(false);
      }
      // Alt+1/2 - Tab navigation
      if (e.altKey && e.key === '1') {
        e.preventDefault();
        setActiveTab('transform');
      }
      if (e.altKey && e.key === '2') {
        e.preventDefault();
        setActiveTab('quality');
      }
      // F1 - Help
      if (e.key === 'F1') {
        e.preventDefault();
        setShowHelp(true);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (view === 'studio' && selectedTable) {
      initializeRules();
      loadColumnMappings();
      fetchLatestSilverJob(); // Fetch real job data
    }
  }, [view, selectedTable]);

  // Fetch the latest Silver processing job for the selected table
  useEffect(() => {
    if (selectedTable) {
      fetchLatestSilverJob();
    }
  }, [selectedTable]);

  const fetchLatestSilverJob = async () => {
    if (!selectedTable) return;
    
    try {
      setSilverJobLoading(true);
      
      // Get list of jobs for this entity
      const response = await axios.get(`${API_BASE}/silver/jobs`, {
        params: { limit: 10 },
        timeout: 10000
      });
      
      // Find the most recent completed job for this table
      const jobs = response.data.jobs || [];
      const matchingJob = jobs.find(job => 
        job.entity === selectedTable.table_name && 
        job.status === 'completed'
      );
      
      if (matchingJob) {
        setSilverJob(matchingJob);
        
        // Update UI with real data
        if (matchingJob.quality_score !== null) {
          setDqScore(Math.round(matchingJob.quality_score));
        }
        
        if (matchingJob.cleaning_summary) {
          const summary = matchingJob.cleaning_summary;
          
          // Update quality metrics from cleaning summary
          if (summary.quality_metrics) {
            setQualityMetrics(summary.quality_metrics);
          }
          
          // Update preview data with real row counts
          setPreviewData({
            rows_input: summary.original_rows || matchingJob.row_count || 0,
            rows_output: matchingJob.row_count || 0,
            rows_quarantined: summary.quarantined_rows || 0,
            duplicates_removed: summary.duplicates_removed || 0,
            rows_rejected: summary.rejected_rows || 0
          });
        } else {
          // Fallback if no cleaning summary
          setPreviewData({
            rows_input: matchingJob.row_count || 0,
            rows_output: matchingJob.row_count || 0,
            rows_quarantined: 0,
            duplicates_removed: 0,
            rows_rejected: 0
          });
        }
        
        console.log('[Silver] Loaded job data:', matchingJob);
      } else {
        setSilverJob(null);
        // Reset to show no data
        setDqScore(null);
        setPreviewData({
          rows_input: null,
          rows_output: null,
          rows_quarantined: null,
          duplicates_removed: null,
          rows_rejected: null
        });
        console.log('[Silver] No completed job found for', selectedTable.table_name);
      }
      
    } catch (error) {
      console.error('[Silver] Error fetching job data:', error);
      setSilverJob(null);
    } finally {
      setSilverJobLoading(false);
    }
  };

  // ===== API CALLS =====
  const loadBronzeTables = async () => {
    try {
      setLoading(true);
      console.log('[Silver] Loading silver tables from MinIO...');
      
      // Try multiple endpoints for Silver tables
      let silverData = [];
      
      try {
        // First try: Direct Silver tables endpoint
        const silverResponse = await axios.get(`${API_BASE}/silver/tables`, {
          timeout: 10000
        });
        silverData = silverResponse.data.tables || [];
        console.log(`[Silver] Loaded ${silverData.length} tables from /api/silver/tables`);
      } catch (err1) {
        console.warn('[Silver] /api/silver/tables failed:', err1.message);
        
        try {
          // Second try: Iceberg tables endpoint
          const icebergResponse = await axios.get(`${API_BASE}/silver/iceberg-tables`, {
            timeout: 15000
          });
          const icebergTables = icebergResponse.data.tables || [];
          
          // Transform Iceberg table format to UI format
          silverData = icebergTables.map(table => ({
            table_name: `${table.namespace}.${table.tableName}`,
            source_type: 'iceberg',
            format: 'iceberg',
            row_count: 0,
            last_modified: new Date().toISOString(),
            status: 'cleaned',
            quality_score: 95,
            data_type: 'structured'
          }));
          console.log(`[Silver] Loaded ${silverData.length} Iceberg tables`);
        } catch (err2) {
          console.warn('[Silver] /api/silver/iceberg-tables failed:', err2.message);
        }
      }
      
      // Map to include status (cleaned vs bronze)
      const tablesWithStatus = silverData.map(table => ({
        ...table,
        status: table.quality_score ? 'cleaned' : 'bronze',
        data_type: table.format === 'image' || table.format === 'video' || table.format === 'audio' ? 'unstructured' : 'structured',
        unstructured_type: ['image', 'video', 'audio'].includes(table.format) ? table.format : null
      }));
      
      setSilverTables(tablesWithStatus);
      setBronzeTables(tablesWithStatus); // Keep for compatibility
      console.log('[Silver] Set tables in state:', tablesWithStatus);
      
    } catch (error) {
      console.error('[Silver] Failed to load tables:', error);
      // Mock data with status badges
      const mockTables = [
        { table_name: 'finance_transactions', row_count: 2400000, last_modified: '2026-03-02T08:30:00Z', source_type: 'postgres', status: 'cleaned', quality_score: 95, data_type: 'structured', format: 'iceberg' },
        { table_name: 'transactions_data', row_count: 0, last_modified: '2026-03-02T08:30:00Z', source_type: 'postgres', status: 'bronze', quality_score: null, data_type: 'structured', format: 'parquet' },
        { table_name: 'product_images', row_count: 15420, last_modified: '2026-03-02T07:15:00Z', source_type: 's3', status: 'bronze', quality_score: null, data_type: 'unstructured', unstructured_type: 'image', format: 'image' },
        { table_name: 'customer_videos', row_count: 3240, last_modified: '2026-03-01T22:45:00Z', source_type: 's3', status: 'bronze', quality_score: null, data_type: 'unstructured', unstructured_type: 'video', format: 'video' }
      ];
      setSilverTables(mockTables);
      setBronzeTables(mockTables);
    } finally {
      setLoading(false);
    }
  };

  const loadCDCStatus = async () => {
    try {
      setCdcLoading(true);
      
      // Load CDC-enabled tables
      const tablesResponse = await axios.get(`${API_BASE}/silver/cdc/tables`);
      if (tablesResponse.data.success) {
        setCdcEnabledTables(tablesResponse.data.tables || []);
      }
      
      // Load CDC streaming status
      const statusResponse = await axios.get(`${API_BASE}/silver/cdc/status`);
      if (statusResponse.data.success) {
        setCdcStatus(statusResponse.data.jobs || {});
      }
    } catch (error) {
      console.error('[Silver] Failed to load CDC status:', error);
    } finally {
      setCdcLoading(false);
    }
  };

  const handleCDCStreamToggle = async (table, action) => {
    try {
      const [source, tableName] = table.table_name.split('_', 2) || [table.source_type, table.table_name];
      
      if (action === 'start') {
        const response = await axios.post(`${API_BASE}/silver/cdc/start`, {
          source,
          table_name: tableName,
          checkpoint_interval: 30,
          max_offsets: 10000
        });
        
        if (response.data.success) {
          alert(`✅ CDC Streaming started for ${table.table_name}`);
          loadCDCStatus(); // Refresh status
        }
      } else if (action === 'stop') {
        const response = await axios.post(`${API_BASE}/silver/cdc/stop?source=${source}&table_name=${tableName}`);
        
        if (response.data.success) {
          alert(`✅ CDC Streaming stopped for ${table.table_name}`);
          loadCDCStatus(); // Refresh status
        }
      }
    } catch (error) {
      console.error('[Silver] CDC stream toggle failed:', error);
      alert(`❌ Failed to ${action} CDC stream: ${error.message}`);
    }
  };

  const isCDCEnabled = (tableName) => {
    return cdcEnabledTables.some(t => t.full_name === tableName || t.table_name === tableName);
  };

  const getCDCStreamStatus = (tableName) => {
    const jobKey = tableName.replace('.', '_');
    return cdcStatus[jobKey]?.status || 'not_running';
  };

  const initializeRules = () => {
    const defaultRules = {};
    Object.values(RULE_CATEGORIES).forEach(category => {
      category.rules.forEach(rule => {
        if (rule.default) {
          defaultRules[rule.id] = true;
        }
      });
    });
    setActiveRules(defaultRules);
  };

  const loadColumnMappings = async () => {
    // TODO: Load actual column mappings from backend
    console.log('[Silver] Loading column mappings for', selectedTable.table_name);
  };

  // ===== EVENT HANDLERS =====
  const handleTableSelect = async (table) => {
    setSelectedTable(table);
    setView('studio');
    
    // Set data type based on table
    if (table.data_type === 'unstructured') {
      setDataType('unstructured');
      setUnstructuredType(table.unstructured_type || 'image');
    } else {
      setDataType('structured');
    }
    
    // Check dataset size for Spark recommendation
    await checkDatasetSize(table);
  };
  
  // Check dataset size and provide recommendation
  const checkDatasetSize = async (table) => {
    setCheckingSizeLoading(true);
    try {
      const response = await axios.get(
        `${API_BASE}/silver/dataset-size/${domain}/${table.table_name}`
      );
      const sizeInfo = response.data;
      
      setDatasetSizeInfo(sizeInfo);
      
      console.log('[Silver] Dataset size:', sizeInfo.size_mb.toFixed(2), 'MB');
      console.log('[Silver] Recommendation:', sizeInfo.recommendation);
      
      // Always use Spark (Spark-first architecture)
      setUseSparkEngine(true);
      
    } catch (error) {
      console.error('[Silver] Failed to check dataset size:', error);
      // Fallback: Still use Spark by default
      setUseSparkEngine(true);
    } finally {
      setCheckingSizeLoading(false);
    }
  };
  
  // Load Iceberg snapshot history
  const loadSnapshotHistory = async () => {
    if (!selectedTable) return;
    
    setSnapshotLoading(true);
    setShowSnapshotViewer(true);
    
    try {
      const response = await axios.get(
        `${API_BASE}/silver/iceberg-table/${domain}/${selectedTable.table_name}/history`
      );
      setSnapshotHistory(response.data.history || []);
      console.log('[Silver] Loaded', response.data.history?.length || 0, 'snapshots');
    } catch (error) {
      console.error('[Silver] Failed to load snapshots:', error);
      setSnapshotHistory([]);
    } finally {
      setSnapshotLoading(false);
    }
  };

  const handleBackToSelection = () => {
    setView('selection');
    setSelectedTable(null);
    setDatasetSizeInfo(null);
    setPerformanceMetrics(null);
  };

  const handleToggleRule = (ruleId) => {
    setActiveRules(prev => ({
      ...prev,
      [ruleId]: !prev[ruleId]
    }));
  };

  const toggleCategory = (categoryKey) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryKey]: !prev[categoryKey]
    }));
  };
  
  const toggleRule = (ruleId) => {
    setExpandedRules(prev => ({
      ...prev,
      [ruleId]: !prev[ruleId]
    }));
  };
  
  const handlePipelineStepClick = (stepId) => {
    setActivePipelineFilter(activePipelineFilter === stepId ? null : stepId);
  };
  
  const handleSQLPreview = async () => {
    console.log('[Silver] Run Preview clicked');
    
    if (!customSQL.trim()) {
      setSqlPreviewError('Please enter a SQL query');
      return;
    }
    
    setSqlPreviewLoading(true);
    setSqlPreviewError(null);
    setSqlPreviewResults(null);
    setSqlPreviewUsingMock(false);
    
    try {
      // Call real backend API
      const response = await axios.post(`${API_BASE}/silver/sql-preview`, {
        sql: customSQL,
        source: domain || 'finance',
        entity: selectedTable?.table_name || 'finance_transactions'
      }, { timeout: 10000 });
      
      setSqlPreviewResults(response.data);
      setSqlPreviewUsingMock(false);
      console.log('[Silver] ✓ SQL preview results from PostgreSQL:', response.data);
      setSqlPreviewLoading(false);
    } catch (error) {
      setSqlPreviewLoading(false);
      
      if (error.response) {
        // Backend returned an error
        const errorMsg = error.response.data?.detail || error.response.data?.message || 'Query execution failed';
        setSqlPreviewError(`Database Error: ${errorMsg}`);
        console.error('[Silver] SQL preview error:', errorMsg);
      } else if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        // Backend not running
        setSqlPreviewError('Backend API not running. Please start the backend server: python gui/api/backend.py');
        console.error('[Silver] Backend not available:', error.message);
      } else {
        // Other errors
        setSqlPreviewError(`Error: ${error.message}`);
        console.error('[Silver] SQL preview failed:', error);
      }
    }
  };
  
  const simulateRealTimeTransformation = () => {
    const logs = [
      { time: 0, type: 'info', step: 'clean', message: '🔄 Starting data cleaning phase...', rowsProcessed: 0 },
      { time: 500, type: 'progress', step: 'clean', message: 'Processing rows 1 - 500,000...', rowsProcessed: 500000 },
      { time: 1000, type: 'progress', step: 'clean', message: 'Processing rows 500,001 - 1,000,000...', rowsProcessed: 1000000 },
      { time: 1500, type: 'success', step: 'clean', message: '✓ Trimmed whitespace from 2.4M rows', rowsProcessed: 2400000 },
      { time: 1600, type: 'success', step: 'clean', message: '✓ Removed empty strings: 100 rows transformed', rowsProcessed: 2400000 },
      { time: 2000, type: 'info', step: 'cast', message: '🔄 Type casting phase started...', rowsProcessed: 0 },
      { time: 2500, type: 'progress', step: 'cast', message: 'Casting user_id: STRING → BIGINT...', rowsProcessed: 1200000 },
      { time: 3000, type: 'success', step: 'cast', message: '✓ Type cast completed: 2.4M rows processed', rowsProcessed: 2400000 },
      { time: 3500, type: 'info', step: 'dedup', message: '🔄 Deduplication phase started...', rowsProcessed: 0 },
      { time: 4000, type: 'warning', step: 'dedup', message: '⚠ Found 341 duplicate rows based on transaction_id', rowsProcessed: 341 },
      { time: 4500, type: 'success', step: 'dedup', message: '✓ Removed 341 duplicate rows', rowsProcessed: 2399659 },
      { time: 5000, type: 'info', step: 'validate', message: '🔄 Data quality validation started...', rowsProcessed: 0 },
      { time: 5500, type: 'progress', step: 'validate', message: 'Checking COMP-001: No NULL Values...', rowsProcessed: 800000 },
      { time: 6000, type: 'error', step: 'validate', message: '✗ Row 1247: user_id=NULL → QUARANTINED', rowsProcessed: 1247 },
      { time: 6200, type: 'error', step: 'validate', message: '✗ Row 2891: email=NULL → QUARANTINED', rowsProcessed: 2891 },
      { time: 6500, type: 'progress', step: 'validate', message: 'Checking VAL-002: Valid Date Format...', rowsProcessed: 1500000 },
      { time: 7000, type: 'error', step: 'validate', message: '✗ Row 332: date="99-99-9999" → REJECTED', rowsProcessed: 332 },
      { time: 7200, type: 'error', step: 'validate', message: '✗ Row 1847: date="invalid" → REJECTED', rowsProcessed: 1847 },
      { time: 7500, type: 'progress', step: 'validate', message: 'Checking VAL-003: Amount Range...', rowsProcessed: 2000000 },
      { time: 8000, type: 'error', step: 'validate', message: '✗ Row 5421: amount=-150.50 → QUARANTINED', rowsProcessed: 5421 },
      { time: 8500, type: 'success', step: 'validate', message: '✓ DQ validation completed: 1,247 quarantined, 89 rejected', rowsProcessed: 2399659 },
      { time: 9000, type: 'info', step: 'enrich', message: '🔄 Data enrichment phase started...', rowsProcessed: 0 },
      { time: 9500, type: 'success', step: 'enrich', message: '✓ Computed transaction_type from business_logic', rowsProcessed: 2398612 },
      { time: 10000, type: 'info', step: 'write', message: '🔄 Writing to Silver layer...', rowsProcessed: 0 },
      { time: 11000, type: 'success', step: 'write', message: '✓ Successfully wrote 2,398,612 rows to Silver', rowsProcessed: 2398612 },
      { time: 11500, type: 'success', step: 'complete', message: '✅ Transformation completed successfully!', rowsProcessed: 2398612 }
    ];
    
    logs.forEach(log => {
      setTimeout(() => {
        setTransformationLogs(prev => [...prev, { ...log, timestamp: new Date().toISOString() }]);
        setCurrentOperation(log.message);
        
        // Update pipeline steps
        if (log.step !== 'complete') {
          setPipelineSteps(prev => prev.map(step => {
            if (step.id === log.step && log.type === 'success') {
              return { ...step, status: 'completed', rows: log.rowsProcessed, time: `${(log.time / 1000).toFixed(1)}s` };
            } else if (step.id === log.step && log.type === 'info') {
              return { ...step, status: 'active' };
            }
            return step;
          }));
        }
        
        if (log.step === 'complete') {
          setIsStreaming(false);
          setIsExecuting(false);
          setExecutionStatus('✅ Transformation completed successfully!');
        }
      }, log.time);
    });
  };

  const handlePreview = async () => {
    console.log('[Silver] Preview clicked', { selectedTable, domain });
    
    if (!selectedTable) {
      console.warn('[Silver] No table selected');
      return;
    }
    
    try {
      // Preview endpoint doesn't exist yet in backend
      // Use a simple GET to view data instead
      const response = await axios.get(`${API_BASE}/silver/view/${domain}/${selectedTable.table_name}`, {
        params: {
          page: 1,
          page_size: 100
        }
      });
      
      if (response.data) {
        // Set mock preview data for now
        setPreviewData({
          rows_input: selectedTable.row_count || 0,
          rows_output: selectedTable.row_count || 0,
          rows_quarantined: 0,
          duplicates_removed: 0,
          rows_rejected: 0  
        });
        console.log('[Silver] Preview data set');
      }
    } catch (error) {
      console.warn('[Silver] Preview API not available:', error.message);
    }
  };

  const handleExecute = async () => {
    console.log('[Silver] Execute clicked', {
      selectedTable,
      domain,
      useSparkEngine,
      runBenchmark,
      executionMode,
      watermarkColumn
    });
    
    if (!selectedTable) {
      console.warn('[Silver] No table selected');
      return;
    }

    if (isExecuting) {
      console.warn('[Silver] Already executing');
      return;
    }

    setIsExecuting(true);
    setIsStreaming(true);
    setTransformationLogs([]);
    setExecutionStatus(`Starting ${useSparkEngine ? 'Spark' : 'Pandas'} transformation...`);
    
    // Start real-time log simulation
    simulateRealTimeTransformation();
    
    try {
      // Prepare quality rules from activeRules state
      const rules = Object.values(activeRules).map(rule => ({
        id: rule.id,
        name: rule.name,
        type: rule.type,
        column: rule.column,
        action: rule.action,
        threshold: rule.threshold,
        params: rule.params || {}
      }));
      
      const startTime = Date.now();
      let sparkResult = null;
      let pandasResult = null;
      
      // ===== SPARK EXECUTION (Primary) =====
      if (useSparkEngine) {
        console.log('[Silver] Running Spark transformation...');
        const sparkRequestBody = {
          source: domain || 'finance',
          entity: selectedTable.table_name,
          domain: domain || 'finance',
          execution_mode: executionMode,
          use_spark: true,
          watermark_column: executionMode === 'incremental' ? watermarkColumn : null,
          rules: rules
        };
        
        const sparkResponse = await axios.post(
          `${API_BASE}/silver/process-spark`,
          sparkRequestBody,
          { headers: { 'Content-Type': 'application/json' } }
        );
        
        sparkResult = {
          job_id: sparkResponse.data.job_id,
          engine: 'spark',
          start_time: startTime
        };
        
        console.log('[Silver] Spark job started:', sparkResult.job_id);
        setExecutionStatus(`⚡ Spark job ${sparkResult.job_id} started`);
      }
      
      // ===== OPTIONAL: PANDAS BENCHMARK =====
      if (runBenchmark && !useSparkEngine) {
        console.log('[Silver] Running Pandas transformation for benchmark...');
        const pandasResponse = await axios.post(`${API_BASE}/silver/process`, null, {
          params: {
            source: domain || 'finance',
            entity: selectedTable.table_name,
            source_type: selectedTable.source_type || 'postgres'
          }
        });
        
        pandasResult = {
          job_id: pandasResponse.data.job_id,
          engine: 'pandas',
          start_time: Date.now()
        };
        
        console.log('[Silver] Pandas benchmark job started:', pandasResult.job_id);
      }
      
      // Poll the primary job (Spark or Pandas)
      const primaryJob = sparkResult || pandasResult;
      if (primaryJob) {
        pollJobStatus(primaryJob.job_id, primaryJob.engine, primaryJob.start_time);
      }
      
    } catch (error) {
      console.error('[Silver] Execute failed:', error);
      setExecutionStatus(`❌ Failed to start: ${error.message}`);
      setIsExecuting(false);
    }
  };

  const pollJobStatus = async (jobId, engine = 'spark', startTime = Date.now()) => {
    const maxAttempts = 60; // 2 minutes max
    let attempts = 0;

    const interval = setInterval(async () => {
      try {
        attempts++;
        const response = await axios.get(`${API_BASE}/silver/status/${jobId}`);
        const job = response.data;

        console.log('[Silver] Job status:', job.status, '| Engine:', engine, '| Progress:', job.progress, '| Message:', job.message);
        setExecutionStatus(job.message || job.status);

        if (job.status === 'completed') {
          clearInterval(interval);
          const endTime = Date.now();
          const executionTimeMs = endTime - startTime;
          const executionTimeSec = (executionTimeMs / 1000).toFixed(2);
          
          setPipelineSteps(prev => prev.map(step => ({ ...step, status: 'completed' })));
          setExecutionStatus(`✅ Transformation completed in ${executionTimeSec}s (${engine.toUpperCase()})`);
          setIsExecuting(false);
          
          // Store performance metrics
          const metrics = {
            engine: engine,
            execution_time_ms: executionTimeMs,
            execution_time_sec: executionTimeSec,
            rows_processed: job.metrics?.final_rows || job.metrics?.rows_processed || 0,
            rows_quarantined: job.metrics?.rows_quarantined || 0,
            dataset_size_mb: datasetSizeInfo?.size_mb || 0,
            timestamp: new Date().toISOString(),
            throughput_rows_per_sec: job.metrics?.final_rows ? Math.round(job.metrics.final_rows / (executionTimeMs / 1000)) : 0
          };
          
          setPerformanceMetrics(prev => ({
            ...prev,
            [engine]: metrics
          }));
          
          console.log('[Silver] Job completed. Performance:', metrics);
          
          // Show detailed completion message with stats
          showNotification(
            `${engine.toUpperCase()} transformation completed: ${metrics.rows_processed.toLocaleString()} rows in ${executionTimeSec}s (${metrics.throughput_rows_per_sec.toLocaleString()} rows/sec)`,
            'success'
          );
          
        } else if (job.status === 'failed') {
          clearInterval(interval);
          const errorMsg = job.error_message || job.error || job.message || 'Unknown error';
          setExecutionStatus(`❌ Job failed: ${errorMsg}`);
          setIsExecuting(false);
          console.error('[Silver] Job failed:', errorMsg);
          console.error('[Silver] Full job object:', job);
        } else if (attempts >= maxAttempts) {
          clearInterval(interval);
          setExecutionStatus('⏱️ Polling timeout');
          setIsExecuting(false);
          console.warn('[Silver] Job polling timeout');
        }
      } catch (error) {
        clearInterval(interval);
        setExecutionStatus(`❌ Error: ${error.message}`);
        setIsExecuting(false);
        console.error('[Silver] Status poll failed:', error);
      }
    }, 2000);
  };
  
  // ===== ENTERPRISE FEATURE HANDLERS =====
  const showNotification = (message, type = 'success') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };
  
  const handleSaveConfiguration = () => {
    const config = {
      id: Date.now(),
      name: `${selectedTable?.table_name || 'Config'}_${new Date().toISOString().split('T')[0]}`,
      executionMode,
      watermarkColumn,
      activeRules,
      columnMappings,
      timestamp: new Date().toISOString()
    };
    setSavedConfigurations(prev => [...prev, config]);
    showNotification('Configuration saved successfully', 'success');
  };
  
  const handleLoadConfiguration = (config) => {
    setExecutionMode(config.executionMode);
    setWatermarkColumn(config.watermarkColumn);
    setActiveRules(config.activeRules);
    setColumnMappings(config.columnMappings);
    showNotification(`Loaded configuration: ${config.name}`, 'info');
    setShowTemplateLibrary(false);
  };
  
  const handleExportConfiguration = () => {
    const config = {
      executionMode,
      watermarkColumn,
      activeRules,
      columnMappings,
      exportedAt: new Date().toISOString(),
      table: selectedTable?.table_name
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `silver_config_${selectedTable?.table_name}_${Date.now()}.json`;
    a.click();
    showNotification('Configuration exported', 'success');
  };
  
  const handleBulkEnableRules = (category) => {
    const categoryRules = RULE_CATEGORIES[category]?.rules || [];
    const updates = {};
    categoryRules.forEach(rule => {
      updates[rule.id] = true;
    });
    setActiveRules(prev => ({ ...prev, ...updates }));
    showNotification(`Enabled all ${RULE_CATEGORIES[category]?.category} rules`, 'success');
  };
  
  const handleBulkDisableRules = (category) => {
    const categoryRules = RULE_CATEGORIES[category]?.rules || [];
    const updates = {};
    categoryRules.forEach(rule => {
      updates[rule.id] = false;
    });
    setActiveRules(prev => ({ ...prev, ...updates }));
    showNotification(`Disabled all ${RULE_CATEGORIES[category]?.category} rules`, 'info');
  };

  // ===== NEW HANDLERS FOR RICH FEATURES =====
  
  // Toggle column constraint
  const handleToggleConstraint = (columnName, constraintType, value) => {
    setColumnConstraints(prev => ({
      ...prev,
      [columnName]: {
        ...prev[columnName],
        [constraintType]: value
      }
    }));
  };
  
  // Set column as primary key
  const handleSetPrimaryKey = (columnName) => {
    setColumnConstraints(prev => {
      const newConstraints = { ...prev };
      // Remove primary key from all other columns
      Object.keys(newConstraints).forEach(col => {
        if (newConstraints[col]) {
          newConstraints[col].isPrimaryKey = false;
        }
      });
      // Set new primary key
      return {
        ...newConstraints,
        [columnName]: {
          ...newConstraints[columnName],
          isPrimaryKey: true,
          unique: true, // Primary key implies unique
          notNull: true // Primary key implies not null
        }
      };
    });
    showNotification(`Set ${columnName} as primary key`, 'success');
  };
  
  // Load transformation preview
  const handleLoadPreview = async () => {
    if (!selectedTable) {
      showNotification('Please select a table first', 'error');
      return;
    }

    setPreviewLoading(true);
    setShowPreview(true);
    
    try {
      // Get real data from Bronze layer (before transformation)
      const bronzeResponse = await axios.get(`${API_BASE}/bronze/view/${domain}/${selectedTable.table_name}`, {
        params: {
          page: 1,
          page_size: 10
        }
      });
      
      const bronzeData = bronzeResponse.data?.data || [];
      
      // Get data from Silver layer if it exists (after transformation)
      let silverData = [];
      try {
        const silverResponse = await axios.get(`${API_BASE}/silver/view/${domain}/${selectedTable.table_name}`, {
          params: {
            page: 1,
            page_size: 10
          }
        });
        silverData = silverResponse.data?.data || [];
      } catch (error) {
        // Silver data might not exist yet, we'll show mock transformed data
        console.log('[Silver] No silver data yet, showing simulated transformation');
        
        // Simulate transformation with DQ status based on rules
        silverData = bronzeData.slice(0, 10).map((row, idx) => {
          const transformedRow = { ...row };
          
          // Apply mock data quality checks
          const hasNullPK = Object.keys(row).some(key => 
            key.includes('id') && (row[key] === null || row[key] === undefined || row[key] === '')
          );
          const hasInvalidData = Object.values(row).some(val => 
            val === '99-99-9999' || val === 'invalid' || (typeof val === 'string' && val.trim() === '')
          );
          
          if (hasNullPK) {
            transformedRow._dq_status = 'REJECTED';
            transformedRow._dq_reason = 'NULL primary key';
          } else if (hasInvalidData) {
            transformedRow._dq_status = 'QUARANTINED';
            transformedRow._dq_reason = 'Invalid data format';
          } else {
            transformedRow._dq_status = 'PASSED';
            transformedRow._dq_reason = null;
          }
          
          return transformedRow;
        });
      }
      
      // Get columns from the first row
      const columns = bronzeData.length > 0 ? Object.keys(bronzeData[0]) : [];
      
      setPreviewData({
        before: bronzeData.slice(0, 10),
        after: silverData.slice(0, 10),
        columns: columns
      });
      
      showNotification(`Preview loaded (${Math.min(bronzeData.length, 10)} rows)`, 'success');
    } catch (error) {
      console.error('[Silver] Preview failed:', error);
      showNotification(`Failed to load preview: ${error.message}`, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // ===== MAIN RENDER WITH TAB NAVIGATION =====
  return (
    <div className="silver-wrapper">
      {/* Top-Level Tab Navigation */}
      <div className="silver-main-tabs">
        <button 
          className={`main-tab ${view === 'selection' ? 'active' : ''}`}
          onClick={() => setView('selection')}
        >
          <Database size={18} />
          <span>Silver Tables</span>
          {silverTables.length > 0 && (
            <span className="tab-count">{silverTables.length}</span>
          )}
        </button>
        <button 
          className={`main-tab ${view === 'studio' ? 'active' : ''}`}
          onClick={() => view === 'studio' ? null : setView('studio')}
          disabled={!selectedTable}
        >
          <Activity size={18} />
          <span>Transformation Control</span>
          {selectedTable && (
            <span className="tab-table-name">{selectedTable.table_name}</span>
          )}
        </button>
      </div>

      {/* TABLE SELECTION VIEW */}
      {view === 'selection' && (() => {
    let filteredTables = silverTables.filter(table => {
      const matchesSearch = table.table_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesSource = !filterSource || table.source_type === filterSource;
      const matchesFormat = !filterFormat || table.format === filterFormat;
      const matchesStatus = !filterStatus || table.status === filterStatus;
      const matchesDataType = !filterDataType || table.data_type === filterDataType;
      return matchesSearch && matchesSource && matchesFormat && matchesStatus && matchesDataType;
    });

    // Sort tables
    filteredTables = [...filteredTables].sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      if (sortBy === 'last_modified') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });

    return (
      <div className="silver-container">
        {/* Silver Layer Header Card */}
        <div className="layer-header-card">
          <div className="layer-header-content">
            <div>
              <h1 className="layer-title" style={{ color: '#3d3a3a', fontWeight: 700 }}>
                Silver Layer — Data Transformation
              </h1>
              <p className="layer-subtitle">
                Cleaned, validated, and transformed data ready for analytics
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {/* CDC Status Indicator */}
              {Object.keys(cdcStatus).length > 0 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  background: Object.values(cdcStatus).some(j => j.status === 'running') ? '#d1fae5' : '#f3f4f6',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: '500',
                  color: Object.values(cdcStatus).some(j => j.status === 'running') ? '#065f46' : '#6b7280'
                }}>
                  <Activity size={16} className={Object.values(cdcStatus).some(j => j.status === 'running') ? 'pulse-animation' : ''} />
                  <span>
                    {Object.values(cdcStatus).filter(j => j.status === 'running').length} CDC Stream{Object.values(cdcStatus).filter(j => j.status === 'running').length !== 1 ? 's' : ''} Active
                  </span>
                </div>
              )}
              <button className="btn-secondary" onClick={() => { loadBronzeTables(); loadCDCStatus(); }}>
                <RefreshCw size={16} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Pipeline Status */}
        <PipelineStatus />

        {/* Search & Filter bar */}
        <div className="filter-section">
          <div className="search-bar">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search Silver tables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="filter-controls">
            <button 
              className={`btn-filter ${showFilters ? 'active' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter size={16} />
              Filters
              {(filterSource || filterFormat || filterStatus || filterDataType) && <span className="filter-dot" />}
            </button>
            
            <div className="sort-control">
              <span className="label">Sort:</span>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="last_modified">Last Modified</option>
                <option value="table_name">Table Name</option>
                <option value="row_count">Row Count</option>
                <option value="source_type">Source Type</option>
              </select>
              <button 
                className="btn-sort-order"
                onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>
          </div>
        </div>

        {/* Filter panel */}
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-group">
              <label>Source Type:</label>
              <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
                <option value="">All Sources</option>
                <option value="postgres">PostgreSQL</option>
                <option value="mariadb">MariaDB</option>
                <option value="mongodb">MongoDB</option>
                <option value="s3">S3</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Format:</label>
              <select value={filterFormat} onChange={(e) => setFilterFormat(e.target.value)}>
                <option value="">All Formats</option>
                <option value="parquet">Parquet</option>
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
                <option value="image">Image</option>
                <option value="video">Video</option>
                <option value="audio">Audio</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Status:</label>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <option value="">All Status</option>
                <option value="bronze">Bronze (Not Processed)</option>
                <option value="cleaned">Cleaned (Processed)</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Data Type:</label>
              <select value={filterDataType} onChange={(e) => setFilterDataType(e.target.value)}>
                <option value="">All Types</option>
                <option value="structured">Structured</option>
                <option value="unstructured">Unstructured</option>
              </select>
            </div>
            <button 
              className="btn-clear-filters"
              onClick={() => { setFilterSource(''); setFilterFormat(''); setFilterStatus(''); setFilterDataType(''); }}
            >
              Clear Filters
            </button>
          </div>
        )}

        {/* Tables list */}
        {loading ? (
          <div className="loading-container">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="tables-wrapper">
            <div className="tables-header-info">
              <span>Showing <strong>{filteredTables.length}</strong> of <strong>{silverTables.length}</strong> tables</span>
            </div>
            <div className="tables-container">
              <table className="tables-table">
                <thead>
                  <tr>
                    <th>Table Name</th>
                    <th>Status</th>
                    <th>Data Type</th>
                    <th>Source</th>
                    <th>Rows</th>
                    <th>Quality</th>
                    <th>Last Modified</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTables.map(table => {
                    const lastModified = new Date(table.last_modified);
                    const now = new Date();
                    const diffHours = Math.floor((now - lastModified) / (1000 * 60 * 60));
                    const timeAgo = diffHours < 1 ? 'Just now' :
                                   diffHours < 24 ? `${diffHours}h ago` :
                                   `${Math.floor(diffHours / 24)}d ago`;
                    
                    return (
                      <tr key={table.table_name} className="table-row">
                        <td>
                          <div className="table-name-cell">
                            {table.data_type === 'unstructured' ? (
                              table.unstructured_type === 'image' ? '🖼️' :
                              table.unstructured_type === 'video' ? '🎥' :
                              table.unstructured_type === 'audio' ? '🎧' : 
                              <Database size={16} className="table-icon" />
                            ) : (
                              <Database size={16} className="table-icon" />
                            )}
                            <span className="table-name">{table.table_name}</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span className={`status-badge status-${table.status}`}>
                              {table.status === 'cleaned' ? (
                                <>
                                  <CheckCircle size={14} style={{ marginRight: '4px' }} />
                                  Cleaned
                                </>
                              ) : (
                                <>
                                  <Clock size={14} style={{ marginRight: '4px' }} />
                                  Bronze
                                </>
                              )}
                            </span>
                            {isCDCEnabled(table.table_name) && (
                              <span 
                                className="cdc-badge"
                                title="CDC Streaming Enabled"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '4px 8px',
                                  borderRadius: '12px',
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  background: getCDCStreamStatus(table.table_name) === 'running' ? '#d1fae5' : '#e0f2fe',
                                  color: getCDCStreamStatus(table.table_name) === 'running' ? '#065f46' : '#0369a1'
                                }}
                              >
                                <Activity size={12} />
                                {getCDCStreamStatus(table.table_name) === 'running' ? 'CDC LIVE' : 'CDC'}
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className={`datatype-badge datatype-${table.data_type}`}>
                            {table.data_type === 'structured' ? 'Structured' : 
                             `Unstructured (${table.unstructured_type})`}
                          </span>
                        </td>
                        <td>
                          <span className={`source-badge badge-${table.source_type}`}>
                            {table.source_type}
                          </span>
                        </td>
                        <td className="numeric">{(table.row_count || 0).toLocaleString()}</td>
                        <td>
                          {table.quality_score !== null && table.quality_score !== undefined ? (
                            <span className={`quality-badge quality-${
                              table.quality_score >= 90 ? 'high' :
                              table.quality_score >= 70 ? 'medium' : 'low'
                            }`}>
                              {table.quality_score}%
                            </span>
                          ) : (
                            <span className="quality-badge quality-none">—</span>
                          )}
                        </td>
                        <td>
                          <div className="timestamp-cell">
                            <Clock size={14} />
                            <div>
                              <div className="timestamp">{lastModified.toLocaleString()}</div>
                              <div className="time-ago">{timeAgo}</div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <button 
                              className="btn-transform-small"
                              onClick={() => handleTableSelect(table)}
                            >
                              <Play size={14} />
                              Transform
                            </button>
                            {isCDCEnabled(table.table_name) && (
                              <button
                                className="btn-cdc-toggle"
                                onClick={() => handleCDCStreamToggle(table, getCDCStreamStatus(table.table_name) === 'running' ? 'stop' : 'start')}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '6px 10px',
                                  borderRadius: '6px',
                                  border: 'none',
                                  fontSize: '12px',
                                  fontWeight: '500',
                                  cursor: 'pointer',
                                  background: getCDCStreamStatus(table.table_name) === 'running' ? '#fecaca' : '#10b981',
                                  color: getCDCStreamStatus(table.table_name) === 'running' ? '#991b1b' : 'white',
                                  transition: 'all 0.2s'
                                }}
                                title={getCDCStreamStatus(table.table_name) === 'running' ? 'Stop CDC Stream' : 'Start CDC Stream'}
                              >
                                {getCDCStreamStatus(table.table_name) === 'running' ? (
                                  <>
                                    <Activity size={12} />
                                    Stop
                                  </>
                                ) : (
                                  <>
                                    <Activity size={12} />
                                    Start CDC
                                  </>
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <style>{`
          .silver-wrapper {
            min-height: 100vh;
            background: #f9fafb;
          }

          .silver-main-tabs {
            background: #ffffff;
            border-bottom: 2px solid #e5e7eb;
            display: flex;
            gap: 0;
            padding: 0 24px;
          }

          .main-tab {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 16px 24px;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: #6b7280;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
          }

          .main-tab:hover:not(:disabled) {
            color: #374151;
            background: #f9fafb;
          }

          .main-tab.active {
            color: #3b82f6;
            border-bottom-color: #3b82f6;
            background: #eff6ff;
          }

          .main-tab:disabled {
            color: #d1d5db;
            cursor: not-allowed;
          }

          .tab-count {
            background: #3b82f6;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
          }

          .main-tab.active .tab-count {
            background: #2563eb;
          }

          .tab-table-name {
            font-size: 12px;
            color: #6b7280;
            background: #f3f4f6;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: 'Monaco', monospace;
          }

          .main-tab.active .tab-table-name {
            background: #dbeafe;
            color: #1e40af;
          }

          .silver-container {
            padding: 24px;
            background: #f9fafb;
            min-height: 100vh;
          }

          .layer-header-card {
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            padding: 24px 32px;
            margin-bottom: 24px;
          }

          .layer-header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
          }

          .layer-title {
            font-size: 32px;
            font-weight: 700;
            margin: 0 0 8px 0;
            letter-spacing: -0.5px;
            color: #C0C0C0 !important; /* Bright silver color */
          }

          .layer-subtitle {
            font-size: 16px;
            color: #000000;
            margin: 0;
            line-height: 1.5;
          }

          .page-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
          }

          .header-left {
            display: flex;
            gap: 16px;
            align-items: center;
          }

          .header-icon {
            color: #3b82f6;
            flex-shrink: 0;
          }

          .page-header h1 {
            font-size: 24px;
            font-weight: 600;
            color: #111827;
            margin: 0 0 4px 0;
          }

          .page-header p {
            color: #242527;
            margin: 0;
            font-size: 14px;
          }

          .btn-secondary {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border: 1.5px solid #6B7280;
            border-radius: 8px;
            background: white;
            color: #6B7280;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
          }

          .btn-secondary:hover {
            background: #f3f4f6;
            border-color: #4b5563;
          }

          .filter-section {
            display: flex;
            gap: 16px;
            margin-bottom: 16px;
          }

          .search-bar {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
          }

          .search-bar input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 14px;
            color: #111827;
          }

          .search-bar input::placeholder {
            color: #9ca3af;
          }

          .filter-controls {
            display: flex;
            gap: 12px;
            align-items: center;
          }

          .btn-filter {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            color: #374151;
            transition: all 0.2s;
            position: relative;
          }

          .btn-filter:hover, .btn-filter.active {
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
          }

          .filter-dot {
            width: 6px;
            height: 6px;
            background: #ef4444;
            border-radius: 50%;
            position: absolute;
            top: 8px;
            right: 8px;
          }

          .sort-control {
            display: flex;
            align-items: center;
            gap: 8px;
            background: white;
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
          }

          .sort-control .label {
            font-size: 13px;
            color: #6b7280;
            font-weight: 500;
          }

          .sort-control select {
            border: none;
            outline: none;
            font-size: 14px;
            color: #111827;
            background: transparent;
            cursor: pointer;
          }

          .btn-sort-order {
            padding: 4px 8px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
          }

          .btn-sort-order:hover {
            background: #f3f4f6;
          }

          .filter-panel {
            display: flex;
            gap: 16px;
            padding: 16px;
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            margin-bottom: 16px;
          }

          .filter-group {
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .filter-group label {
            font-size: 13px;
            color: #6b7280;
            font-weight: 500;
          }

          .filter-group select {
            padding: 6px 12px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            outline: none;
          }

          .btn-clear-filters {
            padding: 6px 12px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            margin-left: auto;
          }

          .btn-clear-filters:hover {
            background: #dc2626;
          }

          .loading-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 400px;
          }

          .tables-wrapper {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
          }

          .tables-header-info {
            padding: 12px 16px;
            background: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
          }

          .tables-header-info strong {
            color: #111827;
            font-weight: 600;
          }

          .tables-container {
            overflow-x: auto;
          }

          .tables-table {
            width: 100%;
            border-collapse: collapse;
          }

          .tables-table thead {
            background: #f9fafb;
            border-bottom: 2px solid #e5e7eb;
          }

          .tables-table th {
            padding: 12px 16px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }

          .tables-table tbody tr {
            border-bottom: 1px solid #f3f4f6;
            transition: background 0.2s;
          }

          .tables-table tbody tr:hover {
            background: #f9fafb;
          }

          .tables-table td {
            padding: 14px 16px;
            font-size: 14px;
            color: #111827;
          }

          .table-name-cell {
            display: flex;
            align-items: center;
            gap: 10px;
          }

          .table-name-cell .table-icon {
            color: #3b82f6;
          }

          .table-name {
            font-weight: 500;
            font-family: 'Monaco', 'Courier New', monospace;
          }

          .source-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
            text-transform: capitalize;
          }

          .badge-postgres {
            background: #dbeafe;
            color: #1e40af;
          }

          .badge-mariadb {
            background: #fed7aa;
            color: #9a3412;
          }

          .badge-mongodb {
            background: #d1fae5;
            color: #065f46;
          }

          .badge-s3 {
            background: #e9d5ff;
            color: #6b21a8;
          }

          .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
          }

          .status-cleaned {
            background: #d1fae5;
            color: #065f46;
          }

          .status-bronze {
            background: #fef3c7;
            color: #92400e;
          }

          .datatype-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
          }

          .datatype-structured {
            background: #dbeafe;
            color: #1e40af;
          }

          .datatype-unstructured {
            background: #fce7f3;
            color: #9f1239;
          }

          .quality-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
          }

          .quality-high {
            background: #d1fae5;
            color: #065f46;
          }

          .quality-medium {
            background: #fed7aa;
            color: #9a3412;
          }

          .quality-low {
            background: #fee2e2;
            color: #991b1b;
          }

          .quality-none {
            background: #f3f4f6;
            color: #9ca3af;
          }

          .numeric {
            font-family: 'Monaco', 'Courier New', monospace;
            font-weight: 500;
          }

          .timestamp-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #6b7280;
          }

          .timestamp-cell > div {
            display: flex;
            flex-direction: column;
            gap: 2px;
          }

          .timestamp {
            font-size: 13px;
            color: #374151;
          }

          .time-ago {
            font-size: 11px;
            color: #9ca3af;
          }

          .origin-badge {
            font-size: 12px;
            color: #6b7280;
            font-family: 'Monaco', 'Courier New', monospace;
            background: #f3f4f6;
            padding: 4px 8px;
            border-radius: 4px;
          }

          .btn-transform-small {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
          }

          .btn-transform-small:hover {
            background: #2563eb;
            transform: translateY(-1px);
          }

          /* CDC Status Pulse Animation */
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
              transform: scale(1);
            }
            50% {
              opacity: 0.7;
              transform: scale(1.1);
            }
          }

          .pulse-animation {
            animation: pulse 2s ease-in-out infinite;
          }

          .cdc-badge {
            animation: fadeIn 0.3s ease-in;
          }

          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translateY(-2px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

        `}</style>
      </div>
    )})()}

      {/* TRANSFORMATION STUDIO VIEW */}
      {view === 'studio' && selectedTable && (() => {
  // ===== RENDER: TRANSFORMATION STUDIO =====
  const enabledRuleCount = Object.values(activeRules).filter(Boolean).length;

  return (
    <div className="studio-container">
      {/* Header */}
      <div className="studio-header">
        <button className="btn-back" onClick={handleBackToSelection}>
          <ArrowLeft size={18} />
          Back to Tables
        </button>
        <div className="breadcrumb">
          <span className="breadcrumb-item bronze">Bronze</span>
          <ChevronRight size={16} className="breadcrumb-sep" />
          <span className="breadcrumb-item silver">Silver</span>
          <ChevronRight size={16} className="breadcrumb-sep" />
          <span className="breadcrumb-item">{selectedTable?.table_name}</span>
        </div>
        <div className="header-actions">
          <button 
            className="btn-icon-action"
            onClick={() => setShowHelp(!showHelp)}
            title="Help (F1)"
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </button>
          <button 
            className="btn-icon-action"
            onClick={() => setShowCommandPalette(true)}
            title="Command Palette (Ctrl+K)"
          >
            <Search size={16} />
          </button>
          <button 
            className="btn-icon-action"
            onClick={() => setShowTemplateLibrary(!showTemplateLibrary)}
            title="Saved Configurations"
          >
            <FileText size={16} />
            {savedConfigurations.length > 0 && (
              <span className="badge-count">{savedConfigurations.length}</span>
            )}
          </button>
          <div className="divider-vertical"></div>
          <button 
            type="button" 
            className="btn-preview" 
            onClick={handlePreview}
            disabled={isExecuting}
            title="Preview transformation results"
          >
            <Eye size={16} />
            Preview
          </button>
          <button 
            type="button" 
            className="btn-execute" 
            onClick={handleExecute}
            disabled={isExecuting}
            title="Execute transformation pipeline"
          >
            <Play size={16} />
            {isExecuting ? 'Processing...' : 'Execute'}
          </button>
          {executionStatus && (
            <div className="execution-status">
              {executionStatus}
            </div>
          )}
        </div>
      </div>
      
      {/* Toast Notifications */}
      <div className="toast-container">
        {notifications.map(notif => (
          <div key={notif.id} className={`toast toast-${notif.type}`}>
            <div className="toast-icon">
              {notif.type === 'success' && <CheckCircle size={18} />}
              {notif.type === 'error' && <AlertTriangle size={18} />}
              {notif.type === 'info' && <Activity size={18} />}
            </div>
            <span className="toast-message">{notif.message}</span>
          </div>
        ))}
      </div>
      
      {/* Command Palette */}
      {showCommandPalette && (
        <div className="modal-overlay" onClick={() => setShowCommandPalette(false)}>
          <div className="command-palette" onClick={e => e.stopPropagation()}>
            <div className="command-palette-header">
              <Search size={18} />
              <input
                type="text"
                placeholder="Type a command or search..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                autoFocus
                className="command-palette-input"
              />
              <kbd className="kbd">Esc</kbd>
            </div>
            <div className="command-palette-list">
              <div className="command-section">
                <div className="command-section-title">Actions</div>
                <button className="command-item" onClick={() => { handleExecute(); setShowCommandPalette(false); }}>
                  <Play size={16} />
                  <span>Execute Transformation</span>
                  <kbd className="kbd">Enter</kbd>
                </button>
                <button className="command-item" onClick={() => { handleSaveConfiguration(); setShowCommandPalette(false); }}>
                  <FileText size={16} />
                  <span>Save Configuration</span>
                  <kbd className="kbd">Ctrl+S</kbd>
                </button>
                <button className="command-item" onClick={() => { handleExportConfiguration(); setShowCommandPalette(false); }}>
                  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  <span>Export Configuration</span>
                </button>
              </div>
              <div className="command-section">
                <div className="command-section-title">Navigate</div>
                <button className="command-item" onClick={() => { setActiveTab('transform'); setShowCommandPalette(false); }}>
                  <Layers size={16} />
                  <span>Go to Transform</span>
                  <kbd className="kbd">Alt+1</kbd>
                </button>
                <button className="command-item" onClick={() => { setActiveTab('quality'); setShowCommandPalette(false); }}>
                  <BarChart3 size={16} />
                  <span>Go to Quality</span>
                  <kbd className="kbd">Alt+2</kbd>
                </button>
                <button className="command-item" onClick={() => { setActiveTab('monitor'); setShowCommandPalette(false); }}>
                  <Activity size={16} />
                  <span>Go to Monitor</span>
                  <kbd className="kbd">Alt+3</kbd>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Configuration Library */}
      {showTemplateLibrary && (
        <div className="modal-overlay" onClick={() => setShowTemplateLibrary(false)}>
          <div className="config-library" onClick={e => e.stopPropagation()}>
            <div className="config-library-header">
              <h3>Saved Configurations</h3>
              <button className="btn-close" onClick={() => setShowTemplateLibrary(false)}>×</button>
            </div>
            <div className="config-library-list">
              {savedConfigurations.length === 0 ? (
                <div className="empty-state-small">
                  <FileText size={32} style={{ opacity: 0.3 }} />
                  <p>No saved configurations</p>
                  <p style={{ fontSize: '12px', opacity: 0.7 }}>Press Ctrl+S to save current configuration</p>
                </div>
              ) : (
                savedConfigurations.map(config => (
                  <div key={config.id} className="config-item">
                    <div className="config-item-header">
                      <strong>{config.name}</strong>
                      <span className="config-timestamp">
                        {new Date(config.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="config-item-details">
                      <span className="config-tag">{config.executionMode}</span>
                      <span className="config-tag">{Object.values(config.activeRules).filter(Boolean).length} rules</span>
                      <span className="config-tag">{config.columnMappings.length} mappings</span>
                    </div>
                    <button 
                      className="btn-load-config"
                      onClick={() => handleLoadConfiguration(config)}
                    >
                      Load
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="silver-tabs">
        <button 
          className={`tab-button ${activeTab === 'transform' ? 'active' : ''}`}
          onClick={() => setActiveTab('transform')}
        >
          <Layers size={16} />
          Transform
        </button>
        <button 
          className={`tab-button ${activeTab === 'quality' ? 'active' : ''}`}
          onClick={() => setActiveTab('quality')}
        >
          <BarChart3 size={16} />
          Quality
        </button>
      </div>

      {/* Main content */}
      <div className="studio-content">
        {/* ============ TRANSFORM TAB ============ */}
        {activeTab === 'transform' && (
        <div className="tab-content tab-transform-rich">
          
          {/* DATA TYPE SELECTOR */}
          <div className="data-type-selector-card">
            <div className="data-type-header">
              <h4>Data Type</h4>
              <p>Choose the type of data you're transforming</p>
            </div>
            <div className="data-type-buttons">
              <button 
                className={`data-type-btn ${dataType === 'structured' ? 'active' : ''}`}
                onClick={() => setDataType('structured')}
              >
                <Database size={20} />
                <div>
                  <strong>Structured Data</strong>
                  <small>Tables, CSV, SQL databases</small>
                </div>
              </button>
              <button 
                className={`data-type-btn ${dataType === 'unstructured' ? 'active' : ''}`}
                onClick={() => setDataType('unstructured')}
              >
                <FileText size={20} />
                <div>
                  <strong>Unstructured Data</strong>
                  <small>Images, Videos, Audio files</small>
                </div>
              </button>
            </div>
            
            {dataType === 'unstructured' && (
              <div className="unstructured-type-selector">
                <label>Unstructured Type:</label>
                <div className="unstructured-type-buttons">
                  <button 
                    className={`type-chip ${unstructuredType === 'image' ? 'active' : ''}`}
                    onClick={() => setUnstructuredType('image')}
                  >
                    🖼️ Image
                  </button>
                  <button 
                    className={`type-chip ${unstructuredType === 'video' ? 'active' : ''}`}
                    onClick={() => setUnstructuredType('video')}
                  >
                    🎥 Video
                  </button>
                  <button 
                    className={`type-chip ${unstructuredType === 'audio' ? 'active' : ''}`}
                    onClick={() => setUnstructuredType('audio')}
                  >
                    🎧 Audio
                  </button>
                </div>
              </div>
            )}
          </div>
          
          {/* 1. SCHEMA EVOLUTION & MAPPING UI */}
          <div className="rich-section schema-evolution-section">
            <div className="section-header-rich">
              <div className="section-title-group">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                  <line x1="12" y1="22.08" x2="12" y2="12"/>
                </svg>
                <div>
                  <h3>Schema Evolution & Mapping</h3>
                  <p className="section-subtitle">Define how source columns transform to target schema</p>
                </div>
              </div>
              <div className="section-actions-rich">
                <button 
                  className={`toggle-btn ${schemaEvolutionMode === 'strict' ? 'active' : ''}`}
                  onClick={() => setSchemaEvolutionMode('strict')}
                  title="Reject new columns not in target schema"
                >
                  🔒 Strict Schema
                </button>
                <button 
                  className={`toggle-btn ${schemaEvolutionMode === 'flexible' ? 'active' : ''}`}
                  onClick={() => setSchemaEvolutionMode('flexible')}
                  title="Auto-add new columns to target schema"
                >
                  ✨ Allow Evolution
                </button>
                <span className="count-badge-rich">{columnMappings.length} columns</span>
              </div>
            </div>
            
            {schemaEvolutionMode === 'flexible' && (
              <div className="info-banner evolution-banner">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
                </svg>
                <span><strong>Schema Evolution Enabled:</strong> New columns in source will be automatically added to target schema</span>
              </div>
            )}
            
            <div className="schema-mapping-table">
              <table className="mapping-table-rich">
                <thead>
                  <tr>
                    <th className="col-source">Source Column</th>
                    <th className="col-source-type">Source Type</th>
                    <th className="col-arrow">→</th>
                    <th className="col-target">Target Column</th>
                    <th className="col-target-type">Target Type</th>
                    <th className="col-transform">Transform</th>
                  </tr>
                </thead>
                <tbody>
                  {columnMappings.map((mapping, idx) => (
                    <tr key={idx} className="mapping-row-rich">
                      <td className="col-source">
                        <code className="col-name-code">{mapping.source}</code>
                      </td>
                      <td className="col-source-type">
                        <span className="type-badge source-type">{mapping.sourceType}</span>
                      </td>
                      <td className="col-arrow">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                        </svg>
                      </td>
                      <td className="col-target">
                        <code className="col-name-code">{mapping.target}</code>
                      </td>
                      <td className="col-target-type">
                        <span className="type-badge target-type">{mapping.targetType}</span>
                      </td>
                      <td className="col-transform">
                        <span 
                          className="transform-badge-rich" 
                          style={{ 
                            background: TRANSFORM_COLORS[mapping.transformType] + '20', 
                            color: TRANSFORM_COLORS[mapping.transformType],
                            borderColor: TRANSFORM_COLORS[mapping.transformType]
                          }}
                        >
                          {mapping.transform}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Execution Mode */}
            <div className="execution-mode-rich">
              <label className="mode-label">Execution Strategy:</label>
              <div className="execution-mode-selector-rich">
                {EXECUTION_MODES.map(mode => (
                  <button
                    key={mode.id}
                    className={`mode-chip-rich ${executionMode === mode.id ? 'active' : ''}`}
                    onClick={() => setExecutionMode(mode.id)}
                  >
                    {mode.label}
                    {mode.recommended && <span className="rec-badge">★</span>}
                  </button>
                ))}
              </div>
              
              {executionMode === 'incremental' && (
                <div className="watermark-selector-rich">
                  <label>Watermark Column:</label>
                  <select value={watermarkColumn} onChange={(e) => setWatermarkColumn(e.target.value)}>
                    <option value="created_at">created_at</option>
                    <option value="updated_at">updated_at</option>
                    <option value="ingested_at">ingested_at</option>
                  </select>
                  <span className="watermark-info">
                    Will process rows where <code>{watermarkColumn}</code> &gt; last checkpoint
                  </span>
                </div>
              )}
            </div>
            
            {/* Spark Engine & Dataset Info */}
            <div className="execution-engine-panel" style={{
              backgroundColor: '#f8f4ff',
              border: '2px solid #9d7dff',
              borderRadius: '8px',
              padding: '16px',
              marginTop: '16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Activity size={18} style={{ color: '#7c3aed' }} />
                  <span style={{ fontWeight: 600, color: '#1f2937' }}>
                    Processing Engine
                  </span>
                </div>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 12px',
                  backgroundColor: '#7c3aed',
                  color: 'white',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontWeight: 600
                }}>
                  ⚡ Apache Spark + Iceberg
                </div>
              </div>
              
              {checkingSizeLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6b7280', fontSize: '14px' }}>
                  <RefreshCw size={14} className="spinning" />
                  <span>Analyzing dataset size...</span>
                </div>
              )}
              
              {datasetSizeInfo && !checkingSizeLoading && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', fontSize: '13px' }}>
                  <div>
                    <div style={{ color: '#6b7280', marginBottom: '4px' }}>Dataset Size</div>
                    <div style={{ fontWeight: 600, fontSize: '16px', color: '#1f2937' }}>
                      {datasetSizeInfo.size_mb.toFixed(2)} MB
                    </div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280', marginBottom: '4px' }}>Recommended Engine</div>
                    <div style={{ fontWeight: 600, fontSize: '16px', color: '#7c3aed' }}>
                      {datasetSizeInfo.recommend_spark ? 'Spark ⚡' : 'Pandas/Spark'}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: '#6b7280', marginBottom: '4px' }}>Storage Format</div>
                    <div style={{ fontWeight: 600, fontSize: '16px', color: '#1f2937' }}>
                      Parquet → Iceberg
                    </div>
                  </div>
                </div>
              )}
              
              {datasetSizeInfo && datasetSizeInfo.size_mb < 10 && (
                <div style={{
                  marginTop: '12px',
                  padding: '10px',
                  backgroundColor: '#fef3c7',
                  border: '1px solid #f59e0b',
                  borderRadius: '6px',
                  fontSize: '13px',
                  color: '#78350f',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <AlertTriangle size={14} />
                  <span>
                    <strong>Small dataset detected ({datasetSizeInfo.size_mb.toFixed(1)} MB).</strong>&nbsp;
                    Spark has ~5-10s JVM startup overhead. For production datasets &gt;100MB, Spark is 3-8x faster.
                  </span>
                </div>
              )}
              
              {/* Optional: Benchmark Mode */}
              <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e5e7eb' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: '#4b5563' }}>
                  <input
                    type="checkbox"
                    checked={runBenchmark}
                    onChange={(e) => setRunBenchmark(e.target.checked)}
                    style={{ width: '16px', height: '16px' }}
                  />
                  <span>
                    <strong>Enable Performance Benchmarking</strong>
                    <span style={{ color: '#9ca3af', marginLeft: '8px' }}>
                      (Track execution time for optimization analysis)
                    </span>
                  </span>
                </label>
              </div>
              
              {/* Performance Metrics Display */}
              {performanceMetrics && performanceMetrics.spark && (
                <div style={{
                  marginTop: '12px',
                  padding: '12px',
                  backgroundColor: '#ecfdf5',
                  border: '1px solid #10b981',
                  borderRadius: '6px'
                }}>
                  <div style={{ fontWeight: 600, marginBottom: '8px', color: '#065f46', fontSize: '14px' }}>
                    ⚡ Performance Results
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', fontSize: '13px' }}>
                    <div>
                      <div style={{ color: '#6b7280' }}>Execution Time</div>
                      <div style={{ fontWeight: 600, fontSize: '18px', color: '#059669' }}>
                        {performanceMetrics.spark.execution_time_sec}s
                      </div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280' }}>Rows Processed</div>
                      <div style={{ fontWeight: 600, fontSize: '18px', color: '#059669' }}>
                        {performanceMetrics.spark.rows_processed.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280' }}>Throughput</div>
                      <div style={{ fontWeight: 600, fontSize: '18px', color: '#059669' }}>
                        {performanceMetrics.spark.throughput_rows_per_sec.toLocaleString()} rows/s
                      </div>
                    </div>
                  </div>
                  
                  {performanceMetrics.pandas && (
                    <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #d1fae5' }}>
                      <div style={{ fontSize: '13px', color: '#065f46' }}>
                        <strong>Comparison:</strong> Spark was&nbsp;
                        <strong style={{ color: '#7c3aed' }}>
                          {(performanceMetrics.pandas.execution_time_ms / performanceMetrics.spark.execution_time_ms).toFixed(1)}x faster
                        </strong>
                        &nbsp;than Pandas ({performanceMetrics.pandas.execution_time_sec}s)
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Iceberg Actions */}
            {useSparkEngine && selectedTable && (
              <div style={{
                marginTop: '16px',
                padding: '12px',
                backgroundColor: '#faf5ff',
                border: '1px solid #c084fc',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Layers size={16} style={{ color: '#7c3aed' }} />
                  <span style={{ fontSize: '14px', fontWeight: 500, color: '#4b5563' }}>
                    Iceberg Table Features
                  </span>
                </div>
                <button
                  onClick={loadSnapshotHistory}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: 'white',
                    border: '1px solid #c084fc',
                    borderRadius: '6px',
                    color: '#7c3aed',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Clock size={14} />
                  View Snapshots (Time-Travel)
                </button>
              </div>
            )}
          </div>

          {/* UNSTRUCTURED DATA TRANSFORMATIONS */}
          {dataType === 'unstructured' && (
            <div className="rich-section unstructured-transforms-section">
              <div className="section-header-rich">
                <div className="section-title-group">
                  <span style={{ fontSize: '24px' }}>
                    {unstructuredType === 'image' ? '🖼️' : 
                     unstructuredType === 'video' ? '🎥' : '🎧'}
                  </span>
                  <div>
                    <h3>{unstructuredType === 'image' ? 'Image' : 
                         unstructuredType === 'video' ? 'Video' : 'Audio'} Transformation Rules</h3>
                    <p className="section-subtitle">Configure cleaning, standardization, and feature extraction</p>
                  </div>
                </div>
              </div>

              {/* Image Transformations */}
              {unstructuredType === 'image' && (
                <div className="unstructured-transforms-grid">
                  {/* 1. Cleaning / Quality Improvement */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🧹 Cleaning / Quality Improvement</h4>
                      <p>Improving raw image quality</p>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.removeCorrupted}
                        onChange={(e) => setImageTransforms({...imageTransforms, removeCorrupted: e.target.checked})}
                      />
                      <span>Remove corrupted files</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.resize}
                        onChange={(e) => setImageTransforms({...imageTransforms, resize: e.target.checked})}
                      />
                      <span>Resize to standard resolution</span>
                    </label>
                    
                    {imageTransforms.resize && (
                      <div className="image-resize-inputs">
                        <div className="input-group-inline">
                          <label>Width:</label>
                          <input 
                            type="number" 
                            value={imageTransforms.resizeWidth}
                            onChange={(e) => setImageTransforms({...imageTransforms, resizeWidth: parseInt(e.target.value)})}
                            className="size-input"
                          />
                        </div>
                        <div className="input-group-inline">
                          <label>Height:</label>
                          <input 
                            type="number" 
                            value={imageTransforms.resizeHeight}
                            onChange={(e) => setImageTransforms({...imageTransforms, resizeHeight: parseInt(e.target.value)})}
                            className="size-input"
                          />
                        </div>
                      </div>
                    )}
                    
                    <div className="select-group">
                      <label>Format Conversion:</label>
                      <select 
                        value={imageTransforms.formatConversion}
                        onChange={(e) => setImageTransforms({...imageTransforms, formatConversion: e.target.value})}
                      >
                        <option value="">No conversion</option>
                        <option value="PNG">Convert to PNG</option>
                        <option value="JPG">Convert to JPG</option>
                        <option value="WEBP">Convert to WEBP</option>
                        <option value="TIFF">Convert to TIFF</option>
                        <option value="BMP">Convert to BMP</option>
                      </select>
                    </div>
                  </div>

                  {/* 2. Standardization / Normalization */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>📐 Standardization / Normalization</h4>
                      <p>Making all images follow the same format</p>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.convertToRGB}
                        onChange={(e) => setImageTransforms({...imageTransforms, convertToRGB: e.target.checked})}
                      />
                      <span>Convert to RGB</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.normalizePixels}
                        onChange={(e) => setImageTransforms({...imageTransforms, normalizePixels: e.target.checked})}
                      />
                      <span>Normalize pixel values (0–255 → 0–1)</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.fixedAspectRatio}
                        onChange={(e) => setImageTransforms({...imageTransforms, fixedAspectRatio: e.target.checked})}
                      />
                      <span>Fixed aspect ratio</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.standardNaming}
                        onChange={(e) => setImageTransforms({...imageTransforms, standardNaming: e.target.checked})}
                      />
                      <span>Standard file naming</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.standardMetadata}
                        onChange={(e) => setImageTransforms({...imageTransforms, standardMetadata: e.target.checked})}
                      />
                      <span>Standard metadata format (timestamp, location)</span>
                    </label>
                  </div>

                  {/* 3. Feature Extraction / Transformation */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🔍 Feature Extraction / Transformation</h4>
                      <p>Convert images into machine-readable features</p>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.grayscale}
                        onChange={(e) => setImageTransforms({...imageTransforms, grayscale: e.target.checked})}
                      />
                      <span>Convert to grayscale</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.edgeDetection}
                        onChange={(e) => setImageTransforms({...imageTransforms, edgeDetection: e.target.checked})}
                      />
                      <span>Edge detection</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={imageTransforms.objectDetection}
                        onChange={(e) => setImageTransforms({...imageTransforms, objectDetection: e.target.checked})}
                      />
                      <span>Object detection (bounding boxes)</span>
                    </label>
                  </div>

                  {/* 4. Data Augmentation */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🔄 Data Augmentation</h4>
                      <p>Creating variations for AI training</p>
                    </div>
                    
                    <div className="augmentation-options">
                      {['Rotation', 'Flipping', 'Cropping', 'Brightness', 'Zoom'].map(aug => (
                        <label key={aug} className="checkbox-label-large">
                          <input 
                            type="checkbox" 
                            checked={imageTransforms.augmentation.includes(aug)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setImageTransforms({
                                  ...imageTransforms, 
                                  augmentation: [...imageTransforms.augmentation, aug]
                                });
                              } else {
                                setImageTransforms({
                                  ...imageTransforms, 
                                  augmentation: imageTransforms.augmentation.filter(a => a !== aug)
                                });
                              }
                            }}
                          />
                          <span>{aug}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Video Transformations */}
              {unstructuredType === 'video' && (
                <div className="unstructured-transforms-grid">
                  {/* 1. Cleaning / Preprocessing */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🧹 Cleaning / Preprocessing</h4>
                      <p>Basic video quality improvements</p>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.removeCorrupted}
                        onChange={(e) => setVideoTransforms({...videoTransforms, removeCorrupted: e.target.checked})}
                      />
                      <span>Remove corrupted files</span>
                    </label>
                    
                    <div className="select-group">
                      <label>Format Conversion:</label>
                      <select 
                        value={videoTransforms.formatConversion}
                        onChange={(e) => setVideoTransforms({...videoTransforms, formatConversion: e.target.value})}
                      >
                        <option value="">No conversion</option>
                        <option value="MP4">Convert to MP4</option>
                        <option value="AVI">Convert to AVI</option>
                        <option value="MOV">Convert to MOV</option>
                        <option value="WEBM">Convert to WEBM</option>
                        <option value="MKV">Convert to MKV</option>
                      </select>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.standardizeResolution}
                        onChange={(e) => setVideoTransforms({...videoTransforms, standardizeResolution: e.target.checked})}
                      />
                      <span>Standardize resolution</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.normalizeFPS}
                        onChange={(e) => setVideoTransforms({...videoTransforms, normalizeFPS: e.target.checked})}
                      />
                      <span>Normalize frame rate</span>
                    </label>
                    
                    {videoTransforms.normalizeFPS && (
                      <div className="input-group-inline">
                        <label>Target FPS:</label>
                        <input 
                          type="number" 
                          value={videoTransforms.targetFPS}
                          onChange={(e) => setVideoTransforms({...videoTransforms, targetFPS: parseInt(e.target.value)})}
                          className="size-input"
                        />
                      </div>
                    )}
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.removeSilent}
                        onChange={(e) => setVideoTransforms({...videoTransforms, removeSilent: e.target.checked})}
                      />
                      <span>Remove silent or empty sections</span>
                    </label>
                  </div>

                  {/* 2. Compression / Optimization */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>⚡ Compression / Optimization</h4>
                      <p>Optimize video size and quality</p>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.compression}
                        onChange={(e) => setVideoTransforms({...videoTransforms, compression: e.target.checked})}
                      />
                      <span>Enable compression</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.reduceBitrate}
                        onChange={(e) => setVideoTransforms({...videoTransforms, reduceBitrate: e.target.checked})}
                      />
                      <span>Reduce bitrate</span>
                    </label>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={videoTransforms.trimUnnecessary}
                        onChange={(e) => setVideoTransforms({...videoTransforms, trimUnnecessary: e.target.checked})}
                      />
                      <span>Trim unnecessary parts</span>
                    </label>
                  </div>

                  {/* 3. Audio Processing */}
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🎧 Audio Processing</h4>
                      <p>Audio track transformations</p>
                    </div>
                    
                    <div className="select-group">
                      <label>Audio Conversion:</label>
                      <select 
                        value={videoTransforms.audioConversion}
                        onChange={(e) => setVideoTransforms({...videoTransforms, audioConversion: e.target.value})}
                      >
                        <option value="">Keep original</option>
                        <option value="mono">Convert to Mono</option>
                        <option value="stereo">Convert to Stereo</option>
                        <option value="normalize">Normalize volume</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Audio Transformations */}
              {unstructuredType === 'audio' && (
                <div className="unstructured-transforms-grid">
                  <div className="transform-category-card">
                    <div className="transform-category-header">
                      <h4>🎧 Audio Transformations</h4>
                      <p>Audio processing and normalization</p>
                    </div>
                    
                    <div className="select-group">
                      <label>Format Conversion:</label>
                      <select 
                        className="form-select"
                        value={audioTransforms.formatConversion}
                        onChange={(e) => setAudioTransforms({...audioTransforms, formatConversion: e.target.value})}
                      >
                        <option value="">No conversion</option>
                        <option value="MP3">Convert to MP3</option>
                        <option value="WAV">Convert to WAV</option>
                        <option value="FLAC">Convert to FLAC</option>
                        <option value="AAC">Convert to AAC</option>
                        <option value="OGG">Convert to OGG</option>
                      </select>
                    </div>
                    
                    <div className="select-group">
                      <label>Channel Configuration:</label>
                      <select 
                        className="form-select"
                        value={audioTransforms.channelConfig}
                        onChange={(e) => setAudioTransforms({...audioTransforms, channelConfig: e.target.value})}
                      >
                        <option value="">Keep original</option>
                        <option value="mono">Convert to Mono</option>
                        <option value="stereo">Convert to Stereo</option>
                      </select>
                    </div>
                    
                    <label className="checkbox-label-large">
                      <input 
                        type="checkbox" 
                        checked={audioTransforms.normalizeVolume}
                        onChange={(e) => setAudioTransforms({...audioTransforms, normalizeVolume: e.target.checked})}
                      />
                      <span>Normalize volume</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Show structured data options only for structured data */}
          {dataType === 'structured' && (
            <>
              {/* 2. DATA QUALITY CONSTRAINTS (Great Expectations Style) */}
              <div className="rich-section data-quality-constraints-section">
            <div className="section-header-rich">
              <div className="section-title-group">
                <CheckCircle size={20} />
                <div>
                  <h3>Quick Data Quality Constraints</h3>
                  <p className="section-subtitle">Set column-level validation rules (Great Expectations style)</p>
                </div>
              </div>
              <button className="btn-add-constraint" onClick={() => showNotification('Add constraint dialog (coming soon)', 'info')}>
                + Add Constraint
              </button>
            </div>
            
            <div className="constraints-grid">
              {columnMappings.slice(0, 5).map((mapping, idx) => {
                const colName = mapping.target;
                const constraints = columnConstraints[colName] || {};
                
                return (
                  <div key={idx} className="constraint-card">
                    <div className="constraint-card-header">
                      <code className="col-name-constraint">{colName}</code>
                      <span className="col-type-small">{mapping.targetType}</span>
                    </div>
                    <div className="constraint-checks">
                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={constraints.notNull || false}
                          onChange={(e) => handleToggleConstraint(colName, 'notNull', e.target.checked)}
                        />
                        <span>Not Null</span>
                      </label>
                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={constraints.unique || false}
                          onChange={(e) => handleToggleConstraint(colName, 'unique', e.target.checked)}
                        />
                        <span>Unique</span>
                      </label>
                      {mapping.targetType.includes('VARCHAR') && (
                        <div className="regex-input-group">
                          <input 
                            type="text" 
                            placeholder="Regex pattern..."
                            value={constraints.regex || ''}
                            onChange={(e) => handleToggleConstraint(colName, 'regex', e.target.value)}
                            className="regex-input"
                          />
                          {constraints.regex && (
                            <span className="regex-label" title={`Pattern: ${constraints.regex}`}>
                              📝 Regex
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    {!constraints.isPrimaryKey && (
                      <button 
                        className="btn-set-pk"
                        onClick={() => handleSetPrimaryKey(colName)}
                      >
                        🔑 Set as Primary Key
                      </button>
                    )}
                    {constraints.isPrimaryKey && (
                      <div className="pk-badge">
                        🔑 PRIMARY KEY
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            
            <div className="constraints-summary">
              <span>
                {Object.values(columnConstraints).filter(c => c?.notNull).length} NOT NULL constraints
              </span>
              <span>•</span>
              <span>
                {Object.values(columnConstraints).filter(c => c?.unique).length} UNIQUE constraints
              </span>
              <span>•</span>
              <span>
                {Object.values(columnConstraints).filter(c => c?.regex).length} REGEX validations
              </span>
              <span>•</span>
              <span>
                {Object.values(columnConstraints).filter(c => c?.isPrimaryKey).length} PRIMARY KEY
              </span>
            </div>
          </div>

          {/* 3. TRANSFORMATION PREVIEW (Side-by-Side) */}
          <div className="rich-section preview-section">
            <div className="section-header-rich">
              <div className="section-title-group">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                <div>
                  <h3>Transformation Preview</h3>
                  <p className="section-subtitle">See before & after transformation (10 sample rows)</p>
                </div>
              </div>
              <button 
                className="btn-load-preview" 
                onClick={handleLoadPreview}
                disabled={previewLoading}
              >
                {previewLoading ? (
                  <>
                    <RefreshCw size={16} className="spinning" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Load Preview
                  </>
                )}
              </button>
            </div>
            
            {showPreview && previewData.before.length > 0 && (
              <div className="preview-container">
                <div className="preview-panel">
                  <div className="preview-panel-header before">
                    <h4>Before Transformation</h4>
                    <span className="panel-subtitle">Raw Bronze Data</span>
                  </div>
                  <div className="preview-table-wrapper">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          {previewData.columns.map((col, idx) => (
                            <th key={idx}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.before.map((row, rowIdx) => (
                          <tr key={rowIdx}>
                            {previewData.columns.map((col, colIdx) => (
                              <td key={colIdx} className={row[col] === null ? 'null-cell' : ''}>
                                {row[col] !== null ? row[col] : 'NULL'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                
                <div className="preview-divider">
                  <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                  </svg>
                </div>
                
                <div className="preview-panel">
                  <div className="preview-panel-header after">
                    <h4>After Transformation</h4>
                    <span className="panel-subtitle">Cleaned Silver Data</span>
                  </div>
                  <div className="preview-table-wrapper">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          {[...previewData.columns, '_dq_status', '_dq_reason'].map((col, idx) => (
                            <th key={idx}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.after.map((row, rowIdx) => (
                          <tr key={rowIdx} className={`row-status-${row._dq_status?.toLowerCase()}`}>
                            {previewData.columns.map((col, colIdx) => (
                              <td key={colIdx} className={row[col] === null ? 'null-cell' : ''}>
                                {row[col] !== null ? row[col] : 'NULL'}
                              </td>
                            ))}
                            <td>
                              <span className={`status-badge status-${row._dq_status?.toLowerCase()}`}>
                                {row._dq_status}
                              </span>
                            </td>
                            <td className="reason-cell">{row._dq_reason || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
            
            {!showPreview && (
              <div className="preview-empty-state">
                <svg width="64" height="64" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" opacity="0.3">
                  <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                <p>Click "Load Preview" to see transformation results</p>
                <p className="hint-text">Preview shows first 10 rows with all transformations & quality checks applied</p>
              </div>
            )}
          </div>

          {/* 4. ADVANCED PERFORMANCE TUNING */}
          <div className="rich-section performance-tuning-section">
            <div className="section-header-rich">
              <div className="section-title-group">
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6m8.66-12L16 10.5M12 12 7.34 7M20.66 19 16 13.5M12 12l-4.66 5.5M23 12h-6m-6 0H1"/>
                </svg>
                <div>
                  <h3>Performance Tuning</h3>
                  <p className="section-subtitle">Optimize query performance with partitioning & clustering</p>
                </div>
              </div>
            </div>
            
            <div className="tuning-grid">
              {/* Traditional Partitioning */}
              <div className="tuning-card">
                <div className="tuning-card-header">
                  <h4>📁 Partitioning</h4>
                  <span className="tuning-badge">Traditional</span>
                </div>
                <p className="tuning-description">
                  Organize data into separate folders by column values (e.g., by date)
                </p>
                <div className="column-selector">
                  <label>Partition Columns:</label>
                  <select 
                    multiple 
                    value={partitionColumns}
                    onChange={(e) => setPartitionColumns(Array.from(e.target.selectedOptions, opt => opt.value))}
                    className="multi-select"
                  >
                    <option value="transaction_date">transaction_date</option>
                    <option value="region">region</option>
                    <option value="category">category</option>
                    <option value="year">year</option>
                    <option value="month">month</option>
                  </select>
                  <span className="selected-count">{partitionColumns.length} selected</span>
                </div>
                {partitionColumns.length > 0 && (
                  <div className="selected-columns-display">
                    {partitionColumns.map((col, idx) => (
                      <span key={idx} className="selected-col-badge">{col}</span>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Z-Ordering */}
              <div className="tuning-card">
                <div className="tuning-card-header">
                  <h4>⚡ Z-Ordering</h4>
                  <span className="tuning-badge advanced">Delta Lake</span>
                </div>
                <p className="tuning-description">
                  Optimize file skipping within partitions for faster queries
                </p>
                <div className="column-selector">
                  <label>Z-Order Columns:</label>
                  <select 
                    multiple 
                    value={zOrderColumns}
                    onChange={(e) => setZOrderColumns(Array.from(e.target.selectedOptions, opt => opt.value))}
                    className="multi-select"
                  >
                    <option value="customer_id">customer_id</option>
                    <option value="product_id">product_id</option>
                    <option value="status">status</option>
                    <option value="amount">amount</option>
                  </select>
                  <span className="selected-count">{zOrderColumns.length} selected</span>
                </div>
                {zOrderColumns.length > 0 && (
                  <div className="selected-columns-display">
                    {zOrderColumns.map((col, idx) => (
                      <span key={idx} className="selected-col-badge zorder">{col}</span>
                    ))}
                  </div>
                )}
                <div className="info-note">
                  <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
                  </svg>
                  Best for frequently filtered columns
                </div>
              </div>
              
              {/* Liquid Clustering */}
              <div className="tuning-card">
                <div className="tuning-card-header">
                  <h4>🌊 Liquid Clustering</h4>
                  <span className="tuning-badge modern">Databricks</span>
                </div>
                <p className="tuning-description">
                  Modern, adaptive clustering that auto-optimizes over time
                </p>
                <label className="toggle-label-large">
                  <input 
                    type="checkbox" 
                    checked={useLiquidClustering}
                    onChange={(e) => {
                      setUseLiquidClustering(e.target.checked);
                      if (e.target.checked) {
                        showNotification('Liquid Clustering enabled - replaces static partitioning', 'success');
                      }
                    }}
                  />
                  <span>Enable Liquid Clustering</span>
                </label>
                
                {useLiquidClustering && (
                  <>
                    <div className="column-selector">
                      <label>Clustering Columns:</label>
                      <select 
                        multiple 
                        value={clusteringColumns}
                        onChange={(e) => setClusteringColumns(Array.from(e.target.selectedOptions, opt => opt.value))}
                        className="multi-select"
                      >
                        <option value="transaction_date">transaction_date</option>
                        <option value="customer_id">customer_id</option>
                        <option value="region">region</option>
                        <option value="product_id">product_id</option>
                      </select>
                      <span className="selected-count">{clusteringColumns.length} selected</span>
                    </div>
                    {clusteringColumns.length > 0 && (
                      <div className="selected-columns-display">
                        {clusteringColumns.map((col, idx) => (
                          <span key={idx} className="selected-col-badge liquid">{col}</span>
                        ))}
                      </div>
                    )}
                    <div className="info-note success">
                      <CheckCircle size={14} />
                      Hands-off optimization - no manual tuning needed
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Transformation Logs & Stats */}
          <div className="transform-section logs-section-integrated">
            <div className="transformation-backlog-card-large">
              <div className="backlog-header">
                <h3>🔄 Transformation Logs</h3>
                {isStreaming && <span className="streaming-badge">● LIVE</span>}
              </div>
              
              {currentOperation && (
                <div className="current-operation">
                  <div className="operation-label">Current Operation:</div>
                  <div className="operation-text">{currentOperation}</div>
                </div>
              )}
              
              <div className="log-viewer-integrated">
                {transformationLogs.length === 0 ? (
                  <div className="empty-state-large">
                    <Activity size={48} style={{ opacity: 0.3 }} />
                    <p style={{ fontSize: '16px', marginTop: '16px' }}>No active transformation</p>
                    <p className="empty-hint" style={{ fontSize: '14px' }}>
                      Click "Execute" to start transformation and see real-time logs
                    </p>
                  </div>
                ) : (
                  <div className="log-entries-large">
                    {transformationLogs.slice().reverse().map((log, idx) => (
                      <div key={idx} className={`log-entry-large log-${log.type}`}>
                        <div className="log-time-large">{new Date(log.timestamp).toLocaleTimeString()}</div>
                        <div className="log-message-large">{log.message}</div>
                        {log.rowsProcessed > 0 && (
                          <div className="log-rows-large">{log.rowsProcessed.toLocaleString()} rows</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Performance Stats - Integrated */}
          <div className="transform-section performance-section-integrated">
            <div className="performance-card-large">
              <h3>Last Run Statistics</h3>
              {silverJob ? (
                <div className="perf-stats-large">
                  <div className="perf-stat-large">
                    <Clock size={20} />
                    <div>
                      <div className="stat-label-perf">Runtime</div>
                      <div className="stat-value-perf">
                        {(() => {
                          if (silverJob.completed_at && silverJob.started_at) {
                            const start = new Date(silverJob.started_at);
                            const end = new Date(silverJob.completed_at);
                            const seconds = Math.round((end - start) / 1000);
                            const mins = Math.floor(seconds / 60);
                            const secs = seconds % 60;
                            return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')}` : `${secs}s`;
                          }
                          return 'N/A';
                        })()}
                      </div>
                    </div>
                  </div>
                  <div className="perf-stat-large">
                    <Activity size={20} />
                    <div>
                      <div className="stat-label-perf">Throughput</div>
                      <div className="stat-value-perf">
                        {(() => {
                          if (silverJob.completed_at && silverJob.started_at && silverJob.row_count) {
                            const start = new Date(silverJob.started_at);
                            const end = new Date(silverJob.completed_at);
                            const seconds = (end - start) / 1000;
                            const rowsPerSec = Math.round(silverJob.row_count / seconds);
                            if (rowsPerSec >= 1000) {
                              return `${Math.round(rowsPerSec / 1000)}K rows/sec`;
                            }
                            return `${rowsPerSec} rows/sec`;
                          }
                          return 'N/A';
                        })()}
                      </div>
                    </div>
                  </div>
                  <div className="perf-stat-large">
                    <BarChart3 size={20} />
                    <div>
                      <div className="stat-label-perf">Rows Processed</div>
                      <div className="stat-value-perf">{silverJob.row_count?.toLocaleString() || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ padding: '30px', textAlign: 'center', color: '#888' }}>
                  <p style={{ fontSize: '14px' }}>No run history available yet</p>
                </div>
              )}
            </div>
          </div>

          {/* Watermark & Schema Monitoring */}
          <div className="transform-section-grid">
            <div className="watermark-card-large">
              <h3>Incremental Load State</h3>
              <div className="watermark-info-large">
                <div className="watermark-row-large">
                  <span className="label-large">Watermark Column:</span>
                  <code className="value-large">{watermarkState.column}</code>
                </div>
                <div className="watermark-row-large">
                  <span className="label-large">Last Processed:</span>
                  <code className="value-large">{new Date(watermarkState.lastValue).toLocaleString()}</code>
                </div>
                <div className="watermark-row-large">
                  <span className="label-large">Next Run Will Pick:</span>
                  <code className="next-run-large">{watermarkState.nextRunWillProcess}</code>
                </div>
                <div className="watermark-row-large">
                  <span className="label-large">Pending Rows:</span>
                  <span className="pending-count-large">{watermarkState.rowsSinceLastRun.toLocaleString()} new rows</span>
                </div>
              </div>
            </div>

            <div className={`schema-drift-card-large status-${schemaDrift.status}`}>
              <h3>Schema Monitoring</h3>
              <div className="drift-status-large">
                <div className="status-indicator-large">
                  {schemaDrift.status === 'stable' ? '✅' : schemaDrift.status === 'warning' ? '⚠️' : '❌'}
                </div>
                <div className="status-text-large">
                  <div className="status-label-large">{schemaDrift.status.toUpperCase()}</div>
                  <div className="status-time-large">
                    Last checked: {new Date(schemaDrift.lastChecked).toLocaleString()}
                  </div>
                </div>
              </div>
              {schemaDrift.changes.length > 0 && (
                <div className="drift-changes-large">
                  {schemaDrift.changes.map((change, idx) => (
                    <div key={idx} className="change-item-large">
                      <span className="change-type-large">{change.type}</span>
                      <span className="change-column-large">{change.column}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          </>
          )}
        </div>
        )}

        {/* ============ QUALITY TAB ============ */}
        {activeTab === 'quality' && (
        <div className="tab-content tab-quality">
          {/* DQ Score - Large and prominent */}
          <div className="quality-section dq-score-section">
            <div className="dq-score-card-large">
              <div className="dq-score-header">
                <h3>Data Quality Score</h3>
                {dqTrend.length > 0 && (
                  <div className="dq-trend">
                    {dqTrend.map((score, idx) => (
                      <div
                        key={idx}
                        className="trend-bar"
                        style={{ height: `${score}%` }}
                      />
                    ))}
                  </div>
                )}
              </div>
              {dqScore !== null ? (
                <>
                  <div className="dq-score-value-large">
                    <span className="score-large">{dqScore}</span>
                    <span className="score-label-large">/100</span>
                    <TrendingUp size={32} className="trend-icon up" />
                  </div>
                  <div className="quality-breakdown-grid">
                    {Object.entries(qualityMetrics).map(([key, value]) => {
                      if (value === null) return null;
                      const trend = dimensionTrends[key] || [];
                      const isDecreasing = trend.length >= 2 && trend[trend.length - 1] < trend[trend.length - 2];
                      
                      return (
                        <div key={key} className="quality-metric-card">
                          <div className="metric-header">
                            <div className="metric-label-large">{key}</div>
                            <div className="metric-value-large">{value}%</div>
                          </div>
                          <div className="metric-bar-large">
                            <div className="metric-fill-large" style={{ width: `${value}%` }} />
                          </div>
                          {trend.length > 0 && (
                            <div className="metric-trend-large">
                              {trend.map((score, idx) => (
                                <div 
                                  key={idx}
                                  className="trend-dot-large"
                                  style={{ height: `${(score / 100) * 30}px` }}
                                  title={`Run ${idx + 1}: ${score}%`}
                                />
                              ))}
                              {isDecreasing && <span className="trend-arrow-down-large">↓</span>}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : (
                <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
                  <BarChart3 size={48} style={{ opacity: 0.3, margin: '0 auto 16px' }} />
                  <p style={{ fontSize: '16px', fontWeight: 500 }}>No quality data available</p>
                  <p style={{ fontSize: '14px', marginTop: '8px' }}>
                    Run a transformation to see quality metrics
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Preview Stats */}
          <div className="quality-section preview-stats-section">
            <h3>Transformation Preview</h3>
            {previewSummary.rows_input !== null ? (
              <div className="stats-grid-large">
                <div className="stat-box-large">
                  <div className="stat-value-large">
                    {previewSummary.rows_input >= 1000000 
                      ? `${(previewSummary.rows_input / 1000000).toFixed(1)}M` 
                      : previewSummary.rows_input.toLocaleString()}
                  </div>
                  <div className="stat-label-large">Input Rows</div>
                </div>
                <div className="stat-box-large">
                  <div className="stat-value-large">
                    {previewSummary.rows_output >= 1000000 
                      ? `${(previewSummary.rows_output / 1000000).toFixed(2)}M` 
                      : previewSummary.rows_output.toLocaleString()}
                  </div>
                  <div className="stat-label-large">Output Rows</div>
                </div>
                <div 
                  className="stat-box-large warn clickable" 
                  onClick={() => setShowQuarantineViewer(true)}
                  title="Click to view quarantined rows"
                >
                  <div className="stat-value-large">{previewSummary.rows_quarantined.toLocaleString()}</div>
                  <div className="stat-label-large">Quarantined 🔍</div>
                </div>
                <div 
                  className="stat-box-large error clickable"
                  onClick={() => setShowRejectionViewer(true)}
                  title="Click to view rejected rows"
                >
                  <div className="stat-value-large">{previewSummary.rows_rejected}</div>
                  <div className="stat-label-large">Rejected 🔍</div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
                <p style={{ fontSize: '16px' }}>No transformation data available</p>
                <p style={{ fontSize: '14px', marginTop: '8px' }}>
                  Run a transformation to see row statistics
                </p>
              </div>
            )}
          </div>

          {/* Quality Rules */}
          <div className="quality-section rules-section-large">
            <div className="rules-header">
              <h3>Quality Rules Configuration</h3>
              <span className="count-badge">{enabledRuleCount} active</span>
            </div>

            <div className="rule-categories">
              {Object.entries(RULE_CATEGORIES).map(([key, category]) => (
                <div key={key} className="rule-category">
                  <div className="category-header" onClick={() => toggleCategory(key)}>
                    {expandedCategories[key] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <span className="category-title">{category.category}</span>
                    <span className="category-count">
                      {category.rules.filter(r => activeRules[r.id]).length}/{category.rules.length}
                    </span>
                    <div className="category-actions" onClick={e => e.stopPropagation()}>
                      <button 
                        className="btn-mini-action"
                        onClick={() => handleBulkEnableRules(key)}
                        title="Enable all rules in this category"
                      >
                        <CheckCircle size={14} />
                      </button>
                      <button 
                        className="btn-mini-action"
                        onClick={() => handleBulkDisableRules(key)}
                        title="Disable all rules in this category"
                      >
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                  
                  {expandedCategories[key] && (
                    <div className="rules-list">
                      {category.rules
                        .filter(rule => !activePipelineFilter || rule.pipelineStep === activePipelineFilter)
                        .map(rule => {
                        const result = ruleResults[rule.id];
                        const isExpanded = expandedRules[rule.id];
                        
                        return (
                          <div key={rule.id} className="rule-item-enhanced">
                            <div className="rule-header-row" onClick={() => handleToggleRule(rule.id)}>
                              <input
                                type="checkbox"
                                checked={!!activeRules[rule.id]}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleToggleRule(rule.id);
                                }}
                                readOnly
                              />
                              <div className="rule-info">
                                <div className="rule-label">{rule.label}</div>
                                <div className="rule-description">{rule.description}</div>
                              </div>
                              <div className="rule-status">
                                {result && (
                                  <>
                                    <span className="pass-count">✓ {result.passed.toLocaleString()}</span>
                                    <span className={`fail-count ${result.failed > 0 ? 'has-failures' : ''}`}>
                                      ✗ {result.failed.toLocaleString()}</span>
                                  </>
                                )}
                              </div>
                              <span className={`severity-badge ${rule.severity.toLowerCase()}`}>
                                {rule.severity}
                              </span>
                              <button className="expand-btn" onClick={(e) => { e.stopPropagation(); toggleRule(rule.id); }}>
                                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                              </button>
                            </div>
                            
                            {isExpanded && result && (
                              <div className="rule-details">
                                <div className="detail-grid">
                                  <div className="detail-item">
                                    <span className="detail-label">Threshold:</span>
                                    {editingThreshold === rule.id ? (
                                      <input
                                        type="text"
                                        className="threshold-input"
                                        value={thresholdInput}
                                        onChange={(e) => setThresholdInput(e.target.value)}
                                        onBlur={() => {
                                          setRuleResults(prev => ({
                                            ...prev,
                                            [rule.id]: { ...prev[rule.id], threshold: thresholdInput }
                                          }));
                                          setEditingThreshold(null);
                                        }}
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter') {
                                            setRuleResults(prev => ({
                                              ...prev,
                                              [rule.id]: { ...prev[rule.id], threshold: thresholdInput }
                                            }));
                                            setEditingThreshold(null);
                                          }
                                        }}
                                        autoFocus
                                        onClick={(e) => e.stopPropagation()}
                                      />
                                    ) : (
                                      <span 
                                        className="detail-value threshold-editable" 
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setEditingThreshold(rule.id);
                                          setThresholdInput(result.threshold);
                                        }}
                                        style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}
                                        title="Click to edit"
                                      >
                                        {result.threshold}
                                      </span>
                                    )}
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">Action:</span>
                                    <span className={`action-badge action-${result.action}`}>
                                      {result.action.toUpperCase()}
                                    </span>
                                  </div>
                                  <div className="detail-item">
                                    <span className="detail-label">Pass Rate:</span>
                                    <span className="detail-value">
                                      {((result.passed / (result.passed + result.failed)) * 100).toFixed(2)}%
                                    </span>
                                  </div>
                                </div>
                                
                                {result.samples && result.samples.length > 0 && (
                                  <div className="failure-samples">
                                    <div className="samples-header">Sample Failures:</div>
                                    {result.samples.map((sample, idx) => (
                                      <div key={idx} className="sample-row">
                                        <code>{sample}</code>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                
                                {result.failed > 0 && (
                                  <div className="rule-actions">
                                    <button 
                                      className="btn-mini"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setEditingThreshold(rule.id);
                                        setThresholdInput(result.threshold);
                                      }}
                                    >
                                      Edit Threshold
                                    </button>
                                    <button 
                                      className="btn-mini"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedRuleForFailures(rule.id);
                                        setShowAllFailuresModal(true);
                                      }}
                                    >
                                      View All Failures
                                    </button>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        )}
      </div>
      
      {/* Help Panel */}
      {showHelp && (
        <div className="modal-overlay" onClick={() => setShowHelp(false)}>
          <div className="help-panel" onClick={e => e.stopPropagation()}>
            <div className="help-panel-header">
              <h3>🎓 Silver Layer Guide</h3>
              <button className="btn-close" onClick={() => setShowHelp(false)}>×</button>
            </div>
            <div className="help-panel-content">
              <div className="help-section">
                <h4>⌨️ Keyboard Shortcuts</h4>
                <div className="help-shortcuts">
                  <div className="help-shortcut">
                    <kbd className="kbd">Ctrl</kbd> + <kbd className="kbd">K</kbd>
                    <span>Command Palette</span>
                  </div>
                  <div className="help-shortcut">
                    <kbd className="kbd">Ctrl</kbd> + <kbd className="kbd">S</kbd>
                    <span>Save Configuration</span>
                  </div>
                  <div className="help-shortcut">
                    <kbd className="kbd">Alt</kbd> + <kbd className="kbd">1</kbd>
                    <span>Transform Tab</span>
                  </div>
                  <div className="help-shortcut">
                    <kbd className="kbd">Alt</kbd> + <kbd className="kbd">2</kbd>
                    <span>Quality Tab</span>
                  </div>
                  <div className="help-shortcut">
                    <kbd className="kbd">Esc</kbd>
                    <span>Close Modals</span>
                  </div>
                </div>
              </div>
              
              <div className="help-section">
                <h4>🎯 Quick Actions</h4>
                <ul className="help-list">
                  <li><strong>Bulk Enable/Disable Rules:</strong> Use the ✓ and × buttons next to each rule category</li>
                  <li><strong>Save Configurations:</strong> Save your current rules and mappings for reuse</li>
                  <li><strong>Export Configuration:</strong> Download as JSON for version control</li>
                  <li><strong>Monitor Logs:</strong> View real-time transformation progress in Transform tab</li>
                </ul>
              </div>
              
              <div className="help-section">
                <h4>📊 Quality Dimensions</h4>
                <ul className="help-list">
                  <li><strong>Completeness:</strong> Measures null values and missing data</li>
                  <li><strong>Conformity:</strong> Validates data format and structure</li>
                  <li><strong>Uniqueness:</strong> Checks for duplicate records</li>
                  <li><strong>Validity:</strong> Ensures data meets business rules</li>
                </ul>
              </div>
              
              <div className="help-section">
                <h4>🚀 Execution Modes</h4>
                <ul className="help-list">
                  <li><strong>Full Refresh:</strong> Process all data from source</li>
                  <li><strong>Incremental:</strong> Process only new/updated records based on watermark</li>
                  <li><strong>Merge:</strong> Upsert based on primary key</li>
                </ul>
              </div>
              
              <div className="help-section">
                <h4>💡 Pro Tips</h4>
                <ul className="help-list">
                  <li>Use the command palette (Ctrl+K) for quick navigation</li>
                  <li>Click on quality metric trends to see historical performance</li>
                  <li>Quarantined rows can be reviewed and reprocessed</li>
                  <li>Save configurations for different tables to speed up setup</li>
                  <li>Check transformation logs and stats in the Transform tab</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .studio-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #f9fafb;
        }

        .studio-header {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px 24px;
          background: white;
          border-bottom: 1px solid #e5e7eb;
          position: relative;
          z-index: 100;
        }
        
        /* ===== ENTERPRISE UI ENHANCEMENTS ===== */
        .btn-icon-action {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          background: white;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s;
          position: relative;
        }
        
        .btn-icon-action:hover {
          background: #f3f4f6;
          color: #111827;
          border-color: #d1d5db;
        }
        
        .badge-count {
          position: absolute;
          top: -4px;
          right: -4px;
          background: #3b82f6;
          color: white;
          border-radius: 10px;
          padding: 2px 6px;
          font-size: 10px;
          font-weight: 600;
        }
        
        .divider-vertical {
          width: 1px;
          height: 24px;
          background: #e5e7eb;
        }
        
        /* Toast Notifications */
        .toast-container {
          position: fixed;
          top: 80px;
          right: 24px;
          z-index: 1000;
          display: flex;
          flex-direction: column;
          gap: 12px;
          pointer-events: none;
        }
        
        .toast {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
          border-left: 4px solid;
          min-width: 320px;
          animation: slideIn 0.3s ease;
          pointer-events: auto;
        }
        
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        .toast-success {
          border-left-color: #10b981;
        }
        
        .toast-error {
          border-left-color: #ef4444;
        }
        
        .toast-info {
          border-left-color: #3b82f6;
        }
        
        .toast-icon {
          display: flex;
          align-items: center;
        }
        
        .toast-success .toast-icon {
          color: #10b981;
        }
        
        .toast-error .toast-icon {
          color: #ef4444;
        }
        
        .toast-info .toast-icon {
          color: #3b82f6;
        }
        
        .toast-message {
          flex: 1;
          font-size: 14px;
          color: #374151;
          font-weight: 500;
        }
        
        /* Command Palette */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(4px);
          z-index: 999;
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding-top: 100px;
          animation: fadeIn 0.2s ease;
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
        
        .command-palette {
          width: 600px;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          overflow: hidden;
          animation: slideDown 0.3s ease;
        }
        
        @keyframes slideDown {
          from {
            transform: translateY(-20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        
        .command-palette-header {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          border-bottom: 1px solid #e5e7eb;
          background: #f9fafb;
        }
        
        .command-palette-input {
          flex: 1;
          border: none;
          background: transparent;
          font-size: 16px;
          color: #111827;
          outline: none;
        }
        
        .kbd {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 24px;
          height: 24px;
          padding: 0 6px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          color: #6b7280;
          font-family: monospace;
        }
        
        .command-palette-list {
          max-height: 500px;
          overflow-y: auto;
        }
        
        .command-section {
          padding: 8px;
          border-bottom: 1px solid #e5e7eb;
        }
        
        .command-section:last-child {
          border-bottom: none;
        }
        
        .command-section-title {
          padding: 8px 12px;
          font-size: 11px;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .command-item {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 12px;
          border: none;
          background: transparent;
          color: #374151;
          font-size: 14px;
          text-align: left;
          cursor: pointer;
          border-radius: 8px;
          transition: all 0.2s;
        }
        
        .command-item:hover {
          background: #f3f4f6;
          color: #111827;
        }
        
        .command-item svg {
          color: #6b7280;
        }
        
        .command-item span {
          flex: 1;
        }
        
        /* Configuration Library */
        .config-library {
          width: 700px;
          max-height: 80vh;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .config-library-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 24px;
          border-bottom: 1px solid #e5e7eb;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }
        
        .config-library-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        
        .btn-close {
          width: 32px;
          height: 32px;
          border: none;
          background: rgba(255, 255, 255, 0.2);
          color: white;
          border-radius: 8px;
          font-size: 20px;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .btn-close:hover {
          background: rgba(255, 255, 255, 0.3);
        }
        
        .config-library-list {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
        }
        
        .empty-state-small {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 60px 20px;
          color: #9ca3af;
        }
        
        .config-item {
          padding: 16px;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          margin-bottom: 12px;
          position: relative;
          transition: all 0.2s;
        }
        
        .config-item:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 6px rgba(59, 130, 246, 0.1);
        }
        
        .config-item-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        
        .config-item-header strong {
          font-size: 15px;
          color: #111827;
        }
        
        .config-timestamp {
          font-size: 12px;
          color: #6b7280;
        }
        
        .config-item-details {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }
        
        .config-tag {
          padding: 4px 10px;
          background: white;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 12px;
          color: #6b7280;
        }
        
        .btn-load-config {
          padding: 8px 16px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .btn-load-config:hover {
          background: #2563eb;
          transform: translateY(-1px);
        }
        
        /* Bulk Action Buttons */
        .category-actions {
          display: flex;
          gap: 4px;
          margin-left: auto;
        }
        
        .btn-mini-action {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border: 1px solid #e5e7eb;
          background: white;
          border-radius: 6px;
          cursor: pointer;
          color: #6b7280;
          transition: all 0.2s;
        }
        
        .btn-mini-action:hover {
          background: #f3f4f6;
          border-color: #3b82f6;
          color: #3b82f6;
        }
        
        /* Help Panel */
        .help-panel {
          width: 700px;
          max-height: 80vh;
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .help-panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 24px;
          border-bottom: 1px solid #e5e7eb;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
        }
        
        .help-panel-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        
        .help-panel-content {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
        }
        
        .help-section {
          margin-bottom: 32px;
        }
        
        .help-section h4 {
          margin: 0 0 16px 0;
          font-size: 15px;
          font-weight: 600;
          color: #111827;
        }
        
        .help-shortcuts {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .help-shortcut {
          display: flex;
          align-items: center;
          gap:12px;
          padding: 12px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }
        
        .help-shortcut span {
          flex: 1;
          color: #6b7280;
          font-size: 14px;
        }
        
        .help-list {
          margin: 0;
          padding-left: 20px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        
        .help-list li {
          color: #6b7280;
          font-size: 14px;
          line-height: 1.6;
        }
        
        .help-list strong {
          color: #374151;
          font-weight: 600;
        }

        /* ===== TAB NAVIGATION ===== */
        .silver-tabs {
          display: flex;
          gap: 4px;
          padding: 0 24px;
          background: white;
          border-bottom: 2px solid #e5e7eb;
        }

        .tab-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 14px 24px;
          border: none;
          background: none;
          color: #6b7280;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          margin-bottom: -2px;
          transition: all 0.2s;
        }

        .tab-button:hover {
          color: #374151;
          background: #f9fafb;
        }

        .tab-button.active {
          color: #3b82f6;
          border-bottom-color: #3b82f6;
          background: none;
        }

        /* ===== TAB CONTENT LAYOUT ===== */
        .studio-content {
          flex: 1;
          overflow: auto;
          padding: 24px;
        }

        .tab-content {
          display: grid;
          gap: 24px;
          max-width: 1600px;
          margin: 0 auto;
        }

        .tab-transform {
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }

        .tab-quality {
          grid-template-columns: 1fr;
        }

        /* ===== DATA TYPE SELECTOR ===== */
        .data-type-selector-card {
          background: #ffffff;
          border-radius: 12px;
          border: 2px solid #e5e7eb;
          padding: 24px;
          margin-bottom: 24px;
        }

        .data-type-header h4 {
          margin: 0 0 4px 0;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
        }

        .data-type-header p {
          margin: 0;
          font-size: 14px;
          color: #6b7280;
        }

        .data-type-buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-top: 20px;
        }

        .data-type-btn {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 20px;
          background: #f9fafb;
          border: 2px solid #e5e7eb;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s;
          text-align: left;
        }

        .data-type-btn:hover {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .data-type-btn.active {
          border-color: #3b82f6;
          background: #eff6ff;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .data-type-btn strong {
          display: block;
          font-size: 16px;
          color: #111827;
          margin-bottom: 4px;
        }

        .data-type-btn small {
          display: block;
          font-size: 13px;
          color: #6b7280;
        }

        .unstructured-type-selector {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid #e5e7eb;
        }

        .unstructured-type-selector label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #374151;
          margin-bottom: 12px;
        }

        .unstructured-type-buttons {
          display: flex;
          gap: 12px;
        }

        .type-chip {
          padding: 10px 20px;
          background: #f3f4f6;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .type-chip:hover {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .type-chip.active {
          border-color: #3b82f6;
          background: #3b82f6;
          color: white;
        }

        .tab-monitor {
          grid-template-columns: 1fr;
        }

        .transform-section,
        .quality-section,
        .monitor-section {
          background: white;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
          border: 1px solid #f3f4f6;
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
        }
        
        .transform-section::before,
        .quality-section::before,
        .monitor-section::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
          opacity: 0;
          transition: opacity 0.3s ease;
        }
        
        .transform-section:hover,
        .quality-section:hover,
        .monitor-section:hover {
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
          transform: translateY(-2px);
        }
        
        .transform-section:hover::before,
        .quality-section:hover::before,
        .monitor-section:hover::before {
          opacity: 1;
        }
        
        .transform-section h3,
        .quality-section h3,
        .monitor-section h3 {
          color: #111827;
          font-size: 16px;
          font-weight: 600;
          margin: 0 0 16px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .transform-section h3::before {
          content: '';
          width: 4px;
          height: 20px;
          background: linear-gradient(180deg, #3b82f6, #8b5cf6);
          border-radius: 2px;
        }

        .column-mappings-section {
          grid-column: 1 / 2;
        }

        .pipeline-section {
          grid-column: 2 / 3;
        }

        /* ===== LARGE DQ SCORE ===== */
        .dq-score-section {
          min-height: 300px;
        }

        .dq-score-card-large {
          padding: 12px;
        }

        .dq-score-value-large {
          display: flex;
          align-items: baseline;
          gap: 8px;
          justify-content: center;
          margin: 32px 0;
        }

        .score-large {
          font-size: 96px;
          font-weight: 700;
          background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          line-height: 1;
        }

        .score-label-large {
          font-size: 36px;
          color: #9ca3af;
          font-weight: 600;
        }

        .quality-breakdown-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 20px;
          margin-top: 32px;
        }

        .quality-metric-card {
          padding: 20px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .metric-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .metric-label-large {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          text-transform: capitalize;
        }

        .metric-value-large {
          font-size: 24px;
          font-weight: 700;
          color: #3b82f6;
        }

        .metric-bar-large {
          height: 12px;
          background: #e5e7eb;
          border-radius: 6px;
          overflow: hidden;
          margin-bottom: 8px;
        }

        .metric-fill-large {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          transition: width 0.3s ease;
        }

        .metric-trend-large {
          display: flex;
          align-items: flex-end;
          gap: 4px;
          height: 30px;
          margin-top: 8px;
        }

        .trend-dot-large {
          flex: 1;
          background: #3b82f6;
          border-radius: 2px;
          opacity: 0.6;
          transition: all 0.2s;
        }

        .trend-dot-large:hover {
          opacity: 1;
        }

        .trend-arrow-down-large {
          color: #ef4444;
          font-size: 16px;
          margin-left: 8px;
        }

        /* ===== LARGE STATS GRID ===== */
        .stats-grid-large {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
        }

        .stat-box-large {
          padding: 24px;
          background: #f9fafb;
          border-radius: 8px;
          border: 2px solid #e5e7eb;
          text-align: center;
          transition: all 0.2s;
        }

        .stat-box-large.warn {
          border-color: #fbbf24;
          background: #fef3c7;
        }

        .stat-box-large.error {
          border-color: #f87171;
          background: #fee2e2;
        }

        .stat-box-large.clickable {
          cursor: pointer;
        }

        .stat-box-large.clickable:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stat-value-large {
          font-size: 36px;
          font-weight: 700;
          color: #111827;
          margin-bottom: 8px;
        }

        .stat-label-large {
          font-size: 13px;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        /* ===== LARGE LOGS ===== */
        .logs-section-large {
          min-height: 400px;
        }

        .transformation-backlog-card-large {
          padding: 12px;
        }

        .log-viewer-large {
          min-height: 400px;
          max-height: 600px;
          overflow-y: auto;
          background: #1f2937;
          border-radius: 8px;
          padding: 16px;
        }

        .log-entries-large {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .log-entry-large {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: #374151;
          border-radius: 6px;
          font-size: 13px;
          border-left: 3px solid #6b7280;
        }

        .log-entry-large.log-info {
          border-left-color: #3b82f6;
        }

        .log-entry-large.log-success {
          border-left-color: #10b981;
        }

        .log-entry-large.log-warning {
          border-left-color: #f59e0b;
        }

        .log-entry-large.log-error {
          border-left-color: #ef4444;
        }

        .log-time-large {
          color: #9ca3af;
          font-family: 'Monaco', monospace;
          font-size: 12px;
          min-width: 80px;
        }

        .log-message-large {
          flex: 1;
          color: #e5e7eb;
          font-family: 'Monaco', monospace;
          line-height: 1.5;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .log-rows-large {
          color: #60a5fa;
          font-family: 'Monaco', monospace;
          font-size: 12px;
          font-weight: 600;
        }

        .empty-state-large {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          color: #9ca3af;
        }

        /* ===== LARGE PERFORMANCE STATS ===== */
        .performance-card-large {
          padding: 24px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .performance-card-large h3 {
          font-size: 18px;
          margin-bottom: 20px;
          color: #111827;
        }

        .perf-stats-large {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
        }

        .perf-stat-large {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 20px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .perf-stat-large svg {
          color: #3b82f6;
        }

        .stat-label-perf {
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
        }

        .stat-value-perf {
          font-size: 24px;
          font-weight: 700;
          color: #111827;
        }

        /* ===== STATUS GRID ===== */
        .status-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }

        .watermark-card-large,
        .schema-drift-card-large {
          padding: 24px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .watermark-card-large h3,
        .schema-drift-card-large h3 {
          font-size: 16px;
          margin-bottom: 16px;
          color: #111827;
        }

        .watermark-info-large {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .watermark-row-large {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: #f9fafb;
          border-radius: 6px;
        }

        .label-large {
          font-size: 13px;
          color: #6b7280;
          min-width: 140px;
        }

        .value-large {
          font-family: 'Monaco', monospace;
          font-size: 13px;
          color: #111827;
          background: #e5e7eb;
          padding: 4px 8px;
          border-radius: 4px;
        }

        .next-run-large {
          font-family: 'Monaco', monospace;
          font-size: 13px;
          color: #3b82f6;
          background: #dbeafe;
          padding: 4px 8px;
          border-radius: 4px;
        }

        .pending-count-large {
          font-size: 14px;
          font-weight: 600;
          color: #f59e0b;
        }

        .drift-status-large {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: #f9fafb;
          border-radius: 8px;
        }

        .status-indicator-large {
          font-size: 32px;
        }

        .status-label-large {
          font-size: 16px;
          font-weight: 600;
          color: #111827;
        }

        .status-time-large {
          font-size: 12px;
          color: #6b7280;
          margin-top: 4px;
        }

        .drift-changes-large {
          margin-top: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .change-item-large {
          display: flex;
          gap: 12px;
          padding: 8px;
          background: #fef3c7;
          border-radius: 4px;
          font-size: 13px;
        }

        .change-type-large {
          font-weight: 600;
          color: #92400e;
        }

        .change-column-large {
          color: #6b7280;
          font-family: 'Monaco', monospace;
        }

        /* ===== LARGE SQL EDITOR ===== */
        .sql-section-large {
          min-height: 400px;
        }

        .sql-editor-card-large {
          padding: 24px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .sql-textarea-large {
          width: 100%;
          min-height: 300px;
          padding: 16px;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 14px;
          line-height: 1.6;
          resize: vertical;
          background: #f9fafb;
          color: #111827;
        }

        .sql-textarea-large:focus {
          outline: none;
          border-color: #3b82f6;
          background: white;
        }

        .preview-table-wrapper-large {
          max-height: 500px;
          overflow: auto;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          margin-top: 16px;
        }

        .preview-table-large {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }

        .preview-table-large thead {
          position: sticky;
          top: 0;
          background: #f3f4f6;
          z-index: 10;
        }

        .preview-table-large th {
          padding: 12px;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 2px solid #d1d5db;
        }

        .preview-table-large td {
          padding: 10px 12px;
          border-bottom: 1px solid #e5e7eb;
          color: #6b7280;
        }

        .preview-table-large tbody tr:hover {
          background: #f9fafb;
        }

        .sql-preview-results-large {
          margin-top: 24px;
        }

        /* ===== RULES SECTION LARGE ===== */
        .rules-section-large {
          min-height: 400px;
        }

        .btn-back {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: white;
          color: #374151;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .btn-back:hover {
          background: #f9fafb;
        }

        .breadcrumb {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        .breadcrumb-item {
          font-size: 14px;
          color: #6b7280;
        }

        .breadcrumb-item.bronze {
          color: #d97706;
          font-weight: 500;
        }

        .breadcrumb-item.silver {
          color: #3b82f6;
          font-weight: 600;
        }

        .breadcrumb-sep {
          color: #d1d5db;
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 12px;
          position: relative;
          z-index: 10;
        }

        .version-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: #fef3c7;
          border: 1px solid #fde047;
          border-radius: 6px;
          font-size: 12px;
          color: #92400e;
          font-weight: 500;
        }

        .btn-preview, .btn-execute {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          position: relative;
          z-index: 10;
          pointer-events: auto;
          user-select: none;
        }

        .btn-preview {
          background: #f3f4f6;
          color: #374151;
        }

        .btn-preview:hover {
          background: #e5e7eb;
        }

        .btn-preview:active {
          background: #d1d5db;
        }

        .btn-execute {
          background: #3b82f6;
          color: white;
        }

        .btn-execute:hover:not(:disabled) {
          background: #2563eb;
        }

        .btn-execute:active:not(:disabled) {
          background: #1e40af;
        }

        .btn-preview:disabled,
        .btn-execute:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .execution-status {
          padding: 6px 12px;
          background: #dbeafe;
          border: 1px solid #93c5fd;
          border-radius: 6px;
          font-size: 12px;
          color: #1e40af;
          font-weight: 500;
          max-width: 300px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .studio-content {
          display: grid;
          grid-template-columns: 340px 1fr 360px;
          gap: 20px;
          padding: 20px;
          overflow: hidden;
          flex: 1;
        }

        .left-panel, .middle-panel, .right-panel {
          display: flex;
          flex-direction: column;
          gap: 16px;
          overflow-y: auto;
        }

        .panel-header, .rules-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .panel-header h3, .rules-header h3 {
          font-size: 16px;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .count-badge {
          background: #f3f4f6;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
          color: #6b7280;
        }

        .execution-mode-selector {
          display: flex;
          gap: 8px;
          padding: 16px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .mode-chip {
          flex: 1;
          padding: 8px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: white;
          color: #6b7280;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          position: relative;
        }

        .mode-chip.active {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }

        .mode-chip:hover:not(.active) {
          border-color: #9ca3af;
        }

        .rec-badge {
          position: absolute;
          top: -6px;
          right: -6px;
          color: #f59e0b;
        }

        .watermark-selector {
          padding: 16px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .watermark-selector label {
          display: block;
          font-size: 13px;
          color: #6b7280;
          margin-bottom: 8px;
          font-weight: 500;
        }

        .watermark-selector select {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          color: #111827;
          background: white;
        }

        .column-mapping-list {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .mapping-row {
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          gap: 12px;
          align-items: center;
          padding: 12px;
          background: #f9fafb;
          border-radius: 6px;
          border: 1px solid #e5e7eb;
        }

        .source-col, .target-col {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .col-name {
          font-size: 13px;
          font-weight: 500;
          color: #111827;
          font-family: 'Courier New', monospace;
        }

        .col-type {
          font-size: 11px;
          color: #9ca3af;
          font-family: 'Courier New', monospace;
        }

        .transform-badge {
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          text-align: center;
          white-space: nowrap;
        }

        .pipeline-section {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
        }

        .pipeline-section h3 {
          font-size: 16px;
          font-weight: 600;
          color: #111827;
          margin: 0 0 16px 0;
        }

        .pipeline-steps {
          display: flex;
          align-items: center;
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 8px;
        }

        .pipeline-step-wrapper {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .pipeline-step {
          min-width: 120px;
          padding: 16px;
          background: #f9fafb;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          text-align: center;
          transition: all 0.2s;
        }

        .pipeline-step.completed {
          background: #ecfdf5;
          border-color: #10b981;
        }

        .pipeline-step.active {
          background: #dbeafe;
          border-color: #3b82f6;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        .step-label {
          font-size: 13px;
          font-weight: 600;
          color: #111827;
          margin-bottom: 8px;
        }

        .step-metrics {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .metric {
          font-size: 14px;
          font-weight: 600;
          color: #10b981;
        }

        .metric-label {
          font-size: 11px;
          color: #6b7280;
        }

        .step-spinner {
          color: #3b82f6;
          animation: rotate 1s linear infinite;
        }

        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .step-arrow {
          color: #d1d5db;
          font-size: 20px;
          flex-shrink: 0;
        }

        .rules-section {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
        }

        .rule-categories {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .rule-category {
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          overflow: hidden;
        }

        .category-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          background: #f9fafb;
          cursor: pointer;
          transition: all 0.2s;
        }

        .category-header:hover {
          background: #f3f4f6;
        }

        .category-title {
          flex: 1;
          font-size: 14px;
          font-weight: 600;
          color: #111827;
        }

        .category-count {
          font-size: 12px;
          color: #6b7280;
          background: white;
          padding: 2px 8px;
          border-radius: 10px;
        }

        .rules-list {
          display: flex;
          flex-direction: column;
          gap: 1px;
          background: #f3f4f6;
        }

        .rule-item {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 14px 12px;
          background: white;
          cursor: pointer;
          transition: all 0.15s;
        }

        .rule-item:hover {
          background: #f9fafb;
        }

        .rule-item input[type="checkbox"] {
          margin-top: 2px;
          cursor: pointer;
        }

        .rule-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .rule-label {
          font-size: 13px;
          font-weight: 500;
          color: #111827;
        }

        .rule-description {
          font-size: 12px;
          color: #6b7280;
          line-height: 1.4;
        }

        .severity-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
          align-self: flex-start;
        }

        .severity-badge.error {
          background: #fee2e2;
          color: #991b1b;
        }

        .severity-badge.warning {
          background: #fef3c7;
          color: #92400e;
        }

        .severity-badge.info {
          background: #dbeafe;
          color: #1e40af;
        }

        .dq-score-card, .preview-stats, .performance-card {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
        }

        .dq-score-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .dq-score-header h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .dq-trend {
          display: flex;
          align-items: flex-end;
          gap: 3px;
          height: 24px;
        }

        .trend-bar {
          width: 4px;
          background: #3b82f6;
          border-radius: 2px;
          transition: all 0.3s;
        }

        .dq-score-value {
          display: flex;
          align-items: baseline;
          gap: 4px;
          margin-bottom: 20px;
        }

        .score {
          font-size: 48px;
          font-weight: 700;
          color: #10b981;
        }

        .score-label {
          font-size: 20px;
          color: #9ca3af;
        }

        .trend-icon.up {
          color: #10b981;
          margin-left: auto;
        }

        .quality-breakdown {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .quality-metric {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .quality-metric .metric-label {
          width: 90px;
          font-size: 12px;
          color: #6b7280;
          text-transform: capitalize;
          font-weight: 500;
        }

        .metric-bar {
          flex: 1;
          height: 8px;
          background: #f3f4f6;
          border-radius: 4px;
          overflow: hidden;
        }

        .metric-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #10b981);
          transition: width 0.3s;
        }

        .quality-metric .metric-value {
          width: 40px;
          text-align: right;
          font-size: 13px;
          font-weight: 600;
          color: #111827;
        }

        .preview-stats h3, .performance-card h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0 0 16px 0;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .stat-box {
          padding: 12px;
          background: #f9fafb;
          border-radius: 6px;
          text-align: center;
          border: 1px solid #e5e7eb;
        }

        .stat-box.warn {
          background: #fef3c7;
          border-color: #fde047;
        }

        .stat-box.error {
          background: #fee2e2;
          border-color: #fca5a5;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: #111827;
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 11px;
          color: #6b7280;
          text-transform: uppercase;
          font-weight: 600;
        }

        .perf-stats {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .perf-stat {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
          color: #6b7280;
        }

        .perf-stat b {
          color: #111827;
          font-weight: 600;
        }

        .sql-editor-card {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
        }

        .sql-editor-card h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0 0 12px 0;
        }

        .sql-textarea {
          width: 100%;
          min-height: 180px;
          padding: 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          color: #111827;
          resize: vertical;
          background: #f9fafb;
        }

        .sql-textarea:focus {
          outline: none;
          border-color: #3b82f6;
          background: white;
        }

        /* Transformation Backlog */
        .transformation-backlog-card {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
          display: flex;
          flex-direction: column;
          max-height: 600px;
        }

        .backlog-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .backlog-header h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .streaming-badge {
          padding: 4px 10px;
          background: #ef4444;
          color: white;
          font-size: 11px;
          font-weight: 600;
          border-radius: 12px;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }

        .current-operation {
          background: #dbeafe;
          border-left: 3px solid #3b82f6;
          padding: 10px 12px;
          border-radius: 4px;
          margin-bottom: 12px;
        }

        .operation-label {
          font-size: 11px;
          font-weight: 600;
          color: #1e40af;
          text-transform: uppercase;
          margin-bottom: 4px;
        }

        .operation-text {
          font-size: 13px;
          color: #111827;
          font-weight: 500;
        }

        .log-viewer {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        .empty-state {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: #9ca3af;
          gap: 8px;
        }

        .empty-state p {
          margin: 0;
          font-size: 13px;
        }

        .empty-hint {
          font-size: 11px;
          color: #d1d5db;
        }

        .log-entries {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding-right: 4px;
        }

        .log-entries::-webkit-scrollbar {
          width: 6px;
        }

        .log-entries::-webkit-scrollbar-track {
          background: #f3f4f6;
          border-radius: 3px;
        }

        .log-entries::-webkit-scrollbar-thumb {
          background: #d1d5db;
          border-radius: 3px;
        }

        .log-entries::-webkit-scrollbar-thumb:hover {
          background: #9ca3af;
        }

        .log-entry {
          display: grid;
          grid-template-columns: 70px 1fr auto;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 4px;
          font-size: 12px;
          border-left: 3px solid transparent;
          transition: all 0.15s;
        }

        .log-entry:hover {
          background: #f9fafb;
        }

        .log-time {
          font-family: 'Courier New', monospace;
          color: #9ca3af;
          font-size: 11px;
        }

        .log-message {
          color: #111827;
          font-family: 'Courier New', monospace;
          line-height: 1.4;
        }

        .log-rows {
          font-size: 11px;
          color: #6b7280;
          text-align: right;
          white-space: nowrap;
        }

        .log-info {
          border-left-color: #3b82f6;
          background: #eff6ff;
        }

        .log-progress {
          border-left-color: #8b5cf6;
          background: #f5f3ff;
        }

        .log-success {
          border-left-color: #10b981;
          background: #f0fdf4;
        }

        .log-warning {
          border-left-color: #f59e0b;
          background: #fffbeb;
        }

        .log-error {
          border-left-color: #ef4444;
          background: #fef2f2;
        }

        .failure-summary {
          background: #f9fafb;
          padding: 16px;
          border-radius: 6px;
          margin-bottom: 16px;
          border: 1px solid #e5e7eb;
        }

        .failure-summary p {
          margin: 8px 0;
          font-size: 13px;
          color: #374151;
        }

        .failure-summary strong {
          color: #111827;
          font-weight: 600;
        }

        /* Clickable stat boxes */
        .stat-box.clickable {
          cursor: pointer;
          transition: all 0.2s;
        }

        .stat-box.clickable:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        /* Watermark card */
        .watermark-card {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
          margin-top: 16px;
        }

        .watermark-card h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0 0 12px 0;
        }

        .watermark-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .watermark-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 12px;
        }

        .watermark-row .label {
          color: #6b7280;
          font-weight: 500;
        }

        .watermark-row code {
          background: #f3f4f6;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          color: #111827;
          font-family: 'Monaco', monospace;
        }

        .watermark-row .next-run {
          background: #dbeafe;
          color: #1e40af;
        }

        .watermark-row .pending-count {
          color: #2563eb;
          font-weight: 600;
        }

        /* Schema Drift card */
        .schema-drift-card {
          background: white;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          padding: 16px;
          margin-top: 16px;
        }

        .schema-drift-card.status-stable {
          border-color: #10b981;
        }

        .schema-drift-card.status-warning {
          border-color: #f59e0b;
          background: #fffbeb;
        }

        .schema-drift-card.status-error {
          border-color: #ef4444;
          background: #fef2f2;
        }

        .schema-drift-card h3 {
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          margin: 0 0 12px 0;
        }

        .drift-status {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .status-indicator {
          font-size: 24px;
        }

        .status-text {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .status-label {
          font-size: 13px;
          font-weight: 600;
          color: #111827;
        }

        .status-time {
          font-size: 11px;
          color: #6b7280;
        }

        /* Pipeline interactive */
        .pipeline-step.active-filter {
          border: 2px solid #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .pipeline-filter-info {
          margin-top: 12px;
          padding: 10px;
          background: #dbeafe;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 13px;
          color: #1e40af;
        }

        .pipeline-filter-info button {
          padding: 4px 10px;
          background: white;
          border: 1px solid #60a5fa;
          border-radius: 4px;
          color: #1e40af;
          font-size: 12px;
          cursor: pointer;
        }

        .pipeline-filter-info button:hover {
          background: #60a5fa;
          color: white;
        }

        /* Enhanced rule items */
        .rule-item-enhanced {
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          margin-bottom: 8px;
          overflow: hidden;
        }

        .rule-header-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          cursor: pointer;
          background: white;
          transition: background 0.2s;
        }

        .rule-header-row:hover {
          background: #f9fafb;
        }

        .rule-status {
          display: flex;
          gap: 12px;
          margin-left: auto;
        }

        .pass-count {
          color: #10b981;
          font-size: 12px;
          font-weight: 600;
        }

        .fail-count {
          color: #6b7280;
          font-size: 12px;
          font-weight: 600;
        }

        .fail-count.has-failures {
          color: #ef4444;
        }

        .expand-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
          color: #6b7280;
        }

        .rule-details {
          background: #f9fafb;
          border-top: 1px solid #e5e7eb;
          padding: 16px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-bottom: 12px;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .detail-label {
          font-size: 11px;
          color: #6b7280;
          text-transform: uppercase;
          font-weight: 600;
        }

        .detail-value {
          font-size: 13px;
          color: #111827;
          font-weight: 500;
        }

        .action-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }

        .action-pass {
          background: #d1fae5;
          color: #065f46;
        }

        .action-transform {
          background: #dbeafe;
          color: #1e40af;
        }

        .action-quarantine {
          background: #fef3c7;
          color: #92400e;
        }

        .action-reject {
          background: #fee2e2;
          color: #991b1b;
        }

        .failure-samples {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          padding: 12px;
          margin-top: 12px;
        }

        .samples-header {
          font-size: 12px;
          color: #6b7280;
          font-weight: 600;
          margin-bottom: 8px;
        }

        .sample-row {
          margin-bottom: 6px;
        }

        .sample-row code {
          font-size: 11px;
          background: #f3f4f6;
          padding: 4px 8px;
          border-radius: 4px;
          display: block;
          color: #ef4444;
        }

        .rule-actions {
          display: flex;
          gap: 8px;
          margin-top: 12px;
        }

        .btn-mini {
          padding: 6px 12px;
          font-size: 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          background: white;
          color: #374151;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-mini:hover {
          background: #f3f4f6;
          border-color: #9ca3af;
        }

        .threshold-input {
          padding: 4px 8px;
          border: 1px solid #3b82f6;
          border-radius: 4px;
          font-size: 12px;
          font-family: 'Courier New', monospace;
          outline: none;
          background: white;
        }

        .metric-trend {
          display: flex;
          align-items: flex-end;
          gap: 2px;
          height: 20px;
          margin-left: 8px;
        }

        .trend-dot {
          width: 3px;
          background: #3b82f6;
          border-radius: 1px;
          transition: all 0.2s;
        }

        .trend-dot:hover {
          background: #2563eb;
          transform: scaleY(1.1);
        }

        .trend-arrow-down {
          color: #ef4444;
          font-size: 14px;
          font-weight: bold;
          margin-left: 4px;
        }

        .sql-editor-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .sql-toolbar {
          display: flex;
          gap: 8px;
        }

        .btn-sql-action {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          font-size: 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          background: white;
          color: #374151;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-sql-action:hover {
          background: #f3f4f6;
          border-color: #9ca3af;
        }

        .btn-sql-action.btn-primary {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }

        .btn-sql-action.btn-primary:hover:not(:disabled) {
          background: #2563eb;
          border-color: #2563eb;
        }
        
        .btn-sql-action:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .spinning {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .sql-preview-error {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 14px 16px;
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 6px;
          color: #dc2626;
          font-size: 13px;
          margin-top: 12px;
        }
        
        .error-content {
          flex: 1;
        }
        
        .error-content strong {
          display: block;
          margin-bottom: 6px;
          font-weight: 600;
        }
        
        .error-content pre {
          background: #fee2e2;
          padding: 8px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-family: 'Courier New', monospace;
          overflow-x: auto;
          white-space: pre-wrap;
          word-wrap: break-word;
          margin: 8px 0;
          border: 1px solid #fca5a5;
        }
        
        .error-hint {
          margin-top: 12px;
          padding: 12px;
          background: #fffbeb;
          border: 1px solid #fde047;
          border-radius: 4px;
          color: #92400e;
        }
        
        .error-hint p {
          margin: 0 0 8px 0;
          font-weight: 600;
        }
        
        .error-hint ol {
          margin: 8px 0;
          padding-left: 20px;
        }
        
        .error-hint li {
          margin: 4px 0;
          line-height: 1.5;
        }
        
        .error-hint code {
          background: #fef3c7;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
          font-size: 11px;
        }
        
        .btn-check-tables {
          margin-top: 10px;
          padding: 8px 14px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .btn-check-tables:hover {
          background: #2563eb;
          transform: translateY(-1px);
        }
        
        .sql-preview-results {
          margin-top: 12px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          background: white;
          overflow: hidden;
        }
        
        .preview-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 14px;
          background: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
        }
        
        .preview-header-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .preview-header h4 {
          margin: 0;
          font-size: 13px;
          font-weight: 600;
          color: #111827;
        }
        
        .mock-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          background: #fef3c7;
          border: 1px solid #fbbf24;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 700;
          color: #92400e;
          letter-spacing: 0.5px;
        }
        
        .mock-warning {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 10px 14px;
          background: #fffbeb;
          border-bottom: 1px solid #fbbf24;
          font-size: 12px;
          color: #92400e;
          line-height: 1.5;
        }
        
        .mock-warning code {
          background: #fef3c7;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
          font-size: 11px;
        }
        
        .preview-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: #6b7280;
        }
        
        .preview-table-wrapper {
          max-height: 300px;
          overflow: auto;
        }
        
        .preview-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        
        .preview-table thead {
          position: sticky;
          top: 0;
          background: white;
          z-index: 1;
        }
        
        .preview-table th {
          text-align: left;
          padding: 8px 12px;
          font-weight: 600;
          color: #374151;
          border-bottom: 2px solid #e5e7eb;
          background: #f9fafb;
        }
        
        .preview-table td {
          padding: 8px 12px;
          border-bottom: 1px solid #f3f4f6;
          color: #111827;
          font-family: 'Courier New', monospace;
        }
        
        .preview-table tbody tr:hover {
          background: #f9fafb;
        }
        
        .preview-table tbody tr:last-child td {
          border-bottom: none;
        }

        /* Modal styles */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal-content {
          background: white;
          border-radius: 12px;
          width: 90%;
          max-width: 1000px;
          max-height: 80vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        .modal-header {
          padding: 20px;
          border-bottom: 1px solid #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .modal-header h2 {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 18px;
          font-weight: 600;
          color: #111827;
          margin: 0;
        }

        .modal-close {
          padding: 8px;
          background: none;
          border: none;
          cursor: pointer;
          border-radius: 6px;
          color: #6b7280;
        }

        .modal-close:hover {
          background: #f3f4f6;
          color: #111827;
        }

        .modal-body {
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        }

        .modal-table {
          width: 100%;
          border-collapse: collapse;
        }

        .modal-table thead {
          background: #f9fafb;
          position: sticky;
          top: 0;
        }

        .modal-table th {
          padding: 12px;
          text-align: left;
          font-size: 11px;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          border-bottom: 2px solid #e5e7eb;
        }

        .modal-table td {
          padding: 12px;
          font-size: 13px;
          color: #374151;
          border-bottom: 1px solid #f3f4f6;
        }

        .modal-table tbody tr:hover {
          background: #f9fafb;
        }

        .modal-table code {
          background: #f3f4f6;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-family: 'Monaco', monospace;
        }

        .rule-badge {
          display: inline-block;
          padding: 4px 8px;
          background: #fef3c7;
          color: #92400e;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }

        /* ============================================ */
        /* RICH SILVER LAYER STYLES */
        /* ============================================ */

        .tab-transform-rich {
          display: flex;
          flex-direction: column;
          gap: 24px;
          padding: 24px;
          overflow-y: auto;
          max-height: calc(100vh - 200px);
        }

        .rich-section {
          background: #ffffff;
          border-radius: 12px;
          border: 1px solid #e5e7eb;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          transition: all 0.3s ease;
        }

        .rich-section:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          border-color: #d1d5db;
        }

        .section-header-rich {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 2px solid #f3f4f6;
        }

        .section-title-group {
          display: flex;
          align-items: flex-start;
          gap: 12px;
        }

        .section-title-group svg {
          flex-shrink: 0;
          margin-top: 4px;
          color: #3b82f6;
        }

        .section-title-group h3 {
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          color: #111827;
          letter-spacing: -0.5px;
        }

        .section-subtitle {
          margin: 4px 0 0 0;
          font-size: 14px;
          color: #6b7280;
          font-weight: 400;
        }

        .section-actions-rich {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .toggle-btn {
          padding: 8px 16px;
          border: 1.5px solid #e5e7eb;
          background: #ffffff;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .toggle-btn:hover {
          border-color: #3b82f6;
          background: #eff6ff;
          color: #3b82f6;
        }

        .toggle-btn.active {
          border-color: #3b82f6;
          background: #3b82f6;
          color: #ffffff;
          box-shadow: 0 1px 3px rgba(59, 130, 246, 0.3);
        }

        .count-badge-rich {
          padding: 6px 12px;
          background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
          color: #ffffff;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 700;
        }

        .info-banner {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 8px;
          margin-bottom: 20px;
          font-size: 14px;
          color: #1e40af;
        }

        .evolution-banner {
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Schema Mapping Table */
        .schema-mapping-table {
          margin: 20px 0;
          overflow-x: auto;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .mapping-table-rich {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }

        .mapping-table-rich thead {
          background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        }

        .mapping-table-rich th {
          padding: 14px 16px;
          text-align: left;
          font-weight: 700;
          color: #374151;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 2px solid #d1d5db;
        }

        .mapping-table-rich .col-arrow {
          text-align: center;
          width: 60px;
        }

        .mapping-table-rich .col-source,
        .mapping-table-rich .col-target {
          width: 25%;
        }

        .mapping-table-rich .col-source-type,
        .mapping-table-rich .col-target-type {
          width: 15%;
        }

        .mapping-table-rich .col-transform {
          width: 15%;
        }

        .mapping-row-rich {
          transition: all 0.2s ease;
        }

        .mapping-row-rich:hover {
          background: #f9fafb;
        }

        .mapping-row-rich td {
          padding: 16px;
          border-bottom: 1px solid #f3f4f6;
        }

        .col-name-code {
          font-family: 'Monaco', 'Courier New', monospace;
          font-size: 13px;
          color: #111827;
          font-weight: 600;
          background: #f9fafb;
          padding: 4px 8px;
          border-radius: 4px;
        }

        .type-badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 700;
          font-family: 'Monaco', monospace;
          text-transform: uppercase;
        }

        .type-badge.source-type {
          background: #fef3c7;
          color: #92400e;
        }

        .type-badge.target-type {
          background: #d1fae5;
          color: #065f46;
        }

        .transform-badge-rich {
          display: inline-block;
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 600;
          border: 1.5px solid;
        }

        .col-arrow svg {
          opacity: 0.4;
          transition: opacity 0.2s;
        }

        .mapping-row-rich:hover .col-arrow svg {
          opacity: 1;
        }

        /* Execution Mode */
        .execution-mode-rich {
          margin-top: 24px;
          padding: 20px;
          background: #f9fafb;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .mode-label {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 12px;
          display: block;
        }

        .execution-mode-selector-rich {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
        }

        .mode-chip-rich {
          padding: 10px 20px;
          border: 2px solid #e5e7eb;
          background: #ffffff;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
        }

        .mode-chip-rich:hover {
          border-color: #8b5cf6;
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(139, 92, 246, 0.2);
        }

        .mode-chip-rich.active {
          border-color: #8b5cf6;
          background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
          color: #ffffff;
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
        }

        .watermark-selector-rich {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-top: 16px;
          padding: 16px;
          background: #ffffff;
          border-radius: 8px;
          border: 1px dashed #cbd5e1;
        }

        .watermark-selector-rich label {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
        }

        .watermark-selector-rich select {
          padding: 8px 12px;
          border: 1.5px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          color: #111827;
          background: #ffffff;
          cursor: pointer;
          min-width: 180px;
        }

        .watermark-info {
          font-size: 13px;
          color: #6b7280;
          font-style: italic;
        }

        .watermark-info code {
          background: #fef3c7;
          color: #92400e;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 600;
        }

        /* Data Quality Constraints */
        .constraints-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 16px;
          margin: 20px 0;
        }

        .constraint-card {
          background: #f9fafb;
          border: 1.5px solid #e5e7eb;
          border-radius: 10px;
          padding: 16px;
          transition: all 0.3s ease;
        }

        .constraint-card:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
          transform: translateY(-2px);
        }

        .constraint-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #e5e7eb;
        }

        .col-name-constraint {
          font-family: 'Monaco', monospace;
          font-size: 14px;
          font-weight: 700;
          color: #111827;
          background: #ffffff;
          padding: 4px 8px;
          border-radius: 6px;
        }

        .col-type-small {
          font-size: 10px;
          font-weight: 700;
          color: #6b7280;
          text-transform: uppercase;
          background: #e5e7eb;
          padding: 3px 8px;
          border-radius: 4px;
        }

        .constraint-checks {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: #374151;
          cursor: pointer;
          user-select: none;
        }

        .checkbox-label input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
          accent-color: #3b82f6;
        }

        .regex-input-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .regex-input {
          width: 100%;
          padding: 8px 12px;
          border: 1.5px solid #d1d5db;
          border-radius: 6px;
          font-size: 13px;
          font-family: 'Monaco', monospace;
          color: #111827;
        }

        .regex-input:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .regex-label {
          font-size: 11px;
          color: #6b7280;
          font-style: italic;
        }

        .btn-set-pk {
          margin-top: 12px;
          padding: 10px;
          border: 1.5px dashed #d1d5db;
          background: #ffffff;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-set-pk:hover {
          border-color: #fbbf24;
          background: #fffbeb;
          color: #92400e;
        }

        .pk-badge {
          margin-top: 12px;
          padding: 10px;
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          color: #ffffff;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 700;
          text-align: center;
          box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
        }

        .constraints-summary {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px;
          background: #f3f4f6;
          border-radius: 8px;
          font-size: 13px;
          color: #6b7280;
          margin-top: 20px;
        }

        .constraints-summary span:not(:last-child) {
          font-weight: 600;
        }

        .btn-add-constraint {
          padding: 8px 16px;
          border: 1.5px solid #10b981;
          background: #ffffff;
          color: #10b981;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-add-constraint:hover {
          background: #10b981;
          color: #ffffff;
          box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }

        /* Transformation Preview */
        .preview-container {
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          gap: 20px;
          margin-top: 20px;
        }

        .preview-panel {
          background: #f9fafb;
          border: 1.5px solid #e5e7eb;
          border-radius: 10px;
          overflow: hidden;
        }

        .preview-panel-header {
          padding: 16px 20px;
          border-bottom: 2px solid #e5e7eb;
        }

        .preview-panel-header.before {
          background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%);
        }

        .preview-panel-header.after {
          background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        }

        .preview-panel-header h4 {
          margin: 0 0 4px 0;
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .panel-subtitle {
          margin: 0;
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .preview-table-wrapper {
          overflow: auto;
          max-height: 400px;
        }

        .preview-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }

        .preview-table thead {
          position: sticky;
          top: 0;
          background: #ffffff;
          z-index: 10;
        }

        .preview-table th {
          padding: 12px;
          text-align: left;
          font-weight: 700;
          color: #374151;
          border-bottom: 2px solid #e5e7eb;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .preview-table td {
          padding: 10px 12px;
          border-bottom: 1px solid #f3f4f6;
          color: #111827;
        }

        .preview-table tbody tr:hover {
          background: #ffffff;
        }

        .null-cell {
          color: #9ca3af;
          font-style: italic;
        }

        .status-badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
        }

        .status-passed {
          background: #d1fae5;
          color: #065f46;
        }

        .status-quarantined {
          background: #fed7aa;
          color: #92400e;
        }

        .status-rejected {
          background: #fee2e2;
          color: #991b1b;
        }

        .row-status-passed {
          background: #f0fdf4;
        }

        .row-status-quarantined {
          background: #fffbeb;
        }

        .row-status-rejected {
          background: #fef2f2;
        }

        .reason-cell {
          color: #6b7280;
          font-size: 12px;
          font-style: italic;
        }

        .preview-divider {
          display: flex;
          align-items: center;
          justify-content: center;
          color: #3b82f6;
        }

        .btn-load-preview {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 20px;
          border: none;
          background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
          color: #ffffff;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }

        .btn-load-preview:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .btn-load-preview:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .preview-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 80px 40px;
          background: #f9fafb;
          border: 2px dashed #d1d5db;
          border-radius: 10px;
          margin-top: 20px;
        }

        .preview-empty-state p {
          margin: 16px 0 8px 0;
          font-size: 16px;
          font-weight: 600;
          color: #374151;
        }

        .hint-text {
          font-size: 14px;
          color: #6b7280;
          max-width: 400px;
          text-align: center;
        }

        /* Performance Tuning */
        .tuning-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 20px;
          margin-top: 20px;
        }

        .tuning-card {
          background: #f9fafb;
          border: 1.5px solid #e5e7eb;
          border-radius: 10px;
          padding: 20px;
          transition: all 0.3s ease;
        }

        .tuning-card:hover {
          border-color: #8b5cf6;
          box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
          transform: translateY(-2px);
        }

        .tuning-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .tuning-card-header h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .tuning-badge {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          background: #e5e7eb;
          color: #6b7280;
        }

        .tuning-badge.advanced {
          background: #fef3c7;
          color: #92400e;
        }

        .tuning-badge.modern {
          background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
          color: #ffffff;
        }

        .tuning-description {
          font-size: 14px;
          color: #6b7280;
          margin: 0 0 16px 0;
          line-height: 1.6;
        }

        .column-selector {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-top: 16px;
        }

        .column-selector label {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
        }

        .multi-select {
          padding: 10px;
          border: 1.5px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          color: #111827;
          background: #ffffff;
          min-height: 120px;
          cursor: pointer;
        }

        .multi-select:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .selected-count {
          font-size: 12px;
          color: #6b7280;
          font-weight: 600;
        }

        .selected-columns-display {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
        }

        .selected-col-badge {
          padding: 6px 12px;
          background: #dbeafe;
          color: #1e40af;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          font-family: 'Monaco', monospace;
        }

        .selected-col-badge.zorder {
          background: #fef3c7;
          color: #92400e;
        }

        .selected-col-badge.liquid {
          background: linear-gradient(135deg, #ddd6fe 0%, #c7d2fe 100%);
          color: #4c1d95;
        }

        .info-note {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 6px;
          font-size: 12px;
          color: #1e40af;
          margin-top: 12px;
        }

        .info-note.success {
          background: #f0fdf4;
          border-color: #bbf7d0;
          color: #166534;
        }

        .toggle-label-large {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 14px;
          font-weight: 600;
          color: #111827;
          cursor: pointer;
          padding: 12px;
          background: #ffffff;
          border-radius: 8px;
          border: 1.5px solid #e5e7eb;
          transition: all 0.2s ease;
        }

        .toggle-label-large:hover {
          border-color: #8b5cf6;
          background: #f5f3ff;
        }

        .toggle-label-large input[type="checkbox"] {
          width: 20px;
          height: 20px;
          cursor: pointer;
          accent-color: #8b5cf6;
        }

        /* Responsive */
        @media (max-width: 1400px) {
          .preview-container {
            grid-template-columns: 1fr;
          }
          
          .preview-divider {
            transform: rotate(90deg);
          }
        }

        @media (max-width: 1024px) {
          .constraints-grid {
            grid-template-columns: 1fr;
          }
          
          .tuning-grid {
            grid-template-columns: 1fr;
          }
        }

        /* ===== UNSTRUCTURED DATA TRANSFORMATION STYLES ===== */
        .unstructured-transforms-section {
          background: linear-gradient(135deg, #fef3c7 0%, #fce7f3 100%);
          border: 2px solid #f59e0b;
        }

        .unstructured-transforms-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 20px;
          margin-top: 16px;
        }

        .transform-category-card {
          background: white;
          border-radius: 12px;
          padding: 20px;
          border: 1.5px solid #e5e7eb;
          transition: all 0.2s;
        }

        .transform-category-card:hover {
          border-color: #f59e0b;
          box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
        }

        .transform-category-header {
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 2px solid #f3f4f6;
        }

        .transform-category-header h4 {
          margin: 0 0 4px 0;
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .transform-category-header p {
          margin: 0;
          font-size: 13px;
          color: #6b7280;
        }

        .checkbox-label-large {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          margin-bottom: 8px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
          font-size: 14px;
          color: #374151;
        }

        .checkbox-label-large:hover {
          background: #f9fafb;
        }

        .checkbox-label-large input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
          accent-color: #f59e0b;
        }

        .checkbox-label-large span {
          font-weight: 500;
        }

        .select-group {
          margin-top: 12px;
          margin-bottom: 12px;
        }

        .select-group label {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 6px;
        }

        .select-group select,
        .form-select {
          width: 100%;
          padding: 10px 12px;
          border: 1.5px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          color: #111827;
          background: white;
          cursor: pointer;
          transition: all 0.2s;
        }

        .select-group select:focus,
        .form-select:focus {
          outline: none;
          border-color: #f59e0b;
          box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
        }

        .image-resize-inputs {
          display: flex;
          gap: 12px;
          margin-top: 12px;
          padding: 12px;
          background: #fef3c7;
          border-radius: 8px;
        }

        .input-group-inline {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        .input-group-inline label {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          white-space: nowrap;
        }

        .size-input {
          flex: 1;
          padding: 8px 12px;
          border: 1.5px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          color: #111827;
        }

        .size-input:focus {
          outline: none;
          border-color: #f59e0b;
        }

        .augmentation-options {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-top: 8px;
        }

        @media (max-width: 768px) {
          .unstructured-transforms-grid {
            grid-template-columns: 1fr;
          }
          
          .augmentation-options {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
      
      {/* Quarantine Viewer Modal */}
      {showQuarantineViewer && (
        <div className="modal-overlay" onClick={() => setShowQuarantineViewer(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
                Quarantined Rows ({quarantineData.length})
              </h2>
              <button className="modal-close" onClick={() => setShowQuarantineViewer(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Row ID</th>
                    <th>Rule</th>
                    <th>Column</th>
                    <th>Value</th>
                    <th>Reason</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {quarantineData.map((row, idx) => (
                    <tr key={idx}>
                      <td><code>{row.row_id}</code></td>
                      <td><span className="rule-badge">{row.rule}</span></td>
                      <td><code>{row.column}</code></td>
                      <td><code>{row.value}</code></td>
                      <td>{row.reason}</td>
                      <td>{new Date(row.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Viewer Modal */}
      {showRejectionViewer && (
        <div className="modal-overlay" onClick={() => setShowRejectionViewer(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <AlertTriangle size={20} style={{ color: '#ef4444' }} />
                Rejected Rows ({rejectionData.length})
              </h2>
              <button className="modal-close" onClick={() => setShowRejectionViewer(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Row ID</th>
                    <th>Rule</th>
                    <th>Column</th>
                    <th>Value</th>
                    <th>Reason</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {rejectionData.map((row, idx) => (
                    <tr key={idx}>
                      <td><code>{row.row_id}</code></td>
                      <td><span className="rule-badge">{row.rule}</span></td>
                      <td><code>{row.column}</code></td>
                      <td><code>{row.value}</code></td>
                      <td>{row.reason}</td>
                      <td>{new Date(row.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* All Failures Viewer Modal */}
      {showAllFailuresModal && selectedRuleForFailures && (
        <div className="modal-overlay" onClick={() => setShowAllFailuresModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                <AlertTriangle size={20} style={{ color: '#ef4444' }} />
                All Failures for Rule: {selectedRuleForFailures}
              </h2>
              <button className="modal-close" onClick={() => setShowAllFailuresModal(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="failure-summary">
                <p><strong>Total Failures:</strong> {ruleResults[selectedRuleForFailures]?.failed || 0}</p>
                <p><strong>Action:</strong> <span className={`action-badge action-${ruleResults[selectedRuleForFailures]?.action}`}>
                  {ruleResults[selectedRuleForFailures]?.action?.toUpperCase()}
                </span></p>
                <p><strong>Threshold:</strong> {ruleResults[selectedRuleForFailures]?.threshold}</p>
              </div>
              <table className="modal-table">
                <thead>
                  <tr>
                    <th>Failure Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleResults[selectedRuleForFailures]?.samples?.map((sample, idx) => (
                    <tr key={idx}>
                      <td><code>{sample}</code></td>
                    </tr>
                  ))}
                  {(!ruleResults[selectedRuleForFailures]?.samples || ruleResults[selectedRuleForFailures]?.samples.length === 0) && (
                    <tr>
                      <td colSpan="1" style={{ textAlign: 'center', padding: '24px', color: '#9ca3af' }}>
                        No detailed failure samples available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      
      {/* Iceberg Snapshot Viewer Modal */}
      {showSnapshotViewer && (
        <div className="modal-overlay" onClick={() => setShowSnapshotViewer(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={20} style={{ color: '#7c3aed' }} />
                Iceberg Snapshot History - {selectedTable?.table_name}
              </h2>
              <button className="modal-close" onClick={() => setShowSnapshotViewer(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              {snapshotLoading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
                  <RefreshCw size={24} className="spinning" style={{ marginBottom: '12px' }} />
                  <div>Loading snapshot history...</div>
                </div>
              ) : snapshotHistory.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                  <Layers size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
                  <p>No snapshots available yet.</p>
                  <p style={{ fontSize: '14px', marginTop: '8px' }}>
                    Snapshots will appear after running Spark transformations.
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{
                    marginBottom: '16px',
                    padding: '12px',
                    backgroundColor: '#faf5ff',
                    borderRadius: '6px',
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    <strong style={{ color: '#7c3aed' }}>Time-Travel Feature:</strong> Query any historical version of this table using snapshot IDs
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {snapshotHistory.map((snapshot, idx) => (
                      <div key={idx} style={{
                        padding: '16px',
                        backgroundColor: idx === 0 ? '#ecfdf5' : '#f9fafb',
                        border: `2px solid ${idx === 0 ? '#10b981' : '#e5e7eb'}`,
                        borderRadius: '8px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'between', marginBottom: '12px' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                              <code style={{
                                fontSize: '15px',
                                fontWeight: 600,
                                color: '#1f2937',
                                padding: '2px 8px',
                                backgroundColor: 'white',
                                borderRadius: '4px',
                                border: '1px solid #d1d5db'
                              }}>
                                Snapshot {snapshot.snapshot_id || idx + 1}
                              </code>
                              {idx === 0 && (
                                <span style={{
                                  fontSize: '11px',
                                  fontWeight: 600,
                                  color: '#059669',
                                  padding: '2px 8px',
                                  backgroundColor: '#d1fae5',
                                  borderRadius: '4px'
                                }}>
                                  CURRENT
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '13px', color: '#6b7280' }}>
                              {snapshot.committed_at ? new Date(snapshot.committed_at).toLocaleString() : 'Unknown date'}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '2px' }}>
                              Operation
                            </div>
                            <div style={{
                              fontSize: '14px',
                              fontWeight: 600,
                              color: '#7c3aed',
                              textTransform: 'uppercase'
                            }}>
                              {snapshot.operation || 'APPEND'}
                            </div>
                          </div>
                        </div>
                        
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(4, 1fr)',
                          gap: '12px',
                          fontSize: '13px'
                        }}>
                          <div>
                            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Total Records</div>
                            <div style={{ fontWeight: 600, fontSize: '16px', color: '#1f2937' }}>
                              {snapshot.summary?.['total-records']?.toLocaleString() || 'N/A'}
                            </div>
                          </div>
                          <div>
                            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Data Files</div>
                            <div style={{ fontWeight: 600, fontSize: '16px', color: '#1f2937' }}>
                              {snapshot.summary?.['total-data-files'] || 'N/A'}
                            </div>
                          </div>
                          <div>
                            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Added Files</div>
                            <div style={{ fontWeight: 600, fontSize: '16px', color: '#059669' }}>
                              {snapshot.summary?.['added-data-files'] || '0'}
                            </div>
                          </div>
                          <div>
                            <div style={{ color: '#6b7280', marginBottom: '4px' }}>Deleted Files</div>
                            <div style={{ fontWeight: 600, fontSize: '16px', color: '#dc2626' }}>
                              {snapshot.summary?.['deleted-data-files'] || '0'}
                            </div>
                          </div>
                        </div>
                        
                        {snapshot.parent_snapshot_id && (
                          <div style={{
                            marginTop: '8px',
                            paddingTop: '8px',
                            borderTop: '1px solid #e5e7eb',
                            fontSize: '12px',
                            color: '#9ca3af'
                          }}>
                            Parent: {snapshot.parent_snapshot_id}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {/* Query Example */}
                  {snapshotHistory.length > 0 && (
                    <div style={{
                      marginTop: '16px',
                      padding: '12px',
                      backgroundColor: '#f9fafb',
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px'
                    }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#4b5563' }}>
                        💡 Query Historical Snapshot (Time-Travel):
                      </div>
                      <code style={{
                        display: 'block',
                        padding: '8px',
                        backgroundColor: '#1f2937',
                        color: '#10b981',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        overflowX: 'auto'
                      }}>
                        SELECT * FROM syniq_iceberg.silver_{domain}.{selectedTable?.table_name}
                        <br />
                        VERSION AS OF {snapshotHistory[0]?.snapshot_id || 'SNAPSHOT_ID'}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )})()}
    </div>
  );
}
