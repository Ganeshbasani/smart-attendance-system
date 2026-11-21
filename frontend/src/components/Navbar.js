import React, { useState, useEffect, useCallback } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Stack,
  useTheme,
  useMediaQuery,
  Divider,
  Badge,
} from '@mui/material';
import {
  MoreVert,
  Notifications,
  LightMode,
  DarkMode,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { useThemeMode } from '../theme/ThemeContext';
import { notificationsAPI } from '../services/api';

const Navbar = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { mode, toggleMode } = useThemeMode();
  const dark = mode === 'dark';
  const roleLabel = (role) => (role === 'admin' ? 'Administrator' : role === 'teacher' ? 'Teacher' : 'Student');
  const [anchorEl, setAnchorEl] = useState(null);
  const [mobileMenuEl, setMobileMenuEl] = useState(null);
  const [scrolled, setScrolled] = useState(false);
  // Notifications (current user only).
  const [notifAnchorEl, setNotifAnchorEl] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [notifLoading, setNotifLoading] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Refresh the unread badge on mount and whenever the route changes (a
  // decision may have happened while the user was elsewhere). Silent by
  // design — a failed poll must never disrupt navigation.
  useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      setNotifications([]);
      return undefined;
    }
    let cancelled = false;
    notificationsAPI
      .unreadCount()
      .then((res) => {
        if (!cancelled) setUnreadCount(res.data?.count ?? 0);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user, location.pathname]);

  const handleNotifOpen = (event) => {
    setNotifAnchorEl(event.currentTarget);
    setNotifLoading(true);
    notificationsAPI
      .list({ limit: 10 })
      .then((res) => setNotifications(res.data || []))
      .catch(() => setNotifications([]))
      .finally(() => setNotifLoading(false));
  };
  const handleNotifClose = () => setNotifAnchorEl(null);

  const handleNotifMarkRead = async (id) => {
    // Optimistic: flip locally, then reconcile with the server.
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
    try {
      await notificationsAPI.markRead(id);
    } catch {
      // Re-sync the badge if the server rejected it.
      notificationsAPI
        .unreadCount()
        .then((res) => setUnreadCount(res.data?.count ?? 0))
        .catch(() => {});
    }
  };

  const handleNotifMarkAllRead = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await notificationsAPI.markAllRead();
    } catch {
      notificationsAPI
        .unreadCount()
        .then((res) => setUnreadCount(res.data?.count ?? 0))
        .catch(() => {});
    }
  };

  const handleMenuOpen = (event) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);
  const handleMobileMenuOpen = (event) => setMobileMenuEl(event.currentTarget);
  const handleMobileMenuClose = () => setMobileMenuEl(null);

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleMenuClose();
  };

  const navigateToPage = (path) => {
    navigate(path);
    handleMenuClose();
    handleMobileMenuClose();
  };

  // Scrolls to a landing-page section. Returns false when the section isn't
  // in the DOM (i.e. we're not on the home page).
  const scrollToSection = useCallback((sectionId) => {
    const element = document.getElementById(sectionId);
    if (!element) return false;

    const navbarHeight = 80; // Approximate navbar height
    const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition - navbarHeight;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth',
    });
    return true;
  }, []);

  // The Features / How It Works / Industries sections only exist on the home
  // page. From any other route (e.g. /login, /register) navigate home first and
  // hand the target off via router state, then scroll once it has rendered.
  const goToSection = (sectionId) => {
    handleMobileMenuClose();
    if (location.pathname === '/') {
      scrollToSection(sectionId);
    } else {
      navigate('/', { state: { scrollTo: sectionId } });
    }
  };

  // Consume a pending `scrollTo` handed over by a cross-route section link.
  useEffect(() => {
    const target = location.state?.scrollTo;
    if (!target || location.pathname !== '/') return undefined;

    // Home mounts in the same commit, but wait for the section to actually be
    // in the DOM before scrolling rather than assuming it is.
    let frame;
    let attempts = 0;
    const attemptScroll = () => {
      if (scrollToSection(target) || attempts >= 60) {
        // Clear the state so a refresh or back-navigation doesn't re-scroll.
        navigate('/', { replace: true, state: null });
        return;
      }
      attempts += 1;
      frame = requestAnimationFrame(attemptScroll);
    };
    frame = requestAnimationFrame(attemptScroll);

    return () => cancelAnimationFrame(frame);
  }, [location, navigate, scrollToSection]);

  const isActivePage = (path) => location.pathname === path;
  
  // Check if we're on a page that needs a solid navbar
  // Only the home page (/) should have transparent navbar
  const needsSolidNavbar = location.pathname !== '/';
  const shouldShowSolid = scrolled || needsSolidNavbar;

  const navigationItems = [
    { path: '/mark-attendance', label: 'Mark Attendance' },
    ...((user?.role === 'admin' || user?.role === 'teacher')
      ? [{ path: '/live', label: 'Live Session' }] : []),
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/settings', label: 'Settings' },
    ...(user?.role === 'admin' ? [
      { path: '/admin', label: 'Admin' },
      { path: '/admin/academic', label: 'Academic' },
    ] : []),
    ...(user?.role === 'teacher' ? [{ path: '/teacher', label: 'Classes' }] : []),
  ];

  const publicNavigationItems = [
    { label: 'Features', sectionId: 'features' },
    { label: 'How It Works', sectionId: 'how-it-works' },
    { label: 'Industries', sectionId: 'industries' },
  ];

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        background: shouldShowSolid ? (dark ? 'rgba(30,41,59,0.92)' : 'rgba(255,255,255,0.85)') : 'transparent',
        backdropFilter: shouldShowSolid ? 'blur(20px) saturate(180%)' : 'none',
        borderBottom: shouldShowSolid ? (dark ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.06)') : '1px solid transparent',
        color: shouldShowSolid ? (dark ? '#e2e8f0' : '#1a1a1a') : '#ffffff',
        transition: 'all 0.3s ease',
        zIndex: 1100,
      }}
    >
      <Toolbar sx={{ px: { xs: 3, md: 4 }, py: 1.5 }}>
        {/* Logo */}
        <Box
          display="flex"
          alignItems="center"
          sx={{ flexGrow: isMobile ? 1 : 0, cursor: 'pointer' }}
          onClick={() => navigateToPage('/')}
        >
          <Typography variant="h6" fontWeight="700" sx={{ color: shouldShowSolid ? (dark ? '#ffffff' : '#212E46') : '#ffffff', letterSpacing: '-0.02em', fontSize: '1.1rem', transition: 'color 0.3s ease', fontFamily: '"Inter", sans-serif' }}>
            SAS
          </Typography>
        </Box>

        {/* Desktop Navigation */}
        {!isMobile && !user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mx: 6, flexGrow: 1 }}>
            {publicNavigationItems.map((item) => (
              <Button
                key={item.label}
                onClick={() => goToSection(item.sectionId)}
                sx={{
                  px: 3,
                  py: 1.5,
                  borderRadius: '10px',
                  fontWeight: 500,
                  textTransform: 'none',
                  color: shouldShowSolid ? '#64748b' : 'rgba(255,255,255,0.8)',
                  '&:hover': { background: shouldShowSolid ? '#f8fafc' : 'rgba(255,255,255,0.1)', color: shouldShowSolid ? '#0f172a' : '#ffffff' },
                  transition: 'all 0.2s ease',
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>
        )}

        {!isMobile && user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mx: 6, flexGrow: 1 }}>
            {navigationItems.map((item) => (
              <Button
                key={item.path}
                onClick={() => navigateToPage(item.path)}
                sx={{
                  px: 3,
                  py: 1.5,
                  borderRadius: '10px',
                  fontWeight: 500,
                  textTransform: 'none',
                  color: isActivePage(item.path) ? (dark ? '#ffffff' : '#0f172a') : (dark ? '#94a3b8' : '#64748b'),
                  background: isActivePage(item.path) ? (dark ? 'rgba(255,255,255,0.12)' : '#f1f5f9') : 'transparent',
                  '&:hover': { background: dark ? 'rgba(255,255,255,0.08)' : '#f8fafc', color: dark ? '#ffffff' : '#0f172a' },
                  transition: 'all 0.2s ease',
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>
        )}

        {/* User Section */}
        {user ? (
          <Box display="flex" alignItems="center" gap={2}>
            {!isMobile && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <IconButton
                  onClick={toggleMode}
                  aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
                  title={dark ? 'Light theme' : 'Dark theme'}
                  sx={{ p: 1, color: shouldShowSolid ? (dark ? '#cbd5e1' : '#475569') : '#ffffff',
                    '&:hover': { background: dark ? 'rgba(255,255,255,0.12)' : '#f1f5f9' } }}
                >
                  {dark ? <LightMode fontSize="small" /> : <DarkMode fontSize="small" />}
                </IconButton>
                <IconButton
                  onClick={handleNotifOpen}
                  aria-label="Notifications"
                  sx={{
                    p: 1,
                    color: shouldShowSolid ? '#475569' : '#ffffff',
                    '&:hover': { background: shouldShowSolid ? '#f1f5f9' : 'rgba(255,255,255,0.15)' },
                    transition: 'all 0.3s ease',
                  }}
                >
                  <Badge
                    badgeContent={unreadCount}
                    color="error"
                    max={9}
                    sx={{ '& .MuiBadge-badge': { fontSize: '0.65rem', fontWeight: 700 } }}
                  >
                    <Notifications fontSize="small" />
                  </Badge>
                </IconButton>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography variant="body2" fontWeight="600" sx={{ color: shouldShowSolid ? '#0f172a' : '#ffffff', transition: 'color 0.3s ease' }}>
                    {user.full_name.split(' ')[0]}
                  </Typography>
                  <Typography variant="caption" sx={{ color: shouldShowSolid ? '#94a3b8' : 'rgba(255,255,255,0.7)', transition: 'color 0.3s ease' }}>
                    {roleLabel(user.role)}
                  </Typography>
                </Box>
                <IconButton
                  onClick={handleMenuOpen}
                  sx={{ p: 0.5, background: shouldShowSolid ? '#f1f5f9' : 'rgba(255,255,255,0.15)', '&:hover': { background: shouldShowSolid ? '#e2e8f0' : 'rgba(255,255,255,0.25)' }, transition: 'background 0.3s ease' }}
                >
                  <Avatar
                    sx={{
                      width: 36, height: 36,
                      background: 'linear-gradient(135deg, #212E46, #2c3e5a)',
                      fontSize: '0.9rem', fontWeight: 'bold',
                    }}
                  >
                    {user.full_name.charAt(0)}
                  </Avatar>
                </IconButton>
              </Box>
            )}
            {isMobile && (
              <>
                <IconButton
                  onClick={handleNotifOpen}
                  aria-label="Notifications"
                  sx={{
                    color: shouldShowSolid ? '#475569' : '#ffffff',
                    '&:hover': { background: shouldShowSolid ? '#f1f5f9' : 'rgba(255,255,255,0.15)' },
                    transition: 'all 0.3s ease',
                  }}
                >
                  <Badge
                    badgeContent={unreadCount}
                    color="error"
                    max={9}
                    sx={{ '& .MuiBadge-badge': { fontSize: '0.65rem', fontWeight: 700 } }}
                  >
                    <Notifications fontSize="small" />
                  </Badge>
                </IconButton>
                <IconButton
                  onClick={handleMobileMenuOpen}
                  sx={{ background: shouldShowSolid ? '#f1f5f9' : 'rgba(255,255,255,0.15)', color: shouldShowSolid ? '#475569' : '#ffffff', '&:hover': { background: shouldShowSolid ? '#e2e8f0' : 'rgba(255,255,255,0.25)' }, transition: 'all 0.3s ease' }}
                >
                  <MoreVert />
                </IconButton>
              </>
            )}
          </Box>
        ) : (
          <Stack direction="row" spacing={1}>
            {isMobile && (
              <IconButton
                onClick={handleMobileMenuOpen}
                sx={{ color: shouldShowSolid ? '#475569' : '#ffffff', '&:hover': { background: shouldShowSolid ? '#f1f5f9' : 'rgba(255,255,255,0.1)' }, transition: 'all 0.3s ease' }}
              >
                <MoreVert />
              </IconButton>
            )}
            {!isMobile && (
              <>
                <Button
                  onClick={() => navigateToPage('/login')}
                  sx={{ color: shouldShowSolid ? '#64748b' : 'rgba(255,255,255,0.8)', textTransform: 'none', fontWeight: 500, '&:hover': { color: shouldShowSolid ? '#0f172a' : '#ffffff' }, transition: 'color 0.3s ease' }}
                >
                  Sign in
                </Button>
                <Button
                  variant="contained"
                  onClick={() => navigateToPage('/register')}
                  sx={{
                    borderRadius: '10px', textTransform: 'none', fontWeight: 600, px: 3,
                    background: shouldShowSolid ? '#212E46' : '#ffffff', 
                    color: shouldShowSolid ? '#ffffff' : '#212E46', 
                    boxShadow: 'none',
                    fontFamily: '"Inter", sans-serif',
                    '&:hover': { background: shouldShowSolid ? '#2c3e5a' : '#f8fafc', boxShadow: 'none' },
                    transition: 'all 0.3s ease',
                  }}
                >
                  Get Started
                </Button>
              </>
            )}
          </Stack>
        )}

        {/* Desktop User Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          PaperProps={{
            elevation: 0,
            sx: {
              mt: 1, borderRadius: '14px', border: '1px solid #f1f5f9',
              boxShadow: '0 20px 60px rgba(0,0,0,0.08)', minWidth: 240,
              '& .MuiMenuItem-root': {
                px: 3, py: 1.5, borderRadius: '8px', mx: 1, my: 0.5,
                '&:hover': { background: '#f8fafc' },
              },
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <Box sx={{ p: 3, borderBottom: '1px solid #f1f5f9' }}>
            <Box display="flex" alignItems="center" gap={2}>
              <Avatar sx={{ width: 40, height: 40, background: 'linear-gradient(135deg, #212E46, #2c3e5a)', fontSize: '1rem', fontWeight: 'bold' }}>
                {user?.full_name.charAt(0)}
              </Avatar>
              <Box>
                <Typography variant="subtitle2" fontWeight="600" sx={{ color: '#0f172a' }}>
                  {user?.full_name}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                  {user?.email}
                </Typography>
              </Box>
            </Box>
          </Box>
          <MenuItem onClick={() => navigateToPage('/profile')}>
            <Typography fontWeight="500">My Profile</Typography>
          </MenuItem>
          <Divider sx={{ mx: 1, my: 0.5 }} />
          <MenuItem onClick={handleLogout} sx={{ color: '#ef4444' }}>
            <Typography fontWeight="500">Sign out</Typography>
          </MenuItem>
        </Menu>

        {/* Notifications Menu (shared by desktop + mobile bells) */}
        <Menu
          anchorEl={notifAnchorEl}
          open={Boolean(notifAnchorEl)}
          onClose={handleNotifClose}
          PaperProps={{
            elevation: 0,
            sx: {
              mt: 1, borderRadius: '14px', border: '1px solid #f1f5f9',
              boxShadow: '0 20px 60px rgba(0,0,0,0.08)', minWidth: 320, maxWidth: '90vw',
              '& .MuiMenuItem-root': {
                px: 3, py: 1.5, borderRadius: '8px', mx: 1, my: 0.5,
                '&:hover': { background: '#f8fafc' },
              },
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <Box sx={{ p: 3, borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="subtitle2" fontWeight="700" sx={{ color: '#0f172a' }}>
              Notifications
            </Typography>
            {unreadCount > 0 && (
              <Typography
                component="button"
                onClick={handleNotifMarkAllRead}
                sx={{
                  border: 'none', background: 'transparent', cursor: 'pointer', p: 0,
                  fontFamily: '"Inter", sans-serif', fontSize: '0.75rem', fontWeight: 600,
                  color: '#f97316', '&:hover': { textDecoration: 'underline' },
                }}
              >
                Mark all as read
              </Typography>
            )}
          </Box>
          <Box sx={{ maxHeight: 360, overflowY: 'auto', py: 1 }}>
            {notifLoading ? (
              <Box sx={{ px: 3, py: 3, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: '#94a3b8' }}>Loading…</Typography>
              </Box>
            ) : notifications.length === 0 ? (
              <Box sx={{ px: 3, py: 3, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: '#94a3b8' }}>No notifications yet</Typography>
              </Box>
            ) : (
              notifications.map((n) => (
                <MenuItem
                  key={n.id}
                  onClick={() => {
                    if (!n.is_read) handleNotifMarkRead(n.id);
                  }}
                  sx={{
                    alignItems: 'flex-start !important',
                    background: n.is_read ? 'transparent' : '#fff7ed',
                    '&:hover': { background: n.is_read ? '#f8fafc' : '#ffedd5' },
                  }}
                >
                  <Box sx={{ display: 'flex', gap: 1.5, width: '100%' }}>
                    <Box
                      sx={{
                        width: 8, height: 8, borderRadius: '50%', mt: 0.75, flexShrink: 0,
                        background: n.is_read ? 'transparent' : '#f97316',
                      }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" fontWeight={n.is_read ? 500 : 700} sx={{ color: '#0f172a' }}>
                        {n.title}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748b', display: 'block', wordBreak: 'break-word' }}>
                        {n.message}
                      </Typography>
                      {n.created_at && (
                        <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mt: 0.5 }}>
                          {new Date(n.created_at).toLocaleString()}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </MenuItem>
              ))
            )}
          </Box>
        </Menu>

        {/* Mobile Menu */}
        <Menu
          anchorEl={mobileMenuEl}
          open={Boolean(mobileMenuEl)}
          onClose={handleMobileMenuClose}
          PaperProps={{
            elevation: 0,
            sx: {
              mt: 1, borderRadius: '14px', border: '1px solid #f1f5f9',
              boxShadow: '0 20px 60px rgba(0,0,0,0.08)', minWidth: 260, maxWidth: '90vw',
              '& .MuiMenuItem-root': {
                px: 3, py: 1.5, borderRadius: '8px', mx: 1, my: 0.5,
                '&:hover': { background: '#f8fafc' },
              },
            },
          }}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          {user ? (
            <>
              <Box sx={{ p: 3, borderBottom: '1px solid #f1f5f9' }}>
                <Box display="flex" alignItems="center" gap={2}>
                  <Avatar sx={{ width: 40, height: 40, background: 'linear-gradient(135deg, #212E46, #2c3e5a)', fontSize: '1rem', fontWeight: 'bold' }}>
                    {user?.full_name.charAt(0)}
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle2" fontWeight="600">{user?.full_name}</Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      {roleLabel(user?.role)}
                    </Typography>
                  </Box>
                </Box>
              </Box>
              {navigationItems.map((item) => (
                <MenuItem key={item.path} onClick={() => navigateToPage(item.path)}
                  sx={{ background: isActivePage(item.path) ? '#f8fafc' : 'transparent' }}
                >
                  <Typography fontWeight={isActivePage(item.path) ? 600 : 500}>{item.label}</Typography>
                </MenuItem>
              ))}
              <MenuItem onClick={toggleMode}>
                <Typography fontWeight="500">{dark ? 'Light theme' : 'Dark theme'}</Typography>
              </MenuItem>
              <MenuItem onClick={() => navigateToPage('/profile')}
                sx={{ background: isActivePage('/profile') ? '#f8fafc' : 'transparent' }}
              >
                <Typography fontWeight={isActivePage('/profile') ? 600 : 500}>My Profile</Typography>
              </MenuItem>
              <Divider sx={{ mx: 1, my: 1 }} />
              <MenuItem onClick={handleLogout} sx={{ color: '#ef4444' }}>
                <Typography fontWeight="500">Sign out</Typography>
              </MenuItem>
            </>
          ) : (
            <>
              {publicNavigationItems.map((item) => (
                <MenuItem key={item.label} onClick={() => goToSection(item.sectionId)}>
                  <Typography fontWeight="500">{item.label}</Typography>
                </MenuItem>
              ))}
              <Divider sx={{ mx: 1, my: 1 }} />
              <MenuItem onClick={() => navigateToPage('/login')}>
                <Typography fontWeight="500">Sign in</Typography>
              </MenuItem>
              <MenuItem onClick={() => navigateToPage('/register')}>
                <Typography fontWeight="600" sx={{ color: '#0f172a' }}>Get Started</Typography>
              </MenuItem>
            </>
          )}
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
