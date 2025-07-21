import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import SignIn from './pages/SignIn'
import DashBoards from './pages/DashBoards'
import TopTweets from './pages/TopTweets'
import TargetUserTweets from './pages/TargetUserTweets'
import RepurposedTweets from './pages/RepurposedTweets'
import Settings from './pages/Settings'
import Documentation from './pages/Documentation'
import Layout from './components/Layout'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<SignIn />} />
        <Route path="/documentation" element={<Documentation />} />
        <Route path="/dashboard" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard/top-tweets" replace />} />
          <Route path="analytics" element={<div className="p-6"><h1 className="text-2xl font-bold">Analytics</h1><p>Analytics page coming soon...</p></div>} />
          <Route path="settings" element={<Settings />} />
          <Route path="top-tweets" element={<TopTweets />} />
          <Route path="target-user-tweets" element={<TargetUserTweets />} />
          <Route path="repurposed-tweets" element={<RepurposedTweets />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App