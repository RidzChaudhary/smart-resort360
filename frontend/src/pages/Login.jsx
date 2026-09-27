import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Sparkles, Shield, UserCheck, ArrowRight, Lock, Mail, ChevronDown, Building2, Users, BedDouble, Wrench, Utensils, Package, ClipboardCheck } from 'lucide-react';
import { guestIntelligenceAPI } from '../services/api';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [departmentHeadsOpen, setDepartmentHeadsOpen] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e?.preventDefault();
    setError('');
    setIsLoading(true);

    const result = await login(email, password);
    setIsLoading(false);

    if (result.success) {
      const role = result.user.role;
      if (role === 'MANAGER') navigate('/dashboard');
      else if (role === 'FRONT_DESK') navigate('/front-desk');
      else if (role === 'DEPARTMENT_HEAD') navigate('/department');
      else if (role === 'STAFF') navigate('/staff');
      else navigate('/dashboard');
    } else {
      setError(result.error);
    }
  };

  const handleQuickLogin = async (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError('');
    setIsLoading(true);
    if (demoEmail === 'guest.demo@resort360.com') {
      try {
        const response = await guestIntelligenceAPI.login(demoEmail, demoPassword);
        sessionStorage.setItem('guestToken', response.data.access_token);
        sessionStorage.setItem('guestAccount', JSON.stringify(response.data.guest));
        window.dispatchEvent(new Event('guest-session-changed'));
        navigate('/guest-experiences');
      } catch (requestError) {
        const errorMsg =
          requestError.response?.data?.detail ||
          (!requestError.response
            ? 'Cannot connect to backend API server. Please check if the backend service is running.'
            : 'Guest demo login failed.');
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
      return;
    }
    const result = await login(demoEmail, demoPassword);
    setIsLoading(false);
    if (result.success) {
      const role = result.user.role;
      if (role === 'MANAGER') navigate('/dashboard');
      else if (role === 'FRONT_DESK') navigate('/front-desk');
      else if (role === 'DEPARTMENT_HEAD') navigate('/department');
      else if (role === 'STAFF') navigate('/staff');
    } else {
      setError(result.error);
    }
  };

  const demoAccounts = [
    {
      role: 'General Manager',
      email: 'manager@resort360.com',
      password: 'password123',
      desc: 'Full operations oversight, AI recommendation approvals, and closed-loop execution',
      badge: 'MANAGER',
      icon: Shield,
      accent: 'border-l-brass-600',
      iconBg: 'bg-brass-100',
      iconColor: 'text-brass-800',
    },
    {
      role: 'Front Desk Lead',
      email: 'frontdesk@resort360.com',
      password: 'password123',
      desc: 'Arrivals, departures, early-checkin flags & room readiness',
      badge: 'FRONT_DESK',
      icon: Building2,
      accent: 'border-l-forest-600',
      iconBg: 'bg-forest-100',
      iconColor: 'text-forest-800',
    },
    {
      role: 'Department Head',
      badge: '4 DEPARTMENTS',
      desc: 'Choose a department head account',
      icon: Users,
      accent: 'border-l-forest-500',
      iconBg: 'bg-forest-100',
      iconColor: 'text-forest-800',
      accounts: [
        {
          role: 'Housekeeping Head',
          email: 'housekeeping.head@resort360.com',
          password: 'password123',
          icon: BedDouble,
          iconBg: 'bg-forest-50',
          iconColor: 'text-forest-800',
        },
        {
          role: 'Maintenance Head',
          email: 'maintenance.head@resort360.com',
          password: 'password123',
          icon: Wrench,
          iconBg: 'bg-red-50',
          iconColor: 'text-red-700',
        },
        {
          role: 'Food & Beverage Head',
          email: 'fb.head@resort360.com',
          password: 'password123',
          icon: Utensils,
          iconBg: 'bg-brass-50',
          iconColor: 'text-brass-800',
        },
        {
          role: 'Inventory Head',
          email: 'inventory.head@resort360.com',
          password: 'password123',
          icon: Package,
          iconBg: 'bg-forest-50',
          iconColor: 'text-forest-800',
        },
      ],
    },
    {
      role: 'Operations Staff',
      email: 'staff.elena@resort360.com',
      password: 'password123',
      desc: 'Task execution, progress tracking, shift completion',
      badge: 'STAFF',
      icon: ClipboardCheck,
      accent: 'border-l-forest-700',
      iconBg: 'bg-forest-100',
      iconColor: 'text-forest-800',
    },
    {
      role: 'Guest',
      email: 'guest.demo@resort360.com',
      password: 'guest123',
      desc: 'Recommendations, service requests, activities, and feedback',
      badge: 'GUEST',
      icon: Sparkles,
      accent: 'border-l-brass-600',
      iconBg: 'bg-brass-100',
      iconColor: 'text-brass-800',
    }
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl w-full">
        <div className="mb-8 max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-forest-100 border border-forest-200 text-forest-800 text-xs font-bold mb-4 shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-forest-700" />
              <span>AI Operations Co-Pilot</span>
            </div>
            <h1 className="text-3xl font-extrabold text-charcoal-900 tracking-tight">
              Smart Resort <span className="text-forest-800">360</span>
            </h1>
            <p className="mt-2 text-sm text-charcoal-600 leading-relaxed font-medium">
              Predictive operations management and closed-loop decision orchestration for luxury resorts.
            </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Quick Demo Access Roles */}
          <div className="surface border border-ivory-300 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-charcoal-800 flex items-center gap-1.5">
                <UserCheck className="w-4 h-4 text-forest-700" />
                1-Click Demo Login
              </span>
              <span className="text-[11px] text-charcoal-500 font-semibold">Pick any role to evaluate</span>
            </div>

            <div className="space-y-2.5">
              {demoAccounts.map((acc) => {
                const Icon = acc.icon;
                return acc.accounts ? (
                <div key={acc.role}>
                  <button
                    type="button"
                    onClick={() => setDepartmentHeadsOpen((open) => !open)}
                    aria-expanded={departmentHeadsOpen}
                    className={`w-full text-left p-3 rounded-xl bg-white hover:bg-ivory-50 border border-ivory-300 border-l-4 ${acc.accent} shadow-sm transition-all flex items-center justify-between group`}
                  >
                    <div className="flex min-w-0 items-center gap-3 pr-2">
                      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${acc.iconBg}`}><Icon className={`h-4.5 w-4.5 ${acc.iconColor}`} /></span>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-charcoal-900 group-hover:text-forest-800">{acc.role}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-ivory-100 text-charcoal-700 border border-ivory-300 rounded-md font-mono">{acc.badge}</span>
                        </div>
                        <p className="text-xs text-charcoal-600 mt-0.5 font-medium">{acc.desc}</p>
                      </div>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-charcoal-500 transition-transform flex-shrink-0 ${departmentHeadsOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {departmentHeadsOpen && (
                    <div className="ml-3 mt-1.5 pl-3 border-l-2 border-ivory-300 space-y-1.5" role="group" aria-label="Department Head accounts">
                      {acc.accounts.map((head) => {
                        const HeadIcon = head.icon;
                        return (
                        <button
                          key={head.email}
                          type="button"
                          onClick={() => handleQuickLogin(head.email, head.password)}
                          disabled={isLoading}
                          className={`w-full text-left px-3 py-2.5 rounded-lg ${head.iconBg} hover:bg-ivory-100 border border-ivory-300 transition-colors flex items-center justify-between group disabled:opacity-60 shadow-sm`}
                        >
                          <span className="flex items-center gap-2.5 text-xs font-bold text-charcoal-900 group-hover:text-forest-800">
                            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-white shadow-xs">
                              <HeadIcon className={`h-3.5 w-3.5 ${head.iconColor}`} />
                            </span>
                            {head.role}
                          </span>
                          <ArrowRight className="w-4 h-4 text-charcoal-500 group-hover:text-forest-800 flex-shrink-0" />
                        </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => handleQuickLogin(acc.email, acc.password)}
                  disabled={isLoading}
                  className={`w-full text-left p-3 rounded-xl bg-white hover:bg-ivory-50 border border-ivory-300 border-l-4 ${acc.accent} shadow-sm transition-all flex items-center justify-between group disabled:opacity-60`}
                >
                  <div className="flex min-w-0 items-center gap-3 pr-2">
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${acc.iconBg}`}><Icon className={`h-4.5 w-4.5 ${acc.iconColor}`} /></span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-charcoal-900 group-hover:text-forest-800">{acc.role}</span>
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-ivory-100 text-charcoal-700 border border-ivory-300 rounded-md font-mono">{acc.badge}</span>
                      </div>
                      <p className="text-xs text-charcoal-600 mt-0.5 font-medium">{acc.desc}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-charcoal-500 group-hover:text-forest-800 group-hover:translate-x-0.5 transition-transform flex-shrink-0" />
                </button>
              );})}
            </div>
          </div>

          {/* Traditional Login Form */}
          <div className="surface border border-ivory-300 rounded-2xl p-8 shadow-sm">
          <h2 className="text-xl font-bold text-charcoal-900 mb-1">Sign In to Dashboard</h2>
          <p className="text-xs text-charcoal-600 mb-6 font-medium">Enter your internal resort credentials</p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 font-bold">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="manager@resort360.com"
                  className="w-full bg-white border border-ivory-300 rounded-lg pl-9 pr-3 py-2.5 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-charcoal-700 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white border border-ivory-300 rounded-lg pl-9 pr-3 py-2.5 text-sm text-charcoal-900 placeholder-charcoal-400 focus:outline-none focus:ring-2 focus:ring-forest-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-forest-800 hover:bg-forest-900 text-white font-bold rounded-lg shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              <Shield className="w-4 h-4" />
              <span>{isLoading ? 'Authenticating...' : 'Sign In'}</span>
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-ivory-200 text-center">
            <p className="text-xs text-charcoal-600 font-medium">
              Evaluating as Guest?{' '}
              <a href="/guest-request" className="text-forest-800 hover:underline font-bold">
                Submit QR Guest Request →
              </a>
            </p>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
};

