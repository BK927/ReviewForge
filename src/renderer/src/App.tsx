import { useState } from 'react'
import { Layout } from './components/Layout'
import { Dashboard } from './components/Dashboard'
import { TopicAnalysis, AnalysisResult } from './components/TopicAnalysis'
import { SegmentAnalysis } from './components/SegmentAnalysis'
import { ExportPanel } from './components/ExportPanel'

export default function App() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)

  return (
    <Layout>
      {(appId, activeTab) => {
        if (!appId) {
          return <div className="empty-state">Add a game from the sidebar to get started</div>
        }
        return (
          <>
            <div style={{ display: activeTab === 'dashboard' ? 'block' : 'none' }}>
              <Dashboard appId={appId} />
            </div>
            <div style={{ display: activeTab === 'topics' ? 'block' : 'none' }}>
              <TopicAnalysis appId={appId} onAnalysisComplete={setAnalysisResult} />
            </div>
            <div style={{ display: activeTab === 'segments' ? 'block' : 'none' }}>
              <SegmentAnalysis appId={appId} />
            </div>
            <div style={{ display: activeTab === 'export' ? 'block' : 'none' }}>
              <ExportPanel appId={appId} analysisResult={analysisResult} />
            </div>
          </>
        )
      }}
    </Layout>
  )
}
