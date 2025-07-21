import { useLocation } from 'react-router-dom'

function DashBoards() {
  const location = useLocation()
  const userName = location.state?.name || 'User'

  return (
    <div className="p-6">
      {/* Central area - now blank */}
      <div className="flex items-center justify-center h-96 text-gray-500">
        {/* This area is intentionally left blank as requested */}
        </div>
    </div>
  )
}

export default DashBoards
