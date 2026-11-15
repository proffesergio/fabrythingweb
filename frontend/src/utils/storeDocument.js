// The head bootstrap keeps the catalog out of normal first paint. React mounts
// beside it and replaces the loading state only when the real route commits.
// Script failures/no-JS keep the catalog usable instead of stranding a loader.
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
  if (window.__fabStoreBoot?.finish() === false) return;
  const root = document.getElementById('root');
  // All changes occur in useLayoutEffect, before the browser can paint.
  root.hidden = false;
  root.inert = false;
  fallback.remove();
  document.getElementById('store-document-style')?.remove();
  document.getElementById('store-document-schema')?.remove();
  document.getElementById('store-document-loader')?.remove();
  document.getElementById('store-document-fallback-note')?.remove();
  document.getElementById('store-document-startup-style')?.remove();
}
