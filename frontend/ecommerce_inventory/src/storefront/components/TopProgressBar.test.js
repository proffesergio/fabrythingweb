import { render, screen, act } from '@testing-library/react';
import TopProgressBar from './TopProgressBar';

beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

const SLOW_COPY = /server is waking up/i;

test('renders nothing when not loading', () => {
  render(<TopProgressBar loading={false} />);
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
});

test('shows a progress bar immediately while loading', () => {
  render(<TopProgressBar loading />);
  expect(screen.getAllByRole('progressbar').length).toBeGreaterThan(0);
});

test('stays quiet about slowness for a normal-length wait', () => {
  render(<TopProgressBar loading />);
  act(() => { jest.advanceTimersByTime(1500); });
  // A 1.5s load is not worth explaining; saying "waking up" then would be noise.
  expect(screen.queryByText(SLOW_COPY)).not.toBeInTheDocument();
});

test('explains the wait once it stops looking normal', () => {
  render(<TopProgressBar loading />);
  act(() => { jest.advanceTimersByTime(5000); });
  expect(screen.getByText(SLOW_COPY)).toBeInTheDocument();
});

test('clears the slow notice when loading finishes', () => {
  const { rerender } = render(<TopProgressBar loading />);
  act(() => { jest.advanceTimersByTime(5000); });
  expect(screen.getByText(SLOW_COPY)).toBeInTheDocument();

  rerender(<TopProgressBar loading={false} />);
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  expect(screen.queryByText(SLOW_COPY)).not.toBeInTheDocument();
});

test('does not re-show the stale notice on a second, fast load', () => {
  const { rerender } = render(<TopProgressBar loading />);
  act(() => { jest.advanceTimersByTime(5000); });
  rerender(<TopProgressBar loading={false} />);
  rerender(<TopProgressBar loading />);
  // The timer restarts; a quick second fetch must not inherit the last one's
  // "waking up" message.
  expect(screen.queryByText(SLOW_COPY)).not.toBeInTheDocument();
});
