import { render, screen, fireEvent } from '@testing-library/react';
import AcademicManagement from './AcademicManagement';
import { academicAPI } from '../services/api';

jest.mock('../services/api', () => ({
  academicAPI: {
    list: jest.fn(() => Promise.resolve({ data: [] })),
    create: jest.fn(() => Promise.resolve({ data: { id: 1 } })),
    update: jest.fn(() => Promise.resolve({ data: {} })),
    remove: jest.fn(() => Promise.resolve({ data: {} })),
    listEnrollments: jest.fn(() => Promise.resolve({ data: [] })),
    enroll: jest.fn(() => Promise.resolve({ data: {} })),
    unenroll: jest.fn(() => Promise.resolve({ data: {} })),
  },
}));

describe('AcademicManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // CRA sets resetMocks: true, so implementations must be re-applied here.
    academicAPI.list.mockImplementation(() => Promise.resolve({ data: [] }));
    academicAPI.create.mockImplementation(() => Promise.resolve({ data: { id: 1 } }));
    academicAPI.update.mockImplementation(() => Promise.resolve({ data: {} }));
    academicAPI.remove.mockImplementation(() => Promise.resolve({ data: {} }));
    academicAPI.listEnrollments.mockImplementation(() => Promise.resolve({ data: [] }));
    academicAPI.enroll.mockImplementation(() => Promise.resolve({ data: {} }));
    academicAPI.unenroll.mockImplementation(() => Promise.resolve({ data: {} }));
  });

  it('renders all resource tabs and opens the create dialog', async () => {
    render(<AcademicManagement />);
    expect(screen.getByText('Academic Management')).toBeInTheDocument();
    for (const label of ['Departments', 'Academic Sessions', 'Courses', 'Teachers', 'Students', 'Classes']) {
      expect(screen.getByRole('tab', { name: label })).toBeInTheDocument();
    }
    fireEvent.click(screen.getByRole('button', { name: /Add Department/i }));
    expect(screen.getByText(/New Department/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
  });

  it('loads the active resource from the versioned API', () => {
    render(<AcademicManagement />);
    expect(academicAPI.list).toHaveBeenCalledWith('departments');
  });
});
