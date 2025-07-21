import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, BarChart3, Settings, Sparkles, MessageSquare, Target } from 'lucide-react';

export const Navigation = () => {
  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Feed', end: true },
    { path: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/dashboard/settings', icon: Settings, label: 'Settings' },
    { path: '/dashboard/repurposed-tweets', icon: Sparkles, label: 'Tweet Ideas' },
  ];

  // Mobile-only navigation items for tweet sections
  const mobileOnlyNavItems = [
    { path: '/dashboard/top-tweets', icon: MessageSquare, label: 'Top Tweets & Replies' },
    { path: '/dashboard/target-user-tweets', icon: Target, label: 'Target User Tweets & Replies' },
  ];

  return (
    <div className="p-4 max-md:p-3 max-md:pt-0">
      {/* Logo */}
      <div className="mb-8 max-md:mb-4">
        <div className="w-8 h-8 flex items-center justify-center max-md:w-6 max-md:h-6">
          {/* X (Twitter) Icon */}
          <svg className="w-6 h-6 text-gray-700 max-md:w-5 max-md:h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
          </svg>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="space-y-2 max-md:space-y-1">
        {/* Mobile-only tweet navigation items */}
        <div className="md:hidden">
          {mobileOnlyNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 p-2 rounded-full transition-all duration-200 hover:bg-gray-100 ${
                  isActive ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                }`
              }
            >
              <item.icon size={20} className="min-w-[20px]" />
              <span className="text-lg font-medium">{item.label}</span>
            </NavLink>
          ))}
          {/* Divider */}
          <div className="border-t border-gray-200 my-2"></div>
        </div>

        {/* Regular navigation items */}
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center space-x-4 p-3 rounded-full transition-all duration-200 hover:bg-gray-100 max-md:space-x-3 max-md:p-2 ${
                isActive ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
              }`
            }
          >
            <item.icon size={24} className="min-w-[24px] max-md:w-5 max-md:h-5 max-md:min-w-[20px]" />
            <span className="text-xl font-medium max-md:text-lg">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}; 