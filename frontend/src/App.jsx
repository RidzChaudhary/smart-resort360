import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Navbar } from './components/Navbar';
import { Login } from './pages/Login';
import { ManagerDashboard } from './pages/ManagerDashboard';
import { FrontDeskDashboard } from './pages/FrontDeskDashboard';
import { DepartmentDashboard } from './pages/DepartmentDashboard';
import { StaffDashboard } from './pages/StaffDashboard';
import { Forecast } from './pages/Forecast';
import { Inventory } from './pages/Inventory';
import { ActivityLog } from './pages/ActivityLog';
import { GuestRequest } from './pages/GuestRequest';
import { GuestIntelligence } from './pages/GuestIntelligence';
import { GuestExperiences } from './pages/GuestExperiences';
import { WeatherIntelligence } from './pages/WeatherIntelligence';

// Protected Route Wrapper
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-sky-400">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
};

// Main App Router
function AppRouter() {
  const { user } = useAuth();

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <Navbar />
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login />} />
          <Route path="/guest-request" element={<GuestRequest />} />
          <Route path="/guest-experiences" element={<GuestExperiences />} />

          {/* Manager Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRoles={['MANAGER']}>
                <ManagerDashboard />
              </ProtectedRoute>
            }
          />

          {/* Front Desk Routes */}
          <Route
            path="/front-desk"
            element={
              <ProtectedRoute allowedRoles={['FRONT_DESK']}>
                <FrontDeskDashboard />
              </ProtectedRoute>
            }
          />

          {/* Department Head Routes */}
          <Route
            path="/department"
            element={
              <ProtectedRoute allowedRoles={['DEPARTMENT_HEAD']}>
                <DepartmentDashboard />
              </ProtectedRoute>
            }
          />

          {/* Staff Routes */}
          <Route
            path="/staff"
            element={
              <ProtectedRoute allowedRoles={['STAFF']}>
                <StaffDashboard />
              </ProtectedRoute>
            }
          />

          {/* Forecast (Manager + Dept Heads) */}
          <Route
            path="/forecast"
            element={
              <ProtectedRoute allowedRoles={['MANAGER', 'DEPARTMENT_HEAD']}>
                <Forecast />
              </ProtectedRoute>
            }
          />

          {/* Inventory (Manager) */}
          <Route
            path="/inventory"
            element={
              <ProtectedRoute allowedRoles={['MANAGER']}>
                <Inventory />
              </ProtectedRoute>
            }
          />

          {/* Activity Log (Manager) */}
          <Route
            path="/activity-log"
            element={
              <ProtectedRoute allowedRoles={['MANAGER']}>
                <ActivityLog />
              </ProtectedRoute>
            }
          />

          <Route
            path="/guest-intelligence"
            element={
              <ProtectedRoute allowedRoles={['MANAGER']}>
                <GuestIntelligence />
              </ProtectedRoute>
            }
          />

          <Route
            path="/weather"
            element={
              <ProtectedRoute allowedRoles={['MANAGER', 'DEPARTMENT_HEAD']}>
                <WeatherIntelligence />
              </ProtectedRoute>
            }
          />

          {/* Default Redirect */}
          <Route
            path="/"
            element={
              user ? (
                user.role === 'MANAGER' ? (
                  <Navigate to="/dashboard" />
                ) : user.role === 'FRONT_DESK' ? (
                  <Navigate to="/front-desk" />
                ) : user.role === 'DEPARTMENT_HEAD' ? (
                  <Navigate to="/department" />
                ) : user.role === 'STAFF' ? (
                  <Navigate to="/staff" />
                ) : (
                  <Navigate to="/login" />
                )
              ) : (
                <Navigate to="/login" />
              )
            }
          />

          {/* 404 Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;
