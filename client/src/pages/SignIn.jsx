import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function SignIn() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { login } = useAuth()

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await login(formData)
      
      if (result.success) {
        console.log('Authentication successful:', result.data)
        navigate('/dashboard')
      } else {
        setError(result.error)
      }
    } catch (err) {
      setError('Network error. Please try again.')
      console.error('Authentication error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 max-md:px-4 max-md:py-8">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 max-md:p-6">
          <div className="text-center mb-8 max-md:mb-6">
            <h1 className="text-2xl font-semibold text-gray-900 mb-2 max-md:text-xl">Sign in to Twitter Growth</h1>
            <p className="text-gray-600 text-sm">Enter your details to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-gray-900 placeholder-gray-500 max-md:px-3 max-md:text-base"
                placeholder="Email"
              />
            </div>

            <div>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-gray-900 placeholder-gray-500 max-md:px-3 max-md:text-base"
                placeholder="Password"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-md:p-3">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-sky-400 hover:bg-sky-500 disabled:bg-sky-300 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center text-lg max-md:py-4 max-md:text-base"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <div className="mt-8 text-center max-md:mt-6">
            <p className="text-gray-600 text-sm">
              Don't have an account? Just enter your email and password to create one!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SignIn 