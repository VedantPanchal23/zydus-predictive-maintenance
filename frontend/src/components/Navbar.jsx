import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, Activity } from 'lucide-react';

export default function Navbar({ connected }) {
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  const navLinks = [
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'Alerts', path: '/alerts' },
    { name: 'Work Orders', path: '/workorders' },
    { name: 'Logs', path: '/logs' },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center gap-8">
            <Link to="/dashboard" className="flex items-center gap-2">
              <div className="rounded-md bg-slate-900 p-1.5">
                <Activity className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-slate-900">
                Zydus Maintenance
              </span>
            </Link>

            <div className="flex max-w-[55vw] gap-2 overflow-x-auto">
              {navLinks.map((link) => {
                const isActive = location.pathname.startsWith(link.path);
                return (
                  <Link
                    key={link.name}
                    to={link.path}
                    className={`rounded-md px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    {link.name}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5">
              <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
              <span className="text-xs font-medium text-slate-700">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-md p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
