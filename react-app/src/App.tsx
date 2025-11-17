import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Models from './pages/Models'
import Tools from './pages/Tools'
import Generations from './pages/Generations'
import DatasetCreator from './pages/DatasetCreator'
import Training from './pages/Training'
import Instagrams from './pages/Instagrams'
import './App.css'

function Navigation() {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <nav className="bg-slate-800/50 backdrop-blur border-b border-slate-700">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              AI Studio
            </h1>

            <div className="flex space-x-1">
              <Link
                to="/"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                👤 Models
              </Link>
              <Link
                to="/tools"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/tools')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                🛠️ Tools
              </Link>
              <Link
                to="/generations"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/generations')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                ✨ Generations
              </Link>
              <Link
                to="/dataset-creator"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/dataset-creator')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                📦 Dataset Creator
              </Link>
              <Link
                to="/training"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/training')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                🚀 Training
              </Link>
              <Link
                to="/instagrams"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/instagrams')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                📸 Instagrams
              </Link>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-400">
              API: <span className="text-green-400">●</span> Connected
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-white">
        <Navigation />

        <main className="max-w-7xl mx-auto px-8 py-8">
          <Routes>
            <Route path="/" element={<Models />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/generations" element={<Generations />} />
            <Route path="/dataset-creator" element={<DatasetCreator />} />
            <Route path="/training" element={<Training />} />
            <Route path="/instagrams" element={<Instagrams />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
