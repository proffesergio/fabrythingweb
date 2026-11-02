import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import useApi from '../../hooks/APIHandler';
import useShopControlCenter from './useShopControlCenter';

jest.mock('../../hooks/APIHandler');

const insights = {
  days: 30,
  inventory_state: 'available',
  inventory_velocity: [{ variant__product_id: 7, product_name: 'Field jacket', units: 12, revenue: 3600 }],
  sales_heatmap: [{ day: '2026-11-01', units: 4, orders: 3 }],
  conversion_funnel: [{ stage: 'visits', count: 100 }, { stage: 'orders', count: 8 }],
  search_gaps: null,
  sync_logs: [],
  providers: { merchant: { state: 'unconfigured' }, analytics: { state: 'completed' }, search_console: { state: 'unconfigured' } },
};
const job = { id: 11, mode: 'PRICE', source: 3, source_name: 'Fabrilife', interval_minutes: 60, batch_limit: 20, is_paused: false };

function Probe({ pollIntervalMs = 0 }) {
  const state = useShopControlCenter({ pollIntervalMs });
  return (
    <div>
      <div>{state.loading ? 'loading' : state.error ? 'insights unavailable' : `velocity:${state.insights?.inventory_velocity?.[0]?.units ?? 'none'}`}</div>
      <div>{state.jobsError ? 'jobs unavailable' : `jobs:${state.jobs.length}`}</div>
      <div>{state.insights?.providers?.merchant?.state || 'no source state'}</div>
      <button onClick={() => state.performJobAction(job, 'pause')}>Pause job</button>
      <button onClick={() => state.performJobAction(job, 'run')}>Run job</button>
      <button onClick={() => state.saveJob({ interval_minutes: 30 }, job.id)}>Reschedule</button>
      <div role="alert">{state.actionError?.message || ''}</div>
      <div>{state.pendingAction || 'idle'}</div>
    </div>
  );
}

const response = (data, status = 200) => ({ status, data: { data, message: 'ok' } });
const setupLoaded = () => {
  const calls = [];
  useApi.mockReturnValue({ callApi: jest.fn((options) => {
    calls.push(options);
    if (options.url.includes('/insights/')) return Promise.resolve(response(insights));
    if (options.url.includes('/sync-jobs/')) return Promise.resolve(response([job]));
      if (options.url.includes('/sync-runs/')) return Promise.resolve(response([]));
    return Promise.resolve(response({ id: 1 }, options.method === 'POST' && options.url.endsWith('/run/') ? 202 : 200));
  }) });
  render(<Probe />);
  return calls;
};

beforeEach(() => jest.clearAllMocks());

test('loads only live insight and sync job endpoints, with explicit provider state', async () => {
  const calls = setupLoaded();
  expect(await screen.findByText('velocity:12')).toBeInTheDocument();
  expect(screen.getByText('jobs:1')).toBeInTheDocument();
  expect(screen.getByText('unconfigured')).toBeInTheDocument();
  expect(calls.map((call) => call.url)).toEqual([
    'products/admin/insights/?days=30', 'products/admin/sync-jobs/', 'products/admin/sync-runs/',
  ]);
  expect(calls.every((call) => call.silent && call.timeout === 25000)).toBe(true);
});

test('rechecks telemetry when a hidden tab becomes visible', async () => {
  const calls = setupLoaded();
  await screen.findByText('jobs:1');
  document.dispatchEvent(new Event('visibilitychange'));
  await waitFor(() => expect(calls).toHaveLength(6));
});

test('pause and run call the real job actions; accepted run is not reported as completed', async () => {
  const calls = setupLoaded();
  await screen.findByText('jobs:1');
  fireEvent.click(screen.getByRole('button', { name: 'Pause job' }));
  await waitFor(() => expect(calls.some((call) => call.url.endsWith('/11/pause/'))).toBe(true));
  await screen.findByText('11:pause');
  await screen.findByText('idle');
  fireEvent.click(screen.getByRole('button', { name: 'Run job' }));
  await waitFor(() => expect(calls.some((call) => call.url.endsWith('/11/run/'))).toBe(true));
  const run = calls.find((call) => call.url.endsWith('/11/run/'));
  expect(run.method).toBe('POST');
  expect(screen.queryByText(/COMPLETED/)).not.toBeInTheDocument();
});

test('reschedule uses PATCH and keeps the supplied schedule payload', async () => {
  const calls = setupLoaded();
  await screen.findByText('jobs:1');
  fireEvent.click(screen.getByRole('button', { name: 'Reschedule' }));
  await waitFor(() => expect(calls.some((call) => call.method === 'PATCH')).toBe(true));
  const patch = calls.find((call) => call.method === 'PATCH');
  expect(patch.url).toBe('products/admin/sync-jobs/11/');
  expect(patch.body).toEqual({ interval_minutes: 30 });
});

test('failed reads stay visibly unavailable without substituting sample metrics', async () => {
  useApi.mockReturnValue({ callApi: jest.fn().mockResolvedValue(null) });
  render(<Probe />);
  expect(await screen.findByText('insights unavailable')).toBeInTheDocument();
  expect(screen.getByText('jobs unavailable')).toBeInTheDocument();
  expect(screen.getByText('no source state')).toBeInTheDocument();
});
