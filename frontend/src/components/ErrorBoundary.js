import React from 'react';
import { Box, Button, Typography } from '@mui/material';

/**
 * Catches render-time crashes anywhere in the tree and shows a styled
 * fallback instead of a white screen. The error is logged to the console
 * for debugging; technical details are never shown to the user.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Application error:', error, info?.componentStack);
  }

  handleReload = () => {
    window.location.href = '/';
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        px={3}
        textAlign="center"
        sx={{ background: 'linear-gradient(135deg, #f5f3f0 0%, #fafaf9 50%, #ffffff 100%)' }}
      >
        <Typography
          variant="h4"
          fontWeight="800"
          gutterBottom
          sx={{ color: '#212E46', fontFamily: '"Inter", sans-serif' }}
        >
          Something went wrong
        </Typography>
        <Typography
          variant="body1"
          sx={{ color: '#78716c', maxWidth: 480, mb: 4, fontFamily: '"Inter", sans-serif' }}
        >
          An unexpected error interrupted this page. Your data is unaffected —
          reload to return to the home page.
        </Typography>
        <Button
          variant="contained"
          onClick={this.handleReload}
          sx={{
            borderRadius: '12px',
            textTransform: 'none',
            fontWeight: 700,
            px: 4,
            background: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)',
            boxShadow: 'none',
            fontFamily: '"Inter", sans-serif',
            '&:hover': { background: 'linear-gradient(135deg, #ea580c 0%, #f97316 100%)', boxShadow: 'none' },
          }}
        >
          Reload
        </Button>
      </Box>
    );
  }
}

export default ErrorBoundary;
