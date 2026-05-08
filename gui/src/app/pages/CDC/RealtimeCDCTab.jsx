import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Activity, CheckCircle, AlertCircle, PlayCircle, StopCircle, 
  RefreshCw, Zap, Server, Layers, AlertTriangle, ArrowRight
} from 'lucide-react';
import axios from 'axios';
import KafkaBacklog from '../../components/KafkaBacklog';

const API_BASE = 'http://localhost:8000/api';

export default function RealtimeCDCTab({ domain, autoRefresh, onRefreshed }) {
  const navigate = useNavigate();
  
  const [cdcStatus, setCdcStatus] = useState(null);
  const [cdcHealth, setCdcHealth] = useState(null);
  const [debeziumConnectors, setDebeziumConnectors] = useState([]);
  const [kafkaConnectHealth, setKafkaConnectHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const fetchCDCStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cdc/consumer/status`);
      setCdcStatus(response.data.consumer);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch CDC status:', err);
      setError('Unable to connect to backend. Is the server running?');
    }
  };
  
  const fetchCDCHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cdc/consumer/health`);
      setCdcHealth(response.data);
    } catch (err) {
      console.error('Failed to fetch CDC health:', err);
    }
  };
  
  const fetchDebeziumConnectors = async () => {
    try {
      const response = await axios.get(`${API_BASE}/debezium/connectors`);
      if (response.data.success) {
        setDebeziumConnectors(response.data.connectors);
      }
    } catch (err) {
      console.error('Failed to fetch Debezium connectors:', err);
      setDebeziumConnectors([]);
    }
  };
  
  const fetchKafkaConnectHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE}/debezium/health`);
      setKafkaConnectHealth(response.data);
    } catch (err) {
      console.error('Failed to fetch Kafka Connect health:', err);
      setKafkaConnectHealth({ status: 'unavailable', error: err.message });
    }
  };
  
  const refreshAll = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchCDCStatus(), 
        fetchCDCHealth(), 
        fetchDebeziumConnectors(),
        fetchKafkaConnectHealth()
      ]);
      if (onRefreshed) onRefreshed();
    } finally {
      setLoading(false);
    }
  };
  
  const handleStartCDC = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/cdc/consumer/start`);
      if (response.data.success) {
        await refreshAll();
      } else {
        alert(`CDC Start Failed: ${response.data.error || 'Unknown error'}\n\nMake sure Kafka is running on localhost:9092`);
      }
    } catch (err) {
      console.error('Failed to start CDC:', err);
      const msg = err.response?.data?.detail || err.message;
      alert(`Failed to start CDC consumer:\n\n${msg}\n\nChecklist:\n✓ Kafka running on localhost:9092\n✓ Backend is running\n✓ CDC consumer script exists`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleStopCDC = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/cdc/consumer/stop`);
      await refreshAll();
    } catch (err) {
      console.error('Failed to stop CDC:', err);
      alert(`Failed to stop CDC consumer: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRestartConnector = async (connectorName) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/debezium/connector/${connectorName}/restart`);
      if (response.data.success) {
        await fetchDebeziumConnectors();
      }
    } catch (err) {
      console.error(`Failed to restart connector ${connectorName}:`, err);
      alert(`Failed to restart connector: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handlePauseConnector = async (connectorName) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/debezium/connector/${connectorName}/pause`);
      if (response.data.success) {
        await fetchDebeziumConnectors();
      }
    } catch (err) {
      console.error(`Failed to pause connector ${connectorName}:`, err);
      alert(`Failed to pause connector: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleResumeConnector = async (connectorName) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/debezium/connector/${connectorName}/resume`);
      if (response.data.success) {
        await fetchDebeziumConnectors();
      }
    } catch (err) {
      console.error(`Failed to resume connector ${connectorName}:`, err);
      alert(`Failed to resume connector: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleDeleteConnector = async (connectorName) => {
    if (!confirm(`Are you sure you want to delete connector '${connectorName}'? This action cannot be undone.`)) {
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.delete(`${API_BASE}/debezium/connector/${connectorName}`);
      if (response.data.success) {
        await fetchDebeziumConnectors();
      }
    } catch (err) {
      console.error(`Failed to delete connector ${connectorName}:`, err);
      alert(`Failed to delete connector: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    refreshAll();
  }, []);
  
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(refreshAll, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);
  
  const getStatusBadge = (running) => {
    return running ? (
      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold flex items-center">
        <CheckCircle className="w-4 h-4 mr-1" />
        Running
      </span>
    ) : (
      <span className="px-3 py-1 bg-gray-200 text-gray-700 rounded-full text-sm font-semibold flex items-center">
        <AlertCircle className="w-4 h-4 mr-1" />
        Stopped
      </span>
    );
  };
  
  const getConnectorStateBadge = (state) => {
    const stateColors = {
      'RUNNING': 'bg-green-100 text-green-700',
      'PAUSED': 'bg-yellow-100 text-yellow-700',
      'FAILED': 'bg-red-100 text-red-700',
      'UNASSIGNED': 'bg-gray-100 text-gray-700',
      'UNKNOWN': 'bg-gray-100 text-gray-600'
    };
    
    const colorClass = stateColors[state] || 'bg-gray-100 text-gray-600';
    
    return (
      <span className={`px-2 py-1 ${colorClass} rounded-full text-xs font-semibold`}>
        {state || 'UNKNOWN'}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-red-800 font-semibold">Error</p>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Intro Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-2 flex items-center">
          <Zap className="w-6 h-6 text-blue-600 mr-2" />
          Real-time Change Data Capture
        </h2>
        <p className="text-gray-700 mb-3">
          Stream database changes in real-time using Debezium CDC. Supports PostgreSQL, MariaDB, and MySQL databases.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <p className="font-semibold text-blue-900"> PostgreSQL</p>
            <p className="text-gray-600">Transactional data, OLTP workloads</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <p className="font-semibold text-orange-900"> MariaDB / MySQL</p>
            <p className="text-gray-600">Web applications, E-commerce</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <p className="font-semibold text-green-900"> Real-time</p>
            <p className="text-gray-600">Sub-second latency streaming</p>
          </div>
        </div>
      </div>

      {/* CDC Consumer Status */}
      <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border-2 border-yellow-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className={`p-4 rounded-xl ${cdcStatus?.running ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}>
              <Zap className="w-8 h-8 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 flex items-center gap-3">
                CDC Consumer
                {getStatusBadge(cdcStatus?.running)}
              </h3>
              <div className="space-y-1 text-sm text-gray-700">
                {cdcStatus?.running ? (
                  <>
                    <p><strong>PID:</strong> {cdcStatus.pid}</p>
                    <p><strong>Uptime:</strong> {Math.floor((cdcStatus.uptime_seconds || 0) / 60)} minutes</p>
                    <p><strong>Memory:</strong> {cdcStatus.memory_mb?.toFixed(1)} MB</p>
                    <p><strong>CPU:</strong> {cdcStatus.cpu_percent?.toFixed(1)}%</p>
                    <p className="text-gray-500 text-xs mt-2">{cdcStatus.command}</p>
                  </>
                ) : (
                  <p className="text-gray-600">CDC consumer is not running. Start it to begin streaming data changes.</p>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            {cdcStatus?.running ? (
              <button 
                onClick={handleStopCDC}
                disabled={loading}
                className="px-5 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 font-medium flex items-center gap-2"
              >
                <StopCircle className="w-4 h-4" />
                Stop CDC
              </button>
            ) : (
              <button 
                onClick={handleStartCDC}
                disabled={loading}
                className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium flex items-center gap-2 animate-pulse"
              >
                <PlayCircle className="w-4 h-4" />
                Start CDC
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Debezium Connectors Status */}
      <div className="bg-white rounded-xl border-2 border-purple-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Server className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Debezium Connectors</h3>
              <p className="text-sm text-gray-600">Kafka Connect @ localhost:8083</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {kafkaConnectHealth && (
              <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                kafkaConnectHealth.status === 'healthy' 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-red-100 text-red-700'
              }`}>
                Kafka Connect: {kafkaConnectHealth.status === 'healthy' ? 'UP' : 'DOWN'}
              </div>
            )}
            <button
              onClick={() => fetchDebeziumConnectors()}
              disabled={loading}
              className="px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 text-sm font-medium flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Connectors List */}
        {debeziumConnectors.length > 0 ? (
          <div className="space-y-3">
            {debeziumConnectors.map((connector) => (
              <div 
                key={connector.name}
                className="bg-gray-50 rounded-lg border-2 border-gray-200 p-4 hover:border-purple-300 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-semibold text-gray-900">{connector.name}</h4>
                      {getConnectorStateBadge(connector.state)}
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                        {connector.type}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Database:</span> {connector.database}
                      </div>
                      <div>
                        <span className="font-medium">Topic Prefix:</span> {connector.topic_prefix}
                      </div>
                      <div>
                        <span className="font-medium">Tasks:</span> {connector.tasks?.length || 0}
                      </div>
                      <div>
                        <span className="font-medium">Worker:</span> {connector.worker_id || 'N/A'}
                      </div>
                    </div>
                    
                    {/* Task Status */}
                    {connector.tasks && connector.tasks.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300">
                        <p className="text-xs font-semibold text-gray-700 mb-2">Tasks:</p>
                        <div className="flex gap-2 flex-wrap">
                          {connector.tasks.map((task, idx) => (
                            <div 
                              key={idx}
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                task.state === 'RUNNING' 
                                  ? 'bg-green-100 text-green-700' 
                                  : task.state === 'FAILED'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}
                            >
                              Task {task.id}: {task.state}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Action Buttons */}
                  <div className="flex gap-2 ml-4">
                    {connector.state === 'RUNNING' && (
                      <button
                        onClick={() => handlePauseConnector(connector.name)}
                        disabled={loading}
                        className="px-3 py-1.5 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:bg-gray-400 text-sm font-medium"
                        title="Pause Connector"
                      >
                        Pause
                      </button>
                    )}
                    {connector.state === 'PAUSED' && (
                      <button
                        onClick={() => handleResumeConnector(connector.name)}
                        disabled={loading}
                        className="px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400 text-sm font-medium"
                        title="Resume Connector"
                      >
                        Resume
                      </button>
                    )}
                    <button
                      onClick={() => handleRestartConnector(connector.name)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 text-sm font-medium"
                      title="Restart Connector"
                    >
                      Restart
                    </button>
                    <button
                      onClick={() => handleDeleteConnector(connector.name)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400 text-sm font-medium"
                      title="Delete Connector"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-yellow-50 border-2 border-yellow-200 rounded-lg p-4">
            <div className="flex items-start">
              <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-yellow-900 font-semibold mb-1">No Debezium Connectors Found</p>
                <p className="text-yellow-800 text-sm">
                  {kafkaConnectHealth?.status === 'healthy' 
                    ? 'Kafka Connect is running, but no connectors are configured. Run setup_cdc_connectors.py to create connectors.' 
                    : 'Kafka Connect is not available. Make sure it is running on localhost:8083.'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* System Health Grid */}
      {cdcHealth && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health Checks</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            {cdcHealth.checks?.kafka && (
              <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Server className="w-6 h-6 text-purple-600" />
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                    cdcHealth.checks.kafka.status === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {cdcHealth.checks.kafka.status.toUpperCase()}
                  </div>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">Kafka Broker</h4>
                <p className="text-sm text-gray-600">{cdcHealth.checks.kafka.message}</p>
              </div>
            )}
            
            {cdcHealth.checks?.minio && (
              <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Layers className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                    cdcHealth.checks.minio.status === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {cdcHealth.checks.minio.status.toUpperCase()}
                  </div>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">MinIO Storage</h4>
                <p className="text-sm text-gray-600">{cdcHealth.checks.minio.message}</p>
              </div>
            )}
            
            {cdcHealth.checks?.cdc_consumer && (
              <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Activity className="w-6 h-6 text-green-600" />
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                    cdcHealth.checks.cdc_consumer.status === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {cdcHealth.checks.cdc_consumer.status.toUpperCase()}
                  </div>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">CDC Consumer</h4>
                <p className="text-sm text-gray-600">{cdcHealth.checks.cdc_consumer.message}</p>
                {cdcHealth.checks.cdc_consumer.uptime_seconds && (
                  <p className="text-xs text-gray-500 mt-2">
                    Uptime: {Math.floor(cdcHealth.checks.cdc_consumer.uptime_seconds / 60)} minutes
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Kafka Backlog */}
      <KafkaBacklog />

      {/* Setup Guide */}
      {(!cdcStatus || !cdcStatus.running) && (
        <div className="bg-yellow-50 border-2 border-yellow-300 rounded-xl p-6">
          <div className="flex items-start">
            <AlertTriangle className="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 mb-2">CDC Consumer Not Running</h3>
              <p className="text-yellow-800 text-sm mb-4">
                The CDC consumer needs to be started to stream real-time data changes from Kafka to Bronze layer.
              </p>
              <div className="space-y-2 text-sm text-yellow-900 bg-yellow-100 rounded-lg p-4">
                <p className="font-semibold">Quick Start Guide:</p>
                <ol className="list-decimal list-inside space-y-1 ml-2">
                  <li>Ensure Kafka is running on localhost:9092</li>
                  <li>Click the "Start CDC" button above</li>
                  <li>CDC consumer will begin streaming Kafka topics → Bronze layer (MinIO)</li>
                  <li>Monitor progress in real-time on this page</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Bar */}
      <div className="flex justify-between items-center bg-gray-100 border-2 border-gray-200 rounded-xl p-5">
        <div className="text-sm text-gray-700">
          <p className="font-medium">Need help with CDC setup?</p>
          <p className="text-gray-500">Check the CDC documentation for detailed instructions</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/${domain}/bronze`)}
            className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors font-medium"
          >
            View Bronze Layer
          </button>
          <button
            onClick={() => navigate(`/${domain}/silver`)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
          >
            Silver Processing
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
