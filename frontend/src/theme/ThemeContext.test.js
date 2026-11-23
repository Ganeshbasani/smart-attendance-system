import { createAppTheme } from './ThemeContext';

describe('AttendX theme', () => {
  it('builds both light and dark themes with the AttendX identity', () => {
    const light = createAppTheme('light');
    const dark = createAppTheme('dark');
    expect(light.palette.mode).toBe('light');
    expect(dark.palette.mode).toBe('dark');
    expect(light.palette.secondary.main).toBe('#f97316');
    expect(light.typography.fontFamily).toContain('Inter');
    expect(light.shape.borderRadius).toBe(12);
  });

  it('uses a dark surface palette in dark mode', () => {
    const dark = createAppTheme('dark');
    expect(dark.palette.background.default).toBe('#0f172a');
  });
});
