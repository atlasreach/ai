import { useState, useEffect } from 'react';
import { Instagram, Plus, Heart, MessageCircle, Eye, Grid3X3, ChevronLeft, ChevronRight, Star, Trash2, Loader, X, Play } from 'lucide-react';
import { supabase } from '../lib/supabase';

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8002'
  : `https://vigilant-rotary-phone-7v5g5q99jpjjfw57w-8002.app.github.dev`;

interface InstagramAccount {
  id: string;
  username: string;
  full_name: string;
  profile_pic_url: string;
  total_posts_scraped: number;
  last_scraped_at: string;
  is_favorite: boolean;
  posts_count: number;
  tags: string[];
}

interface InstagramPost {
  id: string;
  post_type: string;
  display_url: string;
  media_urls: string[];
  caption: string;
  likes_count: number;
  comments_count: number;
  views_count: number;
  post_url: string;
  posted_at: string;
}

export default function Instagrams() {
  const [view, setView] = useState<'list' | 'detail'>('list');
  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<InstagramAccount | null>(null);
  const [posts, setPosts] = useState<InstagramPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showScrapeModal, setShowScrapeModal] = useState(false);
  const [scrapeUsername, setScrapeUsername] = useState('');
  const [scrapeNumPosts, setScrapeNumPosts] = useState(50);
  const [isScraping, setIsScraping] = useState(false);
  const [carouselModal, setCarouselModal] = useState<{ post: InstagramPost; index: number } | null>(null);
  const [videoModal, setVideoModal] = useState<InstagramPost | null>(null);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/instagram/accounts`);
      const data = await response.json();
      if (data.success) {
        setAccounts(data.accounts);
      }
    } catch (error) {
      console.error('Error loading accounts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAccountDetail = async (account: InstagramAccount) => {
    setSelectedAccount(account);
    setView('detail');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/instagram/accounts/${account.id}`);
      const data = await response.json();
      if (data.success) {
        setPosts(data.posts);
      }
    } catch (error) {
      console.error('Error loading posts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleScrape = async () => {
    if (!scrapeUsername) return;

    setIsScraping(true);
    try {
      const response = await fetch(`${API_BASE}/api/instagram/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: scrapeUsername,
          num_posts: scrapeNumPosts,
        }),
      });

      const data = await response.json();
      if (data.success) {
        alert(data.message);
        setShowScrapeModal(false);
        setScrapeUsername('');
        await loadAccounts();
      } else {
        alert('Failed to scrape: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error scraping:', error);
      alert('Failed to scrape account');
    } finally {
      setIsScraping(false);
    }
  };

  const deleteAccount = async (accountId: string, username: string) => {
    if (!confirm(`Delete @${username} and all its posts?`)) return;

    try {
      const response = await fetch(`${API_BASE}/api/instagram/accounts/${accountId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadAccounts();
        if (selectedAccount?.id === accountId) {
          setView('list');
          setSelectedAccount(null);
        }
      }
    } catch (error) {
      console.error('Error deleting account:', error);
      alert('Failed to delete account');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-500 rounded-xl flex items-center justify-center">
              <Instagram className="w-6 h-6 text-white" />
            </div>
            Instagram Library
          </h1>
          <p className="text-slate-400 mt-1">
            {view === 'list'
              ? 'Manage your scraped Instagram accounts'
              : `@${selectedAccount?.username}`
            }
          </p>
        </div>

        {view === 'list' ? (
          <button
            onClick={() => setShowScrapeModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-lg hover:from-pink-600 hover:to-purple-600 transition-all"
          >
            <Plus className="w-5 h-5" />
            Add Account
          </button>
        ) : (
          <button
            onClick={() => {
              setView('list');
              setSelectedAccount(null);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700"
          >
            <ChevronLeft className="w-5 h-5" />
            Back to List
          </button>
        )}
      </div>

      {/* Content */}
      {view === 'list' ? (
        /* List View */
        isLoading ? (
          <div className="text-center py-12 text-slate-400">
            <Loader className="w-8 h-8 animate-spin mx-auto mb-3" />
            Loading accounts...
          </div>
        ) : accounts.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-slate-700 rounded-xl">
            <Instagram className="w-12 h-12 mx-auto text-slate-500 mb-3" />
            <p className="text-slate-400 mb-4">No Instagram accounts scraped yet</p>
            <button
              onClick={() => setShowScrapeModal(true)}
              className="px-4 py-2 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-lg hover:from-pink-600 hover:to-purple-600"
            >
              Scrape Your First Account
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl hover:border-slate-700 transition-colors group relative"
              >
                {/* Delete button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteAccount(account.id, account.username);
                  }}
                  className="absolute top-3 right-3 p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-4 h-4" />
                </button>

                <div onClick={() => loadAccountDetail(account)} className="cursor-pointer">
                  <div className="flex items-center gap-3 mb-4">
                    {account.profile_pic_url ? (
                      <img
                        src={account.profile_pic_url}
                        alt={account.username}
                        className="w-12 h-12 rounded-full"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-pink-500 to-purple-500 flex items-center justify-center">
                        <Instagram className="w-6 h-6 text-white" />
                      </div>
                    )}
                    <div className="flex-1">
                      <h3 className="font-bold text-white group-hover:text-pink-400 transition-colors">
                        @{account.username}
                      </h3>
                      <p className="text-sm text-slate-400">{account.full_name || account.username}</p>
                    </div>
                    {account.is_favorite && (
                      <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-sm text-slate-400">
                    <div className="flex items-center gap-1">
                      <Grid3X3 className="w-4 h-4" />
                      <span>{account.posts_count || account.total_posts_scraped} posts</span>
                    </div>
                  </div>

                  {account.tags && account.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {account.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 text-xs bg-slate-800 text-slate-300 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 text-xs text-slate-500">
                    Scraped {new Date(account.last_scraped_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Detail View - Instagram Grid */
        <div className="space-y-6">
          {/* Account Header */}
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-xl">
            <div className="flex items-center gap-4">
              {selectedAccount?.profile_pic_url ? (
                <img
                  src={selectedAccount.profile_pic_url}
                  alt={selectedAccount.username}
                  className="w-20 h-20 rounded-full"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-pink-500 to-purple-500 flex items-center justify-center">
                  <Instagram className="w-10 h-10 text-white" />
                </div>
              )}
              <div>
                <h2 className="text-2xl font-bold text-white">@{selectedAccount?.username}</h2>
                <p className="text-slate-400">{selectedAccount?.full_name}</p>
                <p className="text-sm text-slate-500 mt-1">{posts.length} posts</p>
              </div>
            </div>
          </div>

          {/* Posts Grid */}
          {isLoading ? (
            <div className="text-center py-12 text-slate-400">
              <Loader className="w-8 h-8 animate-spin mx-auto mb-3" />
              Loading posts...
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-1">
              {posts.map((post) => (
                <div
                  key={post.id}
                  onClick={() => {
                    // Open video modal for videos
                    if (post.post_type === 'Video' && post.video_url) {
                      setVideoModal(post);
                    }
                    // Open carousel modal if it's a carousel with multiple images
                    else if (post.post_type === 'Sidecar' && post.media_urls && post.media_urls.length > 1) {
                      setCarouselModal({ post, index: 0 });
                    }
                  }}
                  className="relative aspect-square group cursor-pointer overflow-hidden bg-slate-800"
                >
                  {/* Post Media - Thumbnail for video or image */}
                  <img
                    src={post.display_url}
                    alt={post.caption?.substring(0, 50)}
                    className="w-full h-full object-cover group-hover:opacity-75 transition-opacity"
                  />

                  {/* Play button overlay for videos */}
                  {post.post_type === 'Video' && post.video_url && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition-colors">
                      <div className="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center">
                        <Play className="w-8 h-8 text-black fill-black ml-1" />
                      </div>
                    </div>
                  )}

                  {/* Carousel Indicator */}
                  {post.post_type === 'Sidecar' && post.media_urls && post.media_urls.length > 1 && (
                    <div className="absolute top-2 right-2">
                      <Grid3X3 className="w-5 h-5 text-white drop-shadow-lg" />
                    </div>
                  )}

                  {/* Hover Overlay */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="flex items-center gap-4 text-white">
                      <div className="flex items-center gap-1">
                        <Heart className="w-5 h-5 fill-white" />
                        <span className="font-medium">{post.likes_count?.toLocaleString() || 0}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <MessageCircle className="w-5 h-5 fill-white" />
                        <span className="font-medium">{post.comments_count?.toLocaleString() || 0}</span>
                      </div>
                      {post.views_count > 0 && (
                        <div className="flex items-center gap-1">
                          <Eye className="w-5 h-5" />
                          <span className="font-medium">{post.views_count?.toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scrape Modal */}
      {showScrapeModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Instagram className="w-6 h-6 text-pink-500" />
              Scrape Instagram Account
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Instagram Username
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">@</span>
                  <input
                    type="text"
                    value={scrapeUsername}
                    onChange={(e) => setScrapeUsername(e.target.value)}
                    placeholder="officialskylarmaexo"
                    className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Number of Posts
                </label>
                <input
                  type="number"
                  value={scrapeNumPosts}
                  onChange={(e) => setScrapeNumPosts(parseInt(e.target.value) || 50)}
                  min="1"
                  max="100"
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Cost: ~${((scrapeNumPosts / 1000) * 0.5).toFixed(3)}
                </p>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowScrapeModal(false)}
                  disabled={isScraping}
                  className="flex-1 px-4 py-2 bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleScrape}
                  disabled={isScraping || !scrapeUsername}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-lg hover:from-pink-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isScraping ? 'Scraping...' : 'Scrape'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Carousel Modal */}
      {carouselModal && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4">
          {/* Close button */}
          <button
            onClick={() => setCarouselModal(null)}
            className="absolute top-4 right-4 p-2 text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>

          {/* Image container */}
          <div className="relative max-w-4xl w-full aspect-square">
            <img
              src={carouselModal.post.media_urls[carouselModal.index]}
              alt={`Image ${carouselModal.index + 1} of ${carouselModal.post.media_urls.length}`}
              className="w-full h-full object-contain"
            />

            {/* Navigation buttons */}
            {carouselModal.post.media_urls.length > 1 && (
              <>
                {/* Left arrow */}
                {carouselModal.index > 0 && (
                  <button
                    onClick={() =>
                      setCarouselModal({
                        ...carouselModal,
                        index: carouselModal.index - 1,
                      })
                    }
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                )}

                {/* Right arrow */}
                {carouselModal.index < carouselModal.post.media_urls.length - 1 && (
                  <button
                    onClick={() =>
                      setCarouselModal({
                        ...carouselModal,
                        index: carouselModal.index + 1,
                      })
                    }
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                )}

                {/* Image counter */}
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-black/70 text-white text-sm rounded-full">
                  {carouselModal.index + 1} / {carouselModal.post.media_urls.length}
                </div>
              </>
            )}
          </div>

          {/* Caption */}
          {carouselModal.post.caption && (
            <div className="absolute bottom-8 left-8 right-8 max-w-2xl mx-auto p-4 bg-black/70 text-white text-sm rounded-lg max-h-32 overflow-y-auto">
              {carouselModal.post.caption}
            </div>
          )}
        </div>
      )}

      {/* Video Modal */}
      {videoModal && (
        <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4">
          {/* Close button */}
          <button
            onClick={() => setVideoModal(null)}
            className="absolute top-4 right-4 p-2 text-white hover:bg-white/10 rounded-lg transition-colors z-10"
          >
            <X className="w-6 h-6" />
          </button>

          {/* Video container */}
          <div className="relative max-w-4xl w-full">
            <video
              src={videoModal.video_url}
              poster={videoModal.display_url}
              controls
              autoPlay
              className="w-full rounded-lg"
              style={{ maxHeight: '80vh' }}
            />

            {/* Caption */}
            {videoModal.caption && (
              <div className="mt-4 p-4 bg-black/70 text-white text-sm rounded-lg max-h-32 overflow-y-auto">
                {videoModal.caption}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
