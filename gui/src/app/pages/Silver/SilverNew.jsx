import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  Database, 
  Table, 
  GitBranch, 
  Code, 
  Shield, 
  Activity, 
  Zap,
  Search,
  Bell,
  Settings,
  User,
  ChevronDown,
  Star,
  Clock,
  HelpCircle
} from 'lucide-react';

// Import all page components
import Dashboard from './Dashboard';
import DataCatalog from './DataCatalog';
import DatasetViewer from './DatasetViewer';
import PipelineBuilder from './PipelineBuilder';
import SQLEditorEnhanced from './SQLEditorEnhanced';
import DataQualityRules from './DataQualityRules';
import JobMonitoring from './JobMonitoring';
import DataLineage from './DataLineage';

/**
 * Silver - Complete Data Transformation System UI
 * Enterprise-grade UI with navigation, workspace management, and 8 core pages
 */
export default function Silver() {
  const [activePage, setActivePage] = useState('dashboard');
  const [environment, setEnvironment] = useState('dev'); // dev, staging, production
  const [showEnvDropdown, setShowEnvDropdown] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState(null);

  // Navigation items
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'catalog', label: 'Data Catalog', icon: Database },
    { id: 'pipeline', label: 'Pipeline Builder', icon: Zap },
    { id: 'sql', label: 'SQL Editor', icon: Code },
    { id: 'quality', label: 'Data Quality', icon: Shield },
    { id: 'jobs', label: 'Job Monitoring', icon: Activity },
    { id: 'lineage', label: 'Data Lineage', icon: GitBranch }
  ];

  const environments = [
    { id: 'dev', name: 'Development', color: '#3b82f6' },
    { id: 'staging', name: 'Staging', color: '#f59e0b' },
    { id: 'production', name: 'Production', color: '#ef4444' }
  ];

  const recentItems = [
    { name: 'finance_transactions', type: 'table', page: 'catalog' },
    { name: 'Finance ETL Pipeline', type: 'pipeline', page: 'pipeline' },
    { name: 'Customer Cleanup', type: 'query', page: 'sql' }
  ];

  const favorites = [
    { name: 'Revenue Dashboard', type: 'dashboard', page: 'dashboard' },
    { name: 'sales_orders', type: 'table', page: 'catalog' }
  ];

  const currentEnv = environments.find(e => e.id === environment);

  const handleDatasetSelect = (dataset) => {
    setSelectedDataset(dataset);
    setActivePage('viewer');
  };

  const renderPage = () => {
    switch(activePage) {
      case 'dashboard':
        return <Dashboard />;
      case 'catalog':
        return <DataCatalog onDatasetSelect={handleDatasetSelect} />;
      case 'viewer':
        return <DatasetViewer dataset={selectedDataset} />;
      case 'pipeline':
        return <PipelineBuilder />;
      case 'sql':
        return <SQLEditorEnhanced />;
      case 'quality':
        return <DataQualityRules />;
      case 'jobs':
        return <JobMonitoring />;
      case 'lineage':
        return <DataLineage />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Left Sidebar Navigation */}
      <div className="w-64 bg-gradient-to-b from-gray-900 to-gray-800 text-white flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold">SyniqAI</h1>
              <p className="text-xs text-gray-400">Data Transformation</p>
            </div>
          </div>
        </div>

        {/* Environment Selector */}
        <div className="px-4 py-3 border-b border-gray-700">
          <div className="relative">
            <button
              onClick={() => setShowEnvDropdown(!showEnvDropdown)}
              className="w-full flex items-center justify-between px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: currentEnv.color }}
                />
                <span className="text-sm font-medium">{currentEnv.name}</span>
              </div>
              <ChevronDown className="w-4 h-4" />
            </button>

            {showEnvDropdown && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 rounded-lg shadow-xl border border-gray-700 z-50">
                {environments.map(env => (
                  <button
                    key={env.id}
                    onClick={() => {
                      setEnvironment(env.id);
                      setShowEnvDropdown(false);
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-700 first:rounded-t-lg last:rounded-b-lg transition-colors ${
                      environment === env.id ? 'bg-gray-700' : ''
                    }`}
                  >
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: env.color }}
                    />
                    {env.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <div className="space-y-1">
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Recent Items */}
          <div className="mt-8">
            <div className="px-3 mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-500" />
              <span className="text-xs font-semibold text-gray-400 uppercase">Recent</span>
            </div>
            <div className="space-y-1">
              {recentItems.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setActivePage(item.page)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-300 rounded-lg transition-colors"
                >
                  <span className="truncate">{item.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Favorites */}
          <div className="mt-6">
            <div className="px-3 mb-2 flex items-center gap-2">
              <Star className="w-4 h-4 text-gray-500" />
              <span className="text-xs font-semibold text-gray-400 uppercase">Favorites</span>
            </div>
            <div className="space-y-1">
              {favorites.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setActivePage(item.page)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-300 rounded-lg transition-colors"
                >
                  <span className="truncate">{item.name}</span>
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* User Profile */}
        <div className="p-4 border-t border-gray-700">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <User className="w-5 h-5" />
            </div>
            <div className="flex-1 text-left">
              <div className="text-sm font-medium">Data Engineer</div>
              <div className="text-xs text-gray-400">View Profile</div>
            </div>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          {/* Left: Breadcrumb or Title */}
          <div className="flex items-center gap-3">
            <span className="text-gray-400">/</span>
            <span className="text-sm font-medium text-gray-600">
              {environment.toUpperCase()}
            </span>
            <span className="text-gray-400">/</span>
            <span className="text-sm font-medium text-gray-900">
              {navItems.find(item => item.id === activePage)?.label || 'Dashboard'}
            </span>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            {/* Global Search */}
            <button
              onClick={() => setShowSearch(!showSearch)}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Search className="w-5 h-5" />
            </button>

            {/* Notifications */}
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>

            {/* Help */}
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <HelpCircle className="w-5 h-5" />
            </button>

            {/* Settings */}
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Global Search Overlay */}
        {showSearch && (
          <div className="absolute inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center pt-20">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl">
              <div className="p-4">
                <input
                  type="text"
                  placeholder="Search tables, pipelines, jobs, queries..."
                  autoFocus
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') setShowSearch(false);
                  }}
                />
              </div>
              <div className="border-t border-gray-200 p-4">
                <p className="text-sm text-gray-500">Start typing to search...</p>
              </div>
            </div>
          </div>
        )}

        {/* Page Content */}
        <div className="flex-1 overflow-hidden">
          {renderPage()}
        </div>
      </div>
    </div>
  );
}
