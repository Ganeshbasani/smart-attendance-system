import React from 'react';
import {
  Box, Typography, Button, Card, CardContent, Chip, CircularProgress,
  IconButton, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Dialog, DialogTitle, DialogContent, DialogContentText,
  DialogActions, Paper,
} from '@mui/material';
import { InboxOutlined } from '@mui/icons-material';

/** Consistent page title + optional action buttons. */
export function PageHeader({ title, subtitle, actions }) {
  return (
    <Box sx={{ display: 'flex', alignItems: { xs: 'flex-start', sm: 'center' },
      justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, mb: 3 }}>
      <Box>
        <Typography variant="h4" fontWeight="800" sx={{ fontFamily: '"Inter", sans-serif' }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {actions && <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>{actions}</Box>}
    </Box>
  );
}

/** Metric card used across dashboards. `tone` maps to a MUI palette color. */
export function StatCard({ label, value, caption, icon, tone = 'primary' }) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="body2" color="text.secondary" fontWeight="600">{label}</Typography>
            <Typography variant="h4" fontWeight="800" sx={{ mt: 1, fontFamily: '"Inter", sans-serif' }}>
              {value}
            </Typography>
            {caption && <Typography variant="caption" color="text.secondary">{caption}</Typography>}
          </Box>
          {icon && (
            <Box sx={{ p: 1.2, borderRadius: 3, display: 'grid', placeItems: 'center',
              color: (t) => (t.palette.mode === 'dark' ? '#fff' : (t.palette[tone]?.dark || '#212E46')),
              bgcolor: (t) => (t.palette[tone]?.main || '#1976d2'),
              opacity: 0.85 }}>
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

const STATUS_TONES = {
  present: 'success', verified: 'success', approved: 'success', active: 'success',
  late: 'warning', pending: 'warning', review: 'warning', review_required: 'warning',
  absent: 'error', rejected: 'error', denied: 'error', duplicate: 'error',
  student: 'info', teacher: 'primary', admin: 'secondary',
};

export function StatusChip({ status }) {
  const key = String(status || '').toLowerCase().replace(/[\s-]+/g, '_');
  const tone = STATUS_TONES[key] || 'default';
  return <Chip label={status ?? '—'} size="small" color={tone} sx={{ fontWeight: 700 }} />;
}

export function LoadingState({ label = 'Loading…' }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, py: 6 }}>
      <CircularProgress size={22} />
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}

export function EmptyState({ message = 'Nothing here yet', action }) {
  return (
    <Box sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
      <InboxOutlined sx={{ fontSize: 44, opacity: 0.5 }} />
      <Typography sx={{ mt: 1 }}>{message}</Typography>
      {action && <Box sx={{ mt: 2 }}>{action}</Box>}
    </Box>
  );
}

/** Inline error banner — keeps failures visible and actionable. */
export function ErrorBanner({ error, onRetry }) {
  if (!error) return null;
  return (
    <Box sx={{ mb: 2, p: 1.5, borderRadius: 2, bgcolor: 'error.main', color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
      <Typography variant="body2">{error}</Typography>
      {onRetry && <Button size="small" onClick={onRetry} sx={{ color: '#fff' }}>Retry</Button>}
    </Box>
  );
}

/** Accessible confirm dialog for destructive actions. */
export function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', onConfirm, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle fontWeight="700">{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" color="error" onClick={onConfirm}>{confirmLabel}</Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Lightweight data table: columns = [{ key, label, render?, width? }].
 * Handles loading, empty, and error states so every management screen is
 * consistent without repeating table boilerplate.
 */
export function DataTable({ columns, rows, loading, emptyText, rowKey = 'id', actions, dense }) {
  if (loading) return <LoadingState />;
  if (!rows?.length) return <EmptyState message={emptyText || 'No records found'} />;
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3 }}>
      <Table size={dense ? 'small' : 'medium'}>
        <TableHead>
          <TableRow>
            {columns.map((c) => <TableCell key={c.key} sx={{ fontWeight: 700 }}>{c.label}</TableCell>)}
            {actions && <TableCell align="right" sx={{ fontWeight: 700 }}>Actions</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row[rowKey] ?? row.id} hover>
              {columns.map((c) => (
                <TableCell key={c.key}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</TableCell>
              ))}
              {actions && <TableCell align="right">{actions(row)}</TableCell>}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export { IconButton };
