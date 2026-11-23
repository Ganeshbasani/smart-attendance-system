import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Cancel, HowToReg } from '@mui/icons-material';
import { adminAPI } from '../services/api';

const statusChip = (status) => {
  if (status === 'approved') return { background: '#dcfce7', color: '#16a34a' };
  if (status === 'rejected') return { background: '#fee2e2', color: '#dc2626' };
  return { background: '#fef3c7', color: '#d97706' };
};

const AdminRequests = () => {
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [correctionRequests, setCorrectionRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [statusFilter, setStatusFilter] = useState('pending');

  const [reviewDialog, setReviewDialog] = useState({
    open: false,
    kind: null, // 'leave' | 'correction'
    id: null,
    decision: null,
    note: '',
  });
  const [reviewSaving, setReviewSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter === 'all' ? {} : { status: statusFilter };
      const [leaveRes, correctionRes] = await Promise.all([
        adminAPI.getLeaveRequests({ ...params, limit: 100 }),
        adminAPI.getCorrectionRequests({ ...params, limit: 100 }),
      ]);
      setLeaveRequests(leaveRes.data || []);
      setCorrectionRequests(correctionRes.data || []);
    } catch (err) {
      console.error('Error fetching requests:', err);
      setError(err.response?.data?.detail || 'Failed to load requests.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const openReview = (kind, id, decision) =>
    setReviewDialog({ open: true, kind, id, decision, note: '' });

  const handleReview = async () => {
    const { kind, id, decision, note } = reviewDialog;
    if (decision === 'rejected' && !note.trim()) return;
    setReviewSaving(true);
    setError(null);
    try {
      const review =
        kind === 'leave'
          ? adminAPI.reviewLeaveRequest
          : adminAPI.reviewCorrectionRequest;
      await review(id, decision, note.trim() || null);
      setSuccess(`Request ${decision}`);
      setReviewDialog({ open: false, kind: null, id: null, decision: null, note: '' });
      setTimeout(() => setSuccess(null), 4000);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to review request.');
    } finally {
      setReviewSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress size={40} sx={{ color: '#212E46' }} />
      </Box>
    );
  }

  const pendingCount =
    leaveRequests.filter((r) => r.status === 'pending').length +
    correctionRequests.filter((r) => r.status === 'pending').length;

  return (
    <Stack spacing={3}>
      {error && (
        <Alert severity="error" sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif' }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif' }}>
          {success}
        </Alert>
      )}

      <Card
        elevation={0}
        sx={{
          borderRadius: '20px',
          background: '#ffffff',
          boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
          border: '1px solid rgba(0,0,0,0.08)',
          p: 3,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box>
          <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
            Approval Queue
          </Typography>
          <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
            {pendingCount > 0 ? `${pendingCount} pending in current view` : 'Nothing pending'}
          </Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel sx={{ fontFamily: '"Inter", sans-serif' }}>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
            sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif', background: '#fafaf9' }}
          >
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="approved">Approved</MenuItem>
            <MenuItem value="rejected">Rejected</MenuItem>
            <MenuItem value="all">All</MenuItem>
          </Select>
        </FormControl>
      </Card>

      <Grid container spacing={3}>
        {/* Leave requests */}
        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              borderRadius: '24px',
              background: '#ffffff',
              boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
              border: '1px solid rgba(0,0,0,0.08)',
              height: '100%',
            }}
          >
            <Box sx={{ p: 4, borderBottom: '2px solid #f3f4f6' }}>
              <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                Leave Requests
              </Typography>
              <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                Approved leave suppresses bulk absent-marking for those dates
              </Typography>
            </Box>
            <Box sx={{ p: 3, maxHeight: 560, overflow: 'auto' }}>
              {leaveRequests.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                    No {statusFilter === 'all' ? '' : statusFilter} leave requests
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={2}>
                  {leaveRequests.map((req) => (
                    <Paper key={req.id} elevation={0} sx={{ borderRadius: '16px', border: '1px solid #f3f4f6', p: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Box>
                          <Typography fontWeight="700" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                            {req.user?.full_name || 'Unknown user'}
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', display: 'block' }}>
                            {req.user?.email} · {req.start_date} → {req.end_date}
                          </Typography>
                        </Box>
                        <Chip
                          label={req.status}
                          size="small"
                          sx={{
                            ...statusChip(req.status),
                            fontWeight: '700',
                            fontSize: '0.65rem',
                            fontFamily: '"Inter", sans-serif',
                            textTransform: 'capitalize',
                          }}
                        />
                      </Box>
                      <Typography variant="body2" sx={{ color: '#475569', fontFamily: '"Inter", sans-serif', mb: 1 }}>
                        <Chip
                          label={req.leave_type}
                          size="small"
                          sx={{ mr: 1, background: '#ede9fe', color: '#7c3aed', fontWeight: 700, fontSize: '0.6rem', height: 20 }}
                        />
                        {req.reason || 'No reason provided'}
                      </Typography>
                      {req.review_note && (
                        <Typography variant="caption" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif', display: 'block', mb: 1 }}>
                          Review note: {req.review_note}
                        </Typography>
                      )}
                      {req.status === 'pending' && (
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<HowToReg sx={{ fontSize: 16 }} />}
                            onClick={() => openReview('leave', req.id, 'approved')}
                            sx={{
                              borderRadius: '10px',
                              textTransform: 'none',
                              fontWeight: 700,
                              fontFamily: '"Inter", sans-serif',
                              background: '#16a34a',
                              '&:hover': { background: '#15803d' },
                            }}
                          >
                            Approve
                          </Button>
                          <Button
                            size="small"
                            startIcon={<Cancel sx={{ fontSize: 16 }} />}
                            onClick={() => openReview('leave', req.id, 'rejected')}
                            sx={{
                              borderRadius: '10px',
                              textTransform: 'none',
                              fontWeight: 700,
                              fontFamily: '"Inter", sans-serif',
                              color: '#dc2626',
                              border: '1px solid #fecaca',
                              '&:hover': { background: '#fef2f2' },
                            }}
                          >
                            Reject
                          </Button>
                        </Box>
                      )}
                    </Paper>
                  ))}
                </Stack>
              )}
            </Box>
          </Card>
        </Grid>

        {/* Correction requests */}
        <Grid item xs={12} lg={6}>
          <Card
            elevation={0}
            sx={{
              borderRadius: '24px',
              background: '#ffffff',
              boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
              border: '1px solid rgba(0,0,0,0.08)',
              height: '100%',
            }}
          >
            <Box sx={{ p: 4, borderBottom: '2px solid #f3f4f6' }}>
              <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                Attendance Corrections
              </Typography>
              <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                Approval applies the proposed values to the attendance record
              </Typography>
            </Box>
            <Box sx={{ p: 3, maxHeight: 560, overflow: 'auto' }}>
              {correctionRequests.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                    No {statusFilter === 'all' ? '' : statusFilter} correction requests
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={2}>
                  {correctionRequests.map((req) => (
                    <Paper key={req.id} elevation={0} sx={{ borderRadius: '16px', border: '1px solid #f3f4f6', p: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Box>
                          <Typography fontWeight="700" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                            {req.user?.full_name || 'Unknown user'}
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', display: 'block' }}>
                            Record #{req.attendance_id} · {req.attendance?.date}
                          </Typography>
                        </Box>
                        <Chip
                          label={req.status}
                          size="small"
                          sx={{
                            ...statusChip(req.status),
                            fontWeight: '700',
                            fontSize: '0.65rem',
                            fontFamily: '"Inter", sans-serif',
                            textTransform: 'capitalize',
                          }}
                        />
                      </Box>

                      <Box sx={{ display: 'flex', gap: 2, my: 1.5, alignItems: 'center' }}>
                        <Chip
                          size="small"
                          label={`Current: ${req.attendance?.current_status}${req.attendance?.current_time_in ? ` @ ${req.attendance.current_time_in.slice(0, 5)}` : ''}`}
                          sx={{ background: '#f3f4f6', color: '#475569', fontWeight: 700, fontSize: '0.65rem', fontFamily: '"Inter", sans-serif' }}
                        />
                        <Typography sx={{ color: '#9ca3af' }}>→</Typography>
                        <Chip
                          size="small"
                          label={`Proposed: ${req.proposed_status}${req.proposed_time_in ? ` @ ${req.proposed_time_in.slice(0, 5)}` : ''}`}
                          sx={{ background: '#dbeafe', color: '#1d4ed8', fontWeight: 700, fontSize: '0.65rem', fontFamily: '"Inter", sans-serif' }}
                        />
                      </Box>

                      <Typography variant="body2" sx={{ color: '#475569', fontFamily: '"Inter", sans-serif' }}>
                        “{req.reason}”
                      </Typography>
                      {req.review_note && (
                        <Typography variant="caption" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif', display: 'block', mt: 0.5 }}>
                          Review note: {req.review_note}
                        </Typography>
                      )}
                      {req.status === 'pending' && (
                        <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<HowToReg sx={{ fontSize: 16 }} />}
                            onClick={() => openReview('correction', req.id, 'approved')}
                            sx={{
                              borderRadius: '10px',
                              textTransform: 'none',
                              fontWeight: 700,
                              fontFamily: '"Inter", sans-serif',
                              background: '#16a34a',
                              '&:hover': { background: '#15803d' },
                            }}
                          >
                            Approve & Apply
                          </Button>
                          <Button
                            size="small"
                            startIcon={<Cancel sx={{ fontSize: 16 }} />}
                            onClick={() => openReview('correction', req.id, 'rejected')}
                            sx={{
                              borderRadius: '10px',
                              textTransform: 'none',
                              fontWeight: 700,
                              fontFamily: '"Inter", sans-serif',
                              color: '#dc2626',
                              border: '1px solid #fecaca',
                              '&:hover': { background: '#fef2f2' },
                            }}
                          >
                            Reject
                          </Button>
                        </Box>
                      )}
                    </Paper>
                  ))}
                </Stack>
              )}
            </Box>
          </Card>
        </Grid>
      </Grid>

      {/* Review dialog (note required for rejection) */}
      <Dialog
        open={reviewDialog.open}
        onClose={() => setReviewDialog({ ...reviewDialog, open: false })}
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 800, color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
          {reviewDialog.decision === 'approved' ? 'Approve request' : 'Reject request'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1, minWidth: 360 }}>
            {reviewDialog.decision === 'rejected' && (
              <Alert severity="warning" sx={{ borderRadius: '10px', fontFamily: '"Inter", sans-serif' }}>
                A note is required when rejecting so the applicant knows why.
              </Alert>
            )}
            <TextField
              label={reviewDialog.decision === 'rejected' ? 'Reason (required)' : 'Note (optional)'}
              multiline
              minRows={3}
              value={reviewDialog.note}
              onChange={(e) => setReviewDialog({ ...reviewDialog, note: e.target.value })}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setReviewDialog({ ...reviewDialog, open: false })}
            sx={{ textTransform: 'none', fontWeight: 700, fontFamily: '"Inter", sans-serif', color: '#78716c' }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={
              reviewSaving ||
              (reviewDialog.decision === 'rejected' && !reviewDialog.note.trim())
            }
            onClick={handleReview}
            sx={{
              textTransform: 'none',
              fontWeight: 700,
              fontFamily: '"Inter", sans-serif',
              borderRadius: '10px',
              background: reviewDialog.decision === 'rejected' ? '#dc2626' : '#16a34a',
              '&:hover': { background: reviewDialog.decision === 'rejected' ? '#b91c1c' : '#15803d' },
            }}
          >
            {reviewSaving ? 'Saving…' : reviewDialog.decision === 'approved' ? 'Approve' : 'Reject'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
};

export default AdminRequests;
