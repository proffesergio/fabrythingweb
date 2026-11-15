import React, { act, Suspense, lazy, useLayoutEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { prepareStoreDocument, completeStoreDocument } from './storeDocument';

beforeAll(() => { global.IS_REACT_ACT_ENVIRONMENT = true; });
afterAll(() => { delete global.IS_REACT_ACT_ENVIRONMENT; });
afterEach(() => { delete window.__fabStoreBoot; });

test('styled product document survives a delayed route and is replaced only when its content commits', async () => {
  document.head.innerHTML = '<style id="store-document-style">.store-document{color:navy}</style><script id="store-document-schema" type="application/ld+json">{}</script>';
  document.body.innerHTML = '<div id="root"><main class="store-document"><h1>Real product</h1><a href="/shop">Shop</a></main></div>';
  let resolve;
  const Route = lazy(() => new Promise(r => { resolve = r; }));
  function Ready() { useLayoutEffect(completeStoreDocument, []); return null; }
  const reactRoot = createRoot(prepareStoreDocument());
  // Raw createRoot needs act; this is not Testing Library's auto-wrapped render.
  // eslint-disable-next-line testing-library/no-unnecessary-act
  await act(async () => reactRoot.render(<Suspense fallback={<p>Loading route</p>}><Route/><Ready/></Suspense>));
  expect(document.querySelector('#store-document-fallback a')).toHaveAttribute('href', '/shop');
  expect(document.getElementById('store-document-style')).not.toBeNull();
  expect(document.getElementById('root').hidden).toBe(true);
  await act(async () => resolve({default: () => <main><h1>Interactive product</h1></main>}));
  expect(document.getElementById('store-document-fallback')).toBeNull();
  expect(document.getElementById('store-document-style')).toBeNull();
  expect(document.getElementById('root').hidden).toBe(false);
  expect(document.querySelector('#root h1').textContent).toBe('Interactive product');
  act(() => reactRoot.unmount());
});

test('ordinary SPA routes remain visible and do not remove unrelated styles', () => {
  document.head.innerHTML = '<style id="other-style">body{margin:0}</style>';
  document.body.innerHTML = '<div id="root"></div>';
  const root = document.getElementById('root');
  expect(prepareStoreDocument()).toBe(root);
  completeStoreDocument();
  expect(root.hidden).toBe(false);
  expect(document.getElementById('other-style')).not.toBeNull();
});

test('a late React commit leaves the catalog stable after a failed or timed-out bootstrap', () => {
  document.head.innerHTML = '<style id="store-document-style">.store-document{color:navy}</style>';
  document.body.innerHTML = '<div id="root"><main class="store-document"><h1>Real product</h1></main></div>';
  window.__fabStoreBoot = {finish: () => false};
  prepareStoreDocument();
  completeStoreDocument();
  expect(document.getElementById('root').hidden).toBe(true);
  expect(document.querySelector('#store-document-fallback h1').textContent).toBe('Real product');
  expect(document.getElementById('store-document-style')).not.toBeNull();
});
