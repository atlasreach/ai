import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Generate from './pages/Generate'
import Gallery from './pages/Gallery'
import Models from './pages/Models'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/generate" replace />} />
          <Route path="/generate" element={<Generate />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/models" element={<Models />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
