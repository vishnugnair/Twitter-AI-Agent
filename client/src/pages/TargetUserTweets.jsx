import { useState, useEffect } from 'react'

function TargetUserTweets() {
  const [loading, setLoading] = useState(false)
  const [fetchComplete, setFetchComplete] = useState(false)
  const [tweets, setTweets] = useState([])
  const [showTweets, setShowTweets] = useState(false)
  const [error, setError] = useState('')
  const [editingTweet, setEditingTweet] = useState(null)
  const [editText, setEditText] = useState('')
  const [userProfileImage, setUserProfileImage] = useState(null)

  // Function to dispatch loading state to Layout
  const dispatchLoadingState = (isLoading) => {
    window.dispatchEvent(new CustomEvent('loadingStateChange', {
      detail: { loading: isLoading }
    }));
  };

  // Function to dispatch fetch complete state to Layout
  const dispatchFetchComplete = (isComplete) => {
    window.dispatchEvent(new CustomEvent('fetchCompleteChange', {
      detail: { complete: isComplete }
    }));
  };

  // Update loading state and dispatch to Layout
  const updateLoading = (isLoading) => {
    setLoading(isLoading);
    dispatchLoadingState(isLoading);
  };

  // Update fetch complete state and dispatch to Layout
  const updateFetchComplete = (isComplete) => {
    setFetchComplete(isComplete);
    dispatchFetchComplete(isComplete);
  };

  // Automatically fetch tweets when component mounts
  useEffect(() => {
    handleViewTweets()
    fetchUserProfileImage()
  }, [])

  // Add event listeners for Layout buttons
  useEffect(() => {
    const handleViewTargetTweets = () => {
      handleViewTweetsAction();
    };

    const handleFetchTargetTweets = () => {
      handleFetchTweetsAction();
    };

    window.addEventListener('viewTargetTweets', handleViewTargetTweets);
    window.addEventListener('fetchTargetTweets', handleFetchTargetTweets);

    return () => {
      window.removeEventListener('viewTargetTweets', handleViewTargetTweets);
      window.removeEventListener('fetchTargetTweets', handleFetchTargetTweets);
    };
  }, []);

  const fetchUserProfileImage = async () => {
    try {
      const response = await fetch('https://twitter-growth-agent.onrender.com/get_user_profile_image', {
        method: 'GET',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        setUserProfileImage(data.profile_image_url)
      }
    } catch (err) {
      console.error('Failed to fetch user profile image:', err)
    }
  }

  const handleFetchTweetsAction = async () => {
    updateLoading(true)
    setError('')
    updateFetchComplete(false)

    try {
      const response = await fetch('https://twitter-growth-agent.onrender.com/scrape_user_tweets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Fetch target user tweets complete:', data)
        updateFetchComplete(true)
        // After fetching, automatically refresh the view
        handleViewTweetsAction()
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to fetch target user tweets')
      }
    } catch (err) {
      setError('Network error. Please try again.')
      console.error('Error:', err)
    } finally {
      updateLoading(false)
    }
  }

  const handleViewTweetsAction = async () => {
    updateLoading(true)
    setError('')

    try {
      const response = await fetch('https://twitter-growth-agent.onrender.com/fetch_pending_replies', {
        method: 'GET',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        setTweets(data.pending_replies || [])
        setShowTweets(true)
      } else {
        setError('Failed to fetch tweets with replies')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      updateLoading(false)
    }
  }

  // Keep the original functions for backward compatibility
  const handleFetchTweets = handleFetchTweetsAction;
  const handleViewTweets = handleViewTweetsAction;

  const handleReplyAction = async (tweetId, action, editedText = null) => {
    updateLoading(true)
    setError('')

    const payload = {
      tweet_id: tweetId,
      action: action
    }

    if (action === 'edit' && editedText) {
      payload.edited_text = editedText
    }

    try {
      const response = await fetch('https://twitter-growth-agent.onrender.com/handle_reply_action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Action complete:', data)
        
        // Remove the tweet from the list or refresh the data
        setTweets(tweets.filter(tweet => tweet.tweet_id !== tweetId))
        setEditingTweet(null)
        setEditText('')
        
        // Show success message
        alert(`Reply ${action}ed successfully!`)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || `Failed to ${action} reply`)
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      updateLoading(false)
    }
  }

  const startEdit = (tweet) => {
    setEditingTweet(tweet.tweet_id)
    setEditText(tweet.draft_reply)
  }

  const cancelEdit = () => {
    setEditingTweet(null)
    setEditText('')
  }

  const submitEdit = (tweetId) => {
    handleReplyAction(tweetId, 'edit', editText)
  }

  return (
    <div className="max-md:px-2 max-md:overflow-x-hidden max-md:w-full">
      {/* Loading Spinner */}
      {loading && (
        <div className="flex justify-center items-center h-64">
          <div className="w-8 h-8 border-4 border-sky-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mx-6 my-6 bg-red-50 border border-red-200 rounded-lg p-4 max-md:mx-2 max-md:my-4 max-md:p-3">
          <p className="text-red-700 text-sm max-md:text-base">{error}</p>
        </div>
      )}

      {/* Tweet Display */}
      {showTweets && !loading && (
        <div className="max-md:overflow-x-hidden">
          <div className="p-4 border-b border-gray-200 max-md:p-3">
            <h3 className="text-lg font-semibold text-gray-900 max-md:text-lg">
              Pending Replies ({tweets.length})
            </h3>
          </div>
          
          {tweets.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 max-md:text-base">No tweets with drafted replies found.</p>
            </div>
          ) : (
            <div className="max-md:overflow-x-hidden">
              {tweets.map((tweet) => (
                <div key={tweet.tweet_id} className="border-b border-gray-200 p-4 hover:bg-gray-50 transition-colors max-md:p-3 max-md:overflow-x-hidden max-md:w-full">
                  <div className="flex space-x-3 max-md:space-x-2 max-md:overflow-x-hidden max-md:w-full">
                    <div className="w-12 h-12 rounded-full overflow-hidden bg-blue-500 flex items-center justify-center flex-shrink-0 max-md:w-10 max-md:h-10">
                      {tweet.profile_image_url ? (
                        <img 
                          src={tweet.profile_image_url} 
                          alt={`${tweet.username} profile`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            // Hide broken image, show initials fallback
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <span 
                        className="text-white font-bold text-sm w-full h-full flex items-center justify-center max-md:text-base" 
                        style={{display: tweet.profile_image_url ? 'none' : 'flex'}}
                      >
                        {tweet.username?.charAt(0)?.toUpperCase() || 'T'}
                      </span>
                    </div>
                    
                    <div className="flex-1 min-w-0 max-md:overflow-x-hidden max-md:w-full">
                      <div className="flex items-center space-x-2 mb-1 max-md:space-x-1 max-md:overflow-x-hidden">
                        <h4 className="font-bold text-gray-900 truncate max-md:text-base max-md:overflow-x-hidden">@{tweet.username}</h4>
                      </div>
                      
                      {/* Original Tweet Text */}
                      <div className="max-md:w-full max-md:overflow-x-hidden">
                        <p className="text-gray-900 mb-3 leading-relaxed max-md:mb-2 max-md:text-base max-md:break-words max-md:word-wrap max-md:overflow-wrap-anywhere max-md:w-full">
                          {tweet.text}
                        </p>
                      </div>
                      
                      {/* Drafted Reply Section */}
                      {tweet.draft_reply && (
                        <div className="mt-4 pl-4 border-l-4 border-blue-200 bg-gray-50 rounded-r-lg p-3 max-md:pl-3 max-md:p-2 max-md:w-full max-md:overflow-x-hidden">
                          <div className="flex items-center space-x-2 mb-2 max-md:space-x-1 max-md:overflow-x-hidden">
                            <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0 max-md:w-6 max-md:h-6">
                              {userProfileImage ? (
                                <img 
                                  src={userProfileImage} 
                                  alt="Your profile"
                                  className="w-full h-full object-cover rounded-full"
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                    e.target.nextSibling.style.display = 'flex';
                                  }}
                                />
                              ) : null}
                              <span 
                                className="text-white font-bold text-xs w-full h-full flex items-center justify-center max-md:text-sm" 
                                style={{display: userProfileImage ? 'none' : 'flex'}}
                              >
                                Y
                              </span>
                            </div>
                            <span className="font-bold text-gray-900 text-sm max-md:text-base">You</span>
                          </div>
                          
                          {editingTweet === tweet.tweet_id ? (
                            <div className="max-md:w-full max-md:overflow-x-hidden">
                              <textarea
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm max-md:text-base max-md:min-h-[44px] max-md:w-full"
                                rows="3"
                              />
                              <div className="flex space-x-2 mt-2 max-md:flex-wrap max-md:gap-2 max-md:w-full max-md:overflow-x-hidden">
                                <button
                                  onClick={() => submitEdit(tweet.tweet_id)}
                                  disabled={loading}
                                  className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={cancelEdit}
                                  className="px-4 py-1.5 border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="max-md:w-full max-md:overflow-x-hidden">
                              <p className="text-gray-900 mb-2 leading-relaxed text-sm max-md:text-base max-md:break-words max-md:word-wrap max-md:overflow-wrap-anywhere max-md:w-full">
                                {tweet.draft_reply}
                              </p>
                              <div className="flex space-x-2 max-md:flex-wrap max-md:gap-2 max-md:w-full max-md:overflow-x-hidden">
                                <button
                                  onClick={() => handleReplyAction(tweet.tweet_id, 'confirm')}
                                  disabled={loading}
                                  className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                                >
                                  Reply
                                </button>
                                <button
                                  onClick={() => startEdit(tweet)}
                                  disabled={loading}
                                  className="px-4 py-1.5 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-200 text-gray-700 font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => handleReplyAction(tweet.tweet_id, 'cancel')}
                                  disabled={loading}
                                  className="px-4 py-1.5 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-200 text-gray-700 font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          )}
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
    </div>
  )
}

export default TargetUserTweets 