import { act, renderHook, waitFor } from '@testing-library/react';
import useOverview from './useOverview';
import useApi from '../../hooks/APIHandler';
import { readSnap, writeSnap } from '../snap';
jest.mock('../../hooks/APIHandler');
jest.mock('../snap', () => ({ readSnap: jest.fn(), writeSnap: jest.fn() }));
beforeEach(() => { jest.clearAllMocks(); readSnap.mockReturnValue(null); });

test('changing reporting range ignores an older in-flight response', async () => {
  const pending = [];
  const callApi = jest.fn(() => new Promise((resolve) => pending.push(resolve)));
  useApi.mockReturnValue({ callApi });
  const { result } = renderHook(() => useOverview('overview/', 'shop'));
  act(() => result.current.setDays(30));
  expect(callApi).toHaveBeenLastCalledWith(expect.objectContaining({ url: 'overview/?days=30' }));
  await act(async () => pending[1]({ status: 200, data: { data: { range: 30 } } }));
  await act(async () => pending[0]({ status: 200, data: { data: { range: 14 } } }));
  expect(result.current.data).toEqual({ range: 30 });
  expect(writeSnap).toHaveBeenCalledTimes(1);
  expect(writeSnap).toHaveBeenCalledWith('shop:30', { range: 30 });
});

test('failed first load remains unavailable and retry recovers', async () => {
  const callApi = jest.fn().mockResolvedValueOnce({ status: 503 }).mockResolvedValueOnce({ status: 200, data: { data: { orders: 4 } } });
  useApi.mockReturnValue({ callApi });
  const { result } = renderHook(() => useOverview('overview/', 'shop'));
  await waitFor(() => expect(result.current.failed).toBe(true));
  expect(result.current.data).toBeNull();
  act(() => result.current.retry());
  await waitFor(() => expect(result.current.data).toEqual({ orders: 4 }));
  expect(result.current.failed).toBe(false);
});

test('switching modules ignores the previous module response', async () => {
  const pending = [];
  useApi.mockReturnValue({ callApi: jest.fn(() => new Promise(resolve => pending.push(resolve))) });
  const { result, rerender } = renderHook(({ module }) => useOverview(module + '/', module), { initialProps: { module: 'shop' } });
  rerender({ module: 'food' });
  await act(async () => pending[1]({ status: 200, data: { data: { module: 'food' } } }));
  await act(async () => pending[0]({ status: 503 }));
  expect(result.current.data).toEqual({ module: 'food' });
  expect(result.current.failed).toBe(false);
});
