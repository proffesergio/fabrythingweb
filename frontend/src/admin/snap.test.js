import { readSnap, writeSnap } from './snap';
const signIn = (id) => localStorage.setItem('token', `header.${btoa(JSON.stringify({ user_id: id, exp: Date.now() / 1000 + 3600 }))}.signature`);
beforeEach(() => localStorage.clear());

test('an operator cannot read another account snapshot', () => {
  signIn(1); writeSnap('finance', { revenue: 500 });
  expect(readSnap('finance')).toEqual({ revenue: 500 });
  signIn(2); expect(readSnap('finance')).toBeNull();
  localStorage.removeItem('token'); expect(readSnap('finance')).toBeNull();
});
test('unscoped legacy snapshots and expired entries are ignored', () => {
  signIn(1);
  localStorage.setItem('finance', JSON.stringify({ at: Date.now(), data: { revenue: 900 } }));
  expect(readSnap('finance')).toBeNull();
  writeSnap('finance', { revenue: 500 });
  const key = 'admin-snap:v2:1:finance';
  const entry = JSON.parse(localStorage.getItem(key));
  localStorage.setItem(key, JSON.stringify({ ...entry, at: Date.now() - 16 * 60 * 1000 }));
  expect(readSnap('finance')).toBeNull();
});
