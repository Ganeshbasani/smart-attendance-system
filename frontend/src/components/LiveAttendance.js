import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box, Button, Card, CardContent, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, FormControlLabel, Grid, InputLabel, MenuItem,
  Select, Snackbar, Alert, Switch, TextField, Typography,
} from '@mui/material';
import Webcam from 'react-webcam';
import StartIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import RefreshIcon from '@mui/icons-material/Refresh';

import { sessionAPI, academicAPI } from '../services/api';
import { PageHeader, DataTable, StatusChip, LoadingState, ErrorBanner } from './ui';

const DECISIONS = ['VERIFIED', 'REVIEW_REQUIRED', 'REJECTED', 'DUPLICATE', 'MANUAL_OVERRIDE'];

/**
 * Live attendance monitor (AttendX Module 5 + 10).
 *
 * Real, wired behaviour: session create/start/stop; verification submission
 * using the CV signals produced by a scanner; polling of decisions + events;
 * reasoned review and manual override. The camera preview is live, but
 * automatic multi-face detection/tracking is a later phase — we do not fake it.
 */
const LiveAttendance = () => {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [records, setRecords] = useState([]);
  const [events, setEvents] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [createOpen, setCreateOpen] = useState(false);
  const [newSession, setNewSession] = useState({ name: '', class_section_id: '' });
  const [classes, setClasses] = useState([]);
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verify, setVerify] = useState({ user_id: '', confidence: 90, quality_score: 90,
    liveness_ok: true, spoof_suspected: false, model_version: 'buffalo_l' });
  const [reviewDialog, setReviewDialog] = useState(null);
  const [reviewText, setReviewText] = useState('');
  const [cameraOn, setCameraOn] = useState(false);
  const webcamRef = useRef(null);

  const notify = (message, severity = 'success') => setToast({ open: true, message, severity });

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await sessionAPI.list();
      setSessions(res.data || []);
      setSelected((prev) => (prev && (res.data || []).some((s) => s.id === prev.id)
        ? (res.data || []).find((s) => s.id === prev.id) : (res.data || [])[0] || null));
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSessions(); academicAPI.list('classes').then((r) => setClasses(r.data || [])).catch(() => {});
    academicAPI.list('students').then((r) => setStudents(r.data || [])).catch(() => {}); }, [loadSessions]);

  // Poll the selected session's live feed while it is active.
  useEffect(() => {
    if (!selected) return undefined;
    let cancelled = false;
    const refresh = async () => {
      try {
        const [rec, ev] = await Promise.all([
          sessionAPI.records(selected.id), sessionAPI.events(selected.id, 30),
        ]);
        if (!cancelled) { setRecords(rec.data || []); setEvents(ev.data || []); }
      } catch { /* a failed poll must never crash the monitor */ }
    };
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [selected]);

  const changeStatus = async (action) => {
    try {
      const res = await sessionAPI[action](selected.id);
      setSelected(res.data);
      notify(`Session ${action === 'start' ? 'started' : 'stopped'}`);
      await loadSessions();
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not change session', 'error');
    }
  };

  const createSession = async () => {
    try {
      const payload = { name: newSession.name };
      if (newSession.class_section_id) payload.class_section_id = Number(newSession.class_section_id);
      const res = await sessionAPI.create(payload);
      setCreateOpen(false);
      setNewSession({ name: '', class_section_id: '' });
      notify('Session created');
      await loadSessions();
      setSelected(res.data);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not create session', 'error');
    }
  };

  const submitVerification = async () => {
    try {
      await sessionAPI.submitDecision(selected.id, {
        user_id: Number(verify.user_id),
        confidence: Number(verify.confidence),
        quality_score: Number(verify.quality_score),
        liveness_ok: verify.liveness_ok,
        spoof_suspected: verify.spoof_suspected,
        model_version: verify.model_version,
      });
      setVerifyOpen(false);
      notify('Verification submitted and decision recorded');
      const [rec, ev] = await Promise.all([
        sessionAPI.records(selected.id), sessionAPI.events(selected.id, 30),
      ]);
      setRecords(rec.data || []); setEvents(ev.data || []);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not submit verification', 'error');
    }
  };

  const submitReview = async () => {
    try {
      await sessionAPI.review(selected.id, reviewDialog.user_id,
        { decision: reviewDialog.verdict || 'VERIFIED', reason: reviewText });
      setReviewDialog(null); setReviewText('');
      notify('Review recorded');
      const [rec, ev] = await Promise.all([
        sessionAPI.records(selected.id), sessionAPI.events(selected.id, 30),
      ]);
      setRecords(rec.data || []); setEvents(ev.data || []);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not record review', 'error');
    }
  };

  const counts = useMemo(() => DECISIONS.reduce((acc, d) => {
    acc[d] = records.filter((r) => r.decision === d).length; return acc;
  }, {}), [records]);

  if (loading) return <Box sx={{ p: 3 }}><LoadingState label="Loading sessions…" /></Box>;

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <PageHeader
        title="Live Attendance"
        subtitle="Run a session, record verification decisions, and review uncertain matches."
        actions={
          <>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadSessions}>Refresh</Button>
            <Button variant="contained" onClick={() => setCreateOpen(true)}>New session</Button>
          </>
        }
      />
      <ErrorBanner error={error} onRetry={loadSessions} />

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Sessions</Typography>
              {sessions.length === 0 && <Typography color="text.secondary">No sessions yet.</Typography>}
              {sessions.map((s) => (
                <Box key={s.id} onClick={() => setSelected(s)}
                  sx={{ p: 1.5, mb: 1, borderRadius: 2, cursor: 'pointer',
                    border: 1, borderColor: selected?.id === s.id ? 'primary.main' : 'divider',
                    bgcolor: selected?.id === s.id ? 'action.selected' : 'transparent' }}>
                  <Typography fontWeight="600">{s.name}</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                    <StatusChip status={s.status} />
                    <Typography variant="caption" color="text.secondary">#{s.id}</Typography>
                  </Box>
                </Box>
              ))}
            </CardContent>
          </Card>

          {selected && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" fontWeight="700">{selected.name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Status: {selected.status}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {selected.status !== 'active' && selected.status !== 'closed' && (
                    <Button variant="contained" startIcon={<StartIcon />} onClick={() => changeStatus('start')}>Start</Button>
                  )}
                  {selected.status === 'active' && (
                    <Button variant="contained" color="error" startIcon={<StopIcon />} onClick={() => changeStatus('stop')}>Stop</Button>
                  )}
                  {selected.status === 'active' && (
                    <Button variant="outlined" onClick={() => setVerifyOpen(true)}>Record verification</Button>
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>

        <Grid item xs={12} md={8}>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            {DECISIONS.map((d) => (
              <Grid item key={d} xs={6} sm={4}>
                <Card variant="outlined"><CardContent>
                  <Typography variant="caption" color="text.secondary">{d}</Typography>
                  <Typography variant="h5" fontWeight="800">{counts[d] || 0}</Typography>
                </CardContent></Card>
              </Grid>
            ))}
          </Grid>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6" fontWeight="700">Camera preview</Typography>
                <FormControlLabel control={<Switch checked={cameraOn} onChange={(e) => setCameraOn(e.target.checked)} />} label="Camera" />
              </Box>
              {cameraOn ? (
                <Webcam ref={webcamRef} audio={false} mirrored
                  screenshotFormat="image/jpeg" videoConstraints={{ facingMode: 'user' }}
                  style={{ width: '100%', maxHeight: 360, borderRadius: 12, background: '#000' }} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Enable the camera to preview the room. Automatic multi-face detection and tracking are
                  planned for a later phase; verification here uses scanner-produced signals.
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Decisions</Typography>
              <DataTable dense
                columns={[
                  { key: 'user_id', label: 'Student' },
                  { key: 'decision', label: 'Outcome', render: (r) => <StatusChip status={r.decision} /> },
                  { key: 'confidence', label: 'Confidence', render: (r) => r.confidence ?? '—' },
                  { key: 'reason', label: 'Reason' },
                ]}
                rows={records}
                emptyText="No decisions recorded in this session yet."
                actions={(row) => row.decision === 'REVIEW_REQUIRED' ? (
                  <Button size="small" onClick={() => setReviewDialog(row)}>Review</Button>
                ) : null}
              />
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight="700" sx={{ mb: 2 }}>Recent events</Typography>
              {events.length === 0 && <Typography color="text.secondary">No events yet.</Typography>}
              {events.slice(0, 12).map((e) => (
                <Box key={e.id} sx={{ display: 'flex', gap: 1, alignItems: 'center', py: 0.75, borderBottom: 1, borderColor: 'divider' }}>
                  <StatusChip status={e.decision} />
                  <Typography variant="body2" color="text.secondary">{e.reason}</Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* New session */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight="700">New attendance session</DialogTitle>
        <DialogContent>
          <TextField label="Session name" fullWidth margin="dense" value={newSession.name}
            onChange={(e) => setNewSession((p) => ({ ...p, name: e.target.value }))} />
          <FormControl fullWidth margin="dense">
            <InputLabel>Class (optional)</InputLabel>
            <Select label="Class (optional)" value={newSession.class_section_id}
              onChange={(e) => setNewSession((p) => ({ ...p, class_section_id: e.target.value }))}>
              <MenuItem value="">None</MenuItem>
              {classes.map((c) => <MenuItem key={c.id} value={c.id}>{c.code} — {c.name}</MenuItem>)}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={createSession} disabled={!newSession.name}>Create</Button>
        </DialogActions>
      </Dialog>

      {/* Verification signals */}
      <Dialog open={verifyOpen} onClose={() => setVerifyOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight="700">Record verification</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enter the signals produced by the scanner. The decision engine applies the policy
            (thresholds are configured server-side).
          </Typography>
          <FormControl fullWidth margin="dense">
            <InputLabel>Student</InputLabel>
            <Select label="Student" value={verify.user_id} onChange={(e) => setVerify((p) => ({ ...p, user_id: e.target.value }))}>
              {students.map((s) => <MenuItem key={s.user_id} value={s.user_id}>{s.roll_number} — {s.full_name}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField label="Recognition confidence (0-100)" type="number" fullWidth margin="dense"
            value={verify.confidence} onChange={(e) => setVerify((p) => ({ ...p, confidence: e.target.value }))} />
          <TextField label="Image quality (0-100)" type="number" fullWidth margin="dense"
            value={verify.quality_score} onChange={(e) => setVerify((p) => ({ ...p, quality_score: e.target.value }))} />
          <FormControlLabel control={<Switch checked={verify.liveness_ok} onChange={(e) => setVerify((p) => ({ ...p, liveness_ok: e.target.checked }))} />} label="Liveness confirmed" />
          <FormControlLabel control={<Switch checked={verify.spoof_suspected} onChange={(e) => setVerify((p) => ({ ...p, spoof_suspected: e.target.checked }))} />} label="Spoof suspected" />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setVerifyOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submitVerification} disabled={!verify.user_id}>Submit</Button>
        </DialogActions>
      </Dialog>

      {/* Review dialog */}
      <Dialog open={!!reviewDialog} onClose={() => setReviewDialog(null)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight="700">Review decision</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">{reviewDialog?.reason}</Typography>
          <TextField label="Reason for verdict" fullWidth margin="dense" multiline minRows={2}
            value={reviewText} onChange={(e) => setReviewText(e.target.value)} />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setReviewDialog(null)}>Cancel</Button>
          <Button color="error" onClick={() => { setReviewDialog((d) => ({ ...d, verdict: 'REJECTED' })); }}>Reject</Button>
          <Button variant="contained" onClick={submitReview} disabled={!reviewText}>Approve</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default LiveAttendance;
