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
        switch (activeTab) {
          case 'dashboard': return <Dashboard appId={appId} />
          case 'topics': return <TopicAnalysis appId={appId} />
          case 'segments': return <SegmentAnalysis appId={appId} />
          case 'export': return <ExportPanel appId={appId} />
          default: return null
        }
      }}
    </Layout>
  )
}
