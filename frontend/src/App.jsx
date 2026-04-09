import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import AlertBanner from './components/AlertBanner';
import { useWebSocket } from './hooks/useWebSocket';

const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const EquipmentDetail = lazy(() => import('./pages/EquipmentDetail'));
const Alerts = lazy(() => import('./pages/Alerts'));
const WorkOrders = lazy(() => import('./pages/WorkOrders'));
const Logs = lazy(() => import('./pages/Logs'));

function RouteFallback() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
      Loading page...
    </div>
  );
}

function AppLayout() {
  const ws = useWebSocket();

  useEffect(() => {
    document.documentElement.classList.remove('dark');
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar connected={ws.connected} />
      <AlertBanner latestAlert={ws.latestAlert} onClose={() => ws.setLatestAlert(null)} />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Suspense fallback={<RouteFallback />}>
          <Outlet context={{ ws }} />
        </Suspense>
      </main>
    </div>
  );
}

function ProtectedRoute() {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/equipment/:id" element={<EquipmentDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/workorders" element={<WorkOrders />} />
            <Route path="/logs" element={<Logs />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
