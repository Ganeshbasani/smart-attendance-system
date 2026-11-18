import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  TextField,
  Alert,
  CircularProgress,
  LinearProgress,
  Stack,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from '@mui/material';
import { Edit } from '@mui/icons-material';
import { userAPI } from '../services/api';

const statusChipStyle = (status) => {
  if (status === 'approved') return { background: '#dcfce7', color: '#16a34a' };
  if (status === 'rejected') return { background: '#fee2e2', color: '#dc2626' };
  return { background: '#fef3c7', color: '#d97706' };
};

const UserAttendance = () => {
  const [user, setUser] = useState(null);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filter states
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  // Correction request states
  const [corrections, setCorrections] = useState([]);
  const [correctionDialog, setCorrectionDialog] = useState({
    open: false,
    record: null,
    proposed_status: 'present',
    proposed_time_in: '09:00',
    reason: '',
  });
  const [correctionSaving, setCorrectionSaving] = useState(false);
  const [correctionError, setCorrectionError] = useState('');
  const [correctionBanner, setCorrectionBanner] = useState(null);

  const fetchCorrections = async () => {
    try {
      const response = await userAPI.getCorrectionRequests();
      setCorrections(response.data || []);
    } catch (err) {
      console.error('Failed to fetch correction requests:', err);
    }
  };

  const openCorrection = (record) => {
    setCorrectionError('');
    setCorrectionDialog({
      open: true,
      record,
      proposed_status: record.status === 'present' ? 'absent' : 'present',
      proposed_time_in: record.time_in ? record.time_in.slice(0, 5) : '09:00',
      reason: '',
    });
  };

  const handleCorrectionSubmit = async () => {
    setCorrectionError('');
    if (!correctionDialog.reason.trim()) {
      setCorrectionError('Please explain what needs correcting.');
      return;
    }
    setCorrectionSaving(true);
    try {
      await userAPI.createCorrectionRequest({
        attendance_id: correctionDialog.record.id,
        proposed_status: correctionDialog.proposed_status,
        proposed_time_in:
          correctionDialog.proposed_status === 'present'
            ? correctionDialog.proposed_time_in
            : null,
        reason: correctionDialog.reason.trim(),
      });
      setCorrectionDialog({ ...correctionDialog, open: false, reason: '' });
      setCorrectionBanner({ type: 'success', text: 'Correction request submitted for review.' });
      await fetchCorrections();
    } catch (err) {
      setCorrectionError(err.response?.data?.detail || 'Failed to submit correction request.');
    } finally {
      setCorrectionSaving(false);
    }
  };

  useEffect(() => {
    fetchAttendanceData();
    fetchAttendanceStats();
    fetchCorrections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchAttendanceData = async (filters = {}) => {
    try {
      setLoading(true);
      const response = await userAPI.getAttendance(filters);
      setUser(response.data.user);
      setAttendanceRecords(response.data.attendance_records);
    } catch (error) {
      setError('Failed to load attendance data');
      console.error('Attendance fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAttendanceStats = async (month = selectedMonth, year = selectedYear) => {
    try {
      const response = await userAPI.getAttendanceStats({ month, year });
      setStats(response.data.stats);
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
  };

  const handleFilterApply = () => {
    const filters = {};
    if (startDate) filters.start_date = startDate;
    if (endDate) filters.end_date = endDate;
    
    fetchAttendanceData(filters);
  };

  const handleStatsFilter = () => {
    fetchAttendanceStats(selectedMonth, selectedYear);
  };

  if (loading && !attendanceRecords.length) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px" sx={{ background: 'linear-gradient(135deg, #f5f3f0 0%, #fafaf9 50%, #ffffff 100%)' }}>
          <CircularProgress sx={{ color: '#f97316' }} />
        </Box>
      </Container>
    );
  }

  return (
    <Box sx={{ background: 'linear-gradient(135deg, #f5f3f0 0%, #fafaf9 50%, #ffffff 100%)', minHeight: '100vh', py: 4 }}>
      <Container maxWidth="lg">
        {/* Header */}
        <Card elevation={0} sx={{ p: 4, mb: 4, borderRadius: '20px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
          <Box display="flex" alignItems="center" mb={2}>
            <Typography variant="h5" fontWeight="700" sx={{ fontFamily: '"Inter", sans-serif', color: '#212E46' }}>
              My Attendance
            </Typography>
          </Box>
          
          {user && (
            <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
              Welcome back, {user.full_name}! Here's your attendance overview.
            </Typography>
          )}
        </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: '12px', border: '1px solid #fecaca', background: '#fef2f2', fontFamily: '"Inter", sans-serif' }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', transition: 'all 0.3s ease', '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 24px rgba(0,0,0,0.08)' } }}>
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box>
                    <Typography variant="h5" fontWeight="700" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                      {stats.total_days}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#78716c', fontWeight: '600', fontFamily: '"Inter", sans-serif' }}>
                      Total Days
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', transition: 'all 0.3s ease', '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 24px rgba(0,0,0,0.08)' } }}>
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box sx={{ width: 48, height: 48, borderRadius: '12px', background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#16a34a' }} />
                  </Box>
                  <Box>
                    <Typography variant="h5" fontWeight="700" sx={{ color: '#16a34a', fontFamily: '"Inter", sans-serif' }}>
                      {stats.present_days}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#78716c', fontWeight: '600', fontFamily: '"Inter", sans-serif' }}>
                      Present Days
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', transition: 'all 0.3s ease', '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 24px rgba(0,0,0,0.08)' } }}>
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" gap={2}>
                  <Box sx={{ width: 48, height: 48, borderRadius: '12px', background: '#fecaca', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Box sx={{ width: 12, height: 12, borderRadius: '50%', background: '#dc2626' }} />
                  </Box>
                  <Box>
                    <Typography variant="h5" fontWeight="700" sx={{ color: '#dc2626', fontFamily: '"Inter", sans-serif' }}>
                      {stats.absent_days}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#78716c', fontWeight: '600', fontFamily: '"Inter", sans-serif' }}>
                      Absent Days
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={0} sx={{ borderRadius: '18px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)', transition: 'all 0.3s ease', '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 24px rgba(0,0,0,0.08)' } }}>
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" gap={2} mb={1}>
                  <Box>
                    <Typography variant="h5" fontWeight="700" sx={{ color: '#f97316', fontFamily: '"Inter", sans-serif' }}>
                      {stats.attendance_percentage}%
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#78716c', fontWeight: '600', fontFamily: '"Inter", sans-serif' }}>
                      Attendance Rate
                    </Typography>
                  </Box>
                </Box>
                <LinearProgress variant="determinate" value={stats.attendance_percentage} sx={{ height: 6, borderRadius: 3, background: '#f3f4f6', '& .MuiLinearProgress-bar': { borderRadius: 3, background: 'linear-gradient(90deg, #f97316 0%, #fb923c 100%)' } }} />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Card elevation={0} sx={{ p: 4, mb: 4, borderRadius: '20px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3, fontFamily: '"Inter", sans-serif', fontWeight: '700', color: '#212E46' }}>
          Filters
        </Typography>
        
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              type="date"
              label="Start Date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif', '&.Mui-focused fieldset': { borderColor: '#f97316' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#f97316' } }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              type="date"
              label="End Date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif', '&.Mui-focused fieldset': { borderColor: '#f97316' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#f97316' } }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={2}>
            <Button
              variant="contained"
              onClick={handleFilterApply}
              fullWidth
              sx={{ py: 1.5, borderRadius: '12px', background: 'linear-gradient(135deg, #212E46 0%, #2c3e5a 100%)', textTransform: 'none', fontWeight: '700', fontFamily: '"Inter", sans-serif', boxShadow: 'none', '&:hover': { background: 'linear-gradient(135deg, #1a2333 0%, #212E46 100%)', boxShadow: 'none' } }}
            >
              Apply Filter
            </Button>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Box display="flex" gap={1} alignItems="center">
              <TextField
                select
                label="Month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                SelectProps={{ native: true }}
                size="small"
                sx={{ minWidth: 100, '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif', '&.Mui-focused fieldset': { borderColor: '#f97316' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#f97316' } }}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i + 1} value={i + 1}>
                    {new Date(0, i).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </TextField>
              
              <TextField
                select
                label="Year"
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                SelectProps={{ native: true }}
                size="small"
                sx={{ minWidth: 100, '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif', '&.Mui-focused fieldset': { borderColor: '#f97316' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#f97316' } }}
              >
                {Array.from({ length: 5 }, (_, i) => {
                  const year = new Date().getFullYear() - 2 + i;
                  return (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  );
                })}
              </TextField>
              
              <Button
                variant="outlined"
                onClick={handleStatsFilter}
                size="small"
                sx={{ borderRadius: '12px', border: '2px solid #e7e5e4', color: '#78716c', textTransform: 'none', fontWeight: '700', fontFamily: '"Inter", sans-serif', '&:hover': { border: '2px solid #d6d3d1', background: '#fafaf9' } }}
              >
                Update Stats
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Card>

      {/* Attendance Records Table */}
      <Card elevation={0} sx={{ borderRadius: '20px', background: '#ffffff', border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
        <Box p={4}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h6" sx={{ fontFamily: '"Inter", sans-serif', fontWeight: '700', color: '#212E46' }}>
              Attendance Records ({attendanceRecords.length} records)
            </Typography>
            {attendanceRecords.length > 0 && (
              <Button
                variant="contained"
                onClick={() => {
                  const csv = [
                    ['Date', 'Time In', 'Status', 'Recorded At'],
                    ...attendanceRecords.map(record => [
                      new Date(record.date).toLocaleDateString(),
                      record.time_in || '-',
                      record.status,
                      new Date(record.created_at).toLocaleString(),
                    ])
                  ].map(row => row.join(',')).join('\n');
                  
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `attendance-${new Date().toISOString().split('T')[0]}.csv`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                }}
                sx={{
                  borderRadius: '12px',
                  textTransform: 'none',
                  fontWeight: '700',
                  fontFamily: '"Inter", sans-serif',
                  background: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)',
                  boxShadow: 'none',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #ea580c 0%, #f97316 100%)',
                    boxShadow: 'none',
                  },
                }}
              >
                Export CSV
              </Button>
            )}
          </Box>
          
          {loading ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress sx={{ color: '#f97316' }} />
            </Box>
          ) : attendanceRecords.length === 0 ? (
            <Box textAlign="center" p={4}>
              <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                No attendance records found for the selected period.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ background: '#fafaf9' }}>
                    <TableCell sx={{ fontWeight: '700', color: '#212E46', fontFamily: '"Inter", sans-serif' }}>Date</TableCell>
                    <TableCell sx={{ fontWeight: '700', color: '#212E46', fontFamily: '"Inter", sans-serif' }}>Time In</TableCell>
                    <TableCell sx={{ fontWeight: '700', color: '#212E46', fontFamily: '"Inter", sans-serif' }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: '700', color: '#212E46', fontFamily: '"Inter", sans-serif' }}>Recorded At</TableCell>
                    <TableCell sx={{ fontWeight: '700', color: '#212E46', fontFamily: '"Inter", sans-serif' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {attendanceRecords.map((record) => (
                    <TableRow key={record.id} hover sx={{ '&:hover': { background: '#fafaf9' } }}>
                      <TableCell sx={{ fontFamily: '"Inter", sans-serif', color: '#212E46' }}>
                        {new Date(record.date).toLocaleDateString('en-US', {
                          weekday: 'short',
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </TableCell>
                      <TableCell sx={{ fontFamily: '"Inter", sans-serif', color: '#212E46' }}>
                        {record.time_in ? 
                          new Date(`2000-01-01T${record.time_in}`).toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit'
                          }) : 
                          '-'
                        }
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={record.status.charAt(0).toUpperCase() + record.status.slice(1)}
                          sx={{ background: record.status === 'present' ? '#dcfce7' : '#fecaca', color: record.status === 'present' ? '#16a34a' : '#dc2626', fontWeight: '700', fontFamily: '"Inter", sans-serif' }}
                          size="small"
                        />
                      </TableCell>
                      <TableCell sx={{ fontFamily: '"Inter", sans-serif', color: '#78716c' }}>
                        {new Date(record.created_at).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          startIcon={<Edit sx={{ fontSize: 15 }} />}
                          onClick={() => openCorrection(record)}
                          sx={{
                            textTransform: 'none',
                            fontWeight: 700,
                            fontSize: '0.75rem',
                            fontFamily: '"Inter", sans-serif',
                            color: '#212E46',
                            border: '1px solid #e7e5e4',
                            borderRadius: '8px',
                            '&:hover': { background: '#fafaf9', border: '1px solid #d6d3d1' },
                          }}
                        >
                          Correct
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      </Card>

      {/* My correction requests */}
      <Card elevation={0} sx={{ mt: 3, borderRadius: '20px', border: '1px solid #e7e5e4', background: '#ffffff' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif', mb: 0.5 }}>
            My Correction Requests
          </Typography>
          <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', display: 'block', mb: 2 }}>
            An administrator must approve a request before your record changes
          </Typography>
          {correctionBanner && (
            <Alert
              severity={correctionBanner.type}
              onClose={() => setCorrectionBanner(null)}
              sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif', mb: 2 }}
            >
              {correctionBanner.text}
            </Alert>
          )}
          {corrections.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif' }}>
              No correction requests yet.
            </Typography>
          ) : (
            <Stack spacing={1.5}>
              {corrections.map((req) => (
                <Box
                  key={req.id}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    border: '1px solid #f3f4f6',
                    borderRadius: '12px',
                    p: 2,
                    gap: 2,
                    flexWrap: 'wrap',
                  }}
                >
                  <Box sx={{ flex: 1, minWidth: 220 }}>
                    <Typography variant="body2" fontWeight="700" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                      {req.attendance?.date} — {req.attendance?.current_status}
                      {req.attendance?.current_time_in ? ` @ ${req.attendance.current_time_in.slice(0, 5)}` : ''}
                      {' → '}
                      {req.proposed_status}
                      {req.proposed_time_in ? ` @ ${req.proposed_time_in.slice(0, 5)}` : ''}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', display: 'block' }}>
                      {req.reason}
                    </Typography>
                    {req.review_note && (
                      <Typography variant="caption" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif', display: 'block' }}>
                        Review note: {req.review_note}
                      </Typography>
                    )}
                  </Box>
                  <Chip
                    label={req.status}
                    size="small"
                    sx={{
                      ...statusChipStyle(req.status),
                      fontWeight: 700,
                      fontSize: '0.65rem',
                      fontFamily: '"Inter", sans-serif',
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      {/* Correction request dialog */}
      <Dialog
        open={correctionDialog.open}
        onClose={() => setCorrectionDialog({ ...correctionDialog, open: false })}
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 800, color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
          Request Attendance Correction
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1, minWidth: 380 }}>
            {correctionError && (
              <Alert severity="error" sx={{ borderRadius: '10px', fontFamily: '"Inter", sans-serif' }}>
                {correctionError}
              </Alert>
            )}
            {correctionDialog.record && (
              <Alert severity="info" sx={{ borderRadius: '10px', fontFamily: '"Inter", sans-serif' }}>
                Record: {correctionDialog.record.date} — currently{' '}
                {correctionDialog.record.status}
                {correctionDialog.record.time_in
                  ? ` @ ${correctionDialog.record.time_in.slice(0, 5)}`
                  : ''}
              </Alert>
            )}
            <FormControl size="small" fullWidth>
              <InputLabel sx={{ fontFamily: '"Inter", sans-serif' }}>Proposed status</InputLabel>
              <Select
                value={correctionDialog.proposed_status}
                label="Proposed status"
                onChange={(e) =>
                  setCorrectionDialog({ ...correctionDialog, proposed_status: e.target.value })
                }
                sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif' }}
              >
                <MenuItem value="present">Present</MenuItem>
                <MenuItem value="absent">Absent</MenuItem>
              </Select>
            </FormControl>
            {correctionDialog.proposed_status === 'present' && (
              <TextField
                label="Proposed time in"
                type="time"
                size="small"
                InputLabelProps={{ shrink: true }}
                value={correctionDialog.proposed_time_in}
                onChange={(e) =>
                  setCorrectionDialog({ ...correctionDialog, proposed_time_in: e.target.value })
                }
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
              />
            )}
            <TextField
              label="Reason (required)"
              multiline
              minRows={3}
              value={correctionDialog.reason}
              onChange={(e) => setCorrectionDialog({ ...correctionDialog, reason: e.target.value })}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setCorrectionDialog({ ...correctionDialog, open: false })}
            sx={{ textTransform: 'none', fontWeight: 700, fontFamily: '"Inter", sans-serif', color: '#78716c' }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={correctionSaving}
            onClick={handleCorrectionSubmit}
            sx={{
              textTransform: 'none',
              fontWeight: 700,
              fontFamily: '"Inter", sans-serif',
              borderRadius: '10px',
              background: '#212E46',
              '&:hover': { background: '#2c3b5c' },
            }}
          >
            {correctionSaving ? 'Submitting…' : 'Submit Request'}
          </Button>
        </DialogActions>
      </Dialog>
      </Container>
    </Box>
  );
};

export default UserAttendance; 