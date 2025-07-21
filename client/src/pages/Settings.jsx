import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const Settings = () => {
  const navigate = useNavigate();
  const [activeModal, setActiveModal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form states
  const [twitterCreds, setTwitterCreds] = useState({
    twitter_username: '',
    twitter_client_id: '',
    twitter_client_secret: '',
    twitter_access_token: '',
    twitter_access_token_secret: ''
  });
  const [targetAccounts, setTargetAccounts] = useState('');
  const [keywords, setKeywords] = useState('');

  // Fetch existing user settings when component mounts
  useEffect(() => {
    fetchUserSettings();
  }, []);

  const fetchUserSettings = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/get_user_settings`, {
        method: 'GET',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        
        // Populate existing data
        setTwitterCreds(prev => ({
          ...prev,
          twitter_username: data.twitter_username || ''
        }));
        setTargetAccounts(data.target_accounts ? data.target_accounts.join(', ') : '');
        setKeywords(data.search_keywords ? data.search_keywords.join(', ') : '');
      }
    } catch (err) {
      console.error('Failed to fetch user settings:', err);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleTwitterSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/update_twitter_credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(twitterCreds)
      });

      if (response.ok) {
        const data = await response.json();
        
        // Handle different persona generation statuses
        if (data.persona_status === 'success') {
          setSuccess('Twitter account connected and persona generated successfully!');
        } else if (data.persona_status === 'no_tweets_found') {
          setSuccess('Twitter account connected! No tweets found for persona generation.');
        } else if (data.persona_status?.includes('failed')) {
          setSuccess('Twitter account connected! Persona generation failed, but credentials are saved.');
        } else {
          setSuccess('Twitter credentials updated successfull!');
        }
        
        setTimeout(() => {
          setActiveModal(null);
          setSuccess('');
        }, 3000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update Twitter credentials');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTargetAccountsSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const accountsArray = targetAccounts
      .split(',')
      .map(acc => acc.trim())
      .filter(acc => acc);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/update_target_accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ target_accounts: accountsArray })
      });

      if (response.ok) {
        setSuccess('Target accounts updated successfully!');
        setTimeout(() => {
          setActiveModal(null);
          setSuccess('');
        }, 2000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update target accounts');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeywordsSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const keywordsArray = keywords
      .split(',')
      .map(kw => kw.trim())
      .filter(kw => kw);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/update_keywords`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ keywords: keywordsArray })
      });

      if (response.ok) {
        setSuccess('Keywords updated successfully!');
        setTimeout(() => {
          setActiveModal(null);
          setSuccess('');
        }, 2000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to update keywords');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const closeModal = () => {
    setActiveModal(null);
    setError('');
    setSuccess('');
  };

  // Icon components
  const TwitterIcon = () => (
    <svg className="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
  );

  const UsersIcon = () => (
    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a4 4 0 11-8 0 4 4 0 018 0z"/>
    </svg>
  );

  const SearchIcon = () => (
    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
    </svg>
  );

  return (
    <div className="max-w-2xl mx-auto p-6 max-md:p-4">
      {/* Initial Loading */}
      {initialLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          {/* Page Header */}
          <div className="mb-8 max-md:mb-6">
            <h1 className="text-2xl font-bold text-gray-900 max-md:text-xl">Settings</h1>
            <p className="text-gray-600 mt-1 max-md:text-sm">Configure your Twitter Growth automation</p>
          </div>

          {/* Settings Options */}
          <div className="space-y-1">
            {[
              { 
                id: 'twitter',
                title: 'Connect Twitter Account', 
                desc: twitterCreds.twitter_username ? `Connected: ${twitterCreds.twitter_username}` : 'Add your Twitter credentials to enable automation',
                icon: <TwitterIcon />
              },
              { 
                id: 'accounts',
                title: 'Target Accounts', 
                desc: targetAccounts ? `${targetAccounts.split(',').length} account(s) configured` : 'Choose Twitter accounts to engage with',
                icon: <UsersIcon />
              },
              { 
                id: 'keywords',
                title: 'Keywords', 
                desc: keywords ? `${keywords.split(',').length} keyword(s) configured` : 'Set keywords to find relevant conversations',
                icon: <SearchIcon />
              }
            ].map((action) => (
              <button 
                key={action.id}
                onClick={() => setActiveModal(action.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors border-b border-gray-200 last:border-b-0 max-md:p-3"
              >
                <div className="flex items-center min-w-0 flex-1">
                  <div className="mr-3 flex-shrink-0">{action.icon}</div>
                  <div className="text-left min-w-0 flex-1">
                    <p className="font-medium text-gray-900 max-md:text-sm">{action.title}</p>
                    <p className="text-sm text-gray-500 truncate pr-2 max-md:text-xs">{action.desc}</p>
                  </div>
                </div>
                <svg className="w-5 h-5 text-gray-400 flex-shrink-0 max-md:w-4 max-md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/>
                </svg>
              </button>
            ))}
          </div>

          {/* Modals */}
          {activeModal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 max-md:p-2">
              <div className="bg-white rounded-xl max-w-md w-full max-h-[80vh] overflow-y-auto max-md:max-h-[90vh]">
                <div className="sticky top-0 bg-white rounded-t-xl border-b border-gray-200 p-4 max-md:p-3">
                  <div className="flex justify-between items-center">
                    <h3 className="text-xl font-semibold text-gray-900 max-md:text-lg">
                      {activeModal === 'twitter' && 'Connect Twitter Account'}
                      {activeModal === 'accounts' && 'Target Accounts'}
                      {activeModal === 'keywords' && 'Keywords'}
                    </h3>
                    <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 rounded-full p-1">
                      <svg className="w-6 h-6 max-md:w-5 max-md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="p-4 max-md:p-3">
                  {/* Twitter Credentials Form */}
                  {activeModal === 'twitter' && (
                    <form onSubmit={handleTwitterSubmit} className="space-y-3">
                      {/* Help Button */}
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 mb-3">
                        <div className="flex items-center justify-between max-sm:flex-col max-sm:gap-2">
                          <div>
                            <p className="text-blue-800 font-medium text-sm max-md:text-xs">Need help getting your API credentials?</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => navigate('/documentation')}
                            className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-1.5 px-3 rounded text-sm whitespace-nowrap max-md:text-xs"
                          >
                            View Guide
                          </button>
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 max-md:text-xs">Twitter Username</label>
                        <input
                          type="text"
                          value={twitterCreds.twitter_username}
                          onChange={(e) => setTwitterCreds({...twitterCreds, twitter_username: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="@username"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 max-md:text-xs">API Key</label>
                        <input
                          type="text"
                          value={twitterCreds.twitter_client_id}
                          onChange={(e) => setTwitterCreds({...twitterCreds, twitter_client_id: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="Your API Key (from Consumer Keys)"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 max-md:text-xs">API Key Secret</label>
                        <input
                          type="password"
                          value={twitterCreds.twitter_client_secret}
                          onChange={(e) => setTwitterCreds({...twitterCreds, twitter_client_secret: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="Your API Key Secret (from Consumer Keys)"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 max-md:text-xs">Access Token</label>
                        <input
                          type="text"
                          value={twitterCreds.twitter_access_token}
                          onChange={(e) => setTwitterCreds({...twitterCreds, twitter_access_token: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="Your Access Token"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1 max-md:text-xs">Access Token Secret</label>
                        <input
                          type="password"
                          value={twitterCreds.twitter_access_token_secret}
                          onChange={(e) => setTwitterCreds({...twitterCreds, twitter_access_token_secret: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="Your Access Token Secret"
                          required
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold py-3 px-4 rounded-full transition-colors disabled:cursor-not-allowed mt-4 max-md:text-base text-base min-h-[44px]"
                      >
                        {loading ? (
                          <div className="flex items-center justify-center">
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 max-md:w-4 max-md:h-4"></div>
                            Connecting...
                          </div>
                        ) : (
                          'Connect Account'
                        )}
                      </button>
                    </form>
                  )}

                  {/* Target Accounts Form */}
                  {activeModal === 'accounts' && (
                    <form onSubmit={handleTargetAccountsSubmit} className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2 max-md:text-xs">Target Accounts</label>
                        <textarea
                          value={targetAccounts}
                          onChange={(e) => setTargetAccounts(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="elonmusk, sundarpichai, tim_cook"
                          rows="4"
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1">Enter usernames without @ symbol, separated by commas</p>
                      </div>
                      <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold py-3 px-4 rounded-full transition-colors disabled:cursor-not-allowed text-base min-h-[44px]"
                      >
                        {loading ? (
                          <div className="flex items-center justify-center">
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                            Processing...
                          </div>
                        ) : (
                          'Save Accounts'
                        )}
                      </button>
                    </form>
                  )}

                  {/* Keywords Form */}
                  {activeModal === 'keywords' && (
                    <form onSubmit={handleKeywordsSubmit} className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2 max-md:text-xs">Keywords</label>
                        <textarea
                          value={keywords}
                          onChange={(e) => setKeywords(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:text-base text-base"
                          placeholder="AI, machine learning, startups, tech"
                          rows="4"
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1">Enter keywords separated by commas</p>
                      </div>
                      <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold py-3 px-4 rounded-full transition-colors disabled:cursor-not-allowed text-base min-h-[44px]"
                      >
                        {loading ? 'Saving...' : 'Save Keywords'}
                      </button>
                    </form>
                  )}

                  {/* Error/Success Messages */}
                  {error && (
                    <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-red-700 text-sm">{error}</p>
                    </div>
                  )}
                  {success && (
                    <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-3">
                      <p className="text-green-700 text-sm">{success}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}


    </div>
  );
};

export default Settings; 