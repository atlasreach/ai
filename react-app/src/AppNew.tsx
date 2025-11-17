import { useState } from 'react';
import { Database, Image, Sparkles, Settings, Instagram } from 'lucide-react';
import ModelManager from './pages/ModelManagerNew';
import Datasets from './pages/DatasetsNew';
import ContentProduction from './pages/ContentProduction';
import Instagrams from './pages/Instagrams';

type Page = 'models' | 'datasets' | 'production' | 'instagrams' | 'settings';

export default function AppNew() {
  const [currentPage, setCurrentPage] = useState<Page>('models');

  const navigation = [
    { id: 'models' as Page, name: 'Model Manager', icon: Database, description: 'Manage your AI models' },
    { id: 'datasets' as Page, name: 'Datasets', icon: Image, description: 'Training & content datasets' },
    { id: 'instagrams' as Page, name: 'Instagram Library', icon: Instagram, description: 'Scrape & manage Instagram accounts' },
    { id: 'production' as Page, name: 'Content Production', icon: Sparkles, description: 'Generate content' },
    { id: 'settings' as Page, name: 'Settings', icon: Settings, description: 'Configure your workspace' },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'models':
        return <ModelManager />;
      case 'datasets':
        return <Datasets />;
      case 'instagrams':
        return <Instagrams />;
      case 'production':
        return <ContentProduction />;
      case 'settings':
        return <div className="text-gray-400">Settings coming soon...</div>;
      default:
        return <ModelManager />;
    }
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Vertical Sidebar Navigation */}
      <aside className="w-72 bg-slate-900/50 border-r border-slate-800/50 backdrop-blur-xl flex flex-col">
        {/* Logo/Header */}
        <div className="p-6 border-b border-slate-800/50">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            AI Studio Pro
          </h1>
          <p className="text-sm text-slate-400 mt-1">Model Training & Content Generation</p>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`
                  w-full flex items-start gap-3 p-4 rounded-xl transition-all duration-200
                  ${isActive
                    ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30 shadow-lg shadow-blue-500/10'
                    : 'hover:bg-slate-800/30 border border-transparent hover:border-slate-700/50'
                  }
                `}
              >
                <Icon
                  className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                    isActive ? 'text-blue-400' : 'text-slate-400'
                  }`}
                />
                <div className="text-left flex-1">
                  <div className={`font-medium ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {item.name}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {item.description}
                  </div>
                </div>
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800/50">
          <div className="text-xs text-slate-500">
            <div>v1.0.0</div>
            <div className="mt-1">Connected to Supabase ✓</div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-8">
          {renderPage()}
        </div>
      </main>
    </div>
  );
}
