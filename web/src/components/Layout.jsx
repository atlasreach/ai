import { Link, useLocation } from 'react-router-dom'

export default function Layout({ children }) {
  const location = useLocation()

  const isActive = (path) => location.pathname === path

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Top Navigation */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">AI Model Generator</h1>

            <nav className="flex gap-2">
              <Link
                to="/generate"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/generate') || isActive('/')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                Generate
              </Link>
              <Link
                to="/gallery"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/gallery')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                Gallery
              </Link>
              <Link
                to="/models"
                className={`px-4 py-2 rounded-lg transition-all ${
                  isActive('/models')
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                Models
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Page Content */}
      <main>
        {children}
      </main>
    </div>
  )
}
