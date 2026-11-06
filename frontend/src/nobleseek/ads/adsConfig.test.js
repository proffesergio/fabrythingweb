import { loadAdSense, shouldSuppressAds } from './adsConfig';

test.each(['/','/shop','/product/phone','/food','/checkout','/admin','/nobleseek-other','/blogger'])('suppresses ads on %s', path => {
  expect(shouldSuppressAds(path)).toBe(true);
});

test.each(['/nobleseek','/nobleseek/story','/blog','/blog/buying-guide'])('allows editorial ads on %s', path => {
  expect(shouldSuppressAds(path)).toBe(false);
});

test('does not load the advertising script outside editorial pages', async () => {
  window.history.replaceState({}, '', '/shop');
  expect(await loadAdSense('ca-pub-1234567890123456')).toBe(false);
  expect(document.querySelector('script[data-ns-adsense]')).toBeNull();
});
