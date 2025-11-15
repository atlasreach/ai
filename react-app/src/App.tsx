import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Studio from './pages/Studio'
import Library from './pages/Library'
import Models from './pages/Models'
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
              Content Studio
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
                🎨 Studio
              </Link>
              <Link
                to="/library"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/library')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                📚 Library
              </Link>
              <Link
                to="/models"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/models')
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                👤 Models
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
            <Route path="/" element={<Studio />} />
            <Route path="/library" element={<Library />} />
            <Route path="/models" element={<Models />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
