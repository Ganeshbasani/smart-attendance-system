import React, { useState, useEffect, createContext, useContext } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';

// Components
import Home from './components/Home';
import Login from './components/Login';
import Register from './components/Register';
import FaceCapture from './components/FaceCapture';
import MarkAttendance from './components/MarkAttendance';
import AdminDashboard from './components/AdminDashboard';
import StudentDashboard from './components/StudentDashboard';
import TeacherDashboard from './components/TeacherDashboard';
import AcademicManagement from './components/AcademicManagement';
import SettingsPage from './components/SettingsPage';
import UserProfile from './components/UserProfile';
import UserAttendance from './components/UserAttendance';
import Navbar from './components/Navbar';
import ErrorBoundary from './components/ErrorBoundary';

// Create Auth Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Layout component - adds top padding for fixed navbar on non-home pages
const AppLayout = ({ children }) => {
  const location = useLocation();
  const isHome = location.pathname === '/';
  
  return (
    <Box sx={{ pt: isHome ? 0 : '72px' }}>
      {children}
    </Box>
  );
};

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on app start
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error('Error parsing user data:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const login = (userData, token) => {
    setUser(userData);
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const authValue = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
    token: localStorage.getItem('token')
  };

  const isAdmin = user?.role === 'admin';
  const isTeacher = user?.role === 'teacher';
  const isStudent = user?.role === 'student' || user?.role === 'user';

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        Loading...
      </Box>
    );
  }

  return (
    <AuthContext.Provider value={authValue}>
      {/* A crash anywhere below shows a styled fallback instead of a
          white screen; the error is logged, never shown to the user. */}
      <ErrorBoundary>
        <AppLayout>
          <Navbar />
          <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Home />} />
          <Route 
            path="/login" 
            element={user ? <Navigate to="/dashboard" /> : <Login />} 
          />
          <Route 
            path="/register" 
            element={user ? <Navigate to="/dashboard" /> : <Register />} 
          />
          
          {/* Protected Routes - Admin Only */}
          <Route 
            path="/admin" 
            element={user && isAdmin ? <AdminDashboard /> : <Navigate to="/login" />} 
          />
          <Route
            path="/admin/academic"
            element={user && isAdmin ? <AcademicManagement /> : <Navigate to="/login" />}
          />

          {/* Role portals */}
          <Route
            path="/teacher"
            element={user && isTeacher ? <TeacherDashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/student"
            element={user && isStudent ? <StudentDashboard /> : <Navigate to="/login" />}
          />
          <Route
            path="/settings"
            element={user ? <SettingsPage /> : <Navigate to="/login" />}
          />
          
          {/* Protected Routes - All Users */}
          <Route 
            path="/dashboard" 
            element={user ? (isAdmin ? <AdminDashboard /> : (isTeacher ? <TeacherDashboard /> : <StudentDashboard />)) : <Navigate to="/login" />} 
          />
          <Route 
            path="/profile" 
            element={user ? <UserProfile /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/attendance" 
            element={user ? <UserAttendance /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/face-capture" 
            element={user ? <FaceCapture /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/mark-attendance" 
            element={<MarkAttendance />} 
          />
          
          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </AppLayout>
      </ErrorBoundary>
    </AuthContext.Provider>
  );
}

export default App; 