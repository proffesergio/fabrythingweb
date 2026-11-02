import { render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import { cacheKey, writeCache } from './apiCache';
import useCachedApi from './useCachedApi';

jest.mock('axios');

beforeEach(() => { localStorage.clear(); jest.clearAllMocks(); });

function Probe({ url }) {
  const { data, loading } = useCachedApi(url);
  return <div>{loading ? 'loading' : `data:${data ? data.value : 'none'}`}</div>;
}

test('renders cached data immediately, then swaps in fresh data', async () => {
  // Seed a stale cache entry
  writeCache(cacheKey('store/homepage/'), { value: 'stale' });
  axios.get.mockResolvedValueOnce({ data: { data: { value: 'fresh' } } });

  render(<Probe url="store/homepage/" />);
  // Cached value shows synchronously (no loading flash)
  expect(screen.getByText('data:stale')).toBeInTheDocument();
  // Background revalidation replaces it
  await waitFor(() => expect(screen.getByText('data:fresh')).toBeInTheDocument());
});

test('revalidates automatically when the tab regains focus', async () => {
  writeCache(cacheKey('store/homepage/'), { value: 'stale' });
  axios.get
    .mockResolvedValueOnce({ data: { data: { value: 'fresh' } } })
    .mockResolvedValueOnce({ data: { data: { value: 'fresh2' } } });

  render(<Probe url="store/homepage/" />);
  await waitFor(() => expect(screen.getByText('data:fresh')).toBeInTheDocument());
  // Returning to the tab pulls the latest data (e.g. newly published products).
  window.dispatchEvent(new Event('focus'));
  await waitFor(() => expect(screen.getByText('data:fresh2')).toBeInTheDocument());
});

test('keeps stale cache when the network fails', async () => {
  writeCache(cacheKey('store/homepage/'), { value: 'stale' });
  axios.get.mockRejectedValueOnce(new Error('offline'));

  render(<Probe url="store/homepage/" />);
  expect(screen.getByText('data:stale')).toBeInTheDocument();
  // Still stale after the failed revalidation (data not wiped)
  await waitFor(() => expect(screen.getByText('data:stale')).toBeInTheDocument());
});
