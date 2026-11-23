import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import LiveAttendance from './LiveAttendance';
import { academicAPI, sessionAPI } from '../services/api';

jest.mock('../services/api', () => ({
  academicAPI: { list: jest.fn() },
  sessionAPI: {
    list: jest.fn(), records: jest.fn(), events: jest.fn(),
    start: jest.fn(), stop: jest.fn(), create: jest.fn(),
    review: jest.fn(), manual: jest.fn(),
  },
}));

jest.mock('react-webcam', () => () => <div data-testid="camera-preview" />);

test('camera monitor identifies itself as view-only and offers no manual CV signal entry', async () => {
  sessionAPI.list.mockResolvedValue({ data: [{ id: 1, name: 'Test Session', status: 'active' }] });
  academicAPI.list.mockResolvedValue({ data: [] });
  sessionAPI.records.mockResolvedValue({ data: [] });
  sessionAPI.events.mockResolvedValue({ data: [] });
  render(<LiveAttendance />);

  await waitFor(() => expect(screen.getAllByText('Test Session').length).toBeGreaterThan(0));

  expect(await screen.findByText(/This is a view-only preview/)).toBeInTheDocument();
  expect(screen.queryByText('Record verification')).not.toBeInTheDocument();
});
