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
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';
import { adminAPI } from '../services/api';

const emptyShift = { name: '', start_time: '09:00', end_time: '17:00', grace_minutes: 15 };

const AdminShiftsHolidays = () => {
  const [shifts, setShifts] = useState([]);
  const [holidays, setHolidays] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [shiftDialog, setShiftDialog] = useState({ open: false, editId: null, ...emptyShift });
  const [shiftSaving, setShiftSaving] = useState(false);
  const [holidayForm, setHolidayForm] = useState({ date: '', name: '' });
  const [assignment, setAssignment] = useState({ user_id: '', shift_id: '' });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [shiftsRes, holidaysRes, usersRes] = await Promise.all([
        adminAPI.getShifts(),
        adminAPI.getHolidays(new Date().getFullYear()),
        adminAPI.getAllUsers(),
      ]);
      setShifts(shiftsRes.data || []);
      setHolidays(holidaysRes.data || []);
      setUsers(usersRes.data || []);
    } catch (err) {
      console.error('Error fetching scheduling data:', err);
      setError(err.response?.data?.detail || 'Failed to load shifts and holidays.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const flash = (message) => {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 4000);
  };

  const handleSaveShift = async () => {
    setShiftSaving(true);
    setError(null);
    try {
      const payload = {
        name: shiftDialog.name,
        start_time: shiftDialog.start_time,
        end_time: shiftDialog.end_time,
        grace_minutes: Number(shiftDialog.grace_minutes),
      };
      if (shiftDialog.editId) {
        await adminAPI.updateShift(shiftDialog.editId, payload);
        flash('Shift updated');
      } else {
        await adminAPI.createShift(payload);
        flash('Shift created');
      }
      setShiftDialog({ open: false, editId: null, ...emptyShift });
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save shift.');
    } finally {
      setShiftSaving(false);
    }
  };

  const handleDeleteShift = async (shiftId) => {
    setError(null);
    try {
      await adminAPI.deleteShift(shiftId);
      flash('Shift deleted');
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete shift.');
    }
  };

  const handleAddHoliday = async (event) => {
    event.preventDefault();
    setError(null);
    try {
      await adminAPI.createHoliday(holidayForm);
      flash('Holiday added');
      setHolidayForm({ date: '', name: '' });
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add holiday.');
    }
  };

  const handleDeleteHoliday = async (holidayId) => {
    setError(null);
    try {
      await adminAPI.deleteHoliday(holidayId);
      flash('Holiday removed');
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete holiday.');
    }
  };

  const handleAssign = async () => {
    if (!assignment.user_id) return;
    setError(null);
    try {
      await adminAPI.assignUserShift(
        assignment.user_id,
        assignment.shift_id ? Number(assignment.shift_id) : null
      );
      flash('Shift assignment saved');
      setAssignment({ user_id: '', shift_id: '' });
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign shift.');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress size={40} sx={{ color: '#212E46' }} />
      </Box>
    );
  }

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

      <Grid container spacing={3}>
        {/* Shifts */}
        <Grid item xs={12} lg={7}>
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
            <Box sx={{ p: 4, borderBottom: '2px solid #f3f4f6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                  Work Shifts
                </Typography>
                <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                  Arrival after start + grace is flagged late
                </Typography>
              </Box>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => setShiftDialog({ open: true, editId: null, ...emptyShift })}
                sx={{
                  borderRadius: '12px',
                  textTransform: 'none',
                  fontWeight: '700',
                  fontFamily: '"Inter", sans-serif',
                  background: '#212E46',
                  '&:hover': { background: '#2c3b5c' },
                }}
              >
                New Shift
              </Button>
            </Box>
            <Box sx={{ p: 3 }}>
              {shifts.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 6 }}>
                  <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', mb: 1 }}>
                    No shifts configured
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif' }}>
                    Create a shift to enable late-arrival and early-departure tracking
                  </Typography>
                </Box>
              ) : (
                <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #f3f4f6', borderRadius: '16px' }}>
                  <Table>
                    <TableHead sx={{ background: '#fafaf9' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Name</TableCell>
                        <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Window</TableCell>
                        <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Grace</TableCell>
                        <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Users</TableCell>
                        <TableCell align="right" sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {shifts.map((shift) => (
                        <TableRow key={shift.id} hover>
                          <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>
                            {shift.name}
                            {!shift.is_active && (
                              <Chip label="Inactive" size="small" sx={{ ml: 1, background: '#f3f4f6', color: '#78716c', fontWeight: 700, fontSize: '0.65rem' }} />
                            )}
                          </TableCell>
                          <TableCell sx={{ fontFamily: '"Inter", sans-serif', fontSize: '0.85rem' }}>
                            {shift.start_time.slice(0, 5)} – {shift.end_time.slice(0, 5)}
                          </TableCell>
                          <TableCell sx={{ fontFamily: '"Inter", sans-serif', fontSize: '0.85rem' }}>
                            {shift.grace_minutes} min
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`${shift.assigned_users} assigned`}
                              size="small"
                              sx={{ background: '#dbeafe', color: '#1d4ed8', fontWeight: 700, fontSize: '0.65rem' }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title="Edit">
                              <IconButton
                                size="small"
                                onClick={() =>
                                  setShiftDialog({
                                    open: true,
                                    editId: shift.id,
                                    name: shift.name,
                                    start_time: shift.start_time.slice(0, 5),
                                    end_time: shift.end_time.slice(0, 5),
                                    grace_minutes: shift.grace_minutes,
                                  })
                                }
                                sx={{ color: '#212E46', '&:hover': { background: '#f5f5f4' } }}
                              >
                                <Edit sx={{ fontSize: 18 }} />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Delete">
                              <IconButton
                                size="small"
                                onClick={() => handleDeleteShift(shift.id)}
                                sx={{ color: '#dc2626', '&:hover': { background: '#fef2f2' } }}
                              >
                                <Delete sx={{ fontSize: 18 }} />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Card>
        </Grid>

        {/* Holidays + assignment */}
        <Grid item xs={12} lg={5}>
          <Stack spacing={3}>
            <Card
              elevation={0}
              sx={{
                borderRadius: '20px',
                background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                border: '1px solid #fcd34d',
                p: 3,
              }}
            >
              <Typography variant="h6" fontWeight="800" sx={{ color: '#92400e', fontFamily: '"Inter", sans-serif', mb: 2 }}>
                Holidays ({new Date().getFullYear()})
              </Typography>
              <Typography variant="caption" sx={{ color: '#92400e', display: 'block', mb: 2, fontFamily: '"Inter", sans-serif' }}>
                Bulk absent-marking is skipped on holidays
              </Typography>
              <form onSubmit={handleAddHoliday}>
                <Stack direction="row" spacing={1} mb={2}>
                  <TextField
                    size="small"
                    type="date"
                    required
                    value={holidayForm.date}
                    onChange={(e) => setHolidayForm({ ...holidayForm, date: e.target.value })}
                    sx={{
                      flex: 1,
                      '& .MuiOutlinedInput-root': { borderRadius: '10px', background: '#ffffff', fontFamily: '"Inter", sans-serif' },
                    }}
                  />
                  <TextField
                    size="small"
                    required
                    placeholder="Holiday name"
                    value={holidayForm.name}
                    onChange={(e) => setHolidayForm({ ...holidayForm, name: e.target.value })}
                    sx={{
                      flex: 1,
                      '& .MuiOutlinedInput-root': { borderRadius: '10px', background: '#ffffff', fontFamily: '"Inter", sans-serif' },
                    }}
                  />
                  <Button
                    type="submit"
                    size="small"
                    sx={{
                      borderRadius: '10px',
                      textTransform: 'none',
                      fontWeight: 700,
                      fontFamily: '"Inter", sans-serif',
                      background: '#92400e',
                      color: '#ffffff',
                      '&:hover': { background: '#78350f' },
                    }}
                  >
                    Add
                  </Button>
                </Stack>
              </form>
              {holidays.length === 0 ? (
                <Typography variant="caption" sx={{ color: '#92400e', fontFamily: '"Inter", sans-serif' }}>
                  No holidays this year
                </Typography>
              ) : (
                <Stack spacing={1} sx={{ maxHeight: 220, overflow: 'auto' }}>
                  {holidays.map((holiday) => (
                    <Paper
                      key={holiday.id}
                      elevation={0}
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        p: 1.5,
                        borderRadius: '10px',
                        background: '#ffffff',
                        border: '1px solid #fde68a',
                      }}
                    >
                      <Box>
                        <Typography variant="body2" fontWeight="700" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
                          {holiday.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
                          {holiday.date}
                        </Typography>
                      </Box>
                      <IconButton size="small" onClick={() => handleDeleteHoliday(holiday.id)} sx={{ color: '#dc2626' }}>
                        <Delete sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Paper>
                  ))}
                </Stack>
              )}
            </Card>

            <Card
              elevation={0}
              sx={{
                borderRadius: '20px',
                background: '#ffffff',
                boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
                border: '1px solid rgba(0,0,0,0.08)',
                p: 3,
              }}
            >
              <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif', mb: 2 }}>
                Assign Shift
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <FormControl size="small" fullWidth>
                  <InputLabel sx={{ fontFamily: '"Inter", sans-serif' }}>User</InputLabel>
                  <Select
                    value={assignment.user_id}
                    label="User"
                    onChange={(e) => setAssignment({ ...assignment, user_id: e.target.value })}
                    sx={{ borderRadius: '10px', fontFamily: '"Inter", sans-serif' }}
                  >
                    {users.map((user) => (
                      <MenuItem key={user.unique_id} value={user.unique_id}>
                        {user.full_name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" fullWidth>
                  <InputLabel sx={{ fontFamily: '"Inter", sans-serif' }}>Shift</InputLabel>
                  <Select
                    value={assignment.shift_id}
                    label="Shift"
                    onChange={(e) => setAssignment({ ...assignment, shift_id: e.target.value })}
                    sx={{ borderRadius: '10px', fontFamily: '"Inter", sans-serif' }}
                  >
                    <MenuItem value="">None</MenuItem>
                    {shifts.map((shift) => (
                      <MenuItem key={shift.id} value={shift.id}>
                        {shift.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Button
                  variant="contained"
                  disabled={!assignment.user_id}
                  onClick={handleAssign}
                  sx={{
                    borderRadius: '10px',
                    textTransform: 'none',
                    fontWeight: 700,
                    fontFamily: '"Inter", sans-serif',
                    background: '#212E46',
                    '&:hover': { background: '#2c3b5c' },
                  }}
                >
                  Save
                </Button>
              </Stack>
            </Card>
          </Stack>
        </Grid>
      </Grid>

      {/* Shift create/edit dialog */}
      <Dialog
        open={shiftDialog.open}
        onClose={() => setShiftDialog({ open: false, editId: null, ...emptyShift })}
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle sx={{ fontWeight: 800, color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
          {shiftDialog.editId ? 'Edit Shift' : 'New Shift'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1, minWidth: 340 }}>
            <TextField
              label="Name"
              size="small"
              required
              value={shiftDialog.name}
              onChange={(e) => setShiftDialog({ ...shiftDialog, name: e.target.value })}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="Start"
                type="time"
                size="small"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={shiftDialog.start_time}
                onChange={(e) => setShiftDialog({ ...shiftDialog, start_time: e.target.value })}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
              />
              <TextField
                label="End"
                type="time"
                size="small"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={shiftDialog.end_time}
                onChange={(e) => setShiftDialog({ ...shiftDialog, end_time: e.target.value })}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
              />
            </Stack>
            <TextField
              label="Grace period (minutes)"
              type="number"
              size="small"
              inputProps={{ min: 0, max: 120 }}
              value={shiftDialog.grace_minutes}
              onChange={(e) => setShiftDialog({ ...shiftDialog, grace_minutes: e.target.value })}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: '12px', fontFamily: '"Inter", sans-serif' } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setShiftDialog({ open: false, editId: null, ...emptyShift })}
            sx={{ textTransform: 'none', fontWeight: 700, fontFamily: '"Inter", sans-serif', color: '#78716c' }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={shiftSaving || !shiftDialog.name}
            onClick={handleSaveShift}
            sx={{
              textTransform: 'none',
              fontWeight: 700,
              fontFamily: '"Inter", sans-serif',
              borderRadius: '10px',
              background: '#212E46',
              '&:hover': { background: '#2c3b5c' },
            }}
          >
            {shiftSaving ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
};

export default AdminShiftsHolidays;
