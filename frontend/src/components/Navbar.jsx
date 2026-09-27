import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard,
  Calendar,
  Package,
  History,
  QrCode,
  LogOut,
  Hotel,
  Building2,
  Users,
  CheckSquare,
  RotateCcw,
  Sparkles,
  CloudSun,
  Menu,
  X
} from 'lucide-react';
import { demoAPI } from '../services/api';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [guestAccount, setGuestAccount] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('guestAccount') || 'null');
    } catch {
      return null;
    }
  });

  useEffect(() => {
    const syncGuestAccount = () => {
      try {
        setGuestAccount(JSON.parse(sessionStorage.getItem('guestAccount') || 'null'));
      } catch {
        setGuestAccount(null);
      }
    };
    window.addEventListener('guest-session-changed', syncGuestAccount);
    window.addEventListener('storage', syncGuestAccount);
    return () => {
      window.removeEventListener('guest-session-changed', syncGuestAccount);
      window.removeEventListener('storage', syncGuestAccount);
    };
  }, []);

  const handleLogout = () => {
    if (guestAccount) {
      sessionStorage.removeItem('guestToken');
      sessionStorage.removeItem('guestAccount');
      setGuestAccount(null);
      navigate('/login');
      return;
    }
    logout();
    navigate('/login');
  };

  const handleResetDemo = async () => {
    if (window.confirm('Reset demo database to fresh realistic operational data?')) {
      setIsResetting(true);
      try {
        await demoAPI.reset();
        alert('Database reset successfully! Reloading...');
        window.location.reload();
      } catch (err) {
        alert('Failed to reset demo: ' + (err.response?.data?.detail || err.message));
      } finally {
        setIsResetting(false);
      }
    }
  };

  // Determine navigation items based on user role
  const getNavLinks = () => {
    const links = [];

    if (!user) {
      return [];
    }

    // Role-specific main dashboard
    if (user.role === 'MANAGER') {
      links.push({ name: 'Manager HQ', path: '/dashboard', icon: LayoutDashboard });
      links.push({ name: '7-Day Forecast', path: '/forecast', icon: Calendar });
      links.push({ name: 'Inventory & POs', path: '/inventory', icon: Package });
      links.push({ name: 'Activity Log', path: '/activity-log', icon: History });
      links.push({ name: 'Guest Intelligence', path: '/guest-intelligence', icon: Sparkles });
      links.push({ name: 'Weather & Digital Twin', path: '/weather', icon: CloudSun });
    } else if (user.role === 'FRONT_DESK') {
      links.push({ name: 'Front Desk', path: '/front-desk', icon: Building2 });
      links.push({ name: 'Guest Requests', path: '/guest-request', icon: QrCode });
    } else if (user.role === 'DEPARTMENT_HEAD') {
      links.push({ name: 'Department Ops', path: '/department', icon: Users });
      links.push({ name: 'Forecast', path: '/forecast', icon: Calendar });
      links.push({ name: 'Weather & Digital Twin', path: '/weather', icon: CloudSun });
    } else if (user.role === 'STAFF') {
      links.push({ name: 'My Tasks', path: '/staff', icon: CheckSquare });
    }

    return links;
  };

  const navLinks = getNavLinks();

  return (
    <nav className="bg-white border-b border-ivory-300 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-9 h-9 rounded-lg bg-brass-50 border border-brass-200 flex items-center justify-center shadow-card">
                <Hotel className="w-5 h-5 text-brass-700" />
              </div>
              <div>
                <span className="text-lg font-bold text-forest-900">
                  Resort 360
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-sage-50 text-forest-900 border border-sage-200'
                      : 'text-charcoal-600 hover:bg-ivory-100 hover:text-forest-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.name}</span>
                </Link>
              );
            })}
          </div>

          {/* Right Side - User Info & Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {user || guestAccount ? (
              <>
                {user?.role === 'MANAGER' && import.meta.env.DEV && (
                  <button
                    onClick={handleResetDemo}
                    disabled={isResetting}
                    className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded transition"
                    title="Reset database to fresh demo operational dataset"
                  >
                    <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
                    <span>Reset Demo</span>
                  </button>
                )}

                <div className="flex items-center space-x-2 pl-2 border-l border-ivory-300">
                  <div className="w-8 h-8 rounded-full bg-sage-50 border border-sage-200 flex items-center justify-center text-xs font-bold text-forest-900">
                    {(guestAccount?.name || user.name).split(' ').map((n) => n[0]).join('')}
                  </div>
                  <div className="text-left text-xs">
                    <p className="font-semibold text-charcoal-900">{guestAccount?.name || user.name}</p>
                    <p className="text-charcoal-500 text-[10px] uppercase">{guestAccount ? 'GUEST' : user.role.replace('_', ' ')}</p>
                  </div>
                </div>

                <button
                  onClick={handleLogout}
                  className="p-1.5 text-charcoal-500 hover:text-status-critical hover:bg-status-criticalBg rounded transition"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            ) : null}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-charcoal-700 hover:text-charcoal-900"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-ivory-300 px-4 pt-2 pb-4 space-y-1 shadow-md">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-semibold transition ${
                  isActive ? 'bg-forest-50 text-forest-900 border border-forest-200' : 'text-charcoal-700 hover:bg-ivory-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{link.name}</span>
              </Link>
            );
          })}
          {(user || guestAccount) && (
            <div className="pt-4 mt-2 border-t border-ivory-200 flex justify-between items-center">
              <div className="text-xs text-charcoal-900">
                <p className="font-bold">{guestAccount?.name || user.name}</p>
                <p className="text-charcoal-500 font-medium">{guestAccount ? 'GUEST' : user.role.replace('_', ' ')}</p>
              </div>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-xs font-bold text-red-700 bg-red-50 rounded-lg border border-red-200 hover:bg-red-100"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      )}
    </nav>
  );
};

