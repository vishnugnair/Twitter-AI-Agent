import { useState, useEffect } from 'react'

function RepurposedTweets() {
  const [loading, setLoading] = useState(false)
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

  // Update loading state and dispatch to Layout
  const updateLoading = (isLoading) => {
    setLoading(isLoading);
    dispatchLoadingState(isLoading);
  };

  // Automatically fetch repurposed tweets when component mounts
  useEffect(() => {
    handleViewRepurposed()
    fetchUserProfileImage()
  }, [])

  // Add event listeners for Layout buttons
  useEffect(() => {
    const handleViewRepurposedTweets = () => {
      handleViewRepurposedAction();
    };

    window.addEventListener('viewRepurposed', handleViewRepurposedTweets);

    return () => {
      window.removeEventListener('viewRepurposed', handleViewRepurposedTweets);
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

  const handleViewRepurposedAction = async () => {
    updateLoading(true)
    setError('')

    try {
      const response = await fetch('https://twitter-growth-agent.onrender.com/fetch_pending_repurposed_tweets', {
        method: 'GET',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        setTweets(data.pending_repurposed || [])
        setShowTweets(true)
      } else {
        setError('Failed to fetch repurposed tweets')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      updateLoading(false)
    }
  }

  // Keep the original function for backward compatibility
  const handleViewRepurposed = handleViewRepurposedAction;

  const handleRepurposeAction = async (tweetId, action, editedText = null) => {
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
      const response = await fetch('https://twitter-growth-agent.onrender.com/handle_repurpose_action_toptweets', {
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
        alert(`Tweet ${action}ed successfully!`)
      } else {
        const errorData = await response.json()
        setError(errorData.detail || `Failed to ${action} tweet`)
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      updateLoading(false)
    }
  }

  const startEdit = (tweet) => {
    setEditingTweet(tweet.tweet_id)
    setEditText(tweet.draft_post)
  }

  const cancelEdit = () => {
    setEditingTweet(null)
    setEditText('')
  }

  const submitEdit = (tweetId) => {
    handleRepurposeAction(tweetId, 'edit', editText)
  }

  const getInitials = (username) => {
    return username ? username.charAt(0).toUpperCase() : 'Y'
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

      {/* Tweet Ideas Display */}
      {showTweets && !loading && (
        <div className="max-md:overflow-x-hidden">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 max-md:p-3">
            <h3 className="text-lg font-semibold text-gray-900 max-md:text-lg">
              Tweet Ideas ({tweets.length})
            </h3>
          </div>
          
          {tweets.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 max-md:text-base">No tweet ideas found.</p>
            </div>
          ) : (
            <div className="max-md:overflow-x-hidden">
              {tweets.map((tweet) => (
                <div key={tweet.tweet_id} className="border-b border-gray-200 p-4 hover:bg-gray-50 transition-colors max-md:p-3 max-md:overflow-x-hidden max-md:w-full">
                  <div className="flex space-x-3 max-md:space-x-2 max-md:overflow-x-hidden max-md:w-full">
                    {/* User Avatar */}
                    <div className="w-12 h-12 rounded-full overflow-hidden bg-blue-500 flex items-center justify-center flex-shrink-0 max-md:w-10 max-md:h-10">
                      {userProfileImage ? (
                        <img 
                          src={userProfileImage} 
                          alt="Your profile"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <span 
                        className="text-white font-bold text-sm w-full h-full flex items-center justify-center max-md:text-base" 
                        style={{display: userProfileImage ? 'none' : 'flex'}}
                      >
                        Y
                      </span>
                    </div>
                    
                    <div className="flex-1 min-w-0 max-md:overflow-x-hidden max-md:w-full">
                      {/* Header */}
                      <div className="flex items-center space-x-2 mb-1 max-md:space-x-1 max-md:overflow-x-hidden">
                        <h4 className="font-bold text-gray-900 max-md:text-base max-md:overflow-x-hidden">You</h4>
                      </div>

                      {/* Content */}
                      <div className="max-md:w-full max-md:overflow-x-hidden">
                        <p className="text-gray-900 mb-3 leading-relaxed max-md:mb-2 max-md:text-base max-md:break-words max-md:word-wrap max-md:overflow-wrap-anywhere max-md:w-full">
                          {editingTweet === tweet.tweet_id ? editText : tweet.draft_post}
                        </p>
                      </div>

                      {/* Edit textarea */}
                      {editingTweet === tweet.tweet_id && (
                        <div className="mb-3 max-md:w-full max-md:overflow-x-hidden">
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent max-md:p-2 max-md:text-base max-md:min-h-[44px] max-md:w-full"
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
                      )}

                      {/* Action buttons */}
                      {editingTweet !== tweet.tweet_id && (
                        <div className="flex space-x-2 mt-3 pt-3 border-t border-gray-100 max-md:flex-wrap max-md:gap-2 max-md:mt-2 max-md:pt-2 max-md:w-full max-md:overflow-x-hidden">
                          <button
                            onClick={() => handleRepurposeAction(tweet.tweet_id, 'confirm')}
                            disabled={loading}
                            className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                          >
                            Post
                          </button>
                          <button
                            onClick={() => startEdit(tweet)}
                            disabled={loading}
                            className="px-4 py-1.5 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-200 text-gray-700 font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleRepurposeAction(tweet.tweet_id, 'cancel')}
                            disabled={loading}
                            className="px-4 py-1.5 border border-gray-300 hover:bg-gray-50 disabled:bg-gray-200 text-gray-700 font-semibold rounded-full text-sm transition-colors max-md:px-4 max-md:text-base max-md:min-h-[44px]"
                          >
                            Delete
                          </button>
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

export default RepurposedTweets 