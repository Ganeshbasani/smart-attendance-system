import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent,
  DialogTitle, Grid, MenuItem, Snackbar, Alert, TextField, Typography,
} from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ScheduleIcon from '@mui/icons-material/Schedule';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';

import { userAPI } from '../services/api';
import { useAuth } from '../App';
import { PageHeader, StatCard, DataTable, StatusChip, LoadingState, ErrorBanner } from './ui';

/** Student portal: real attendance data + real leave/correction requests. */
const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [leaveForm, setLeaveForm] = useState({ start_date: '', end_date: '', leave_type: 'annual', reason: '' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, attendanceRes, leaveRes] = await Promise.all([
        userAPI.getAttendanceStats(),
        userAPI.getAttendance(),
        userAPI.getLeaveRequests(),
      ]);
      setStats(statsRes.data?.stats || null);
      setRecords(attendanceRes.data || []);
      setLeaveRequests(leaveRes.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load your attendance data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submitLeave = async () => {
    try {
      await userAPI.createLeaveRequest(leaveForm);
      setToast({ open: true, message: 'Leave request submitted', severity: 'success' });
      setLeaveOpen(false);
      await load();
    } catch (e) {
      setToast({ open: true, message: e.response?.data?.detail || 'Could not submit request', severity: 'error' });
    }
  };

  if (loading) return <Box sx={{ p: 3 }}><LoadingState label="Loading your attendance…" /></Box>;

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <PageHeader
        title={`Welcome${user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}`}
        subtitle="Your attendance overview and requests."
        actions={
          <>
            <Button variant="outlined" onClick={() => navigate('/attendance')}>History</Button>
            <Button variant="contained" onClick={() => navigate('/mark-attendance')}>Mark attendance</Button>
          </>
        }
      />

      <ErrorBanner error={error} onRetry={load} />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Attendance" value={`${stats?.attendance_percentage ?? 0}%`}
            caption={`${stats?.present_days ?? 0} of ${stats?.total_days ?? 0} days`}
            icon={<CheckCircleOutlineIcon />} tone="success" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Present" value={stats?.present_days ?? 0} icon={<AssignmentTurnedInIcon />} tone="primary" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Absent" value={stats?.absent_days ?? 0} icon={<ReportProblemIcon />} tone="error" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard label="Open requests" value={leaveRequests.filter((r) => r.status === 'pending').length}
            icon={<ScheduleIcon />} tone="warning" />
        </Grid>
      </Grid>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Recent attendance</Typography>
          <DataTable
            dense
            columns={[
              { key: 'date', label: 'Date' },
              { key: 'time_in', label: 'In', render: (r) => r.time_in ? String(r.time_in).slice(0, 5) : '—' },
              { key: 'time_out', label: 'Out', render: (r) => r.time_out ? String(r.time_out).slice(0, 5) : '—' },
              { key: 'status', label: 'Status', render: (r) => <StatusChip status={r.status} /> },
            ]}
            rows={records.slice(0, 10)}
            emptyText="No attendance records yet."
          />
          <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
            <Button variant="outlined" size="small" onClick={() => setLeaveOpen(true)}>Request leave</Button>
            <Button variant="outlined" size="small" onClick={() => navigate('/attendance')}>Request a correction</Button>
          </Box>
        </CardContent>
      </Card>

      <Dialog open={leaveOpen} onClose={() => setLeaveOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight="700">Request leave</DialogTitle>
        <DialogContent>
          <TextField label="Start date" type="date" fullWidth margin="dense" InputLabelProps={{ shrink: true }}
            value={leaveForm.start_date} onChange={(e) => setLeaveForm((p) => ({ ...p, start_date: e.target.value }))} />
          <TextField label="End date" type="date" fullWidth margin="dense" InputLabelProps={{ shrink: true }}
            value={leaveForm.end_date} onChange={(e) => setLeaveForm((p) => ({ ...p, end_date: e.target.value }))} />
          <TextField select label="Type" fullWidth margin="dense" value={leaveForm.leave_type}
            onChange={(e) => setLeaveForm((p) => ({ ...p, leave_type: e.target.value }))}>
            <MenuItem value="annual">Annual</MenuItem><MenuItem value="sick">Sick</MenuItem><MenuItem value="other">Other</MenuItem>
          </TextField>
          <TextField label="Reason" fullWidth margin="dense" multiline minRows={2}
            value={leaveForm.reason} onChange={(e) => setLeaveForm((p) => ({ ...p, reason: e.target.value }))} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setLeaveOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submitLeave}>Submit</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default StudentDashboard;
