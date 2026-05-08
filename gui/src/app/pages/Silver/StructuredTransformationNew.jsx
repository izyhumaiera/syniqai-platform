import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Database, Code, GitBranch, Play, Clock, DollarSign, AlertTriangle, CheckCircle, XCircle, Loader } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

// Constants
const RULE_TYPES = {
  not_null: { label: 'Not Null', description: 'Validate non-null values', params: [] },
  email: { label: 'Email Format', description: 'Validate email addresses', params: [] },
  phone: { label: 'Phone Number', description: 'Validate phone numbers', params: [] },
  range: { label: 'Numeric Range', description: 'Validate numeric values within range', params: ['min', 'max'] },
  length: { label: 'String Length', description: 'Validate string length', params: ['min', 'max'] },
  regex: { label: 'Regex Pattern', description: 'Custom pattern matching', params: ['pattern'] },
  enum: { label: 'Allowed Values', description: 'Validate against allowed values', params: ['values'] }
};

const NORMALIZATION_TYPES = {
  lowercase: 'Lowercase',
  uppercase: 'Uppercase',
  titlecase: 'Title Case',
  trim: 'Trim Whitespace',
  phone_format: 'Phone Format (digits only)',
  round: 'Round Decimals'
};

const SEVERITY_LEVELS = [
  { value: 'ERROR', label: 'ERROR - Fail job', color: 'red', icon: '🚫' },
  { value: 'WARN', label: 'WARN - Log warning', color: 'yellow', icon: '⚠️' },
  { value: 'DROP', label: 'DROP - Skip row', color: 'orange', icon: '🗑️' },
  { value: 'QUARANTINE', label: 'QUARANTINE - Route to DLQ', color: 'purple', icon: '🔒' }
];

const WORKER_TYPES = ['G.1X', 'G.2X', 'G.4X', 'G.8X', 'Z.2X'];
const TRIGGER_TYPES = ['On-Demand', 'Scheduled (Cron)', 'Event-Driven', 'Continuous'];
const TABLE_FORMATS = ['Apache Iceberg', 'Delta Lake', 'Apache Hudi', 'Parquet'];
const COMPRESSION_CODECS = ['snappy', 'gzip', 'zstd', 'lz4', 'none'];

export default function StructuredTransformation() {
  const [searchParams] = useSearchParams();
  
  // Active tab state
  const [activeTab, setActiveTab] = useState('configuration');
  
  // Source context (from Data Catalog)
  const [sourceContext, setSourceContext] = useState({
    tableName: '',
    domain: '',
    source: '',
    layer: 'bronze'
  });
  
  // State management
  const [selectedBronzeTable, setSelectedBronzeTable] = useState('');
  const [silverTableName, setSilverTableName] = useState('');
  const [schema, setSchema] = useState(null);
  const [preview, setPreview] = useState(null);
  
  // AWS Glue Configuration state
  const [glueConfig, setGlueConfig] = useState({
    workerType: 'G.2X',
    numberOfWorkers: 2,
    timeout: 60,
    maxRetries: 1,
    triggerType: 'On-Demand',
    cronExpression: '0 0 * * ? *',
    enableDLQ: true,
    dlqS3Path: 's3://syniqai-quarantine/silver/'
  });
  
  // Output configuration state
  const [outputConfig, setOutputConfig] = useState({
    tableFormat: 'Apache Iceberg',
    s3Path: 's3://syniqai-silver/',
    compression: 'snappy',
    partitionBy: [],
    enableVersioning: true
  });
  
  // Quality rules state
  const [qualityRules, setQualityRules] = useState([]);
  const [currentRule, setCurrentRule] = useState({
    name: '',
    type: 'not_null',
    column: '',
    params: {},
    severity: 'ERROR'
  });
  
  // Normalization state
  const [normalizations, setNormalizations] = useState([]);
  const [currentNormalization, setCurrentNormalization] = useState({
    column: '',
    type: 'lowercase',
    params: {}
  });
  
  // Deduplication state
  const [dedupColumns, setDedupColumns] = useState([]);
  
  // Run history state
  const [runHistory, setRunHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  
  // Transformation state
  const [isTransforming, setIsTransforming] = useState(false);
  const [transformationResult, setTransformationResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Generated script state
  const [generatedScript, setGeneratedScript] = useState('');
  
  // Loading states
  const [loading, setLoading] = useState({ schema: false, preview: false, history: false });

  // Initialize from URL params
  useEffect(() => {
    const tableParam = searchParams.get('table');
    const domainParam = searchParams.get('domain') || 'finance';
    const sourceParam = searchParams.get('source') || 'postgres';
    
    if (tableParam) {
      setSourceContext({
        tableName: tableParam,
        domain: domainParam,
        source: sourceParam,
        layer: 'bronze'
      });
      
      setSelectedBronzeTable(`${domainParam}.${tableParam}`);
      setSilverTableName(`silver.${tableParam}_cleaned`);
      
      setOutputConfig(prev => ({
        ...prev,
        s3Path: `s3://syniqai-silver/${domainParam}/${tableParam}/`
      }));
      
      loadTableSchema(domainParam, sourceParam, tableParam);
    }
  }, [searchParams]);

  // Load schema
  const loadTableSchema = async (domain, source, table) => {
    setLoading(prev => ({ ...prev, schema: true }));
    try {
      const response = await axios.get(`${API_BASE}/bronze-data/schema/${table}`, {
        params: { domain, source }
      });
      if (response.data.success) {
        setSchema(response.data.schema);
      }
    } catch (err) {
      setError(`Failed to load schema: ${err.message}`);
    } finally {
      setLoading(prev => ({ ...prev, schema: false }));
    }
  };

  // Generate PySpark script
  const generatePySparkScript = () => {
    let script = `# Generated PySpark Script for ${silverTableName}\n`;
    script += `# AWS Glue Job Configuration: ${glueConfig.workerType} x ${glueConfig.numberOfWorkers} workers\n`;
    script += `# Estimated DPU: ${calculateGlueCost().totalDPU} | Cost/hour: $${calculateGlueCost().costPerHour}\n\n`;
    script += `from awsglue.context import GlueContext\n`;
    script += `from awsglue.transforms import *\n`;
    script += `from pyspark.sql import SparkSession\n`;
    script += `from pyspark.sql import functions as F\n`;
    script += `from pyspark.sql.types import *\n\n`;
    script += `# Initialize Spark and Glue context\n`;
    script += `spark = SparkSession.builder \\\n`;
    script += `    .appName("${silverTableName}") \\\n`;
    script += `    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \\\n`;
    script += `    .getOrCreate()\n\n`;
    script += `glueContext = GlueContext(spark.sparkContext)\n`;
    script += `logger = glueContext.get_logger()\n\n`;
    script += `# Read from Bronze (${sourceContext.layer})\n`;
    script += `logger.info("Reading from Bronze: ${sourceContext.domain}.${sourceContext.tableName}")\n`;
    script += `df = spark.read \\\n`;
    script += `    .format("parquet") \\\n`;
    script += `    .load("s3://syniqai-bronze/${sourceContext.domain}/${sourceContext.source}/${sourceContext.tableName}/")\n\n`;
    script += `initial_count = df.count()\n`;
    script += `logger.info(f"Initial record count: {initial_count}")\n\n`;
    
    // Quality rules
    if (qualityRules.length > 0) {
      script += `# ========================================\n`;
      script += `# QUALITY RULES (${qualityRules.length} rules)\n`;
      script += `# ========================================\n`;
      qualityRules.forEach(rule => {
        script += `\n# Rule: ${rule.name} [${rule.severity}]\n`;
        if (rule.type === 'not_null') {
          if (rule.severity === 'ERROR') {
            script += `df = df.filter(F.col("${rule.column}").isNotNull())\n`;
          } else if (rule.severity === 'QUARANTINE') {
            script += `bad_rows = df.filter(F.col("${rule.column}").isNull())\n`;
            script += `bad_rows.write.mode("append").parquet("${glueConfig.dlqS3Path}${sourceContext.tableName}/nulls/")\n`;
            script += `df = df.filter(F.col("${rule.column}").isNotNull())\n`;
          } else if (rule.severity === 'DROP') {
            script += `df = df.filter(F.col("${rule.column}").isNotNull())\n`;
          } else if (rule.severity === 'WARN') {
            script += `null_count = df.filter(F.col("${rule.column}").isNull()).count()\n`;
            script += `if null_count > 0:\n`;
            script += `    logger.warn(f"Found {null_count} null values in ${rule.column}")\n`;
          }
        }else if (rule.type === 'range') {
          script += `df = df.filter((F.col("${rule.column}") >= ${rule.params.min}) & (F.col("${rule.column}") <= ${rule.params.max}))\n`;
        } else if (rule.type === 'email') {
          script += `df = df.filter(F.col("${rule.column}").rlike("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$"))\n`;
        }
      });
      script += `\nafter_rules_count = df.count()\n`;
      script += `logger.info(f"After quality rules: {after_rules_count} rows (dropped {initial_count - after_rules_count})")\n\n`;
    }
    
    // Normalizations
    if (normalizations.length > 0) {
      script += `# ========================================\n`;
      script += `# NORMALIZATIONS (${normalizations.length} transformations)\n`;
      script += `# ========================================\n`;
      normalizations.forEach(norm => {
        script += `\n# Normalize: ${norm.column} → ${norm.type}\n`;
        if (norm.type === 'lowercase') {
          script += `df = df.withColumn("${norm.column}", F.lower(F.col("${norm.column}")))\n`;
        } else if (norm.type === 'uppercase') {
          script += `df = df.withColumn("${norm.column}", F.upper(F.col("${norm.column}")))\n`;
        } else if (norm.type === 'titlecase') {
          script += `df = df.withColumn("${norm.column}", F.initcap(F.col("${norm.column}")))\n`;
        } else if (norm.type === 'trim') {
          script += `df = df.withColumn("${norm.column}", F.trim(F.col("${norm.column}")))\n`;
        } else if (norm.type === 'phone_format') {
          script += `df = df.withColumn("${norm.column}", F.regexp_replace(F.col("${norm.column}"), "[^0-9]", ""))\n`;
        }
      });
      script += `\n`;
    }
    
    // Deduplication
    if (dedupColumns.length > 0) {
      script += `# ========================================\n`;
      script += `# DEDUPLICATION\n`;
      script += `# ========================================\n`;
      script += `df = df.dropDuplicates([${dedupColumns.map(c => `"${c}"`).join(', ')}])\n`;
      script += `after_dedup_count = df.count()\n`;
      script += `logger.info(f"After deduplication: {after_dedup_count} rows")\n\n`;
    }
    
    // Write to Silver
    script += `# ========================================\n`;
    script += `# WRITE TO SILVER\n`;
    script += `# ========================================\n`;
    script += `logger.info(f"Writing to Silver: ${silverTableName}")\n`;
    script += `logger.info(f"Format: ${outputConfig.tableFormat}")\n`;
    script += `logger.info(f"Path: ${outputConfig.s3Path}")\n\n`;
    script += `writer = df.write \\\n`;
    script += `    .format("${outputConfig.tableFormat.toLowerCase().replace('apache ', '').replace(' lake', '')}") \\\n`;
    script += `    .mode("overwrite") \\\n`;
    if (outputConfig.partitionBy.length > 0) {
      script += `    .partitionBy(${outputConfig.partitionBy.map(c => `"${c}"`).join(', ')}) \\\n`;
    }
    script += `    .option("compression", "${outputConfig.compression}") \\\n`;
    if (outputConfig.tableFormat === 'Apache Iceberg') {
      script += `    .option("write.format.default", "parquet") \\\n`;
      script += `    .option("write.metadata.compression-codec", "gzip") \\\n`;
    }
    script += `    .save("${outputConfig.s3Path}")\n\n`;
    script += `final_count = df.count()\n`;
    script += `logger.info(f"✅ Transformation complete!")\n`;
    script += `logger.info(f"  • Initial rows: {initial_count}")\n`;
    script += `logger.info(f"  • Final rows: {final_count}")\n`;
    script += `logger.info(f"  • Rows dropped: {initial_count - final_count}")\n`;
    script += `logger.info(f"  • Success rate: {(final_count/initial_count)*100:.2f}%")\n`;
    
    setGeneratedScript(script);
    return script;
  };

  const calculateGlueCost = () => {
    const dpuPerWorker = {
      'G.1X': 1,
      'G.2X': 2,
      'G.4X': 4,
      'G.8X': 8,
      'Z.2X': 2
    };
    
    const totalDPU = dpuPerWorker[glueConfig.workerType] * glueConfig.numberOfWorkers;
    const costPerHour = totalDPU * 0.44;
    const estimatedCost = (costPerHour * glueConfig.timeout) / 60;
    
    return {
      totalDPU,
      costPerHour: costPerHour.toFixed(2),
      estimatedCost: estimatedCost.toFixed(2),
      memory: totalDPU * 16,
      vCPU: totalDPU * 4
    };
  };

  // Auto-generate script when configuration changes
  useEffect(() => {
    if (sourceContext.tableName) {
      generatePySparkScript();
    }
  }, [qualityRules, normalizations, dedupColumns, outputConfig, glueConfig]);

  // Add quality rule
  const addQualityRule = () => {
    if (!currentRule.name || !currentRule.column) {
      alert('Please provide rule name and select column');
      return;
    }
    setQualityRules([...qualityRules, { ...currentRule, id: Date.now() }]);
    setCurrentRule({ name: '', type: 'not_null', column: '', params: {}, severity: 'ERROR' });
  };

  // Add normalization
  const addNormalization = () => {
    if (!currentNormalization.column) {
      alert('Please select a column');
      return;
    }
    setNormalizations([...normalizations, { ...currentNormalization, id: Date.now() }]);
    setCurrentNormalization({ column: '', type: 'lowercase', params: {} });
  };

  const executeTransformation = async () => {
    setIsTransforming(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/silver/execute-transformation`, {
        bronze_table: selectedBronzeTable,
        silver_table: silverTableName,
        quality_rules: qualityRules,
        normalizations,
        dedup_columns: dedupColumns,
        glue_config: glueConfig,
        output_config: outputConfig
      });
      setTransformationResult(response.data);
    } catch (err) {
      setError(`Transformation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsTransforming(false);
    }
  };

  const costEstimate = calculateGlueCost();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-800">Silver Layer Transformation</h1>
          <p className="text-sm text-gray-600 mt-1">
            Transform Bronze data to Silver with quality rules, normalization, and data cleaning
          </p>
        </div>
      </div>

      {/* Source Context Banner (Context-Aware) */}
      {sourceContext.tableName && (
        <div className="bg-blue-50 border-b border-blue-200 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Database className="w-5 h-5 text-blue-600" />
              <div>
                <span className="text-sm font-medium text-gray-700">Source:</span>
                <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-mono">
                  {sourceContext.domain}.{sourceContext.tableName}
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  ({sourceContext.source} • {sourceContext.layer} layer)
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Target:</span>
              <input
                type="text"
                value={silverTableName}
                onChange={(e) => setSilverTableName(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm font-mono"
              />
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('configuration')}
              className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'configuration'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Database className="w-4 h-4" />
                <span>Configuration</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('script')}
              className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'script'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Code className="w-4 h-4" />
                <span>Generated Script</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('schema-map')}
              className={`py-3 px-4 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'schema-map'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <GitBranch className="w-4 h-4" />
                <span>Schema Map</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Column: Configuration Sections */}
          <div className="lg:col-span-3 space-y-6">
            {activeTab === 'configuration' && (
              <>
                {/* Section 2: AWS Glue Configuration */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                    <span className="bg-blue-100 text-blue-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold mr-3">
                      1
                    </span>
                    AWS Glue Configuration
                  </h2>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Worker Type */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Worker Type
                      </label>
                      <select
                        value={glueConfig.workerType}
                        onChange={(e) => setGlueConfig({ ...glueConfig, workerType: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      >
                        {WORKER_TYPES.map(type => (
                          <option key={type} value={type}>{type}</option>
                        ))}
                      </select>
                      <p className="text-xs text-gray-500 mt-1">
                        {glueConfig.workerType === 'G.1X' && '1 DPU - Standard workload'}
                        {glueConfig.workerType === 'G.2X' && '2 DPU - Memory-intensive'}
                        {glueConfig.workerType === 'G.4X' && '4 DPU - Large datasets'}
                        {glueConfig.workerType === 'G.8X' && '8 DPU - Very large datasets'}
                        {glueConfig.workerType === 'Z.2X' && '2 DPU - Ray framework'}
                      </p>
                    </div>

                    {/* Number of Workers */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Number of Workers
                      </label>
                      <input
                        type="number"
                        min="2"
                        max="100"
                        value={glueConfig.numberOfWorkers}
                        onChange={(e) => setGlueConfig({ ...glueConfig, numberOfWorkers: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {costEstimate.totalDPU} DPU total • ${costEstimate.costPerHour}/hour
                      </p>
                    </div>

                    {/* Timeout */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Timeout (minutes)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="2880"
                        value={glueConfig.timeout}
                        onChange={(e) => setGlueConfig({ ...glueConfig, timeout: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    {/* Max Retries */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Max Retries
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={glueConfig.maxRetries}
                        onChange={(e) => setGlueConfig({ ...glueConfig, maxRetries: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    {/* Trigger Type */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Trigger Type
                      </label>
                      <select
                        value={glueConfig.triggerType}
                        onChange={(e) => setGlueConfig({ ...glueConfig, triggerType: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      >
                        {TRIGGER_TYPES.map(type => (
                          <option key={type} value={type}>{type}</option>
                        ))}
                      </select>
                    </div>

                    {/* Cron Expression (conditional) */}
                    {glueConfig.triggerType === 'Scheduled (Cron)' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Cron Expression
                        </label>
                        <input
                          type="text"
                          value={glueConfig.cronExpression}
                          onChange={(e) => setGlueConfig({ ...glueConfig, cronExpression: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-2 focus:ring-blue-500"
                          placeholder="0 0 * * ? *"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Current: Daily at midnight UTC
                        </p>
                      </div>
                    )}
                  </div>

                  {/* DLQ Toggle */}
                  <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-md">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={glueConfig.enableDLQ}
                        onChange={(e) => setGlueConfig({ ...glueConfig, enableDLQ: e.target.checked })}
                        className="rounded border-gray-300"
                      />
                      <span className="text-sm font-medium text-gray-700">
                        Enable Dead Letter Queue (DLQ)
                      </span>
                    </label>
                    {glueConfig.enableDLQ && (
                      <input
                        type="text"
                        value={glueConfig.dlqS3Path}
                        onChange={(e) => setGlueConfig({ ...glueConfig, dlqS3Path: e.target.value })}
                        className="mt-2 w-full px-3 py-1 border border-gray-300 rounded text-sm font-mono"
                        placeholder="s3://bucket/path/"
                      />
                    )}
                  </div>

                  {/* Compute Stats Summary */}
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <div className="bg-gray-50 rounded p-3 text-center">
                      <div className="text-2xl font-bold text-gray-800">{costEstimate.totalDPU}</div>
                      <div className="text-xs text-gray-600">Total DPU</div>
                    </div>
                    <div className="bg-gray-50 rounded p-3 text-center">
                      <div className="text-2xl font-bold text-gray-800">{costEstimate.memory}GB</div>
                      <div className="text-xs text-gray-600">Memory</div>
                    </div>
                    <div className="bg-gray-50 rounded p-3 text-center">
                      <div className="text-2xl font-bold text-gray-800">{costEstimate.vCPU}</div>
                      <div className="text-xs text-gray-600">vCPU Cores</div>
                    </div>
                  </div>
                </div>

                {/* Section 3: Quality Rules */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                    <span className="bg-blue-100 text-blue-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold mr-3">
                      2
                    </span>
                    Configure Quality Rules
                  </h2>

                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                      <input
                        type="text"
                        value={currentRule.name}
                        onChange={(e) => setCurrentRule({ ...currentRule, name: e.target.value })}
                        placeholder="Rule name"
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      />
                      <select
                        value={currentRule.type}
                        onChange={(e) => setCurrentRule({ ...currentRule, type: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        {Object.entries(RULE_TYPES).map(([key, val]) => (
                          <option key={key} value={key}>{val.label}</option>
                        ))}
                      </select>
                      <select
                        value={currentRule.column}
                        onChange={(e) => setCurrentRule({ ...currentRule, column: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        <option value="">Select column...</option>
                        {schema?.map(col => (
                          <option key={col.name} value={col.name}>{col.name}</option>
                        ))}
                      </select>
                      <select
                        value={currentRule.severity}
                        onChange={(e) => setCurrentRule({ ...currentRule, severity: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        {SEVERITY_LEVELS.map(level => (
                          <option key={level.value} value={level.value}>
                            {level.icon} {level.value}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={addQualityRule}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium"
                      >
                        + Add Rule
                      </button>
                    </div>

                    {/* Rules List */}
                    {qualityRules.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {qualityRules.map((rule, index) => (
                          <div key={rule.id} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-200">
                            <div className="flex-1">
                              <span className="font-medium text-sm">{rule.name}</span>
                              <span className="mx-2 text-gray-400">•</span>
                              <span className="text-sm text-gray-600">{RULE_TYPES[rule.type].label}</span>
                              <span className="mx-2 text-gray-400">•</span>
                              <code className="text-xs bg-white px-2 py-1 rounded">{rule.column}</code>
                            </div>
                            <div className="flex items-center space-x-3">
                              <span className={`px-2 py-1 rounded text-xs font-medium bg-${SEVERITY_LEVELS.find(l => l.value === rule.severity)?.color}-100 text-${SEVERITY_LEVELS.find(l => l.value === rule.severity)?.color}-800`}>
                                {SEVERITY_LEVELS.find(l => l.value === rule.severity)?.icon} {rule.severity}
                              </span>
                              <button
                                onClick={() => setQualityRules(qualityRules.filter(r => r.id !== rule.id))}
                                className="text-red-600 hover:text-red-800"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Section 4: Normalization */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                    <span className="bg-blue-100 text-blue-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold mr-3">
                      3
                    </span>
                    Configure Normalization
                  </h2>

                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <select
                        value={currentNormalization.column}
                        onChange={(e) => setCurrentNormalization({ ...currentNormalization, column: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        <option value="">Select column...</option>
                        {schema?.map(col => (
                          <option key={col.name} value={col.name}>{col.name}</option>
                        ))}
                      </select>
                      <select
                        value={currentNormalization.type}
                        onChange={(e) => setCurrentNormalization({ ...currentNormalization, type: e.target.value })}
                        className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        {Object.entries(NORMALIZATION_TYPES).map(([key, label]) => (
                          <option key={key} value={key}>{label}</option>
                        ))}
                      </select>
                      <button
                        onClick={addNormalization}
                        className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium"
                      >
                        + Add
                      </button>
                    </div>

                    {normalizations.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {normalizations.map(norm => (
                          <div key={norm.id} className="flex items-center justify-between p-3 bg-purple-50 rounded border border-purple-200">
                            <div>
                              <code className="text-sm font-mono">{norm.column}</code>
                              <span className="mx-2">→</span>
                              <span className="text-sm">{NORMALIZATION_TYPES[norm.type]}</span>
                            </div>
                            <button
                              onClick={() => setNormalizations(normalizations.filter(n => n.id !== norm.id))}
                              className="text-red-600 hover:text-red-800"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Section 5: Deduplication */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                    <span className="bg-blue-100 text-blue-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold mr-3">
                      4
                    </span>
                    Configure Deduplication
                  </h2>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select columns for deduplication (keep first occurrence)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {schema?.map(col => (
                        <label key={col.name} className="flex items-center space-x-2 p-2 hover:bg-gray-50 rounded">
                          <input
                            type="checkbox"
                            checked={dedupColumns.includes(col.name)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setDedupColumns([...dedupColumns, col.name]);
                              } else {
                                setDedupColumns(dedupColumns.filter(c => c !== col.name));
                              }
                            }}
                            className="rounded border-gray-300"
                          />
                          <span className="text-sm">{col.name}</span>
                        </label>
                      ))}
                    </div>
                    {dedupColumns.length > 0 && (
                      <p className="mt-2 text-sm text-gray-600">
                        Selected: {dedupColumns.join(', ')}
                      </p>
                    )}
                  </div>
                </div>

                {/* Section 6: Output Configuration */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                    <span className="bg-blue-100 text-blue-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold mr-3">
                      5
                    </span>
                    Output Configuration
                  </h2>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Table Format
                      </label>
                      <select
                        value={outputConfig.tableFormat}
                        onChange={(e) => setOutputConfig({ ...outputConfig, tableFormat: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      >
                        {TABLE_FORMATS.map(format => (
                          <option key={format} value={format}>{format}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Compression Codec
                      </label>
                      <select
                        value={outputConfig.compression}
                        onChange={(e) => setOutputConfig({ ...outputConfig, compression: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      >
                        {COMPRESSION_CODECS.map(codec => (
                          <option key={codec} value={codec}>{codec.toUpperCase()}</option>
                        ))}
                      </select>
                    </div>

                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        S3 Output Path
                      </label>
                      <input
                        type="text"
                        value={outputConfig.s3Path}
                        onChange={(e) => setOutputConfig({ ...outputConfig, s3Path: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div className="md:col-span-2">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={outputConfig.enableVersioning}
                          onChange={(e) => setOutputConfig({ ...outputConfig, enableVersioning: e.target.checked })}
                          className="rounded border-gray-300"
                        />
                        <span className="text-sm font-medium text-gray-700">
                          Enable table versioning (time travel queries)
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'script' && (
              <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-700 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-white flex items-center">
                    <Code className="w-5 h-5 mr-2" />
                    Generated PySpark Script
                  </h2>
                  <button
                    onClick={() => navigator.clipboard.writeText(generatedScript)}
                    className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                  >
                    📋 Copy
                  </button>
                </div>
                <pre className="text-green-400 text-sm font-mono overflow-x-auto whitespace-pre-wrap max-h-[600px] overflow-y-auto">
                  {generatedScript || '# Configure transformation rules to generate script...'}
                </pre>
              </div>
            )}

            {activeTab === 'schema-map' && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                  <GitBranch className="w-5 h-5 mr-2" />
                  Schema Mapping: Bronze → Silver
                </h2>
                {schema && (
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Bronze Column</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Nullable</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Silver Column</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">PII</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {schema.map((col, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-mono text-xs">{col.name}</td>
                          <td className="px-4 py-3 text-xs text-gray-600">{col.type}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded text-xs ${col.nullable ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                              {col.nullable ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">{col.name}</td>
                          <td className="px-4 py-3">
                            {(col.name.includes('email') || col.name.includes('phone') || col.name.includes('ssn')) && (
                              <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">🔒 PII</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Cost Estimator + Run History */}
          <div className="space-y-6">
            {/* Cost Estimator */}
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg shadow-sm border border-green-200 p-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center">
                <DollarSign className="w-4 h-4 mr-2 text-green-600" />
                Cost Estimator
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="text-3xl font-bold text-gray-800">${costEstimate.estimatedCost}</div>
                  <div className="text-xs text-gray-600">Estimated cost per run</div>
                </div>
                <div className="pt-3 border-t border-green-200 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Cost/hour:</span>
                    <span className="font-medium">${costEstimate.costPerHour}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Runtime:</span>
                    <span className="font-medium">{glueConfig.timeout} min</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total DPU:</span>
                    <span className="font-medium">{costEstimate.totalDPU}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Execute Transformation */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <button
                onClick={executeTransformation}
                disabled={isTransforming || !sourceContext.tableName}
                className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center space-x-2 shadow-md"
              >
                {isTransforming ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    <span>Transforming...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    <span>Execute Transformation</span>
                  </>
                )}
              </button>
              {transformationResult && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-sm">
                  <div className="font-medium text-green-800">✅ Success!</div>
                  <div className="text-gray-700 mt-1">
                    Rows processed: {transformationResult.rows_processed}
                  </div>
                </div>
              )}
            </div>

            {/* Run History */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-600" />
                  <span className="text-sm font-semibold text-gray-800">Run History</span>
                </div>
                <span className={`text-gray-400 transform transition-transform ${showHistory ? 'rotate-180' : ''}`}>
                  ▼
                </span>
              </button>
              {showHistory && (
                <div className="px-6 pb-4 space-y-2">
                  {runHistory.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No previous runs</p>
                  ) : (
                    runHistory.slice(0, 5).map((run, index) => (
                      <div key={index} className="p-3 border border-gray-200 rounded text-xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{run.job_name}</span>
                          {run.status === 'SUCCESS' && <CheckCircle className="w-4 h-4 text-green-600" />}
                          {run.status === 'FAILED' && <XCircle className="w-4 h-4 text-red-600" />}
                          {run.status === 'RUNNING' && <Loader className="w-4 h-4 text-blue-600 animate-spin" />}
                        </div>
                        <div className="text-gray-600">
                          {run.duration ? `${run.duration}s` : 'In progress'} • {new Date(run.timestamp).toLocaleString()}
                        </div>
                        {run.rows_processed && (
                          <div className="text-gray-500 mt-1">{run.rows_processed} rows processed</div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg max-w-md">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-red-600 mr-2 flex-shrink-0" />
            <div className="flex-1">
              <div className="font-semibold text-red-800">Error</div>
              <div className="text-sm text-red-700 mt-1">{error}</div>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-800 ml-2"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
