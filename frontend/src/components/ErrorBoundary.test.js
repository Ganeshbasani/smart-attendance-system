import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

// A component that throws during render — the boundary must catch it.
const Bomb = () => {
  throw new Error('boom');
};

describe('ErrorBoundary', () => {
  let consoleErrorSpy;

  beforeAll(() => {
    // Silence React's deliberate-crash logging so test output stays clean.
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    consoleErrorSpy.mockRestore();
  });

  it('shows the styled fallback instead of crashing the app', () => {
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument();
  });

  it('renders children normally when nothing throws', () => {
    render(
      <ErrorBoundary>
        <div>All good</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('All good')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });
});
