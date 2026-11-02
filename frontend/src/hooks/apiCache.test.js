import { cacheKey, readCache, writeCache, isFresh, CACHE_VERSION } from './apiCache';

beforeEach(() => localStorage.clear());

test('cacheKey is stable and param-aware', () => {
  expect(cacheKey('store/homepage/')).toBe(cacheKey('store/homepage/'));
  expect(cacheKey('food/restaurants/', { zone: 1 })).not.toBe(cacheKey('food/restaurants/', { zone: 2 }));
});

test('writeCache then readCache round-trips the payload', () => {
  const key = cacheKey('store/homepage/');
  writeCache(key, { hello: 'world' });
  const entry = readCache(key);
  expect(entry.data).toEqual({ hello: 'world' });
  expect(entry.v).toBe(CACHE_VERSION);
  expect(typeof entry.ts).toBe('number');
});

test('readCache returns null for missing or wrong-version entries', () => {
  expect(readCache('swr:none')).toBeNull();
  localStorage.setItem('swr:bad', JSON.stringify({ v: 'v0', ts: 1, data: {} }));
  expect(readCache('swr:bad')).toBeNull();
});

test('isFresh respects the ttl window', () => {
  const entry = { v: CACHE_VERSION, ts: Date.now(), data: {} };
  expect(isFresh(entry, 10000)).toBe(true);
  expect(isFresh({ ...entry, ts: Date.now() - 20000 }, 10000)).toBe(false);
  expect(isFresh(entry, 0)).toBe(false); // no ttl => always revalidate
});
