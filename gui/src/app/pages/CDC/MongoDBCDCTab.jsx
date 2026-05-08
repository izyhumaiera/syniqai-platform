import { useState, useEffect } from 'react';
import { 
  Database, CheckCircle, AlertCircle, PlayCircle, StopCircle,
  Activity, Clock, FileJson, Server, AlertTriangle, TrendingUp,
  Loader
} from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export default function MongoDBCDCTab({ domain, autoRefresh, onRefreshed }) {
  const [cdcStatus, setCdcStatus] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Fetch CDC status
  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cdc/mongodb/status`);
      setCdcStatus(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch MongoDB CDC status:', err);
      setError(err.response?.data?.detail || 'Failed to fetch CDC status');
    }
  };

  // Fetch recent events
  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cdc/events`, {
        params: { source: 'mongodb', limit: 20 }
      });
      setEvents(response.data.events || []);
    } catch (err) {
      console.error('Failed to fetch MongoDB events:', err);
    }
  };

  // Refresh all data
  const refreshAll = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchStatus(), fetchEvents()]);
      if (onRefreshed) onRefreshed();
    } finally {
      setLoading(false);
    }
  };

  // Start CDC
  const handleStart = async () => {
    setActionInProgress(true);
    try {
      const response = await axios.post(`${API_BASE}/cdc/mongodb/start`, {});
      alert(`✓ MongoDB CDC started!\nPID: ${response.data.pid}\n\nEvents will start flowing to Kafka.`);
      await refreshAll();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      alert(`✗ Failed to start MongoDB CDC:\n\n${msg}`);
    } finally {
      setActionInProgress(false);
    }
  };

  // Stop CDC
  const handleStop = async () => {
    if (!confirm('⚠️ Stop MongoDB CDC?\n\nThis will stop capturing change events.')) {
      return;
    }
    
    setActionInProgress(true);
    try {
      const response = await axios.post(`${API_BASE}/cdc/mongodb/stop`);
      alert(`✓ MongoDB CDC stopped\n\n${response.data.message}`);
      await refreshAll();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      alert(`✗ Failed to stop MongoDB CDC:\n\n${msg}`);
    } finally {
      setActionInProgress(false);
    }
  };

  // Initial load
  useEffect(() => {
    refreshAll();
  }, []);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(refreshAll, 10000); // 10 seconds
    return () => clearInterval(interval);
  }, [autoRefresh]);

  // Get status pill color
  const getStatusColor = (isOk) => {
    return isOk ? 'green' : 'red';
  };

  // Get routed-to pill color
  const getRoutePillColor = (topic) => {
    if (topic === 'bronze-ready') return 'green';
    if (topic === 'bronze-media-pending') return 'amber';
    return 'gray';
  };

  const getRoutePillText = (topic) => {
    if (topic === 'bronze-ready') return 'Auto-Process';
    if (topic === 'bronze-media-pending') return 'Media Pending';
    return topic || 'Unknown';
  };

  // Calculate stats
  const eventsToday = cdcStatus?.events_captured || 0;
  const filesInBronze = events.filter(e => e.bronze_minio_key).length;
  const pendingMedia = events.filter(e => e.routed_to === 'bronze-media-pending').length;

  return (
    <div className="space-y-6">
      {/* Status Bar */}
      <div className="grid grid-cols-3 gap-4">
        {/* MongoDB Connection */}
        <div className={`bg-white rounded-lg border-2 ${cdcStatus?.running ? 'border-green-200' : 'border-gray-200'} p-4`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Database className={`w-5 h-5 ${cdcStatus?.running ? 'text-green-600' : 'text-gray-400'} mr-2`} />
              <span className="text-sm font-semibold text-gray-700">MongoDB CDC</span>
            </div>
            <div className={`px-3 py-1 rounded-full text-xs font-bold ${
              cdcStatus?.running 
                ? 'bg-green-100 text-green-700' 
                : 'bg-gray-100 text-gray-600'
            }`}>
              {cdcStatus?.running ? 'RUNNING' : 'STOPPED'}
            </div>
          </div>
          {cdcStatus?.running && (
            <div className="mt-2 text-xs text-gray-600">
              <div>PID: {cdcStatus.pid}</div>
              <div>Uptime: {cdcStatus.uptime}</div>
            </div>
          )}
        </div>

        {/* Kafka Broker */}
        <div className={`bg-white rounded-lg border-2 ${
          cdcStatus?.kafka_connected ? 'border-green-200' : 'border-red-200'
        } p-4`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Server className={`w-5 h-5 ${cdcStatus?.kafka_connected ? 'text-green-600' : 'text-red-600'} mr-2`} />
              <span className="text-sm font-semibold text-gray-700">Kafka Broker</span>
            </div>
            <div className={`px-3 py-1 rounded-full text-xs font-bold ${
              cdcStatus?.kafka_connected 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'
            }`}>
              {cdcStatus?.kafka_connected ? 'CONNECTED' : 'DISCONNECTED'}
            </div>
          </div>
          {cdcStatus?.kafka_error && (
            <div className="mt-2 text-xs text-red-600 font-medium">
              {cdcStatus.kafka_error}
            </div>
          )}
        </div>

        {/* MinIO Bronze */}
        <div className="bg-white rounded-lg border-2 border-blue-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileJson className="w-5 h-5 text-blue-600 mr-2" />
              <span className="text-sm font-semibold text-gray-700">MinIO Bronze</span>
            </div>
            <div className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
              {filesInBronze} FILES
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-600">
            Files written to Bronze layer
          </div>
        </div>
      </div>

      {/* Control Button */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              MongoDB Change Data Capture
            </h3>
            <p className="text-sm text-gray-600">
              Capture real-time changes from MongoDB collections and stream to Bronze layer via Kafka
            </p>
          </div>
          
          <div className="flex gap-3">
            {cdcStatus?.running ? (
              <button
                onClick={handleStop}
                disabled={actionInProgress}
                className="flex items-center px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionInProgress ? (
                  <>
                    <Loader className="w-5 h-5 mr-2 animate-spin" />
                    Stopping...
                  </>
                ) : (
                  <>
                    <StopCircle className="w-5 h-5 mr-2" />
                    Stop CDC
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={handleStart}
                disabled={actionInProgress}
                className="flex items-center px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {actionInProgress ? (
                  <>
                    <Loader className="w-5 h-5 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-5 h-5 mr-2" />
                    Start CDC
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-blue-900">{eventsToday.toLocaleString()}</div>
              <div className="text-sm text-blue-700 font-medium">Events Today</div>
            </div>
            <TrendingUp className="w-8 h-8 text-blue-600 opacity-50" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-green-900">{filesInBronze}</div>
              <div className="text-sm text-green-700 font-medium">Files in Bronze</div>
            </div>
            <FileJson className="w-8 h-8 text-green-600 opacity-50" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-4 border border-amber-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-amber-900">{pendingMedia}</div>
              <div className="text-sm text-amber-700 font-medium">Pending Media</div>
            </div>
            <Clock className="w-8 h-8 text-amber-600 opacity-50" />
          </div>
        </div>
      </div>

      {/* Live Events Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-blue-600" />
              Live Events Stream
              {cdcStatus?.running && (
                <span className="ml-3 px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-semibold animate-pulse">
                  LIVE
                </span>
              )}
            </h3>
            <div className="text-sm text-gray-600">
              Last updated: {cdcStatus?.last_event_at ? new Date(cdcStatus.last_event_at).toLocaleTimeString() : 'Never'}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          {loading && events.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-8 h-8 text-blue-600 animate-spin" />
              <span className="ml-3 text-gray-600">Loading events...</span>
            </div>
          ) : events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <Database className="w-12 h-12 mb-3 opacity-50" />
              <p className="text-lg font-medium">No CDC events yet</p>
              <p className="text-sm">Start CDC to begin capturing change events</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Operation
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Collection
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    File Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Bronze MinIO Path
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Routed To
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {events.map((event, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        event.operation === 'insert' ? 'bg-green-100 text-green-700' :
                        event.operation === 'update' ? 'bg-blue-100 text-blue-700' :
                        event.operation === 'delete' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {event.operation?.toUpperCase() || 'UNKNOWN'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                      {event.collection_or_key || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-semibold">
                        {event.file_type || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 font-mono truncate max-w-xs">
                      {event.bronze_minio_key || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        event.routed_to === 'bronze-ready' 
                          ? 'bg-green-100 text-green-700' 
                          : event.routed_to === 'bronze-media-pending'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {getRoutePillText(event.routed_to)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

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
    </div>
  );
}
