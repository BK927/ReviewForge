import { Layout } from './components/Layout'
import { Dashboard } from './components/Dashboard'
import { TopicAnalysis } from './components/TopicAnalysis'
import { SegmentAnalysis } from './components/SegmentAnalysis'
import { ExportPanel } from './components/ExportPanel'

export default function App() {
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
              <TopicAnalysis appId={appId} />
            </div>
            <div style={{ display: activeTab === 'segments' ? 'block' : 'none' }}>
              <SegmentAnalysis appId={appId} />
            </div>
            <div style={{ display: activeTab === 'export' ? 'block' : 'none' }}>
              <ExportPanel appId={appId} />
            </div>
          </>
        )
      }}
    </Layout>
  )
}
