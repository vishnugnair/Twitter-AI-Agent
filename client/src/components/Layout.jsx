import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Navigation } from './Navigation';
import { MessageSquare, Target, Menu, X, Sparkles, Settings, BarChart3, Home } from 'lucide-react';

const Layout = () => {
  const location = useLocation();
  const userName = location.state?.name || 'User';
  
  // State for managing action buttons
  const [actionButtons, setActionButtons] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchComplete, setFetchComplete] = useState(false);
  
  // Mobile sidebar state
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  // Function to get buttons based on current route
  const getContextualButtons = () => {
    if (location.pathname === '/dashboard/top-tweets') {
      return [
        {
          id: 'view-tweets',
          label: 'View Tweets with Drafted Replies',
          action: () => {
            // This will be handled by the page component
            window.dispatchEvent(new CustomEvent('viewTweets'));
          }
        },
        {
          id: 'fetch-tweets',
          label: fetchComplete ? '✅ Fetched & Drafted' : 'Fetch Top Tweets',
          action: () => {
            // This will be handled by the page component
            window.dispatchEvent(new CustomEvent('fetchTweets'));
          }
        }
      ];
    } else if (location.pathname === '/dashboard/target-user-tweets') {
      return [
        {
          id: 'view-target-tweets',
          label: 'View Tweets with Drafted Replies',
          action: () => {
            window.dispatchEvent(new CustomEvent('viewTargetTweets'));
          }
        },
        {
          id: 'fetch-target-tweets',
          label: fetchComplete ? '✅ Fetched & Drafted' : 'Fetch Target User Tweets',
          action: () => {
            window.dispatchEvent(new CustomEvent('fetchTargetTweets'));
          }
        }
      ];
    } else if (location.pathname === '/dashboard/repurposed-tweets') {
      return [
        {
          id: 'view-repurposed',
          label: 'View Drafted Tweet Ideas',
          action: () => {
            window.dispatchEvent(new CustomEvent('viewRepurposed'));
          }
        }
      ];
    }
    return [];
  };

  // Update buttons when route changes or fetchComplete changes
  useEffect(() => {
    setActionButtons(getContextualButtons());
  }, [location.pathname, fetchComplete]);

  // Listen for loading state changes from page components
  useEffect(() => {
    const handleLoadingState = (e) => {
      setLoading(e.detail.loading);
    };

    const handleFetchComplete = (e) => {
      setFetchComplete(e.detail.complete);
    };

    window.addEventListener('loadingStateChange', handleLoadingState);
    window.addEventListener('fetchCompleteChange', handleFetchComplete);
    return () => {
      window.removeEventListener('loadingStateChange', handleLoadingState);
      window.removeEventListener('fetchCompleteChange', handleFetchComplete);
    };
  }, []);

  // Reset fetch complete status when route changes
  useEffect(() => {
    setFetchComplete(false);
  }, [location.pathname]);

  // Close mobile menu when route changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const headerNavItems = [
    { path: '/dashboard/top-tweets', icon: MessageSquare, label: 'Top Tweets & Replies' },
    { path: '/dashboard/target-user-tweets', icon: Target, label: 'Target User Tweets & Replies' },
  ];

  // Get current page title for mobile
  const getCurrentPageTitle = () => {
    switch (location.pathname) {
      case '/dashboard/top-tweets':
        return { title: 'Top Tweets & Replies', icon: MessageSquare };
      case '/dashboard/target-user-tweets':
        return { title: 'Target User Tweets & Replies', icon: Target };
      case '/dashboard/repurposed-tweets':
        return { title: 'Tweet Ideas', icon: Sparkles };
      case '/dashboard/settings':
        return { title: 'Settings', icon: Settings };
      case '/dashboard/analytics':
        return { title: 'Analytics', icon: BarChart3 };
      default:
        return { title: 'Feed', icon: Home };
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-7xl mx-auto min-h-screen shadow-sm max-md:max-w-none max-md:shadow-none">
        <div className="flex max-md:block">
          {/* Mobile Menu Overlay */}
          {isMobileMenuOpen && (
            <div className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-40" onClick={() => setIsMobileMenuOpen(false)} />
          )}
          
          {/* Left Sidebar - Navigation - Keep original desktop styling */}
          <div className={`
            w-64 border-r border-gray-200 sticky top-0 h-screen overflow-y-auto bg-white
            ${isMobileMenuOpen ? 'max-md:translate-x-0' : 'max-md:-translate-x-full'} 
            max-md:fixed max-md:top-0 max-md:left-0 max-md:z-50 max-md:transition-transform max-md:duration-300 max-md:ease-in-out
          `}>
            {/* Mobile Menu Close Button */}
            <div className="md:hidden flex justify-end p-4">
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="p-2 rounded-lg hover:bg-gray-100"
              >
                <X size={24} />
              </button>
            </div>
            <Navigation />
          </div>
          
          {/* Main Content - Responsive width */}
          <div className="w-[750px] border-l border-r border-gray-300 max-md:w-full max-md:border-0">
            {/* Fixed Header - Keep original desktop styling */}
            <div className="sticky top-0 bg-white/80 backdrop-blur border-b border-gray-200 p-4 z-10 max-md:bg-white max-md:border-b-0">
              <div className="flex justify-between items-center max-md:justify-center max-md:relative">
                {/* Mobile Menu Button - Hamburger icon to open */}
                <button
                  onClick={() => setIsMobileMenuOpen(true)}
                  className="md:hidden absolute left-0 p-2 rounded-lg hover:bg-gray-100"
                >
                  <Menu size={24} />
                </button>
                
                {/* Desktop: Navigation buttons - Mobile: Page title */}
                <div className="flex items-center space-x-6 max-md:space-x-2 max-md:flex-1 max-md:justify-center">
                  {/* Desktop navigation buttons */}
                  <div className="md:flex items-center space-x-6 max-md:hidden">
                    {headerNavItems.map((item) => (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                          `flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 hover:bg-gray-100 whitespace-nowrap ${
                            isActive ? 'bg-blue-50 text-blue-600 font-semibold' : 'text-gray-700'
                          }`
                        }
                      >
                        {item.icon && <item.icon size={20} />}
                        <span className="text-lg">{item.label}</span>
                      </NavLink>
                    ))}
                  </div>
                  
                  {/* Mobile page title with icon - centered */}
                  <div className="md:hidden flex items-center space-x-2">
                    {(() => {
                      const currentPage = getCurrentPageTitle();
                      const IconComponent = currentPage.icon;
                      return (
                        <>
                          <IconComponent size={20} className="text-gray-700" />
                          <h1 className="text-lg font-semibold text-gray-900">{currentPage.title}</h1>
                        </>
                      );
                    })()}
                  </div>
                </div>
              </div>
            </div>

            {/* Mobile Action Buttons - positioned under header, above content */}
            {actionButtons.length > 0 && (
              <div className="md:hidden bg-gray-50 border-b border-gray-200 p-3">
                <div className="flex flex-col gap-2 items-center">
                  {actionButtons.map((button) => (
                    <button
                      key={button.id}
                      onClick={button.action}
                      disabled={loading}
                      className="w-full max-w-sm flex items-center justify-center px-4 py-2 bg-sky-400 hover:bg-sky-500 disabled:bg-sky-300 text-white font-medium rounded-lg transition-colors text-base min-h-[44px]"
                    >
                      {loading && (
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      )}
                      <span className="text-center">{button.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Page Content */}
            <div className="flex-1 max-md:overflow-x-hidden">
              <Outlet />
            </div>
          </div>
        </div>
      </div>

      {/* Desktop Action Buttons - Keep original desktop positioning */}
      {actionButtons.length > 0 && (
        <div className={`
          fixed top-5 z-20 hidden md:block
          ${
            location.pathname === '/dashboard/repurposed-tweets' ? 'right-32' :
            location.pathname === '/dashboard/target-user-tweets' ? 'right-2' :
            location.pathname === '/dashboard/top-tweets' ? 'right-8' : 'right-32'
          }
        `}>
          <div className="flex flex-row gap-3">
            {actionButtons.map((button) => (
              <button
                key={button.id}
                onClick={button.action}
                disabled={loading}
                className="flex items-center justify-center px-3 py-2 bg-sky-400 hover:bg-sky-500 disabled:bg-sky-300 text-white font-medium rounded-full transition-colors shadow-sm text-xs"
              >
                {loading && (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1"></div>
                )}
                <span className="text-center">{button.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Layout; 