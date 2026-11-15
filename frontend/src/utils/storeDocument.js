// Keep the crawlable, styled document usable while the route chunk downloads.
// React mounts beside it, then swaps both trees in the same pre-paint commit.
// A failed script/chunk therefore leaves real product links instead of a blank page.
export function prepareStoreDocument() {
  const root = document.getElementById('root');
  if (!root?.querySelector('.store-document')) return root;
  root.id = 'store-document-fallback';
  const app = document.createElement('div');
  app.id = 'root';
  app.hidden = true;
  app.inert = true;
  root.after(app);
  return app;
}

export function completeStoreDocument() {
  const fallback = document.getElementById('store-document-fallback');
  if (!fallback) return;
  const root = document.getElementById('root');
  // All changes occur in useLayoutEffect, before the browser can paint.
  root.hidden = false;
  root.inert = false;
  fallback.remove();
  document.getElementById('store-document-style')?.remove();
  document.getElementById('store-document-schema')?.remove();
}
