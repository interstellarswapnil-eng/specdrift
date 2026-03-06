import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { OverviewPage } from './pages/OverviewPage'
import { PrdTreePage } from './pages/PrdTreePage'
import { DriftFeedPage } from './pages/DriftFeedPage'

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/tree" element={<PrdTreePage />} />
        <Route path="/tree/:sectionId" element={<PrdTreePage />} />
        <Route path="/feed" element={<DriftFeedPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </AppLayout>
  )
}
