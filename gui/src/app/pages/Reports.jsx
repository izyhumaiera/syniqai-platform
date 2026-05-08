import { useState } from 'react'
import { FileText, Download } from 'lucide-react'
import Alert from '../components/ui/Alert'

export default function Reports() {
  const [reportType, setReportType] = useState('executive')
  const [format, setFormat] = useState('json')
  const [generated, setGenerated] = useState(false)

  const reportTypes = [
    {
      id: 'executive',
      name: 'Executive Summary',
      description: 'High-level overview of data quality and system health',
      icon: '📋',
      items: ['Quality scores', 'Table summaries', 'Key insights'],
    },
    {
      id: 'eda',
      name: 'EDA Report',
      description: 'Detailed exploratory data analysis for specific tables',
      icon: '📊',
      items: ['Statistical analysis', 'Distributions', 'Correlations'],
    },
    {
      id: 'quality',
      name: 'Quality Report',
      description: 'Data quality assessment across all tables',
      icon: '🔍',
      items: ['Quality metrics', 'Issues & alerts', 'Recommendations'],
    },
  ]

  const availableReports = [
    { name: 'executive_summary_20260223.json', type: 'JSON', size: '45.2 KB', date: '2026-02-23 14:30' },
    { name: 'eda_postgres_customers_20260223.html', type: 'HTML', size: '128.5 KB', date: '2026-02-23 14:25' },
    { name: 'quality_report_20260223.csv', type: 'CSV', size: '12.8 KB', date: '2026-02-23 14:20' },
  ]

  const handleGenerate = () => {
    setGenerated(true)
    setTimeout(() => setGenerated(false), 3000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600 mt-1">Generate and download comprehensive data reports</p>
      </div>

      {/* Report Types */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Report Types</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {reportTypes.map((type) => (
            <div
              key={type.id}
              className={`bg-white rounded-xl shadow-sm border-2 p-6 cursor-pointer transition-all ${
                reportType === type.id ? 'border-primary-500' : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setReportType(type.id)}
            >
              <h4 className="text-lg font-semibold text-gray-900 mb-2">{type.name}</h4>
              <p className="text-sm text-gray-600 mb-3">{type.description}</p>
              <ul className="space-y-1 text-sm text-gray-600">
                {type.items.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Generate Report */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Generate Report</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Report Type</label>
            <select 
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            >
              <option value="executive">Executive Summary</option>
              <option value="eda">EDA Report</option>
              <option value="quality">Quality Report</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
            <select 
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              value={format}
              onChange={(e) => setFormat(e.target.value)}
            >
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="html">HTML</option>
              <option value="markdown">Markdown</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="btn-primary" onClick={handleGenerate}>
            Generate Report
          </button>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" className="rounded" />
            Include Visualizations
          </label>
        </div>

        {generated && (
          <div className="mt-4">
            <Alert type="success">
              [SUCCESS] Executive summary generated successfully!
            </Alert>
            <button className="btn-secondary mt-2">
              <Download size={16} className="inline mr-2" />
              Download Report
            </button>
          </div>
        )}
      </div>

      {/* Available Reports */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Reports</h3>
        <div className="space-y-3">
          {availableReports.map((report, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
              <div className="flex items-center gap-3">
                <FileText size={20} className="text-gray-400" />
                <div>
                  <p className="font-medium text-gray-900">{report.name}</p>
                  <p className="text-sm text-gray-500">{report.type} • {report.size} • {report.date}</p>
                </div>
              </div>
              <button className="btn-secondary text-sm py-1.5 px-3">
                <Download size={14} className="inline mr-1" />
                Download
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
