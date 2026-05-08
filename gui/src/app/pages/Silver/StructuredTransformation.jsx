import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

// Rule type definitions with descriptions
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
  const [activeTab, setActiveTab] = useState('configuration'); // configuration | script | schema-map
  
  // Source context (from Data Catalog)
  const [sourceContext, setSourceContext] = useState({
    tableName: '',
    domain: '',
    source: '',
    layer: 'bronze'
  });
  
  // State management
  const [bronzeTables, setBronzeTables] = useState([]);
  const [selectedBronzeTable, setSelectedBronzeTable] = useState('');
  const [silverTableName, setSilverTableName] = useState('');
  const [schema, setSchema] = useState(null);
  const [preview, setPreview] = useState(null);
  
  // AWS Glue Configuration state
  const [glueConfig, setGlueConfig] = useState({
    workerType: 'G.2X',
    numberOfWorkers: 2,
    timeout: 60, // minutes
    maxRetries: 1,
    triggerType: 'On-Demand',
    cronExpression: '0 0 * * ? *', // Daily at midnight
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
  
  // Type mapping state
  const [typeMappings, setTypeMappings] = useState({});
  
  // Deduplication state
  const [dedupColumns, setDedupColumns] = useState([]);
  
  // Run history state
  const [runHistory, setRunHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  
  // Templates state
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  
  // Transformation state
  const [isTransforming, setIsTransforming] = useState(false);
  const [transformationResult, setTransformationResult] = useState(null);
  const [error, setError] = useState(null);
  
  // Generated script state
  const [generatedScript, setGeneratedScript] = useState('');
  
  // Loading states
  const [loading, setLoading] = useState({ tables: false, schema: false, preview: false, history: false });

  // Load Bronze tables on mount
  useEffect(() => {
    loadBronzeTables();
    loadTemplates();
    loadRunHistory();
    
    // Check for pre-selected table from URL params (from Data Catalog)
    const tableParam = searchParams.get('table');
    const domainParam = searchParams.get('domain') || 'finance';
    const sourceParam = searchParams.get('source') || 'postgres';
    
    if (tableParam) {
      // Set source context from URL params
      setSourceContext({
        tableName: tableParam,
        domain: domainParam,
        source: sourceParam,
        layer: 'bronze'
      });
      
      // Set selected Bronze table for API calls
      const tableName = tableParam.includes('.') ? tableParam : `${domainParam}.${tableParam}`;
      setSelectedBronzeTable(tableName);
      
      // Auto-populate Silver table name
      setSilverTableName(`silver.${tableParam}_cleaned`);
      
      // Update output config S3 path
      setOutputConfig(prev => ({
        ...prev,
        s3Path: `s3://syniqai-silver/${domainParam}/${tableParam}/`
      }));
    }
  }, [searchParams]);

  // Load schema when Bronze table selected
  useEffect(() => {
    if (selectedBronzeTable) {
      loadTableSchema();
      loadTablePreview();
      
      // Auto-populate Silver table name
      if (!silverTableName) {
        const tableName = selectedBronzeTable.split('.').pop();
        setSilverTableName(`silver.${tableName}_cleaned`);
      }
    }
  }, [selectedBronzeTable]);

  // API Calls
  const loadBronzeTables = async () => {
    setLoading(prev => ({ ...prev, tables: true }));
    try {
      const response = await axios.get(`${API_BASE}/silver/bronze-tables`);
      setBronzeTables(response.data.tables || []);
    } catch (err) {
      setError('Failed to load Bronze tables: ' + err.message);
    } finally {
      setLoading(prev => ({ ...prev, tables: false }));
    }
  };

  const loadTableSchema = async () => {
    setLoading(prev => ({ ...prev, schema: true }));
    try {
      const response = await axios.get(`${API_BASE}/silver/table-schema/${selectedBronzeTable}`);
      setSchema(response.data.schema);
    } catch (err) {
      setError('Failed to load schema: ' + err.message);
    } finally {
      setLoading(prev => ({ ...prev, schema: false }));
    }
  };

  const loadTablePreview = async () => {
    setLoading(prev => ({ ...prev, preview: true }));
    try {
      const response = await axios.get(`${API_BASE}/silver/preview/${selectedBronzeTable}?limit=5`);
      setPreview(response.data.preview);
    } catch (err) {
      setError('Failed to load preview: ' + err.message);
    } finally {
      setLoading(prev => ({ ...prev, preview: false }));
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await axios.get(`${API_BASE}/silver/templates`);
      setTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const loadRunHistory = async () => {
    if (!sourceContext.tableName) return;
    
    setLoading(prev => ({ ...prev, history: true }));
    try {
      const response = await axios.get(`${API_BASE}/silver/job-history/${sourceContext.tableName}`);
      setRunHistory(response.data.jobs || []);
    } catch (err) {
      console.error('Failed to load run history:', err);
    } finally {
      setLoading(prev => ({ ...prev, history: false }));
    }
  };

  const generatePySparkScript = () => {
    // Generate PySpark script based on current configuration
    let script = `# Generated PySpark Script for ${silverTableName}\n`;
    script += `# AWS Glue Job Configuration: ${glueConfig.workerType} x ${glueConfig.numberOfWorkers} workers\n\n`;
    script += `from awsglue.context import GlueContext\n`;
    script += `from pyspark.sql import SparkSession\n`;
    script += `from pyspark.sql import functions as F\n\n`;
    script += `# Initialize Spark and Glue context\n`;
    script += `spark = SparkSession.builder.appName("${silverTableName}").getOrCreate()\n`;
    script += `glueContext = GlueContext(spark.sparkContext)\n\n`;
    script += `# Read from Bronze\n`;
    script += `df = spark.read.format("${outputConfig.tableFormat.toLowerCase().replace('apache ', '').replace(' lake', '')}").load("${sourceContext.tableName}")\n\n`;
    
    // Add quality rules
    if (qualityRules.length > 0) {
      script += `# Apply Quality Rules\n`;
      qualityRules.forEach(rule => {
        if (rule.type === 'not_null') {
          script += `df = df.filter(F.col("${rule.column}").isNotNull())  # ${rule.name}\n`;
        }
      });
      script += `\n`;
    }
    
    // Add normalizations
    if (normalizations.length > 0) {
      script += `# Apply Normalizations\n`;
      normalizations.forEach(norm => {
        if (norm.type === 'lowercase') {
          script += `df = df.withColumn("${norm.column}", F.lower(F.col("${norm.column}")))\n`;
        } else if (norm.type === 'uppercase') {
          script += `df = df.withColumn("${norm.column}", F.upper(F.col("${norm.column}")))\n`;
        }
      });
      script += `\n`;
    }
    
    // Add deduplication
    if (dedupColumns.length > 0) {
      script += `# Deduplicate\n`;
      script += `df = df.dropDuplicates([${dedupColumns.map(c => `"${c}"`).join(', ')}])\n\n`;
    }
    
    script += `# Write to Silver\n`;
    script += `df.write.format("${outputConfig.tableFormat.toLowerCase().replace('apache ', '').replace(' lake', '')}")\\\n`;
    script += `    .mode("overwrite")\\\n`;
    if (outputConfig.partitionBy.length > 0) {
      script += `    .partitionBy(${outputConfig.partitionBy.map(c => `"${c}"`).join(', ')})\\\n`;
    }
    script += `    .option("compression", "${outputConfig.compression}")\\\n`;
    script += `    .save("${outputConfig.s3Path}${silverTableName}")\n\n`;
    script += `print(f"✅ Transformation complete: {df.count()} rows written to Silver")\n`;
    
    setGeneratedScript(script);
    return script;
  };

  const calculateGlueCost = () => {
    // AWS Glue DPU pricing: $0.44 per DPU-hour
    const dpuPerWorker = {
      'G.1X': 1,
      'G.2X': 2,
      'G.4X': 4,
      'G.8X': 8,
      'Z.2X': 2
    };
    
    const totalDPU = dpuPerWorker[glueConfig.workerType] * glueConfig.numberOfWorkers;
    const costPerHour = totalDPU * 0.44;
    const estimatedCost = (costPerHour * glueConfig.timeout) / 60; // Convert minutes to hours
    
    return {
      totalDPU,
      costPerHour: costPerHour.toFixed(2),
      estimatedCost: estimatedCost.toFixed(2), 
      memory: totalDPU * 16, // GB per DPU
      vCPU: totalDPU * 4 // vCPU per DPU
    };
  };

  // Auto-generate script when configuration changes
  useEffect(() => {
    if (selectedBronzeTable && qualityRules.length >= 0) {
      generatePySparkScript();
    }
  }, [qualityRules, normalizations, dedupColumns, outputConfig, glueConfig]);

  const applyTemplate = async (templateName) => {
    try {
      const response = await axios.post(`${API_BASE}/silver/apply-template`, {
        template_name: templateName,
        bronze_table: selectedBronzeTable,
        silver_table: silverTableName
      })
      
      if (response.data.success) {
        setTransformationResult(response.data);
      }
    } catch (err) {
      setError('Template application failed: ' + err.message);
    }
  };

  const executeTransformation = async () => {
    if (!selectedBronzeTable || !silverTableName) {
      setError('Please select Bronze table and specify Silver table name');
      return;
    }

    setIsTransforming(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API_BASE}/silver/transform`, {
        bronze_table: selectedBronzeTable,
        silver_table: silverTableName,
        quality_rules: qualityRules,
        normalization: normalizations.length > 0 ? 
          normalizations.reduce((acc, norm) => {
            acc[norm.column] = norm.type;
            if (norm.params && Object.keys(norm.params).length > 0) {
              acc[`${norm.column}_params`] = norm.params;
            }
            return acc;
          }, {}) : null,
        type_mapping: Object.keys(typeMappings).length > 0 ? typeMappings : null,
        dedup_columns: dedupColumns.length > 0 ? dedupColumns : null
      });
      
      setTransformationResult(response.data);
    } catch (err) {
      setError('Transformation failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsTransforming(false);
    }
  };

  // Rule management
  const addQualityRule = () => {
    if (!currentRule.column || !currentRule.name) {
      alert('Please fill in rule name and column');
      return;
    }
    
    setQualityRules([...qualityRules, { ...currentRule }]);
    setCurrentRule({
      name: '',
      type: 'not_null',
      column: '',
      params: {},
      severity: 'error'
    });
  };

  const removeQualityRule = (index) => {
    setQualityRules(qualityRules.filter((_, i) => i !== index));
  };

  // Normalization management
  const addNormalization = () => {
    if (!currentNormalization.column) {
      alert('Please select a column');
      return;
    }
    
    setNormalizations([...normalizations, { ...currentNormalization }]);
    setCurrentNormalization({
      column: '',
      type: 'lowercase',
      params: {}
    });
  };

  const removeNormalization = (index) => {
    setNormalizations(normalizations.filter((_, i) => i !== index));
  };

  // Deduplication management
  const toggleDedupColumn = (column) => {
    if (dedupColumns.includes(column)) {
      setDedupColumns(dedupColumns.filter(c => c !== column));
    } else {
      setDedupColumns([...dedupColumns, column]);
    }
  };

  // Render helpers
  const renderRuleParams = (ruleType) => {
    const params = RULE_TYPES[ruleType]?.params || [];
    
    return params.map(param => (
      <div key={param} className="flex items-center space-x-2">
        <label className="text-sm text-gray-600 w-20">{param}:</label>
        <input
          type={param === 'pattern' || param === 'values' ? 'text' : 'number'}
          value={currentRule.params[param] || ''}
          onChange={(e) => setCurrentRule({
            ...currentRule,
            params: { ...currentRule.params, [param]: e.target.value }
          })}
          className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
          placeholder={param === 'values' ? 'comma-separated' : param}
        />
      </div>
    ));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Silver Layer Transformation
        </h1>
        <p className="text-gray-600">
          Transform Bronze data to Silver with quality rules, normalization, and data cleaning
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <span className="text-red-600 font-semibold mr-2">❌ Error:</span>
            <span className="text-red-700">{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-600 hover:text-red-800"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Table Selection */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">1. Select Tables</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bronze Table (Source)
            </label>
            <select
              value={selectedBronzeTable}
              onChange={(e) => setSelectedBronzeTable(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              disabled={loading.tables}
            >
              <option value="">Select Bronze table...</option>
              {bronzeTables.map(table => (
                <option key={table} value={table}>{table}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Silver Table (Target)
            </label>
            <input
              type="text"
              value={silverTableName}
              onChange={(e) => setSilverTableName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholder="silver.table_name"
            />
          </div>
        </div>

        {/* Quick Templates */}
        {templates.length > 0 && (
          <div className="mt-4 p-4 bg-blue-50 rounded-md">
            <h3 className="text-sm font-semibold text-blue-800 mb-2">Quick Start Templates</h3>
            <div className="flex flex-wrap gap-2">
              {templates.map(template => (
                <button
                  key={template.name}
                  onClick={() => applyTemplate(template.name)}
                  className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                  disabled={!selectedBronzeTable || !silverTableName}
                >
                  📋 {template.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Schema & Preview */}
      {schema && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">2. Review Schema & Data</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Schema */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Schema ({schema.columns?.length} columns)</h3>
              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Nullable</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {schema.columns?.map((col, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-mono text-xs">{col.name}</td>
                        <td className="px-3 py-2 text-xs text-gray-600">{col.type}</td>
                        <td className="px-3 py-2 text-xs">
                          <span className={`px-2 py-1 rounded ${col.nullable ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                            {col.nullable ? 'Yes' : 'No'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
            {/* Preview */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Data Preview (5 rows)</h3>
              {preview && (
                <div className="max-h-64 overflow-auto border border-gray-200 rounded">
                  <table className="min-w-full divide-y divide-gray-200 text-xs">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        {preview.columns?.map((col, index) => (
                          <th key={index} className="px-2 py-1 text-left text-xs font-medium text-gray-500">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {preview.data?.map((row, rowIndex) => (
                        <tr key={rowIndex} className="hover:bg-gray-50">
                          {preview.columns?.map((col, colIndex) => (
                            <td key={colIndex} className="px-2 py-1 text-xs">
                              {String(row[col] ?? 'null')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Quality Rules */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">3. Configure Quality Rules</h2>
        
        {/* Add Rule Form */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3 mb-4 p-4 bg-gray-50 rounded">
          <input
            type="text"
            placeholder="Rule name"
            value={currentRule.name}
            onChange={(e) => setCurrentRule({ ...currentRule, name: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          />
          
          <select
            value={currentRule.type}
            onChange={(e) => setCurrentRule({ ...currentRule, type: e.target.value, params: {} })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            {Object.entries(RULE_TYPES).map(([key, value]) => (
              <option key={key} value={key}>{value.label}</option>
            ))}
          </select>
          
          <select
            value={currentRule.column}
            onChange={(e) => setCurrentRule({ ...currentRule, column: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Select column...</option>
            {schema?.columns?.map((col) => (
              <option key={col.name} value={col.name}>{col.name}</option>
            ))}
          </select>
          
          <select
            value={currentRule.severity}
            onChange={(e) => setCurrentRule({ ...currentRule, severity: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            {SEVERITY_LEVELS.map(level => (
              <option key={level} value={level}>{level.toUpperCase()}</option>
            ))}
          </select>
          
          <div className="md:col-span-2 flex items-center space-x-2">
            {RULE_TYPES[currentRule.type]?.params?.length > 0 && (
              <div className="flex-1 space-y-2">
                {renderRuleParams(currentRule.type)}
              </div>
            )}
            <button
              onClick={addQualityRule}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 whitespace-nowrap"
            >
              + Add Rule
            </button>
          </div>
        </div>
        
        {/* Rules List */}
        <div className="space-y-2">
          {qualityRules.map((rule, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-blue-50 rounded border border-blue-200">
              <div className="flex-1">
                <span className="font-semibold text-blue-900">{rule.name}</span>
                <span className="mx-2 text-gray-400">•</span>
                <span className="text-sm text-gray-700">
                  {RULE_TYPES[rule.type]?.label} on <code className="px-1 bg-gray-200 rounded">{rule.column}</code>
                </span>
                {Object.keys(rule.params).length > 0 && (
                  <span className="ml-2 text-xs text-gray-600">
                    ({JSON.stringify(rule.params)})
                  </span>
                )}
                <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
                  rule.severity === 'error' ? 'bg-red-100 text-red-800' :
                  rule.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {rule.severity}
                </span>
              </div>
              <button
                onClick={() => removeQualityRule(index)}
                className="ml-4 text-red-600 hover:text-red-800"
              >
                ✕
              </button>
            </div>
          ))}
          
          {qualityRules.length === 0 && (
            <p className="text-sm text-gray-500 italic">No quality rules configured. Add rules above.</p>
          )}
        </div>
      </div>

      {/* Normalization */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">4. Configure Normalization</h2>
        
        {/* Add Normalization Form */}
        <div className="flex gap-3 mb-4 p-4 bg-gray-50 rounded">
          <select
            value={currentNormalization.column}
            onChange={(e) => setCurrentNormalization({ ...currentNormalization, column: e.target.value })}
            className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Select column...</option>
            {schema?.columns?.map((col) => (
              <option key={col.name} value={col.name}>{col.name}</option>
            ))}
          </select>
          
          <select
            value={currentNormalization.type}
            onChange={(e) => setCurrentNormalization({ ...currentNormalization, type: e.target.value })}
            className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm"
          >
            {Object.entries(NORMALIZATION_TYPES).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          
          <button
            onClick={addNormalization}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            + Add
          </button>
        </div>
        
        {/* Normalizations List */}
        <div className="space-y-2">
          {normalizations.map((norm, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-purple-50 rounded border border-purple-200">
              <div>
                <code className="font-mono text-sm bg-gray-200 px-2 py-1 rounded">{norm.column}</code>
                <span className="mx-2">→</span>
                <span className="text-sm text-gray-700">{NORMALIZATION_TYPES[norm.type]}</span>
              </div>
              <button
                onClick={() => removeNormalization(index)}
                className="text-red-600 hover:text-red-800"
              >
                ✕
              </button>
            </div>
          ))}
          
          {normalizations.length === 0 && (
            <p className="text-sm text-gray-500 italic">No normalizations configured. Add normalizations above.</p>
          )}
        </div>
      </div>

      {/* Deduplication */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">5. Configure Deduplication</h2>
        <p className="text-sm text-gray-600 mb-3">Select columns to use as deduplication keys:</p>
        
        <div className="flex flex-wrap gap-2">
          {schema?.columns?.map((col) => (
            <button
              key={col.name}
              onClick={() => toggleDedupColumn(col.name)}
              className={`px-3 py-1 rounded text-sm ${
                dedupColumns.includes(col.name)
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {col.name}
            </button>
          ))}
        </div>
        
        {dedupColumns.length > 0 && (
          <div className="mt-3 p-3 bg-indigo-50 rounded">
            <span className="text-sm text-indigo-800">
              Deduplication keys: <strong>{dedupColumns.join(', ')}</strong>
            </span>
          </div>
        )}
      </div>

      {/* Execute Transformation */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Execute Transformation</h2>
            <p className="text-blue-100">
              {qualityRules.length} rules • {normalizations.length} normalizations • 
              {dedupColumns.length > 0 ? ` ${dedupColumns.length} dedup keys` : ' no dedup'}
            </p>
          </div>
          <button
            onClick={executeTransformation}
            disabled={isTransforming || !selectedBronzeTable || !silverTableName}
            className={`px-8 py-3 rounded-lg font-semibold text-lg ${
              isTransforming || !selectedBronzeTable || !silverTableName
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-white text-blue-600 hover:bg-gray-100'
            }`}
          >
            {isTransforming ? '⏳ Transforming...' : '🚀 Transform Data'}
          </button>
        </div>
      </div>

      {/* Transformation Result */}
      {transformationResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            {transformationResult.success ? '✅ Transformation Complete' : '❌ Transformation Failed'}
          </h2>
          
          {transformationResult.success && transformationResult.report && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded">
                  <div className="text-2xl font-bold text-blue-600">
                    {transformationResult.report.initial_count}
                  </div>
                  <div className="text-sm text-gray-600">Initial Records</div>
                </div>
                <div className="bg-green-50 p-4 rounded">
                  <div className="text-2xl font-bold text-green-600">
                    {transformationResult.report.final_count}
                  </div>
                  <div className="text-sm text-gray-600">Final Records</div>
                </div>
                <div className="bg-purple-50 p-4 rounded">
                  <div className="text-2xl font-bold text-purple-600">
                    {transformationResult.report.duration_seconds?.toFixed(2)}s
                  </div>
                  <div className="text-sm text-gray-600">Duration</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded">
                  <div className="text-2xl font-bold text-yellow-600">
                    {transformationResult.report.quality_report?.rules_applied}
                  </div>
                  <div className="text-sm text-gray-600">Rules Applied</div>
                </div>
              </div>
              
              {/* Quality Report */}
              {transformationResult.report.quality_report && (
                <div>
                  <h3 className="font-semibold text-gray-800 mb-2">Quality Report</h3>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-green-50 p-3 rounded">
                      <div className="text-lg font-bold text-green-600">
                        {transformationResult.report.quality_report.cleaned_records}
                      </div>
                      <div className="text-sm text-gray-600">Cleaned Records</div>
                    </div>
                    <div className="bg-red-50 p-3 rounded">
                      <div className="text-lg font-bold text-red-600">
                        {transformationResult.report.quality_report.rejected_records}
                      </div>
                      <div className="text-sm text-gray-600">Rejected Records</div>
                    </div>
                  </div>
                  
                  {/* Violations */}
                  {Object.keys(transformationResult.report.quality_report.violations || {}).length > 0 && (
                    <div className="bg-yellow-50 p-4 rounded">
                      <h4 className="font-semibold text-yellow-800 mb-2">Rule Violations</h4>
                      <div className="space-y-1">
                        {Object.entries(transformationResult.report.quality_report.violations).map(([rule, count]) => (
                          <div key={rule} className="flex justify-between text-sm">
                            <span className="text-gray-700">{rule}</span>
                            <span className="font-semibold text-yellow-800">{count} violations</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Success Message */}
              <div className="bg-green-50 border border-green-200 rounded p-4">
                <p className="text-green-800">
                  ✅ Silver table <strong>{transformationResult.silver_table}</strong> created successfully!
                </p>
              </div>
            </div>
          )}
          
          {!transformationResult.success && (
            <div className="bg-red-50 border border-red-200 rounded p-4">
              <p className="text-red-800">
                ❌ {transformationResult.message || 'Transformation failed'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
