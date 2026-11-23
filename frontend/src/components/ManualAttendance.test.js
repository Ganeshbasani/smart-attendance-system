import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ManualAttendance from './ManualAttendance';
import { academicAPI, sessionAPI } from '../services/api';

jest.mock('../services/api', () => ({
  academicAPI: { list: jest.fn(), previewRoster: jest.fn(), importRoster: jest.fn() },
  sessionAPI: {
    list: jest.fn(), create: jest.fn(), start: jest.fn(), roster: jest.fn(),
    saveManualAttendance: jest.fn(), stop: jest.fn(), manualReport: jest.fn(),
  },
}));

test('teacher can start roll call, mark a student present, and save the roster', async () => {
  academicAPI.list.mockResolvedValue({ data: [{ id: 3, name: 'Grade 8 · A', code: 'G8-A', student_count: 1 }] });
  sessionAPI.list.mockResolvedValue({ data: [] });
  sessionAPI.create.mockResolvedValue({ data: { id: 12, status: 'draft', attendance_mode: 'manual' } });
  sessionAPI.start.mockResolvedValue({ data: { id: 12, status: 'active', attendance_mode: 'manual' } });
  sessionAPI.roster.mockResolvedValue({ data: [{ user_id: 41, roll_number: 'ST-41', full_name: 'Sam Student', status: null }] });
  sessionAPI.saveManualAttendance.mockResolvedValue({ data: [] });

  render(<ManualAttendance />);
  fireEvent.click(await screen.findByText('Start roll call'));

  expect(await screen.findByText('Sam Student')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Present'));
  fireEvent.click(screen.getByText('Save roll call'));

  await waitFor(() => expect(sessionAPI.saveManualAttendance).toHaveBeenCalledWith(12, {
    entries: [{ user_id: 41, status: 'present' }],
  }));
});
