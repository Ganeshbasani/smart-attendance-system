import React, { useState } from 'react';
import {
  Box, Button, Card, CardContent, Divider, Grid, Snackbar, Alert,
  Switch, TextField, Typography, FormControlLabel,
} from '@mui/material';
import { useAuth } from '../App';
import { useThemeMode } from '../theme/ThemeContext';
import { userAPI } from '../services/api';
import { PageHeader } from './ui';

/** Settings page: only controls that do something real. */
const SettingsPage = () => {
  const { user, logout } = useAuth();
  const { mode, setMode } = useThemeMode();
  const [ passwords, setPasswords ] = useState({ current_password: '', new_password: '' });
  const [ savingPassword, setSavingPassword ] = useState(false);
  const [ toast, setToast ] = useState({ open: false, message: '', severity: 'success' });

  const changePassword = async () => {
    setSavingPassword(true);
    try {
      await userAPI.changePassword(passwords);
      setToast({ open: true, message: 'Password changed', severity: 'success' });
      setPasswords({ current_password: '', new_password: '' });
    } catch (e) {
      setToast({ open: true, message: e.response?.data?.detail || 'Could not change password', severity: 'error' });
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 900 }}>
      <PageHeader title="Settings" subtitle="Appearance and account security." />

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 1 }}>Appearance</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Choose how AttendX looks on this device. Your choice is saved locally.
              </Typography>
              <FormControlLabel
                control={<Switch checked={mode === 'dark'} onChange={(e) => setMode(e.target.checked ? 'dark' : 'light')} />}
                label={mode === 'dark' ? 'Dark theme' : 'Light theme'}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 1 }}>Account</Typography>
              <Typography variant="body2" color="text.secondary">Name: {user?.full_name || '—'}</Typography>
              <Typography variant="body2" color="text.secondary">Email: {user?.email || '—'}</Typography>
              <Typography variant="body2" color="text.secondary">Role: {user?.role || '—'}</Typography>
              <Divider sx={{ my: 2 }} />
              <Button variant="outlined" color="error" onClick={logout}>Sign out</Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Change password</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
                <TextField label="Current password" type="password" fullWidth
                  value={passwords.current_password}
                  onChange={(e) => setPasswords((p) => ({ ...p, current_password: e.target.value }))} />
                <TextField label="New password" type="password" fullWidth
                  value={passwords.new_password}
                  onChange={(e) => setPasswords((p) => ({ ...p, new_password: e.target.value }))} />
              </Box>
              <Button variant="contained" sx={{ mt: 2 }} onClick={changePassword} disabled={savingPassword || !passwords.current_password || !passwords.new_password}>
                {savingPassword ? 'Saving…' : 'Update password'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default SettingsPage;
