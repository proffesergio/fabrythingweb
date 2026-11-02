import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import useShopControlCenter from './useShopControlCenter';
import ShopControlCenter from './ShopControlCenter';

jest.mock('./useShopControlCenter');

const data = {
  inventory_state: 'available',
  sales_heatmap: [{ day: '2026-11-01', orders: 5, units: 7 }],
  inventory_velocity: [{ variant__product_id: 8, product_name: 'Canvas bag', units: 7, revenue: 1400 }],
  conversion_funnel: [{ stage: 'sessions', count: 100 }, { stage: 'orders', count: 4 }],
  search_gaps: [{ query: 'canvas bag', clicks: 3, impressions: 80, ctr: 0.0375 }],
  product_funnels: [{ item_id: '8', item_name: 'Canvas bag signal', views: 100, adds_to_cart: 20, checkouts: 10, purchases: 4 }],
  providers: { merchant: { state: 'completed', result: { submitted_count: 12 } }, analytics: { state: 'completed', result: { funnel: [] } }, search_console: { state: 'completed', result: { queries: [] } } },
};
const job = { id: 9, mode: 'PRICE', source_name: 'Supplier One', interval_minutes: 1440, batch_limit: 40, is_paused: false, next_run_at: '2026-11-03T01:00:00Z' };

const state = () => ({
  insights: data, jobs: [job], runs: [], loading: false, refreshing: false,
  error: null, jobsError: null, runsError: null, actionError: null,
  pendingAction: null, lastUpdatedAt: new Date('2026-11-02T10:00:00Z'),
  refresh: jest.fn(), performJobAction: jest.fn().mockResolvedValue(true),
  saveJob: jest.fn().mockResolvedValue(true),
});
let hookState;
function mount() {
  return render(<MemoryRouter><ShopControlCenter /></MemoryRouter>);
}

beforeEach(() => {
  hookState = state();
  useShopControlCenter.mockImplementation((options) => {
    if (options?.enabled === false) return { ...hookState, loading: false };
    return hookState;
  });
});

test('renders returned metrics and query gaps from the live snapshot', () => {
  mount();
  expect(screen.getByRole('heading', { name: 'Shop Control Center' })).toBeInTheDocument();
  expect(screen.getByText('5', { selector: 'strong' })).toBeInTheDocument();
  expect(screen.getByText('Canvas bag')).toBeInTheDocument();
  expect(screen.getByText('canvas bag')).toBeInTheDocument();
  expect(screen.getByText('Search Console')).toBeInTheDocument();
  expect(screen.getByText('3.75%')).toBeInTheDocument();
  expect(screen.getByText('12 products submitted · approval pending')).toBeInTheDocument();
  expect(screen.getByText('Canvas bag signal')).toBeInTheDocument();
  expect(screen.getByText('4.0%')).toBeInTheDocument();
});

test('run now queues the selected task through the API action hook', async () => {
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Run now' }));
  await waitFor(() => expect(hookState.performJobAction).toHaveBeenCalledWith(job, 'run'));
});

test('cadence changes PATCH the selected job interval', async () => {
  mount();
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Schedule Price sync' }));
  fireEvent.click(await screen.findByRole('option', { name: 'Weekly' }));
  await waitFor(() => expect(hookState.saveJob).toHaveBeenCalledWith({ interval_minutes: 10080 }, 9));
});

test('can create an analytics provider task with a real POST payload', async () => {
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Add task' }));
  fireEvent.click(screen.getByRole('button', { name: 'Create task' }));
  await waitFor(() => expect(hookState.saveJob).toHaveBeenCalledWith({
    mode: 'ANALYTICS', source: null, interval_minutes: 1440, batch_limit: 12,
  }));
});

test('demo mode is explicit and disables run controls', () => {
  mount();
  fireEvent.click(screen.getByRole('switch', { name: 'Show demo data' }));
  expect(screen.getByText('DEMO PREVIEW')).toBeInTheDocument();
  expect(screen.getByText(/Deterministic sample data/)).toBeInTheDocument();
  screen.getAllByRole('button', { name: 'Run now' }).forEach((button) => expect(button).toBeDisabled());
  expect(useShopControlCenter).toHaveBeenLastCalledWith({ enabled: false });
});

test('rejects oversized batches before creating a task', async () => {
  mount();
  fireEvent.click(screen.getByRole('button', { name: 'Add task' }));
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Batch limit' }), { target: { value: '100' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create task' }));
  expect(await screen.findByText('Batch limit must be a whole number from 1 to 12.')).toBeInTheDocument();
  expect(hookState.saveJob).not.toHaveBeenCalled();
});

test('offline state does not invent zero live metrics or provider status', () => {
  hookState = { ...hookState, insights: null, error: new Error('offline'), jobs: [], runs: [] };
  mount();
  expect(screen.getAllByText('Live metric unavailable')).toHaveLength(3);
  expect(screen.getAllByText('No status data')).toHaveLength(3);
  expect(screen.getByText('Search query data unavailable')).toBeInTheDocument();
  expect(screen.queryByText('DEMO PREVIEW')).not.toBeInTheDocument();
});
