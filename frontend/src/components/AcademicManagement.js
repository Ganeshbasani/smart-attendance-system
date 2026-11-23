import React, { useCallback, useEffect, useState } from 'react';
import {
  Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, FormControlLabel, InputLabel, MenuItem, Select, Snackbar,
  Alert, Tab, Tabs, TextField, Checkbox, Typography, IconButton, Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import GroupAddIcon from '@mui/icons-material/GroupAdd';
import PersonRemoveIcon from '@mui/icons-material/PersonRemove';

import { academicAPI } from '../services/api';
import { PageHeader, DataTable, ConfirmDialog, StatusChip, ErrorBanner } from './ui';

// Single source of truth for each resource: form fields + table columns.
const RESOURCES = {
  departments: {
    label: 'Departments',
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'code', label: 'Code' },
    ],
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'code', label: 'Code' },
    ],
  },
  'academic-sessions': {
    label: 'Academic Sessions',
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'start_date', label: 'Start date', type: 'date', required: true },
      { name: 'end_date', label: 'End date', type: 'date', required: true },
      { name: 'is_active', label: 'Active', type: 'checkbox' },
    ],
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'start_date', label: 'Starts' },
      { key: 'end_date', label: 'Ends' },
      { key: 'is_active', label: 'Status', render: (r) => <StatusChip status={r.is_active ? 'Active' : 'Pending'} /> },
    ],
  },
  courses: {
    label: 'Courses',
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'code', label: 'Code', required: true },
      { name: 'department_id', label: 'Department', type: 'select', optionsKey: 'departments' },
      { name: 'credits', label: 'Credits', type: 'number' },
    ],
    columns: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'credits', label: 'Credits' },
      { key: 'department_id', label: 'Department', render: (r) => r.department_id ?? '—' },
    ],
  },
  teachers: {
    label: 'Teachers',
    fields: [
      { name: 'email', label: 'Email', type: 'email', required: true, createOnly: true },
      { name: 'password', label: 'Password', type: 'password', required: true, createOnly: true },
      { name: 'full_name', label: 'Full name', required: true },
      { name: 'employee_id', label: 'Employee ID', required: true },
      { name: 'department_id', label: 'Department', type: 'select', optionsKey: 'departments' },
    ],
    columns: [
      { key: 'employee_id', label: 'Employee ID' },
      { key: 'full_name', label: 'Name' },
      { key: 'email', label: 'Email' },
    ],
  },
  students: {
    label: 'Students',
    fields: [
      { name: 'email', label: 'Email', type: 'email', required: true, createOnly: true },
      { name: 'password', label: 'Password', type: 'password', required: true, createOnly: true },
      { name: 'full_name', label: 'Full name', required: true },
      { name: 'roll_number', label: 'Roll number', required: true },
      { name: 'department_id', label: 'Department', type: 'select', optionsKey: 'departments' },
      { name: 'academic_session_id', label: 'Academic session', type: 'select', optionsKey: 'academic-sessions' },
    ],
    columns: [
      { key: 'roll_number', label: 'Roll number' },
      { key: 'full_name', label: 'Name' },
      { key: 'email', label: 'Email' },
      { key: 'role', label: 'Role', render: (r) => <StatusChip status={r.role} /> },
    ],
  },
  classes: {
    label: 'Classes',
    fields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'code', label: 'Code', required: true },
      { name: 'level', label: 'Class / grade' },
      { name: 'section', label: 'Section' },
      { name: 'course_id', label: 'Course', type: 'select', optionsKey: 'courses' },
      { name: 'teacher_id', label: 'Teacher', type: 'select', optionsKey: 'teachers' },
      { name: 'academic_session_id', label: 'Academic session', type: 'select', optionsKey: 'academic-sessions' },
    ],
    columns: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'level', label: 'Class / grade', render: (r) => r.level || '—' },
      { key: 'section', label: 'Section', render: (r) => r.section || 'No section' },
      { key: 'student_count', label: 'Students' },
      { key: 'course_id', label: 'Course', render: (r) => r.course_id ?? '—' },
    ],
  },
};

const OPTION_KEYS = ['departments', 'academic-sessions', 'courses', 'teachers', 'students'];

const AcademicManagement = () => {
  const [active, setActive] = useState('departments');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [options, setOptions] = useState({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [toast, setToast] = useState({ open: false, message: '', severity: 'success' });
  const [enrollClass, setEnrollClass] = useState(null);
  const [enrolled, setEnrolled] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState('');
  const [organization, setOrganization] = useState({ name: '', sector: 'school', has_sections: true });
  const [savingOrganization, setSavingOrganization] = useState(false);

  const config = RESOURCES[active];

  const notify = (message, severity = 'success') => setToast({ open: true, message, severity });

  const load = useCallback(async (resource) => {
    setLoading(true);
    setError('');
    try {
      const res = await academicAPI.list(resource);
      setRows(res.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load records');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(active); }, [active, load]);

  useEffect(() => {
    academicAPI.organization().then((res) => setOrganization(res.data)).catch(() => {});
  }, []);

  const saveOrganization = async () => {
    setSavingOrganization(true);
    try {
      const res = await academicAPI.updateOrganization(organization);
      setOrganization(res.data);
      notify('Organization settings saved');
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not save organization settings', 'error');
    } finally {
      setSavingOrganization(false);
    }
  };

  const levelLabel = organization.sector === 'school' ? 'Class / grade'
    : organization.sector === 'college' ? 'Program / course group'
      : organization.sector === 'office' ? 'Department / team' : 'Group';

  useEffect(() => {
    let cancelled = false;
    Promise.all(OPTION_KEYS.map((key) => academicAPI.list(key).then((r) => [key, r.data]).catch(() => [key, []])))
      .then((pairs) => { if (!cancelled) setOptions(Object.fromEntries(pairs)); });
    return () => { cancelled = true; };
  }, [rows]);

  const openCreate = () => {
    setEditing(null);
    const defaults = {};
    config.fields.forEach((f) => {
      if (f.type === 'checkbox') defaults[f.name] = false;
      else if (f.type === 'number') defaults[f.name] = 0;
      else defaults[f.name] = '';
    });
    setForm(defaults);
    setDialogOpen(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    const initial = {};
    config.fields.filter((f) => !f.createOnly).forEach((f) => {
      initial[f.name] = row[f.name] ?? (f.type === 'checkbox' ? false : '');
    });
    setForm(initial);
    setDialogOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      config.fields.forEach((f) => {
        if (editing && f.createOnly) return;
        let value = form[f.name];
        if (f.type === 'number') value = value === '' ? 0 : Number(value);
        if (f.type === 'select') value = value === '' ? null : Number(value);
        if (value === '' && !f.required) value = null;
        payload[f.name] = value;
      });
      if (editing) await academicAPI.update(active, editing.id, payload);
      else await academicAPI.create(active, payload);
      notify(editing ? `${config.label} updated` : `${config.label} created`);
      setDialogOpen(false);
      await load(active);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not save record', 'error');
    } finally {
      setSaving(false);
    }
  };

  const performDelete = async () => {
    if (!confirm) return;
    try {
      await academicAPI.remove(active, confirm.id);
      notify(`${config.label} deleted`);
      await load(active);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not delete record', 'error');
    } finally {
      setConfirm(null);
    }
  };

  const openEnroll = async (classRow) => {
    setEnrollClass(classRow);
    setSelectedStudent('');
    try {
      const res = await academicAPI.listEnrollments(classRow.id);
      setEnrolled(res.data || []);
    } catch {
      setEnrolled([]);
    }
  };

  const enroll = async () => {
    if (!selectedStudent || !enrollClass) return;
    try {
      await academicAPI.enroll(enrollClass.id, Number(selectedStudent));
      notify('Student enrolled');
      const res = await academicAPI.listEnrollments(enrollClass.id);
      setEnrolled(res.data || []);
      await load(active);
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not enroll student', 'error');
    }
  };

  const unenroll = async (studentId) => {
    try {
      await academicAPI.unenroll(enrollClass.id, studentId);
      const res = await academicAPI.listEnrollments(enrollClass.id);
      setEnrolled(res.data || []);
      await load(active);
      notify('Student removed from class');
    } catch (e) {
      notify(e.response?.data?.detail || 'Could not remove student', 'error');
    }
  };

  const renderField = (f) => {
    const common = { label: f.label, fullWidth: true, margin: 'dense', required: f.required,
      type: f.type && ['email', 'password', 'date', 'number'].includes(f.type) ? f.type : 'text',
      value: form[f.name] ?? '',
      onChange: (e) => setForm((prev) => ({ ...prev, [f.name]: e.target.value })) };
    if (f.type === 'checkbox') {
      return (
        <FormControlLabel key={f.name} control={
          <Checkbox checked={!!form[f.name]} onChange={(e) => setForm((p) => ({ ...p, [f.name]: e.target.checked }))} />
        } label={f.label} />
      );
    }
    if (f.type === 'select') {
      return (
        <FormControl fullWidth margin="dense" key={f.name}>
          <InputLabel>{f.label}</InputLabel>
          <Select label={f.label} value={form[f.name] ?? ''}
            onChange={(e) => setForm((p) => ({ ...p, [f.name]: e.target.value }))}>
            <MenuItem value="">None</MenuItem>
            {(options[f.optionsKey] || []).map((opt) => (
              <MenuItem key={opt.id} value={opt.id}>{opt.name || opt.full_name || opt.code || `#${opt.id}`}</MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    return <TextField key={f.name} {...common} />;
  };

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <PageHeader
        title="Academic Management"
        subtitle="Set up your organization, manage classes or teams, and organize enrollments."
        actions={<Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add {config.label.replace(/s$/, '')}</Button>}
      />

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={700} gutterBottom>Organization setup</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Choose the workspace type to tailor class and group labels for attendance.
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr auto' }, gap: 1.5, alignItems: 'center' }}>
            <TextField label="Organization name" value={organization.name || ''} onChange={(e) => setOrganization((o) => ({ ...o, name: e.target.value }))} />
            <FormControl fullWidth>
              <InputLabel>Workspace type</InputLabel>
              <Select label="Workspace type" value={organization.sector || 'other'} onChange={(e) => setOrganization((o) => ({ ...o, sector: e.target.value }))}>
                <MenuItem value="school">School</MenuItem>
                <MenuItem value="college">College / university</MenuItem>
                <MenuItem value="office">Office / workplace</MenuItem>
                <MenuItem value="other">Other organization</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" onClick={saveOrganization} disabled={savingOrganization}>{savingOrganization ? 'Saving…' : 'Save setup'}</Button>
            <FormControlLabel sx={{ gridColumn: { sm: '1 / -1' } }} control={<Checkbox checked={organization.has_sections !== false} onChange={(e) => setOrganization((o) => ({ ...o, has_sections: e.target.checked }))} />} label="This organization uses sections (for example, 10-A or Biology-A)" />
          </Box>
        </CardContent>
      </Card>

      <Tabs value={active} onChange={(_, v) => setActive(v)} variant="scrollable" scrollButtons="auto"
        sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        {Object.entries(RESOURCES).map(([key, value]) => <Tab key={key} value={key} label={value.label} />)}
      </Tabs>

      <ErrorBanner error={error} onRetry={() => load(active)} />

      <DataTable
        columns={config.columns}
        rows={rows}
        loading={loading}
        emptyText={`No ${config.label.toLowerCase()} yet. Use “Add” to create one.`}
        actions={(row) => (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
            {active === 'classes' && (
              <Tooltip title="Manage students"><IconButton size="small" onClick={() => openEnroll(row)}><GroupAddIcon fontSize="small" /></IconButton></Tooltip>
            )}
            <Tooltip title="Edit"><IconButton size="small" onClick={() => openEdit(row)}><EditIcon fontSize="small" /></IconButton></Tooltip>
            <Tooltip title="Delete"><IconButton size="small" color="error" onClick={() => setConfirm(row)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
          </Box>
        )}
      />

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight="700">{editing ? `Edit ${config.label.replace(/s$/, '')}` : `New ${config.label.replace(/s$/, '')}`}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1, pt: 1 }}>
            {config.fields.filter((f) => !(active === 'classes' && f.name === 'section' && organization.has_sections === false))
              .map((f) => f.name === 'level' ? renderField({ ...f, label: levelLabel }) : renderField(f))}
          </Box>
          {editing && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
              Passwords are never changed here — use “Change password” in Settings.
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={!!confirm}
        title={`Delete ${config.label.replace(/s$/, '')}?`}
        message="This also removes the linked account and related records. This action cannot be undone."
        onConfirm={performDelete}
        onClose={() => setConfirm(null)}
      />

      {/* Class enrollment dialog */}
      <Dialog open={!!enrollClass} onClose={() => setEnrollClass(null)} maxWidth="sm" fullWidth>
        <DialogTitle fontWeight="700">Students in {enrollClass?.code || 'class'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Add student</InputLabel>
              <Select label="Add student" value={selectedStudent} onChange={(e) => setSelectedStudent(e.target.value)}>
                {(options.students || []).map((s) => <MenuItem key={s.id} value={s.id}>{s.roll_number} — {s.full_name}</MenuItem>)}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={enroll} disabled={!selectedStudent}>Enroll</Button>
          </Box>
          <Box sx={{ mt: 2 }}>
            {enrolled.length === 0 && <Typography color="text.secondary">No students enrolled yet.</Typography>}
            {enrolled.map((e) => (
              <Box key={e.id} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                py: 1, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="body2">{e.roll_number} — {e.full_name}</Typography>
                <Tooltip title="Remove"><IconButton size="small" color="error" onClick={() => unenroll(e.student_id)}><PersonRemoveIcon fontSize="small" /></IconButton></Tooltip>
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}><Button onClick={() => setEnrollClass(null)}>Close</Button></DialogActions>
      </Dialog>

      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default AcademicManagement;
