import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  FormControl,
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
import { Refresh } from '@mui/icons-material';
import { adminAPI } from '../services/api';
import { format, parseISO } from 'date-fns';

const PAGE_SIZE = 25;

// Known actions grouped for the filter and chip colors. Anything outside
// these groups still renders — the list is display-only, not a whitelist.
const ACTION_OPTIONS = [
  'auth.register',
  'auth.login',
  'attendance.mark',
  'attendance.mark_present',
  'attendance.mark_absent_bulk',
  'attendance.update',
  'attendance.bulk_update',
  'face.register',
  'face.delete',
  'face.bulk_delete',
  'user.delete',
];

const chipStyle = (action) => {
  if (action.startsWith('auth')) return { background: '#dbeafe', color: '#1d4ed8' };
  if (action.startsWith('attendance')) return { background: '#dcfce7', color: '#16a34a' };
  if (action.startsWith('face')) return { background: '#ede9fe', color: '#7c3aed' };
  if (action.startsWith('user')) return { background: '#fee2e2', color: '#dc2626' };
  return { background: '#f3f4f6', color: '#475569' };
};

const formatDetails = (details) => {
  if (!details) return '—';
  return Object.entries(details)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ');
};

const AdminAuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({
    action: '',
    start_date: '',
    end_date: '',
  });

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
      if (filters.action) params.action = filters.action;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      const response = await adminAPI.getAuditLogs(params);
      setLogs(response.data || []);
      setTotal(parseInt(response.headers['x-total-count'] || '0', 10));
    } catch (err) {
      console.error('Error fetching audit logs:', err);
      setError(
        err.response?.data?.detail ||
          'Failed to load audit logs. Please try again.'
      );
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleFilterChange = (key) => (event) => {
    setFilters((prev) => ({ ...prev, [key]: event.target.value }));
    setPage(0);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: '24px',
        background: '#ffffff',
        boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
        border: '1px solid rgba(0,0,0,0.08)',
      }}
    >
      <Box sx={{ p: 4, borderBottom: '2px solid #f3f4f6' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h6" fontWeight="800" sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}>
              Audit Logs
            </Typography>
            <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
              {total} recorded actions — authentication, attendance edits, and face management
            </Typography>
          </Box>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchLogs} sx={{ color: '#78716c', '&:hover': { background: '#fafaf9' } }}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel sx={{ fontFamily: '"Inter", sans-serif' }}>Action</InputLabel>
            <Select
              value={filters.action}
              label="Action"
              onChange={handleFilterChange('action')}
              sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif', background: '#fafaf9' }}
            >
              <MenuItem value="">All actions</MenuItem>
              {ACTION_OPTIONS.map((action) => (
                <MenuItem key={action} value={action}>
                  {action}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            type="date"
            label="From"
            value={filters.start_date}
            onChange={handleFilterChange('start_date')}
            InputLabelProps={{ shrink: true }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '12px',
                background: '#fafaf9',
                fontFamily: '"Inter", sans-serif',
              },
            }}
          />
          <TextField
            size="small"
            type="date"
            label="To"
            value={filters.end_date}
            onChange={handleFilterChange('end_date')}
            InputLabelProps={{ shrink: true }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '12px',
                background: '#fafaf9',
                fontFamily: '"Inter", sans-serif',
              },
            }}
          />
        </Stack>
      </Box>

      {error && (
        <Box sx={{ p: 3, pb: 0 }}>
          <Alert severity="error" sx={{ borderRadius: '12px', fontFamily: '"Inter", sans-serif' }}>
            {error}
          </Alert>
        </Box>
      )}

      <Box sx={{ p: 3 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress size={40} sx={{ color: '#212E46' }} />
          </Box>
        ) : logs.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="body1" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif', mb: 1 }}>
              No audit entries found
            </Typography>
            <Typography variant="caption" sx={{ color: '#9ca3af', fontFamily: '"Inter", sans-serif' }}>
              {filters.action || filters.start_date || filters.end_date
                ? 'Try adjusting your filters'
                : 'Actions performed by administrators will appear here'}
            </Typography>
          </Box>
        ) : (
          <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #f3f4f6', borderRadius: '16px' }}>
            <Table>
              <TableHead sx={{ background: '#fafaf9' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Time</TableCell>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Actor</TableCell>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Action</TableCell>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Target</TableCell>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>Details</TableCell>
                  <TableCell sx={{ fontWeight: '700', fontFamily: '"Inter", sans-serif' }}>IP</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id} hover>
                    <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: '"Inter", sans-serif', fontSize: '0.85rem' }}>
                      {log.created_at
                        ? format(parseISO(log.created_at), 'MMM d, yyyy HH:mm:ss')
                        : '—'}
                    </TableCell>
                    <TableCell sx={{ fontFamily: '"Inter", sans-serif', fontSize: '0.85rem' }}>
                      {log.actor_email || 'Anonymous'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.action}
                        size="small"
                        sx={{
                          ...chipStyle(log.action),
                          fontWeight: '700',
                          fontSize: '0.65rem',
                          fontFamily: '"Inter", sans-serif',
                          '& .MuiChip-label': { px: 1.5 },
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {log.entity_type
                        ? `${log.entity_type}${log.entity_id ? ` #${log.entity_id}` : ''}`
                        : '—'}
                    </TableCell>
                    <TableCell
                      sx={{
                        fontFamily: '"Inter", sans-serif',
                        fontSize: '0.8rem',
                        color: '#78716c',
                        maxWidth: 280,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {formatDetails(log.details)}
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#9ca3af' }}>
                      {log.ip_address || '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      {!loading && total > PAGE_SIZE && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 4, pb: 4 }}>
          <Typography variant="caption" sx={{ color: '#78716c', fontFamily: '"Inter", sans-serif' }}>
            Page {page + 1} of {totalPages} · {total} entries
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              sx={{
                borderRadius: '10px',
                textTransform: 'none',
                fontWeight: '700',
                fontFamily: '"Inter", sans-serif',
                color: '#212E46',
                border: '1px solid #e7e5e4',
              }}
            >
              Previous
            </Button>
            <Button
              size="small"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              sx={{
                borderRadius: '10px',
                textTransform: 'none',
                fontWeight: '700',
                fontFamily: '"Inter", sans-serif',
                color: '#ffffff',
                background: '#212E46',
                '&:hover': { background: '#2c3b5c' },
              }}
            >
              Next
            </Button>
          </Stack>
        </Box>
      )}
    </Card>
  );
};

export default AdminAuditLogs;
