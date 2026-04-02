import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import AlertBanner from './components/AlertBanner';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EquipmentDetail from './pages/EquipmentDetail';
import Alerts from './pages/Alerts';
import WorkOrders from './pages/WorkOrders';
import Logs from './pages/Logs';
import { useWebSocket } from './hooks/useWebSocket';

function AppLayout() {
  const ws = useWebSocket();

  useEffect(() => {
    document.documentElement.classList.remove('dark');
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar connected={ws.connected} />
      <AlertBanner latestAlert={ws.latestAlert} onClose={() => ws.setLatestAlert(null)} />
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <Outlet context={{ ws }} />
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
    </BrowserRouter>
  );
}
