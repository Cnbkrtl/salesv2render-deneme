import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import LiveDashboard from './pages/LiveDashboard'
import Analytics from './pages/Analytics'
import ProductPerformance from './pages/ProductPerformance'
import Settings from './pages/Settings'
import AdminPanel from './pages/AdminPanel'
import './App.css'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<LiveDashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/product-performance" element={<ProductPerformance />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
