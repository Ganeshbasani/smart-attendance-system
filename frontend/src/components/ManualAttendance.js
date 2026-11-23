import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, Grid, InputLabel, MenuItem,
  Select, Snackbar, TextField, Typography,
} from '@mui/material';
import { academicAPI, sessionAPI } from '../services/api';
import { DataTable, ErrorBanner, LoadingState, PageHeader } from './ui';

const today = () => new Date().toISOString().slice(0, 10);

export default function ManualAttendance() {
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState('');
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [roster, setRoster] = useState([]);
  const [report, setReport] = useState(null);
  const [groupBy, setGroupBy] = useState('day');
  const [attendanceDate, setAttendanceDate] = useState(today());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('');

  const loadClasses = useCallback(async () => {
    try {
      const response = await academicAPI.list('classes', { limit: 200 });
      const rows = response.data || [];
      setClasses(rows);
      setClassId((current) => current || (rows[0] ? String(rows[0].id) : ''));
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load classes');
    }
  }, []);

  const loadSessions = useCallback(async (selectedClass) => {
    if (!selectedClass) { setSessions([]); setSelected(null); setRoster([]); return; }
    try {
      const response = await sessionAPI.list({ class_section_id: Number(selectedClass), mode: 'manual' });
      const rows = response.data || [];
      setSessions(rows);
      setSelected((current) => rows.find((row) => row.id === current?.id) || rows[0] || null);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load attendance sessions');
    }
  }, []);

  useEffect(() => {
    loadClasses().finally(() => setLoading(false));
  }, [loadClasses]);

  useEffect(() => { loadSessions(classId); }, [classId, loadSessions]);

  const loadRoster = useCallback(async (session) => {
    if (!session || session.attendance_mode !== 'manual') { setRoster([]); return; }
    try {
      const response = await sessionAPI.roster(session.id);
      setRoster((response.data || []).map((row) => ({ ...row, status: row.status || '' })));
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load this class roster');
      setRoster([]);
    }
  }, []);

  useEffect(() => { loadRoster(selected); }, [selected, loadRoster]);

  const updateMark = (userId, status) => {
    setRoster((rows) => rows.map((row) => row.user_id === userId ? { ...row, status } : row));
  };

  const createSession = async () => {
    if (!classId || !attendanceDate) return;
    setSaving(true); setError('');
    try {
      const scheduled = new Date(`${attendanceDate}T09:00:00`).toISOString();
      const created = await sessionAPI.create({
        name: `Manual attendance · ${attendanceDate}`,
        class_section_id: Number(classId), mode: 'manual', scheduled_start: scheduled,
      });
      const started = await sessionAPI.start(created.data.id);
      await loadSessions(classId);
      setSelected(started.data);
      setToast('Manual roll call started');
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not start manual attendance');
    } finally { setSaving(false); }
  };

  const saveAttendance = async () => {
    setSaving(true); setError('');
    try {
      await sessionAPI.saveManualAttendance(selected.id, {
        entries: roster.map((row) => ({ user_id: row.user_id, status: row.status })),
      });
      setToast('Attendance saved');
      await loadRoster(selected);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save attendance');
    } finally { setSaving(false); }
  };

  const closeSession = async () => {
    setSaving(true); setError('');
    try {
      const response = await sessionAPI.stop(selected.id);
      setSelected(response.data);
      await loadSessions(classId);
      setToast('Roll call finalized');
    } catch (e) {
      setError(e.response?.data?.detail || 'Mark every student before finalizing');
    } finally { setSaving(false); }
  };

  const loadReport = async () => {
    if (!classId) return;
    setError('');
    try {
      const response = await sessionAPI.manualReport({
        class_section_id: Number(classId), group_by: groupBy,
        ...(startDate ? { start_date: startDate } : {}),
        ...(endDate ? { end_date: endDate } : {}),
      });
      setReport(response.data);
      setReportPeriod(response.data.groups.at(-1)?.period || '');
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load attendance report');
    }
  };

  const reportRows = useMemo(() => (report?.groups || []).map((group) => ({
    ...group, id: group.period,
    students_summary: `${group.students.length} students`,
    attendance_percentage: `${group.attendance_percentage}%`,
  })), [report]);
  const selectedReport = report?.groups?.find((group) => group.period === reportPeriod);

  const previewRoster = async () => {
    if (!uploadFile || !classId) return;
    setSaving(true); setError('');
    try {
      const response = await academicAPI.previewRoster(Number(classId), uploadFile);
      setPreview(response.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not read roster file');
    } finally { setSaving(false); }
  };

  const importRoster = async () => {
    const students = (preview?.rows || []).filter((row) => !row.errors.length).map((row) => ({
      full_name: row.full_name.trim(), roll_number: row.roll_number.trim(),
      email: row.email.trim(), phone_number: row.phone_number || null,
    }));
    if (!students.length) return;
    setSaving(true); setError('');
    try {
      const response = await academicAPI.importRoster(Number(classId), students);
      setToast(`Imported ${response.data.enrolled_students} roster entries`);
      setUploadOpen(false); setUploadFile(null); setPreview(null);
      await loadClasses();
      await loadSessions(classId);
      if (selected) await loadRoster(selected);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not import roster');
    } finally { setSaving(false); }
  };

  if (loading) return <Box sx={{ p: 3 }}><LoadingState label="Loading classes…" /></Box>;

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <PageHeader title="Manual Attendance" subtitle="Take a class roll call and review finalized day, month, or year summaries." />
      <ErrorBanner error={error} />

      {classes.length === 0 ? (
        <Alert severity="info">No classes are assigned to this account yet. Ask an administrator to create a class and add its roster.</Alert>
      ) : (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card variant="outlined"><CardContent>
              <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>Class roll call</Typography>
              <FormControl fullWidth margin="dense">
                <InputLabel>Class / section</InputLabel>
                <Select label="Class / section" value={classId} onChange={(e) => { setClassId(e.target.value); setReport(null); }}>
                  {classes.map((item) => <MenuItem key={item.id} value={String(item.id)}>
                    {[item.level, item.name, item.section ? `Section ${item.section}` : 'No section', item.code].filter(Boolean).join(' · ')}
                  </MenuItem>)}
                </Select>
              </FormControl>
              <TextField fullWidth type="date" label="Attendance date" margin="dense"
                value={attendanceDate} onChange={(e) => setAttendanceDate(e.target.value)} InputLabelProps={{ shrink: true }} />
              <Button fullWidth variant="outlined" sx={{ mt: 1 }} onClick={() => { setPreview(null); setUploadOpen(true); }} disabled={!classId}>
                Upload roster (PDF / DOCX / CSV)
              </Button>
              <Button fullWidth variant="contained" sx={{ mt: 1 }} onClick={createSession}
                disabled={!classId || !attendanceDate || saving || sessions.some((s) => s.status === 'active')
                  || !classes.find((item) => String(item.id) === String(classId))?.student_count}>
                Start roll call
              </Button>
              {!classes.find((item) => String(item.id) === String(classId))?.student_count
                && <Typography variant="caption" color="text.secondary">Add students to this class before starting attendance.</Typography>}
              <FormControl fullWidth margin="dense" sx={{ mt: 2 }}>
                <InputLabel>Existing roll call</InputLabel>
                <Select label="Existing roll call" value={selected ? String(selected.id) : ''}
                  onChange={(e) => setSelected(sessions.find((s) => s.id === Number(e.target.value)) || null)}>
                  {sessions.map((session) => <MenuItem key={session.id} value={String(session.id)}>
                    {session.name} · {session.status}
                  </MenuItem>)}
                </Select>
              </FormControl>
              {selected && <Chip sx={{ mt: 1 }} label={`Status: ${selected.status}`} color={selected.status === 'active' ? 'success' : 'default'} />}
            </CardContent></Card>
          </Grid>

          <Grid item xs={12} md={8}>
            <Card variant="outlined"><CardContent>
              <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>Student roster</Typography>
              <Alert severity="info" sx={{ mb: 2 }}>Mark every student present or absent. The session cannot be finalized with unmarked students.</Alert>
              {!selected ? <Typography color="text.secondary">Start or select a roll call to load the roster.</Typography> : (
                <>
                  {roster.map((student) => (
                    <Box key={student.user_id} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, py: 1.25, borderBottom: 1, borderColor: 'divider' }}>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography fontWeight={600}>{student.full_name}</Typography>
                        <Typography variant="body2" color="text.secondary">{student.roll_number}{student.email ? ` · ${student.email}` : ''}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
                        <Button size="small" variant={student.status === 'present' ? 'contained' : 'outlined'} color="success"
                          disabled={selected.status !== 'active'} onClick={() => updateMark(student.user_id, 'present')}>Present</Button>
                        <Button size="small" variant={student.status === 'absent' ? 'contained' : 'outlined'} color="error"
                          disabled={selected.status !== 'active'} onClick={() => updateMark(student.user_id, 'absent')}>Absent</Button>
                      </Box>
                    </Box>
                  ))}
                  {selected.status === 'active' && <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Button variant="contained" onClick={saveAttendance} disabled={saving || !roster.length || roster.some((row) => !row.status)}>Save roll call</Button>
                    <Button variant="outlined" color="primary" onClick={closeSession} disabled={saving || !roster.length || roster.some((row) => !row.status)}>Finalize day</Button>
                  </Box>}
                </>
              )}
            </CardContent></Card>
          </Grid>

          <Grid item xs={12}>
            <Card variant="outlined"><CardContent>
              <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>Attendance reports</Typography>
              <Grid container spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <Grid item xs={12} sm={3}><FormControl fullWidth size="small"><InputLabel>Group by</InputLabel>
                  <Select label="Group by" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                    <MenuItem value="day">Day</MenuItem><MenuItem value="month">Month</MenuItem><MenuItem value="year">Year</MenuItem>
                  </Select></FormControl></Grid>
                <Grid item xs={6} sm={3}><TextField fullWidth size="small" type="date" label="From" value={startDate}
                  onChange={(e) => setStartDate(e.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
                <Grid item xs={6} sm={3}><TextField fullWidth size="small" type="date" label="To" value={endDate}
                  onChange={(e) => setEndDate(e.target.value)} InputLabelProps={{ shrink: true }} /></Grid>
                <Grid item xs={12} sm={3}><Button fullWidth variant="outlined" onClick={loadReport}>Load report</Button></Grid>
              </Grid>
              {report && <DataTable dense rows={reportRows} rowKey="id" emptyText="No finalized manual sessions in this range."
                columns={[
                  { key: 'period', label: 'Period' },
                  { key: 'sessions', label: 'Sessions' },
                  { key: 'present', label: 'Present' },
                  { key: 'absent', label: 'Absent' },
                  { key: 'attendance_percentage', label: 'Attendance' },
                  { key: 'students_summary', label: 'Roster' },
                ]} />}
              {report?.groups?.length > 0 && <Box sx={{ mt: 2 }}>
                <FormControl size="small" sx={{ mb: 1, minWidth: 220 }}><InputLabel>Student detail period</InputLabel>
                  <Select label="Student detail period" value={reportPeriod} onChange={(e) => setReportPeriod(e.target.value)}>
                    {report.groups.map((group) => <MenuItem key={group.period} value={group.period}>{group.period}</MenuItem>)}
                  </Select>
                </FormControl>
                <Typography variant="subtitle1" fontWeight={700}>Student percentages · {selectedReport?.period}</Typography>
                <DataTable dense rows={selectedReport?.students || []} columns={[
                  { key: 'roll_number', label: 'Student ID' }, { key: 'full_name', label: 'Student' },
                  { key: 'present', label: 'Present' }, { key: 'absent', label: 'Absent' },
                  { key: 'attendance_percentage', label: 'Attendance %', render: (row) => `${row.attendance_percentage}%` },
                ]} emptyText="No student attendance data." />
              </Box>}
            </CardContent></Card>
          </Grid>
        </Grid>
      )}
      <Dialog open={uploadOpen} onClose={() => { setUploadOpen(false); setPreview(null); }} maxWidth="md" fullWidth>
        <DialogTitle>Import class roster</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Choose a text-based PDF, DOCX table, or CSV with Student ID/Roll Number, Full Name, and Email columns.
            The file is parsed for preview and is not stored. Scanned image-only PDFs need OCR and are not supported.
          </Typography>
          <input aria-label="Roster file" type="file" accept=".pdf,.docx,.csv"
            onChange={(event) => { setUploadFile(event.target.files?.[0] || null); setPreview(null); }} />
          <Button sx={{ ml: 1 }} variant="outlined" onClick={previewRoster} disabled={!uploadFile || saving}>Preview</Button>
          {preview && <>
            <Typography sx={{ my: 1 }}>Rows found: {preview.count} · Ready to import: {preview.valid_count}</Typography>
            <DataTable dense rows={preview.rows.map((row, index) => ({ ...row, id: `${row.line}-${index}` }))}
              columns={[
                { key: 'line', label: 'Row' }, { key: 'roll_number', label: 'Student ID' },
                { key: 'full_name', label: 'Name' }, { key: 'email', label: 'Email' },
                { key: 'already_in_system', label: 'Existing', render: (row) => row.already_in_system ? 'Yes' : 'New' },
                { key: 'errors', label: 'Validation', render: (row) => row.errors.join('; ') || 'Ready' },
              ]} />
            {preview.valid_count > 0 && <Alert severity="warning" sx={{ mt: 1 }}>
              New student accounts are created inactive because this roster contains no login credentials. An administrator must set up access separately.
            </Alert>}
          </>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setUploadOpen(false); setPreview(null); }}>Cancel</Button>
          <Button variant="contained" onClick={importRoster} disabled={!preview?.valid_count || saving}>Import valid rows</Button>
        </DialogActions>
      </Dialog>
      <Snackbar open={!!toast} autoHideDuration={3500} onClose={() => setToast('')}>
        <Alert severity="success" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  );
}
