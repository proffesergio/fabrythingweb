import { render, screen, waitFor } from '@testing-library/react';

const mockCalls = [];
let mockListStatus = 200;

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

jest.mock('../../hooks/APIHandler', () => () => ({
  loading: false,
  error: '',
  callApi: async (opts) => {
    mockCalls.push(opts);
    if (mockListStatus !== 200) {
      // Mirrors Django's bare HTML 500 page — no envelope to read a message from.
      return { status: mockListStatus, data: '<html>Server Error (500)</html>' };
    }
    return {
      status: 200,
      data: {
        data: [
          { id: 1, name: 'Karim', rider_code: 'RD-AAA11', phone: '017', username: 'karim_rider',
            vehicle_type: 'BIKE', vehicle_number: 'DHA-1', total_deliveries: 3,
            is_available: true, is_online: true, is_verified: true },
          { id: 2, name: 'Rahim', rider_code: 'RD-BBB22', phone: '018', username: null,
            vehicle_type: 'CYCLE', vehicle_number: '', total_deliveries: 0,
            is_available: false, is_online: false, is_verified: false },
        ],
      },
    };
  },
}));

import ManageRiders from './ManageRiders';

beforeEach(() => { mockCalls.length = 0; mockListStatus = 200; });

test('lists riders with their login username', async () => {
  render(<ManageRiders />);
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
  expect(screen.getByText('karim_rider')).toBeInTheDocument();
  // A rider with no account must be visibly distinguishable.
  expect(screen.getByText('No login')).toBeInTheDocument();
});

test('distinguishes heartbeat presence from the availability switch', async () => {
  render(<ManageRiders />);
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
  expect(screen.getByText('Online')).toBeInTheDocument();   // is_online true
  expect(screen.getByText('Offline')).toBeInTheDocument();  // neither flag set
});

test('offers a button to open the rider app', async () => {
  render(<ManageRiders />);
  await waitFor(() => expect(screen.getByText('Karim')).toBeInTheDocument());
  expect(screen.getByRole('button', { name: /open rider app/i })).toBeInTheDocument();
  // The admin needs to know why the tab looks empty when they open it as themselves.
  expect(screen.getByText(/private \/ incognito window/i)).toBeInTheDocument();
});

test('surfaces a server error instead of showing an empty table', async () => {
  // Regression: callApi returns null on non-2xx, so `res?.data?.data || []`
  // rendered "No riders yet" when the API was actually 500ing on a missing
  // column. A silent empty state hid a broken deploy.
  mockListStatus = 500;
  render(<ManageRiders />);
  await waitFor(() => expect(screen.getByText(/could not load riders/i)).toBeInTheDocument());
  expect(screen.queryByText('No riders yet')).not.toBeInTheDocument();
});

test('requests the list with rawError so failures are visible', async () => {
  render(<ManageRiders />);
  await waitFor(() => expect(mockCalls.length).toBeGreaterThan(0));
  expect(mockCalls[0]).toMatchObject({ url: 'food/admin/riders/', rawError: true });
});
