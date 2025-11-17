import { useState, useEffect } from 'react';
import { X, Link as LinkIcon, Loader, Instagram, RefreshCw } from 'lucide-react';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://${window.location.hostname.replace('5173', '8002')}`;

interface InstagramAccount {
  id: string;
  username: string;
  full_name: string;
  profile_pic_url?: string;
  followers_count?: number;
  post_count?: number;
  last_scraped_at?: string;
  scrape_status: string;
  model_id?: string;
}

interface ScrapedAccountsModalProps {
  modelId: string;
  modelName: string;
  onClose: () => void;
}

export default function ScrapedAccountsModal({ modelId, modelName, onClose }: ScrapedAccountsModalProps) {
  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState<string | null>(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeUsername, setScrapeUsername] = useState('');

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/instagram/accounts`);
      const data = await response.json();
      setAccounts(data);
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const linkAccount = async (accountId: string) => {
    setLinking(accountId);
    try {
      const response = await fetch(`${API_BASE}/api/persona/models/${modelId}/link-instagram`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instagram_account_id: accountId }),
      });

      if (response.ok) {
        fetchAccounts(); // Refresh list
      }
    } catch (error) {
      console.error('Failed to link account:', error);
    } finally {
      setLinking(null);
    }
  };

  const scrapeNow = async () => {
    if (!scrapeUsername) return;

    setScraping(true);
    try {
      const response = await fetch(`${API_BASE}/api/instagram/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: scrapeUsername,
          num_posts: 50
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        alert(`Scraping started for @${scrapeUsername}. This will run in the background.`);
        setScrapeUsername('');
        // Refresh accounts after a delay to show the new account
        setTimeout(fetchAccounts, 2000);
      } else {
        alert(data.error || data.message || 'Failed to start scraping');
      }
    } catch (error) {
      console.error('Failed to scrape:', error);
      alert('Failed to start scraping. Check console for details.');
    } finally {
      setScraping(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">Scraped Instagram Accounts</h2>
            <p className="text-sm text-slate-400 mt-1">
              Link accounts to <span className="text-blue-400 capitalize">{modelName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrape New Account */}
        <div className="p-6 border-b border-slate-800 bg-slate-950/50">
          <div className="flex gap-3">
            <div className="flex-1">
              <input
                type="text"
                value={scrapeUsername}
                onChange={(e) => setScrapeUsername(e.target.value)}
                placeholder="Enter Instagram username to scrape..."
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            <button
              onClick={scrapeNow}
              disabled={!scrapeUsername || scraping}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg transition-colors flex items-center gap-2"
            >
              {scraping ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Scraping...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Scrape Now
                </>
              )}
            </button>
          </div>
        </div>

        {/* Accounts List */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : accounts.length === 0 ? (
            <div className="text-center py-12">
              <Instagram className="w-12 h-12 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400">No accounts scraped yet</p>
              <p className="text-sm text-slate-500 mt-1">
                Enter an Instagram username above to scrape
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className={`bg-slate-800/50 border rounded-lg p-4 ${
                    account.model_id === modelId
                      ? 'border-blue-500'
                      : 'border-slate-700'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Profile Pic */}
                    <div className="w-12 h-12 rounded-full bg-slate-700 overflow-hidden flex-shrink-0">
                      {account.profile_pic_url ? (
                        <img
                          src={account.profile_pic_url}
                          alt={account.username}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Instagram className="w-6 h-6 text-slate-500" />
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold">@{account.username}</div>
                      {account.full_name && (
                        <div className="text-sm text-slate-400 truncate">
                          {account.full_name}
                        </div>
                      )}

                      {/* Stats */}
                      <div className="flex gap-3 mt-2 text-xs text-slate-500">
                        <span>{account.followers_count || 0} followers</span>
                        <span>{account.post_count || 0} posts</span>
                      </div>

                      {/* Status */}
                      {account.last_scraped_at && (
                        <div className="text-xs text-slate-600 mt-1">
                          Scraped {new Date(account.last_scraped_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>

                    {/* Link Button */}
                    <div>
                      {account.model_id === modelId ? (
                        <div className="px-3 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                          Linked
                        </div>
                      ) : account.model_id ? (
                        <div className="px-3 py-1 bg-slate-700 text-slate-400 text-xs rounded-full">
                          In Use
                        </div>
                      ) : (
                        <button
                          onClick={() => linkAccount(account.id)}
                          disabled={linking === account.id}
                          className="p-2 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
                          title="Link to this model"
                        >
                          {linking === account.id ? (
                            <Loader className="w-4 h-4 animate-spin" />
                          ) : (
                            <LinkIcon className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 bg-slate-950/50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
