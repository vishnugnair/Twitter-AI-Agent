import { useState } from 'react'

function TrackedUsers() {
  const [loading, setLoading] = useState(false)
  const [fetchComplete, setFetchComplete] = useState(false)
  const [trackedUsers, setTrackedUsers] = useState([])
  const [showUsers, setShowUsers] = useState(false)
  const [error, setError] = useState('')

  const handleFetchUsers = async () => {
    setLoading(true)
    setError('')
    setFetchComplete(false)

    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/scrape_tracked_accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Fetch complete:', data)
        setFetchComplete(true)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to fetch tracked accounts')
      }
    } catch (err) {
      setError('Network error. Please try again.')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleViewUsers = async () => {
    setLoading(true)
    setError('')

    try {
      // For now, I'll use the /users endpoint to get basic info
      // You might need to create a specific endpoint for tracked accounts
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/users`, {
        method: 'GET',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        setTrackedUsers(data.users || [])
        setShowUsers(true)
      } else {
        setError('Failed to fetch user data')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg">
                <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v6.114a4 4 0 10.2 7.114V5.886L16 4.114V11.114a4 4 0 10.2 7.114V3zM8 15a2 2 0 11-4 0 2 2 0 014 0zm10 0a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
              </div>
              <h1 className="text-xl font-bold text-gray-900">Tracked Users</h1>
            </div>
            <a href="/dashboard" className="text-gray-600 hover:text-gray-900 transition-colors">
              ← Back to Dashboard
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Control Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Account Management</h2>
          
          <div className="flex flex-wrap gap-4">
            {/* Fetch Button */}
            <button
              onClick={handleFetchUsers}
              disabled={loading}
              className="flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-lg transition-colors"
            >
              {loading && !fetchComplete ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Fetching Accounts...
                </>
              ) : fetchComplete ? (
                <>
                  <svg className="w-4 h-4 mr-2 text-green-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  ✅ Fetched
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
                  </svg>
                  Fetch Tracked Users
                </>
              )}
            </button>

            {/* View Button */}
            <button
              onClick={handleViewUsers}
              disabled={loading}
              className="flex items-center px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-lg transition-colors"
            >
              {loading && fetchComplete ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Loading...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                  </svg>
                  View Fetched Accounts
                </>
              )}
            </button>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Users Table */}
        {showUsers && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Tracked Accounts ({trackedUsers.length})</h3>
            </div>
            
            {trackedUsers.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Account
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Target Accounts
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Keywords
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {trackedUsers.map((user, index) => (
                      <tr key={user.id || index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                              <span className="text-white text-sm font-bold">
                                {user.name?.charAt(0)?.toUpperCase() || '?'}
                              </span>
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-gray-900">{user.name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex flex-wrap gap-1">
                            {user.target_accounts?.length > 0 ? (
                              user.target_accounts.slice(0, 3).map((account, i) => (
                                <span key={i} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  @{account}
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-400">None</span>
                            )}
                            {user.target_accounts?.length > 3 && (
                              <span className="text-xs text-gray-400">+{user.target_accounts.length - 3} more</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex flex-wrap gap-1">
                            {user.search_keywords?.length > 0 ? (
                              user.search_keywords.slice(0, 3).map((keyword, i) => (
                                <span key={i} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                  {keyword}
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-400">None</span>
                            )}
                            {user.search_keywords?.length > 3 && (
                              <span className="text-xs text-gray-400">+{user.search_keywords.length - 3} more</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No tracked accounts</h3>
                <p className="mt-1 text-sm text-gray-500">Get started by fetching your tracked accounts.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default TrackedUsers 