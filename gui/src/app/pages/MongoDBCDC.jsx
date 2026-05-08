import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Database, Activity, CheckCircle, AlertCircle, Loader2, 
  PlayCircle, StopCircle, RefreshCw, Zap, Clock, BarChart3,
  Settings, Calendar, TrendingUp, AlertTriangle, Eye, FileJson,
  ArrowRight, Wind, Layers, Package
} from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';
const AIRFLOW_BASE = 'http://localhost:8000/api/airflow';

export default function MongoDBCDC() {
  const { domain } = useParams();
  const navigate = useNavigate();
  
  // State
  const [dagStatus, setDagStatus] = useState(null);
  const [dagRuns, setDagRuns] = useState([]);
  const [watermarks, setWatermarks] = useState({});
  const [mongoHealth, setMongoHealth] = useState(null);
  const [kafkaHealth, setKafkaHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [mongoConfig, setMongoConfig] = useState({
    uri: 'mongodb+srv://connector_user:ConnectorPass123@test.pw8zb01.mongodb.net/?appName=Test',
    database: 'media_db',
    collections: 'images_metadata'
  });
  
  // Fetch DAG status from Airflow
  const fetchDAGStatus = async () => {
    try {
      const response = await axios.get(
        `${AIRFLOW_BASE}/dags/mongodb_cdc_extraction`
      );
      setDagStatus(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch DAG status:', err);
      setError('Unable to connect to Airflow. Is it running on port 8082?');
    }
  };
  
  // Fetch DAG runs
  const fetchDAGRuns = async () => {
    try {
      const response = await axios.get(
        `${AIRFLOW_BASE}/dags/mongodb_cdc_extraction/dagRuns?limit=10`
      );
      setDagRuns(response.data.dag_runs || []);
    } catch (err) {
      console.error('Failed to fetch DAG runs:', err);
    }
  };
  
  // Fetch watermarks from backend
  const fetchWatermarks = async () => {
    try {
      const response = await axios.get(`${API_BASE}/mongodb/cdc/watermarks`);
      setWatermarks(response.data.watermarks || {});
    } catch (err) {
      console.error('Failed to fetch watermarks:', err);
    }
  };
  
  // Check MongoDB health
  const checkMongoHealth = async () => {
    try {
      const response = await axios.post(`${API_BASE}/mongodb/health`, {
        uri: mongoConfig.uri,
        database: mongoConfig.database
      });
      setMongoHealth(response.data);
    } catch (err) {
      console.error('Failed to check MongoDB health:', err);
      setMongoHealth({ status: 'error', message: err.message });
    }
  };
  
  // Check Kafka health
  const checkKafkaHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cdc/consumer/health`);
      setKafkaHealth(response.data.checks?.kafka);
    } catch (err) {
      console.error('Failed to check Kafka health:', err);
    }
  };
  
  // Refresh all data
  const refreshAll = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchDAGStatus(),
        fetchDAGRuns(),
        fetchWatermarks(),
        checkMongoHealth(),
        checkKafkaHealth()
      ]);
      setLastRefreshed(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };
  
  // Trigger DAG run
  const handleTriggerDAG = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${AIRFLOW_BASE}/dags/mongodb_cdc_extraction/dagRuns`,
        {
          conf: {
            mongodb_uri: mongoConfig.uri,
            mongodb_database: mongoConfig.database,
            collections: mongoConfig.collections.split(',').map(c => c.trim())
          }
        }
      );
      
      alert(`✅ DAG triggered successfully!\nRun ID: ${response.data.dag_run_id}\n\nCheck the Airflow UI for progress.`);
      await refreshAll();
    } catch (err) {
      console.error('Failed to trigger DAG:', err);
      const msg = err.response?.data?.detail || err.message;
      alert(`❌ Failed to trigger DAG:\n\n${msg}\n\nMake sure Airflow is running on localhost:8082`);
    } finally {
      setLoading(false);
    }
  };
  
  // Pause/Unpause DAG
  const handleToggleDAG = async () => {
    setLoading(true);
    try {
      await axios.patch(
        `${AIRFLOW_BASE}/dags/mongodb_cdc_extraction`,
        {
          is_paused: !dagStatus?.is_paused
        }
      );
      await refreshAll();
    } catch (err) {
      console.error('Failed to toggle DAG:', err);
      alert(`Failed to ${dagStatus?.is_paused ? 'unpause' : 'pause'} DAG: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Reset watermarks
  const handleResetWatermarks = async () => {
    if (!confirm('⚠️ Reset all watermarks? This will re-extract all MongoDB data from the beginning.')) {
      return;
    }
    
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/mongodb/cdc/watermarks/reset`);
      alert('✅ Watermarks reset successfully!');
      await refreshAll();
    } catch (err) {
      console.error('Failed to reset watermarks:', err);
      alert(`Failed to reset watermarks: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Update MongoDB config
  const handleUpdateConfig = async () => {
    try {
      await axios.post(`${API_BASE}/mongodb/cdc/config`, mongoConfig);
      alert('✅ MongoDB configuration updated!');
      await refreshAll();
    } catch (err) {
      alert(`Failed to update config: ${err.message}`);
    }
  };
  
  // Initial fetch
  useEffect(() => {
    refreshAll();
  }, []);
  
  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      refreshAll();
    }, 10000); // Refresh every 10 seconds
    
    return () => clearInterval(interval);
  }, [autoRefresh]);
  
  // Get status badge
  const getStatusBadge = (state) => {
    const badges = {
      'success': { color: 'green', icon: CheckCircle, text: 'Success' },
      'running': { color: 'blue', icon: Activity, text: 'Running' },
      'failed': { color: 'red', icon: AlertCircle, text: 'Failed' },
      'queued': { color: 'yellow', icon: Clock, text: 'Queued' }
    };
    
    const badge = badges[state] || { color: 'gray', icon: AlertCircle, text: state };
    const Icon = badge.icon;
    
    return (
      <span className={`px-3 py-1 bg-${badge.color}-100 text-${badge.color}-700 rounded-full text-xs font-semibold flex items-center`}>
        <Icon className="w-3 h-3 mr-1" />
        {badge.text}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-8 py-6 shadow-lg">
        <div className="flex items-center justify-between max-w-[1400px] mx-auto">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <FileJson className="w-8 h-8 mr-3" />
              MongoDB CDC Orchestration
              <span className="ml-4 px-3 py-1 bg-white/20 rounded-full text-sm font-medium">
                Powered by Apache Airflow
              </span>
            </h1>
            <p className="text-green-100 mt-2">
              Automated batch extraction from MongoDB collections to Kafka streams
              {lastRefreshed && ` · Last refreshed: ${lastRefreshed}`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${
                autoRefresh
                  ? 'border-white bg-white/20 text-white'
                  : 'border-white/50 bg-transparent text-white'
              }`}
            >
              <RefreshCw className={`w-4 h-4 inline mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
              Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
            </button>
            <button
              onClick={refreshAll}
              disabled={loading}
              className="px-4 py-2 bg-white text-green-700 rounded-lg hover:bg-green-50 transition-colors text-sm font-semibold disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4 inline mr-2" />
              Refresh Now
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-8 py-6 space-y-6">

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 flex items-start">
            <AlertCircle className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-red-800 font-semibold">Connection Error</p>
              <p className="text-red-700 text-sm mt-1">{error}</p>
              <p className="text-red-600 text-xs mt-2">
                💡 Make sure Airflow webserver is running on <strong>http://localhost:8082</strong>
              </p>
            </div>
          </div>
        )}

        {/* DAG Status Card */}
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border-2 border-green-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className={`p-4 rounded-xl ${dagStatus?.is_paused === false ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}>
                <Wind className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-2 flex items-center gap-3">
                  MongoDB CDC DAG
                  {dagStatus?.is_paused === false ? (
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold flex items-center">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Active
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-gray-200 text-gray-700 rounded-full text-sm font-semibold flex items-center">
                      <StopCircle className="w-4 h-4 mr-1" />
                      Paused
                    </span>
                  )}
                </h2>
                <div className="space-y-1 text-sm text-gray-700">
                  {dagStatus ? (
                    <>
                      <p><strong>Schedule:</strong> {dagStatus.schedule_interval || 'Manual'} (Every 30 minutes)</p>
                      <p><strong>Next Run:</strong> {dagStatus.next_dagrun ? new Date(dagStatus.next_dagrun).toLocaleString() : 'N/A'}</p>
                      <p><strong>Last Run:</strong> {dagStatus.last_run_state || 'Never'}</p>
                      <p className="text-gray-500 text-xs mt-2">
                        Tags: {dagStatus.tags?.map(t => t.name).join(', ') || 'mongodb, cdc, production'}
                      </p>
                    </>
                  ) : (
                    <p className="text-gray-600">Loading DAG information from Airflow...</p>
                  )}
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <button 
                onClick={handleTriggerDAG}
                disabled={loading || !dagStatus}
                className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium flex items-center gap-2"
              >
                <PlayCircle className="w-4 h-4" />
                Trigger DAG Now
              </button>
              <button 
                onClick={handleToggleDAG}
                disabled={loading || !dagStatus}
                className="px-5 py-2.5 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400 font-medium flex items-center gap-2"
              >
                {dagStatus?.is_paused ? <PlayCircle className="w-4 h-4" /> : <StopCircle className="w-4 h-4" />}
                {dagStatus?.is_paused ? 'Unpause' : 'Pause'} DAG
              </button>
              <a
                href="http://localhost:8082/dags/mongodb_cdc_extraction/grid"
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2 text-center"
              >
                <Eye className="w-4 h-4" />
                Open in Airflow
              </a>
            </div>
          </div>
        </div>

        {/* Health Checks Grid */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* MongoDB Health */}
            <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Database className="w-6 h-6 text-green-600" />
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                  mongoHealth?.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {mongoHealth?.status === 'success' ? 'CONNECTED' : 'DISCONNECTED'}
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1">MongoDB Source</h4>
              <p className="text-sm text-gray-600">{mongoHealth?.message || 'Checking connection...'}</p>
              {mongoHealth?.collections_count && (
                <p className="text-xs text-gray-500 mt-2">
                  Collections: {mongoHealth.collections_count}
                </p>
              )}
            </div>
            
            {/* Kafka Health */}
            <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Layers className="w-6 h-6 text-purple-600" />
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-bold ${
                  kafkaHealth?.status === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {kafkaHealth?.status?.toUpperCase() || 'UNKNOWN'}
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 mb-1">Kafka Broker</h4>
              <p className="text-sm text-gray-600">{kafkaHealth?.message || 'Checking connection...'}</p>
            </div>
          </div>
        </div>

        {/* MongoDB Configuration */}
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Settings className="w-5 h-5 mr-2 text-gray-600" />
            MongoDB Configuration
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MongoDB URI
              </label>
              <input
                type="text"
                value={mongoConfig.uri}
                onChange={(e) => setMongoConfig({...mongoConfig, uri: e.target.value})}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:outline-none"
                placeholder="mongodb://localhost:27017"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Database Name
              </label>
              <input
                type="text"
                value={mongoConfig.database}
                onChange={(e) => setMongoConfig({...mongoConfig, database: e.target.value})}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:outline-none"
                placeholder="syniqai_source"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Collections (comma-separated)
              </label>
              <input
                type="text"
                value={mongoConfig.collections}
                onChange={(e) => setMongoConfig({...mongoConfig, collections: e.target.value})}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-green-500 focus:outline-none"
                placeholder="users,transactions,events"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-4">
            <button
              onClick={handleUpdateConfig}
              className="px-5 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
            >
              Update Configuration
            </button>
          </div>
        </div>

        {/* Watermarks Status */}
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Clock className="w-5 h-5 mr-2 text-gray-600" />
              Incremental Load Watermarks
            </h3>
            <button
              onClick={handleResetWatermarks}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm"
            >
              Reset All Watermarks
            </button>
          </div>
          {Object.keys(watermarks).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(watermarks).map(([collection, watermark]) => (
                <div key={collection} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="font-semibold text-gray-900 mb-1">{collection}</p>
                  <p className="text-sm text-gray-600">
                    {watermark ? new Date(watermark).toLocaleString() : 'No watermark'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No watermarks found. Run the DAG to create watermarks.</p>
          )}
        </div>

        {/* Recent DAG Runs */}
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-gray-600" />
            Recent DAG Runs
          </h3>
          {dagRuns.length > 0 ? (
            <div className="space-y-3">
              {dagRuns.slice(0, 5).map((run) => (
                <div key={run.dag_run_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-4">
                    {getStatusBadge(run.state)}
                    <div>
                      <p className="font-medium text-gray-900">{run.dag_run_id}</p>
                      <p className="text-xs text-gray-500">
                        Started: {new Date(run.start_date).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">
                      Duration: {run.duration ? `${Math.floor(run.duration)}s` : 'In progress...'}
                    </p>
                    <a
                      href={`http://localhost:8082/dags/mongodb_cdc_extraction/grid?dag_run_id=${run.dag_run_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      View Details →
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No DAG runs yet. Trigger the DAG to start extraction.</p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex justify-between items-center bg-gradient-to-r from-green-100 to-emerald-100 border-2 border-green-300 rounded-xl p-5">
          <div className="text-sm text-gray-800">
            <p className="font-semibold text-lg mb-1">🚀 Quick Start Guide</p>
            <ol className="list-decimal list-inside space-y-1 text-gray-700">
              <li>Configure MongoDB connection above</li>
              <li>Click "Trigger DAG Now" to start extraction</li>
              <li>Monitor progress in the DAG runs section</li>
              <li>Data flows: MongoDB → Kafka → Bronze → Silver → Gold</li>
            </ol>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/${domain}/cdc`)}
              className="px-4 py-2 border-2 border-gray-300 bg-white text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              Real-time CDC
            </button>
            <button
              onClick={() => navigate(`/${domain}/bronze`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
            >
              View Bronze Layer
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
