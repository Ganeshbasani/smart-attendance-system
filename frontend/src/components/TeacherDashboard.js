import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, Grid, Typography, Snackbar, Alert, Chip,
} from '@mui/material';
import ClassIcon from '@mui/icons-material/Class';
import GroupsIcon from '@mui/icons-material/Groups';
import ScheduleIcon from '@mui/icons-material/Schedule';

import { academicAPI } from '../services/api';
import { useAuth } from '../App';
import { PageHeader, StatCard, DataTable, LoadingState, ErrorBanner } from './ui';

/**
 * Teacher portal. Shows the classes/students the backend actually exposes to
 * staff. Live session controls are intentionally absent until the attendance
 * session API exists (AttendX Phase 7) — no decorative buttons.
 */
const TeacherDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [classRes, studentRes] = await Promise.all([
        academicAPI.list('classes'),
        academicAPI.list('students'),
      ]);
      setClasses(classRes.data || []);
      setStudents(studentRes.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load your classes');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ p: 3 }}><LoadingState label="Loading your classes…" /></Box>;

  const totalEnrolled = classes.reduce((sum, c) => sum + (c.student_count || 0), 0);

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <PageHeader
        title="Teacher Portal"
        subtitle={`Signed in as ${user?.full_name || user?.email || 'teacher'}`}
        actions={<Button variant="contained" onClick={() => navigate('/mark-attendance')}>Mark attendance</Button>}
      />

      <ErrorBanner error={error} onRetry={load} />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <StatCard label="Classes" value={classes.length} icon={<ClassIcon />} tone="primary" />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard label="Students" value={students.length} icon={<GroupsIcon />} tone="info" />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard label="Class enrollments" value={totalEnrolled} icon={<ScheduleIcon />} tone="success" />
        </Grid>
      </Grid>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Assigned classes</Typography>
          <DataTable
            columns={[
              { key: 'code', label: 'Code' },
              { key: 'name', label: 'Class' },
              { key: 'student_count', label: 'Students' },
              { key: 'is_active', label: 'Status', render: () => <Chip label="Active" color="success" size="small" /> },
            ]}
            rows={classes}
            emptyText="No classes have been created yet."
          />
        </CardContent>
      </Card>

      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default TeacherDashboard;
